# fcstverif/utils/general_utils.py

import os
import xarray as xr
import pandas as pd
import calendar
import numpy as np
from fcstverif.config import *

def generate_yyyymm_list(start_year, end_year):
    """예: 2022~2024 → ['202201', ..., '202412']"""
    return pd.date_range(start=f"{start_year}-01", end=f"{end_year}-12", freq="MS").strftime("%Y%m").tolist()

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
            data_list.append(ds)
    if not data_list:
        raise FileNotFoundError(f"[OBS] No {suffix} files found for var={var}, years={years}")
    
    ds_all = xr.concat(data_list, dim='time')
    if var_suffix:
        return ds_all[var_suffix]
    else:
        return ds_all[var]  # 변수명이 var와 동일한 경우
    
def clip_to_region(da, region_box):
    """
    주어진 DataArray를 지정된 영역 (lat_min, lat_max, lon_min, lon_max)로 자름
    """
    lat_min, lat_max, lon_min, lon_max = region_box
    return da.sel(lat=slice(lat_min, lat_max), lon=slice(lon_min, lon_max))

def convert_prcp_to_mm_per_day(da, source):
    """
    강수량 DataArray를 mm/day 단위로 변환
    - source='ERA5': 단위 m (월별 적산) -> mm/day
    - source='GS6': 단위 kg m-2 s-1 (flux) -> mm/day
    """
    if source == 'ERA5':
        # m/day -> mm/day
        return da * 1000 
    elif source == 'GS6':
        # kg/m2/s = mm/s 이므로 86400초 곱해서 mm/day
        return da * 86400
    else:
        raise ValueError(f"Unknown precipitation source: {source}")

def convert_geopotential_to_m(da, source):
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
