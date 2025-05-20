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


def categorize_fcst_tercile(
    var,
    yyyymm,
    fcst_anom_dir,
    fcst_stat_dir,
    out_dir,
    mode='deterministic'
):
    """
    mode='deterministic': 앙상블 평균 기준 BN/NN/AN
    mode='probabilistic': 멤버별 BN/NN/AN → 확률
    !!! 이거 GS6만 된다 다른 모델에도 쓸거면 sigma, gaus, qntl 만드는거 짜야한다
    """
    os.makedirs(out_dir, exist_ok=True)

    if mode == 'probabilistic':
        fcst_file = os.path.join(model_out_dir, 'forecast', f"ensMem_{var}_{yyyymm}.nc")
    elif mode == 'deterministic':
        fcst_file = os.path.join(fcst_anom_dir, f"ensMem_{var}_anom_{yyyymm}.nc")
    else:
        logger.error(f'Invalid mode: {mode}')
    logger.info(f'[FCST] file: {fcst_file}')
            
    if var =='t2m' :
        if mode=='deterministic':
            sigma_file = os.path.join(fcst_stat_dir, f"ensMean_sigma_{var}_{yyyymm}.nc")
        else: # probabilistic
            sigma_file = os.path.join(fcst_stat_dir, f"ensMean_gaus_{var}_{yyyymm}.nc")    
    elif var == 'prcp':
        sigma_file = os.path.join(fcst_stat_dir, f"ensMean_qntl_prcp_{yyyymm}.nc")
    else:
        sigma_file = os.path.join(fcst_stat_dir, f"ensMean_gaus_{var}_{yyyymm}.nc")

    if not os.path.isfile(fcst_file):
        raise FileNotFoundError(f"[FCST] File not found: {fcst_file}")
    if not os.path.isfile(sigma_file):
        raise FileNotFoundError(f"[SIGMA] File not found: {sigma_file}")


    ds_fcst = xr.open_dataset(fcst_file)
    ds_sigma = xr.open_dataset(sigma_file)

    # --- thresholds ---
    if var == 't2m':
        if mode == 'deterministic':
            std = ds_sigma[f"{var}_sigma"] * 0.43         
        else:  # probabilistic
            std = ds_sigma[f"{var}_gaus"]         
    elif var == 'prcp':
        q33 = ds_sigma[f"{var}_qntl"].sel(pert=100).squeeze()
        #print(q33)
        q67 = ds_sigma[f"{var}_qntl"].sel(pert=101).squeeze()       
    else:
        std = ds_sigma[f"{var}_gaus"] 
    logger.info(f'Checked threshold for {var} {mode}')             

    if var == 't2m' and mode == 'deterministic':
        da_fcst = ds_fcst[var].mean('ens')  # (lead, lat, lon)
        fcst_cate = xr.full_like(da_fcst, fill_value=1).astype(np.int8)
        fcst_cate = xr.where(da_fcst >= std, 2, fcst_cate)   # AN
        fcst_cate = xr.where(da_fcst <= -std, 0, fcst_cate)  # BN

        fcst_cate.name = f"{var}_fcst_cate"
        fcst_cate.attrs['description'] = "Deterministic tercile category (BN=0, NN=1, AN=2)"

        out_file = os.path.join(out_dir, f"cate_det_{var}_{yyyymm}.nc")
        fcst_cate.to_dataset().to_netcdf(out_file)
        logger.info(f"[CATE DET] Saved: {out_file}")
        
    elif var == 'prcp' and mode == 'deterministic':
        da_fcst = ds_fcst[var].mean('ens').squeeze()  # (lead, lat, lon)
        print(da_fcst)
        print(q33)
        fcst_cate = xr.full_like(da_fcst, fill_value=1).astype(np.int8)
        fcst_cate = xr.where(da_fcst <= q33, 0, fcst_cate) # BN
        fcst_cate = xr.where(da_fcst >= q67, 1, fcst_cate) # AN
        print(fcst_cate)

        fcst_cate.name = f"{var}_fcst_det"
        fcst_cate.attrs['description'] = "Deterministic tercile category (BN=0, NN=1, AN=2)"

        out_file = os.path.join(out_dir, f"cate_det_{var}_{yyyymm}.nc")
        fcst_cate.to_dataset().to_netcdf(out_file)
        logger.info(f"[CATE DET] Saved: {out_file}")

    elif var == 'prcp' and mode == 'probabilistic':
        da_fcst = ds_fcst[var]
        is_bn = da_fcst < q33                        
        is_an = da_fcst > q67                          
        is_nn = ~(is_bn | is_an)

        prob_bn = is_bn.sum(dim='ens') / da_fcst.sizes['ens'] #* 100
        prob_nn = is_nn.sum(dim='ens') / da_fcst.sizes['ens'] #* 100
        prob_an = is_an.sum(dim='ens') / da_fcst.sizes['ens'] #* 100

        prob_bn = prob_bn.drop_vars('pert', errors='ignore')    
        prob_nn = prob_nn.drop_vars('pert', errors='ignore')    
        prob_an = prob_an.drop_vars('pert', errors='ignore')

        da_prob = xr.concat([prob_bn, prob_nn, prob_an], dim='category', coords='minimal')
        da_prob = da_prob.assign_coords(category=('category', ['BN', 'NN', 'AN']))
        da_prob.coords['category'].attrs['description'] = 'BN=Below, NN=Normal, AN=Above'

        ds_prob = da_prob.to_dataset(name=f"{var}_fcst_prob")
        ds_prob.attrs['description'] = "Probabilistic tercile probability (prcp)"
        out_file = os.path.join(out_dir, f"cate_prob_{var}_{yyyymm}.nc")
        ds_prob.to_netcdf(out_file)
        logger.info(f"[CATE PROB] Saved: {out_file}")

    elif var != 'prcp' and mode == 'probabilistic':
        da_fcst = ds_fcst[var]  # (ens, lead, lat, lon)
        is_bn = (da_fcst < -std)
        is_an = (da_fcst > std)
        is_nn = ~(is_bn | is_an)

        prob_bn = is_bn.sum(dim='ens') / da_fcst.sizes['ens'] #* 100
        prob_nn = is_nn.sum(dim='ens') / da_fcst.sizes['ens'] #* 100
        prob_an = is_an.sum(dim='ens') / da_fcst.sizes['ens'] #* 100

        prob_bn = prob_bn.drop_vars('pert', errors='ignore')    
        prob_nn = prob_nn.drop_vars('pert', errors='ignore')    
        prob_an = prob_an.drop_vars('pert', errors='ignore')

        da_prob = xr.concat([prob_bn, prob_nn, prob_an], dim='category', coords='minimal')
        da_prob = da_prob.assign_coords(category=('category', ['BN', 'NN', 'AN']))
        da_prob.coords['category'].attrs['long_name'] = 'Tercile Category'
        da_prob.coords['category'].attrs['description'] = 'BN=Below Normal, NN=Normal, AN=Above Normal'

        ds_prob = da_prob.to_dataset(name=f"{var}_fcst_prob")
        ds_prob.attrs['description'] = f"{var} tercile forecast probability (BN/NN/AN)"

        out_file = os.path.join(out_dir, f"cate_prob_{var}_{yyyymm}.nc")
        ds_prob.to_netcdf(out_file)
        logger.info(f"[CATE PROB] Saved: {out_file}")
    else:
        # deterministic 모드인데 t2m/강수 외 변수라면
        raise ValueError(f"Deterministic mode is only implemented for 't2m' or 'prcp', got var={var}")

    return out_file