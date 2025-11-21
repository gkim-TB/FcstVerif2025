# fcstverif/utils/general_utils.py

import os
import xarray as xr
import pandas as pd
import calendar
import numpy as np
from typing import Optional

#from fcstverif.config import *
import logging
from fcstverif.src.utils.logging_utils import init_logger, get_logger
logger = logging.getLogger("fcstverif")

def parse_var_level(v: str):
    import re
    m = re.match(r'([A-Za-z]+)(\d+)$', v)
    return (m.group(1), int(m.group(2))) if m else (v, None)

# def generate_yyyymm_list(verify_start, verify_end) -> list[str]:
#     return pd.date_range(start=f"{verify_start}01", end=f"{verify_end}01", freq="MS").strftime("%Y%m").tolist()

def generate_yyyymm_list(verify_start, verify_end):
    """
    Build a month list between start and end (inclusive) in 'YYYYMM' format.

    Parameters
    ----------
    verify_start : int | str
        Either 6 digits (YYYYMM) or 8 digits (YYYYMMDD).
    verify_end   : int | str
        Either 6 digits (YYYYMM) or 8 digits (YYYYMMDD).

    Returns
    -------
    list[str]
        ['YYYYMM', 'YYYYMM', ...] including both endpoints.
    """
    def norm_yyyymm(x):
        s = str(x).strip()
        if not s.isdigit():
            raise ValueError("Expected numeric YYYYMM or YYYYMMDD.")
        if len(s) == 8:
            s = s[:6]  # YYYYMMDD -> YYYYMM
        elif len(s) != 6:
            raise ValueError("Length must be 6 (YYYYMM) or 8 (YYYYMMDD).")
        # Basic month sanity check
        mm = int(s[4:6])
        if not (1 <= mm <= 12):
            raise ValueError("Month must be in 1..12.")
        return s

    from fcstverif.config import verify_start, verify_end

    s = norm_yyyymm(verify_start)
    e = norm_yyyymm(verify_end)

    rng = pd.date_range(start=f"{s}01", end=f"{e}01", freq="MS")
    return rng.strftime("%Y%m").tolist()

def load_obs_data(var, years, obs_dir, suffix='anom', var_suffix=None):
    """
    관측자료를 연도별로 불러와 concat.
    suffix: 'anom', 'cate', 'std' 등 파일 유형 지정
    var_suffix: 파일 내 변수명이 다를 경우 직접 지정 (예: 't2m_obs_cate')
    """
    data_list = []
    for y in years:
        fpath = os.path.join(obs_dir, f"{var}_{suffix}_{y}.nc")
        if os.path.isfile(fpath):
            ds = xr.open_dataset(fpath)
            # --- Defensive: drop known problematic coords/vars that prevent concat ---
            # Many ERA5/OISST files sometimes include 'expver' or other scalar coords.
            # Remove them if present (errors='ignore' keeps this safe).
            for bad in ("expver",):
                if bad in ds.coords or bad in ds.data_vars:
                    try:
                        ds = ds.drop_vars(bad, errors="ignore")
                        logger.debug(f"[LOAD_OBS] dropped coord/var '{bad}' from {os.path.basename(fpath)}")
                    except Exception as e:
                        logger.warning(f"[LOAD_OBS] failed to drop '{bad}' from {fpath}: {e}")


            data_list.append(ds)
    if not data_list:
        raise FileNotFoundError(f"[OBS] No {suffix} files found for var={var}, years={years}")
    
    ds_all = xr.concat(data_list, dim='time')
    if var_suffix:
        return ds_all[var_suffix]
    else:
        return ds_all[var]  # 변수명이 var와 동일한 경우
    
def ensure_time_from_lead(da: xr.DataArray, init_yyyymm: int) -> xr.DataArray:
    """If DA has 'lead' but no 'time', convert lead=1..N to target monthly time."""
    if "time" in da.dims: 
        return da
    if "lead" not in da.dims:
        raise ValueError("DataArray has neither 'time' nor 'lead'.")
    init_ts = pd.to_datetime(str(init_yyyymm) + "01", format="%Y%m%d")
    tgt_times = pd.date_range(init_ts + pd.offsets.MonthBegin(1), periods=da.sizes["lead"], freq="MS")
    return da.assign_coords(time=("lead", tgt_times)).swap_dims({"lead": "time"})

def match_common_times_by_month(fc_times, obs_times):
    """
    Return (fc_idx, ob_idx, common_time) where month(YYYY-MM) matches exactly.
    보간 없이 월 교집합만 사용.
    """
    fc = pd.to_datetime(fc_times); ob = pd.to_datetime(obs_times)
    fc_lab = fc.to_period("M").astype(str); ob_lab = ob.to_period("M").astype(str)
    common = np.intersect1d(fc_lab, ob_lab)
    if common.size == 0:
        return [], [], pd.DatetimeIndex([])
    fc_idx = [int(np.where(fc_lab == m)[0][0]) for m in common]
    ob_idx = [int(np.where(ob_lab == m)[0][0]) for m in common]
    common_time = pd.to_datetime(common + "-01")
    return fc_idx, ob_idx, common_time

