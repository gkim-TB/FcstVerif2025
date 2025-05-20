# fcstverif/analysis/categorizeTercile.py

import os
import xarray as xr
import numpy as np
import pandas as pd
from config import *
from src.utils.logging_utils import init_logger
logger = init_logger()

def categorize_obs_tercile(var, years, data_dir):
    """
    관측 아노말리(anomaly)와 표준편차(std, 걍수량은 quantile)를 이용하여
    ±0.43σ 기준의 3분위 범주(BN=0, NN=1, AN=2)를 구분하고 저장.
    """
    logger.info(f"[TERCILE] OBS categorize: years={years}, var={var}")


    # 1. std file (monthly std: (month, lat, lon)) 
    #    quantile file (monthly quantile: (month, lat, lon, tercile(2)))

    if var == 'prcp':
        std_file = f'{data_dir}/{var}_tercile_{clim_start}_{clim_end}.nc'
    else:
        std_file = f'{data_dir}/{var}_std_{clim_start}_{clim_end}.nc'

    if not os.path.isfile(std_file):
        logger.warning(f"[Warning] Missing std/tercile file: {std_file}")
        return
    ds_std = xr.open_dataset(std_file)
    
    if var == 'prcp':
        q33 = ds_std[var].sel(tercile='lower')
        q67 = ds_std[var].sel(tercile='upper')
    else:
        std = ds_std[var] * 0.43  # (month, lat, lon)
        
    # 2. Calculate observed tercile categories
    for year in years:

        if var == 'prcp':
            anom_file = f'{data_dir}/{var}_total_{year}.nc'
        else:
            anom_file = f'{data_dir}/{var}_anom_{year}.nc'

        if not os.path.isfile(anom_file):
            logger.warning(f"[Warning] Missing anomaly file: {anom_file}")
            return
        
        ds_anom = xr.open_dataset(anom_file)
        da_anom = ds_anom[var]  # (time, lat, lon)
        #print(da_anom)
        
        # 4. 분류: 기본 NN(1), AN(2), BN(0)
        obs_cate = xr.full_like(da_anom, fill_value=1).astype(np.int8)
        #print(obs_cate)
        if var == 'prcp':
            cond_an = da_anom > q67.sel(month=da_anom.time.dt.month)
            cond_bn = da_anom < q33.sel(month=da_anom.time.dt.month)
        else:
            cond_an = da_anom > std.sel(month=da_anom.time.dt.month)
            cond_bn = da_anom < -std.sel(month=da_anom.time.dt.month)

        # 조건별 값 부여
        obs_cate = xr.where(cond_an, 2, obs_cate)
        obs_cate = xr.where(cond_bn, 0, obs_cate)
        unique, counts = np.unique(obs_cate.values, return_counts=True)
        print(dict(zip(unique, counts)))  # { -1: ..., 0: ..., 1: ... }

        obs_cate.name = f"{var}_obs_cate"
        obs_cate.attrs['description'] = f"Observed tercile category (BN=0, NN=1, AN=2)"

        # 5. 저장
        out_file = os.path.join(era5_out_dir, f"{var}_cate_{year}.nc")
        obs_cate.to_dataset().to_netcdf(out_file)
        logger.info(f"[TERCILE] Saved: {out_file}")


def _load_thresholds(var, yyyymm, stat_dir, mode):
    """
    stat_dir 내 qntl 또는 gaus 파일에서 dynamic thresholds 추출
    """
    if var == 't2m' and mode == 'deterministic':
        sigma_file = os.path.join(stat_dir, f"ensMean_sigma_{var}_{yyyymm}.nc")
        ds = xr.open_dataset(sigma_file)
        lower = ds[f"{var}_sigma"] * -0.43
        upper = ds[f"{var}_sigma"] * 0.43
    elif var == 'prcp' and mode == 'deterministic':
        qntl_file = os.path.join(stat_dir, f"ensMean_qntl_prcp_{yyyymm}.nc")
        ds = xr.open_dataset(qntl_file)
        arr = ds[f"{var}_qntl"]
        lower = arr.min(dim='pert').squeeze()
        upper = arr.max(dim='pert').squeeze()
    else:
        # probabilistic: prcp->qntl, others->gaus
        stat_type = 'qntl' if var=='prcp' else 'gaus'
        stat_file = os.path.join(stat_dir, f"ensMean_gaus_{var}_{yyyymm}.nc")
        ds = xr.open_dataset(stat_file)
        arr = ds[f"{var}_{stat_type}"]
        lower = arr.min(dim='pert').squeeze()
        upper = arr.max(dim='pert').squeeze()
    
    return lower, upper


