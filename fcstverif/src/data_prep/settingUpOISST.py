import os
import xarray as xr
from fcstverif.config import *

from fcstverif.src.utils.general_utils import (
    generate_target_grid
)

import logging
logger = logging.getLogger("fcstverif")

def make_lsmask_from_sst_interp_isel0(sst_interp: xr.DataArray, outpath: str=None, overwrite: bool=True):
    """
    sst_interp: regridded OISST on target grid (dims include time, lat, lon)
    outpath: 저장경로. None이면 model_out_dir/MASK/lsmask.nc 로 저장
    """
    if outpath is None:
        outpath = os.path.join(model_out_dir, "MASK", "lsmask.nc")
    os.makedirs(os.path.dirname(outpath), exist_ok=True)

    # 1) 대표 시점(isel time=0)으로 마스크 생성
    mask = (~sst_interp.isel(time=0).isnull()).astype(bool).squeeze(drop=True)

    # 2) 좌표명 표준화 (latitude -> lat, longitude -> lon 등)
    rename_map = {}
    for c in list(mask.coords):
        cl = c.lower()
        if cl.startswith("latitude") and c != "lat":
            rename_map[c] = "lat"
        if cl.startswith("longitude") and c != "lon":
            rename_map[c] = "lon"
    if rename_map:
        mask = mask.rename(rename_map)

    # 3) lat/lon 외 coords 제거
    for c in list(mask.coords):
        if c not in ("lat", "lon"):
            try:
                mask = mask.reset_coords(c, drop=True)
            except Exception:
                # 제거 불가능한 경우 무시하고 계속 진행
                pass

    # 4) 메타/타입 정리
    mask = mask.astype(bool).squeeze(drop=True)
    mask.name = "lsmask_bool"
    mask.attrs["description"] = "boolean: True=ocean (data present), False=land (NaN in sst) -- derived from sst_interp.isel(time=0)"
    mask.attrs.pop("coordinates", None)

    # 5) 저장 (uint8로 저장하여 용량 절감)
    ds_out = mask.to_dataset()
    encoding = {mask.name: {"dtype": "uint8"}}
    ds_out.to_netcdf(outpath, mode="w" if overwrite else "a", format="NETCDF4", encoding=encoding)
    return outpath

def oisst_anomaly(regrid_option=None):
    os.makedirs(sst_out_dir, exist_ok=True)

    if regrid_option == 'y':

        logger.info("Starting OISST regrid ...")
        gridfile = os.path.join(model_out_dir, "target_grid.nc")
        if not os.path.exists(gridfile):
            logger.warning(f"Target grid file not found: {gridfile}")
            logger.info("Creating target grid ...")
            generate_target_grid(
            nc_file=f"{model_out_dir}/hindcast/ensMem_{var}_anom_{fyears[0]}.nc"
        )
            return 
        with xr.open_dataset(gridfile) as target:
            lat = target.lat
            lon = target.lon

        logger.debug(lat)
        logger.debug(lon) 

        sstfile = os.path.join(sst_base_dir, 'sst.mon.mean.nc')
        if not os.path.exists(sstfile):
            logger.error(f"OISST file not found: {sstfile}")
            return
        with xr.open_dataset(sstfile) as sst_ds:

            sst_var = "sst" if "sst" in sst_ds.data_vars else list(sst_ds.data_vars)[0]
            sst = sst_ds[sst_var]

            sst_interp = sst.interp(lat=lat, lon=lon, kwargs={"fill_value": "extrapolate"})
            #print(sst_interp)
            sst_interp.to_netcdf(f'{sst_out_dir}/sst.mon.mean.regrid.nc')
            logger.info("OISST regrid completed.")

            make_lsmask_from_sst_interp_isel0(sst_interp)
            logger.info("OISST land-sea mask created.")

            del sst, sst_interp
    else:
        logger.info("OISST regrid skipped.")

    regrid_file = f'{sst_out_dir}/sst.mon.mean.regrid.nc'
    if not os.path.exists(regrid_file):
        logger.error(f"Regridded OISST file not found: {regrid_file}")
        return 
    with xr.open_dataset(regrid_file) as oisst:
        oisst_clim_subset = oisst.sel(time=slice(f'{clim_start}-01-01',f'{clim_end}-12-30'))
        oisst_clim = oisst_clim_subset.groupby('time.month').mean(("time"))
        oisst_std = oisst_clim_subset.groupby('time.month').std(("time"))
    logger.info("OISST climate and standard deviation calculated.")
    #print(oisst_clim)

    # std 저장 추가 (향후 활용 가능)
    std_file = f'{sst_out_dir}/sst_std_{clim_start}_{clim_end}.nc'
    oisst_std.to_netcdf(std_file)
    logger.info(f"OISST std saved => {std_file}")

    clim_file = f'{sst_out_dir}/sst_clim_{clim_start}_{clim_end}.nc'
    oisst_clim.to_netcdf(clim_file)
    logger.info(f"OISST clim saved => {clim_file}")

    for year in fyears:
        out_file = f'{sst_out_dir}/sst_anom_{year}.nc'
        oisst_anom = oisst.sel(time=slice(f'{year}-01-01',f'{year}-12-31')).groupby('time.month') - oisst_clim
        oisst_anom.to_netcdf(out_file)
        logger.info(f"Saved OISST anomaly => {out_file}")

if __name__=='__main__':
    regrid_option = input('OISST regrid to GS grid ... proceed? [y/n]')
    oisst_anomaly(regrid_option)
