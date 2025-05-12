# fcstverif/analysis/categorizeTercile.py

import os
import xarray as xr
import numpy as np
import pandas as pd
from fcstverif.config import *
from fcstverif.utils.logging_utils import init_logger
logger = init_logger()

def categorize_obs_tercile(var, years, data_dir):
    """
    관측 아노말리(anomaly)와 표준편차(std, 걍수량은 quantile)를 이용하여
    ±0.43σ 기준의 3분위 범주(BN=0, NN=1, AN=2)를 구분하고 저장.
    """
    logger.info(f"[TERCILE] OBS categorize: years={years}, var={var}")


    # 1. std 파일 (월별 std: (month, lat, lon)) 
    #    quantile 파일  (월별 quantile: (month, lat, lon, tercile(2)))

    if var == 'prcp':
        std_file = f'{data_dir}/{var}_tercile_{clim_start}_{clim_end}.nc'
    else:
        std_file = f'{data_dir}/{var}_std_{clim_start}_{clim_end}.nc'

    if not os.path.isfile(std_file):
        logger.warning(f"[TERCILE] Missing std file: {std_file}")
        return
    ds_std = xr.open_dataset(std_file)
    
    if var == 'prcp':
        q33 = ds_std[var].sel(tercile=1)
        q67 = ds_std[var].sel(tercile=2)
    else:
        std = ds_std[var] * 0.43# (month, lat, lon)
        
    # 2. 관측 아노말리 자료
    for year in years:
        anom_file=f'{data_dir}/{var}_anom_{year}.nc'
        if not os.path.isfile(anom_file):
            logger.warning(f"[TERCILE] Missing anomaly file: {anom_file}")
            return
        ds_anom = xr.open_dataset(anom_file)
        da_anom = ds_anom[var]  # (time, lat, lon)
        #print(da_anom)
        
        # 4. 분류: 기본 NN(0), AN(1), BN(-1)
        obs_cate = xr.full_like(da_anom, fill_value=1).astype(np.int8)
        #print(obs_cate)
        if var == 'prcp':
            cond_an = da_anom > q67.sel(month=da_anom.time.dt.month)
            cond_bn = da_anom < q33.sel(month=da_anom.time.dt.month)
        else:
            cond_an = da_anom > std.sel(month=da_anom.time.dt.month)
            cond_bn = da_anom < -std.sel(month=da_anom.time.dt.month)

        # 조건별 값 부여
        obs_cate = obs_cate.where(~cond_an, 2)
        obs_cate = obs_cate.where(~cond_bn, 0)
        unique, counts = np.unique(obs_cate.values, return_counts=True)
        print(dict(zip(unique, counts)))  # { -1: ..., 0: ..., 1: ... }

        obs_cate.name = f"{var}_obs_cate"
        obs_cate.attrs['description'] = f"Observed tercile category (BN=0, NN=1, AN=2)"

        # 5. 저장
        out_file = os.path.join(era5_out_dir, f"cate_{var}_{year}.nc")
        obs_cate.to_dataset().to_netcdf(out_file)
        logger.info(f"[TERCILE] Saved: {out_file}")


def categorize_fcst_tercile_deterministic(
        var, 
        yyyymm,
        fcst_anom_dir, 
        fcst_stat_dir, 
        out_dir
        ):
    """
    예측 아노말리와 sigma 기준값을 이용한 3분위 예측 분류 (deterministic)
    """

    # 1. 예측 아노말리 불러오기
    fcst_file = os.path.join(fcst_anom_dir, f"ensMem_{var}_anom_{yyyymm}.nc")
    if not os.path.isfile(fcst_file):
        logger.warning(f"[TERCILE_FCST] No forecast anomaly: {fcst_file}")
        return
    ds_fcst = xr.open_dataset(fcst_file)
    da_fcst = ds_fcst[var].mean('ens')  # 앙상블 평균 (lead, lat, lon)

    # 2. 기준값 (±0.43 × σ) 불러오기
    stat_file = os.path.join(fcst_stat_dir, f"ensMean_sigma_{var}_{yyyymm}.nc")
    if not os.path.isfile(stat_file):
        logger.warning(f"[TERCILE_FCST] No sigma file: {stat_file}")
        return
    ds_sigma = xr.open_dataset(stat_file)
    std = ds_sigma[f'{var}_sigma'] * 0.43

    # 3. 기본값 0으로 초기화 후 조건 분류
    fcst_cate = xr.full_like(da_fcst, fill_value=1).astype(np.int8)
    fcst_cate = fcst_cate.where(da_fcst <=  std, 2)  # AN
    fcst_cate = fcst_cate.where(da_fcst >= -std, 0) # BN
    unique, counts = np.unique(fcst_cate.values, return_counts=True)
    print(dict(zip(unique, counts))) 
    
    # 4. 저장
    out_file = os.path.join(out_dir, f"cate_det_{var}_{yyyymm}.nc")
    fcst_cate.name = f"{var}_fcst_cate"
    fcst_cate.attrs['description'] = f"Deterministic tercile category (BN=0, NN=1, AN=2)"
    fcst_cate.to_dataset().to_netcdf(out_file)
    logger.info(f"[TERCILE_FCST] Saved: {out_file}")    