def get_region_extent(region_name: str, var: str):
    """
    Return region extent with optional variable-specific override
    """
    from fcstverif.config import REGIONS, REGION_OVERRIDE_BY_VAR

    if var in REGION_OVERRIDE_BY_VAR and region_name in REGION_OVERRIDE_BY_VAR[var]:
        logger.debug("GL extent changed for sst")
        return REGION_OVERRIDE_BY_VAR[var][region_name]
    return REGIONS[region_name]  

def clip_to_region(obj, region, var:str):
    """
    obj: xr.DataArray or xr.Dataset
    region_name: key into REGIONS giving (lonL_raw, lonR_raw, latS, latN)
    var : variable name

    동작:
     - region이 (0,360) 또는 (-180,180)일 때: 경도 전체 사용(=경도 슬라이스 건너뜀), 위도만 자름
     - 그 외: 경도 체계(0-360 vs -180-180)에 상관없이 안전하게 슬라이스(래핑 포함)
    """

    if isinstance(region, str):
        region_box = get_region_extent(region, var)
    elif isinstance(region, (list, tuple, np.ndarray)):
        if len(region) != 4:
            raise ValueError("region must be 4-element sequence [lonL, lonR, latS, latN]")
        region_box = region
    else:
        raise TypeError("region must be either a region name (str) or a 4-element sequence")

    lonL_raw, lonR_raw, latS, latN = region_box

    # 좌표 이름 추론
    lon_name = "lon"  if "lon"  in obj.coords else ("longitude" if "longitude" in obj.coords else None)
    lat_name = "lat"  if "lat"  in obj.coords else ("latitude"  if "latitude"  in obj.coords else None)
    if lon_name is None or lat_name is None:
        raise ValueError("clip_to_region: lon/lat 좌표를 찾을 수 없습니다.")

    # 데이터셋 경도 체계 파악
    lon_vals = obj[lon_name].values
    use_0360 = (np.nanmin(lon_vals) >= 0.0) and (np.nanmax(lon_vals) <= 360.0)

    # 전체 경도 사용 조건
    if (np.isclose(lonL_raw, 0.0) and np.isclose(lonR_raw, 360.0)) or \
       (np.isclose(lonL_raw, -180.0) and np.isclose(lonR_raw, 180.0)):
        clipped = obj.sel({lat_name: slice(latS, latN)})
        return clipped.sortby(lon_name)
    # region 경도를 데이터셋 체계로 변환
    def to_ds_lon(x):
        return (x % 360.0) if use_0360 else (( (x + 180.0) % 360.0 ) - 180.0)
    lonL = float(to_ds_lon(lonL_raw))
    lonR = float(to_ds_lon(lonR_raw))

    # 위도 슬라이스
    clipped = obj.sel({lat_name: slice(latS, latN)})

    # 경도 슬라이스(날짜변경선 래핑 지원)
    if lonL <= lonR:
        clipped = clipped.sel({lon_name: slice(lonL, lonR)})
    else:
        # wrap: [lonL..max] + [min..lonR]
        part1 = clipped.sel({lon_name: slice(lonL, float(np.nanmax(lon_vals)))})
        part2 = clipped.sel({lon_name: slice(float(np.nanmin(lon_vals)), lonR)})
        clipped = xr.concat([part1, part2], dim=lon_name)

    # 경도 정렬 보장
    clipped = clipped.sortby(lon_name)
    logger.debug(f"Check dataArray over selected region: {clipped}")
    return clipped

def convert_prcp_to_mm_per_day(da: xr.DataArray, source: str, stat_type: Optional[str] = None):
    """
    강수량 DataArray를 mm/day 단위로 변환
    - source='ERA5': 단위 m (월별 적산) -> mm/day
    - source='GS6': 단위 kg m-2 s-1 (flux) -> mm/day
    """
    if source == 'ERA5':
        # m/day -> mm/day
        return da * 1000 
    elif source == 'GS6':
        if stat_type=='qntl':
            days_in_month = da['time'].dt.days_in_month
            da_out = da / days_in_month
            da_out.attrs['units'] = 'mm/day'
            return da_out
        else:
            # kg/m2/s = mm/s 이므로 86400초 곱해서 mm/day
            return  da * 86400 
    else:
        raise ValueError(f"Unknown precipitation source: {source}")

def convert_geopotential_to_m(da, source, ):
    """
    지위(geopotential)를 m(geopotential height)로 변환
    - source='ERA5': 단위 m2/s2 -> m  (divide by g)
    - source='GS6' : 단위 gpm (geopotential meter) -> m  (1:1)
    """
    g = 9.80665
    if source == 'ERA5':
        return da / g
    elif source == 'GS6':
        # 이미 gpm 단위 → 그대로 m으로 해석
        return da
    else:
        raise ValueError(f"Unknown geopotential source: {source}")