def categorize_fcst_tercile_det(var, yyyymm, fcst_dir, stat_dir, out_dir):
    """
    Deterministic tercile category 생성 for t2m, prcp
    BN=0, NN=1, AN=2
    """
    os.makedirs(out_dir, exist_ok=True)
    # Forecast anomaly 파일 로드
    if var == 't2m':
        fcst_file = os.path.join(fcst_dir, 'anomaly', f"ensMem_{var}_anom_{yyyymm}.nc")
    elif var == 'prcp':
        fcst_file = os.path.join(fcst_dir, 'forecast', f"ensMem_{var}_{yyyymm}.nc")
    else:
        raise ValueError(f"Unsupported variable: {var}")
    
    if not os.path.isfile(fcst_file):
        raise FileNotFoundError(f"[FCST] File not found: {fcst_file}")
    
    ds_fcst = xr.open_dataset(fcst_file)
    da = ds_fcst[var].mean('ens')
    #print(da.sel(lat=slice(-5,5), lon=slice(150,180)))
    # Threshold 로드
    lower, upper = _load_thresholds(var, yyyymm, stat_dir, mode='deterministic')
    #print(lower.sel(lat=slice(-5,5), lon=slice(150,180)))
    #print(upper.sel(lat=slice(-5,5), lon=slice(150,180)))

    # Category 할당
    cate = xr.full_like(da, 1).astype(np.int8)
    if var == 't2m':
        cate = xr.where(da >= upper, 2, cate)
        cate = xr.where(da <= lower, 0, cate)
    #print(cate.sel(lat=slice(-5,5), lon=slice(150,180)))

    ds_out = cate.to_dataset(name=f"{var}_fcst_det")
    ds_out.attrs['description'] = "Deterministic tercile category (BN=0, NN=1, AN=2)"
    out_file = os.path.join(out_dir, f"cate_det_{var}_{yyyymm}.nc")
    ds_out.to_netcdf(out_file)
    logger.info(f"[CATE DET] Saved: {out_file}")
    return out_file


def categorize_fcst_tercile_prob(var, yyyymm, fcst_dir, stat_dir, out_dir):
    """
    Probabilistic probability 생성 for all variable
    Returns netCDF with:
      - `{var}_fcst_prob` (probabilities BN, NN, AN)
      - `{var}_fcst_mode` (0=BN, 1=NN, 2=AN) as most probable category
    """
    os.makedirs(out_dir, exist_ok=True)
    # Forecast ensemble 파일 로드
    fcst_file = os.path.join(fcst_dir, f"ensMem_{var}_{yyyymm}.nc")
    if not os.path.isfile(fcst_file):
        raise FileNotFoundError(f"[FCST] File not found: {fcst_file}")
    ds_fcst = xr.open_dataset(fcst_file)
    da = ds_fcst[var]

    # Threshold 로드
    lower, upper = _load_thresholds(var, yyyymm, stat_dir, mode='probabilistic')

    # Probability 계산
    is_bn = da < lower
    is_an = da > upper
    is_nn = ~(is_bn | is_an)
    #print(is_bn)

    prob_bn = is_bn.sum(dim='ens') / da.sizes['ens']
    prob_nn = is_nn.sum(dim='ens') / da.sizes['ens']
    prob_an = is_an.sum(dim='ens') / da.sizes['ens']

    # pert 차원 제거
    prob_bn = prob_bn.drop_vars('pert', errors='ignore')
    prob_nn = prob_nn.drop_vars('pert', errors='ignore')
    prob_an = prob_an.drop_vars('pert', errors='ignore')

    da_prob = xr.concat([prob_bn, prob_nn, prob_an], dim='category', coords='minimal')
    da_prob = da_prob.assign_coords(category=('category', ['BN', 'NN', 'AN']))
    da_prob.coords['category'].attrs['description'] = 'BN=Below, NN=Normal, AN=Above'

    ds_out = da_prob.to_dataset(name=f"{var}_fcst_prob")
    ds_out.attrs['description'] = f"Probabilistic tercile probability ({var})"

    mode_da = da_prob.argmax(dim='category')
    mode_da = mode_da.rename(f"{var}_fcst_mode")
    mode_da.attrs['description'] = 'Most probable tercile category (0=BN, 1=NN, 2=AN)'
    ds_out[f"{var}_fcst_mode"] = mode_da

    out_file = os.path.join(out_dir, f"cate_prob_{var}_{yyyymm}.nc")
    ds_out.to_netcdf(out_file)
    logger.info(f"[CATE PROB] Saved: {out_file}")
    return out_file