def get_combined_mask(mask_path: str = None):
    """ 
    - mask_path: 직접 경로 지정 가능. None이면 config.model_out_dir/MASK/lsmask.nc 를 사용.
    - 반환값: DataArray (bool) 또는 None (파일이 없을 경우)
    """
    from fcstverif.config import model_out_dir

    if mask_path is None:
        mask_path = os.path.join(model_out_dir, "MASK", "lsmask.nc")

    if not os.path.exists(mask_path):
        logger.warning(f"get_combined_mask: mask file not found at {mask_path}. Returning None.")
        return None

    try:
        ds = xr.open_dataset(mask_path)
    except Exception as e:
        logger.error(f"get_combined_mask: failed to open {mask_path}: {e}")
        return None

  
    mask = ds["lsmask_bool"].astype(bool)
    return mask


def generate_target_grid(
    data:xr.DataArray=None,
    nc_file:Optional[str]=None
    ):
    """
    Generate and save a target grid netCDF (lat, lon).
    Accepts either:
      - data : xarray.Dataset or xarray.DataArray containing lat/lon coords
      - nc_file : path to a netCDF to open and extract lat/lon
      - lat, lon : numpy arrays or xarray.DataArray directly
    Save lat/lon grid to a NetCDF file for later use in reanalysis interpolation
    """
    from fcstverif.config import model_out_dir
    if data is None:
        if nc_file is None:
            raise ValueError("Either data or nc_file must be provided.")
        if not os.path.isfile(nc_file):
            logger.error(f"Input netCDF file not found: {nc_file}")
            return
        with xr.open_dataset(nc_file) as ds:
            data = ds

    grid_ds = xr.Dataset({"lat": data["lat"], "lon": data["lon"]})
    output_path =f"{model_out_dir}/target_grid.nc"
    grid_ds.to_netcdf(output_path)
    logger.info(f"[SAVED] Target grid → {model_out_dir}/target_grid.nc")
    
def generate_lsmask_grid(
    data: xr.DataArray=None,
    nc_file:Optional[str]=None,
    var_name: str = "sst"
    ):
    """
    Generate and save a lsmask netCDF from sst variable of <model_name>.
    Accepts either:
      - data : xarray.Dataset or xarray.DataArray containing lat/lon coords
      - nc_file : path to a netCDF to open and extract lat/lon

    Save lsmask to a NetCDF file for later use
    Minimal LSMASK generator (two outputs):
      - lsmask_bool : bool (ocean=True, land=False)
    
    output path : MODEL_OUT/<model_name>/MASK/lsmask.nc
    """
    from fcstverif.config import model_out_dir

    if data is None:
        if nc_file is None:
            raise ValueError("Either data or nc_file must be provided.")
        if not os.path.isfile(nc_file):
            logger.error(f"Input netCDF file not found: {nc_file}")
            return
        with xr.open_dataset(nc_file) as ds:
            da = ds[var_name] if var_name in ds.data_vars else ds[list(ds.data_vars)[0]]
            sel = {}
            for d in ("ens", "init", "lead", "member", "time"):
                if d in da.dims:
                    sel[d] = 0
            if sel:
                da2d = da.isel(**sel).squeeze(drop=True).load()
            else:
                da2d = da.squeeze(drop=True).load()

    else:
        if isinstance(data, xr.Dataset):
            try:
                da = data[var_name]
            except KeyError:
                logger.info(f"generate_lsmask_grid: var '{var_name}' not in provided Dataset.")
        else:
            da = data

        sel = {}
        for d in ("ens", "init", "lead", "member", "time"):
            if d in da.dims:
                sel[d] = 0
        if sel:
            da2d = da.isel(**sel).squeeze(drop=True).load()
        else:
            da2d = da.squeeze(drop=True).load()

    logger.debug(da2d)

    # boolean mask: True = ocean (value present), False = land (NaN)
    mask_bool = (~da2d.isnull()).astype("bool")
    mask_bool.name = "lsmask_bool"
    mask_bool.attrs["description"] = "boolean: True=ocean (data present), False=land (NaN in sst)"
    
    # remove unnecessary coordinates
    for c in ("init", "lead", "time", "ens", "member"):
        if c in mask_bool.coords:
            mask_bool = mask_bool.reset_coords(c, drop=True)
    
    ds_out = xr.Dataset({"lsmask_bool": mask_bool})

    # 저장
    outdir = os.path.join(model_out_dir, "MASK")
    os.makedirs(outdir, exist_ok=True)
    save_path = os.path.join(outdir, f"lsmask.nc")

    ds_out.to_netcdf(save_path)
    logger.info(f"[SAVED] LSMASK -> {save_path}")