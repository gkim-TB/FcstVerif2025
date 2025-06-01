# src/analysis/calcProbSkillScore.py

import os
import xarray as xr
import numpy as np
import pandas as pd
import xskillscore as xs
from sklearn.metrics import roc_curve, roc_auc_score
from sklearn.calibration import calibration_curve

from config import *
from src.utils.logging_utils import init_logger
from src.utils.general_utils import load_obs_data, clip_to_region

logger = init_logger()

def compute_rps_manual(fcst_prob, obs_ohe):
    """
    fcst_prob, obs_ohe: xarray.DataArray with shape (lat, lon, category)
    """
    # 누적합
    fcst_cdf = fcst_prob.cumsum(dim='category')
    obs_cdf  = obs_ohe.cumsum(dim='category')
    
    # 차이 제곱합
    rps = ((fcst_cdf - obs_cdf) ** 2).sum(dim='category')
    return rps

def compute_rpss_manual(fcst_prob, obs_ohe):
    """
    RPSS 계산: 1 - RPS / RPS_climatology
    """
    # Forecast RPS
    rps = compute_rps_manual(fcst_prob, obs_ohe)

    # Climatology: uniform [1/3, 1/3, 1/3]
    clim_prob = xr.full_like(fcst_prob, 1/3)
    rps_clim = compute_rps_manual(clim_prob, obs_ohe)

    # RPSS 계산 (0으로 나누는 경우 NaN 처리)
    rpss = xr.where(rps_clim == 0, float('nan'), 1 - rps / rps_clim)

    return rpss

def compute_roc_auc_all_categories(fcst_prob, obs_ohe, init_time, region_name):
    """
    ROC Curve 및 AUC 계산 함수 (초기화 월 단위, 리드 x 카테고리)
    
    Parameters
    ----------
    fcst_prob : xarray.DataArray
        Forecast probabilities (time, lat, lon, category)
    obs_ohe : xarray.DataArray
        One-hot observed categories (time, lat, lon, category)
    region_box : tuple
        (lat_s, lat_n, lon_w, lon_e)
    init_time : datetime-like
        Forecast initialization time
    var : str
        Variable name (e.g., 't2m')
    out_dir : str
        Output directory
    region_name : str
        Region name for output file naming
    """
    categories = fcst_prob.category.values.tolist()

    # 지역 클리핑
    fcst_sub = clip_to_region(fcst_prob, region_name)
    obs_sub  = clip_to_region(obs_ohe, region_name)

    n_lead = fcst_sub.sizes['time']
    n_cat = len(categories)
    auc_arr = np.full((n_lead, n_cat), np.nan)
    all_roc_records = []

    for t_idx in range(n_lead):
        lead_val = t_idx + 1
        target_time = pd.to_datetime(fcst_sub.time.values[t_idx])

        for c_idx, cat in enumerate(categories):
            try:
                y_score = fcst_sub.isel(time=t_idx).sel(category=cat).values.flatten()
                y_true = obs_sub.isel(time=t_idx).sel(category=cat).values.flatten().astype(int)
                mask = (~np.isnan(y_score)) & (~np.isnan(y_true))
                y_score = y_score[mask]
                y_true = y_true[mask]

                if len(np.unique(y_true)) < 2:
                    continue

                fpr, tpr, thr = roc_curve(y_true, y_score)
                auc_val = roc_auc_score(y_true, y_score)
                auc_arr[t_idx, c_idx] = auc_val

                for f, t, th in zip(fpr, tpr, thr):
                    all_roc_records.append({
                        "init": pd.to_datetime(init_time),
                        "lead": lead_val,
                        "time": target_time,
                        "category": cat,
                        "fpr": f,
                        "tpr": t,
                        "threshold": th
                    })

            except Exception as e:
                print(f"[ROC WARN] Skipped lead={lead_val} cat={cat} due to error: {e}")
                continue

    # AUC 저장 (NetCDF)
    auc_da = xr.DataArray(
        auc_arr,
        dims=['time', 'category'],
        coords={
            'time': fcst_sub.time,
            'category': categories
        },
        name='auc'
    ).expand_dims(init=[init_time])

    return auc_da, all_roc_records


def compute_probabilistic_scores(var, yyyymm_list, obs_dir, prob_dir, out_dir, region_name):
    os.makedirs(out_dir, exist_ok=True)
    # region_out_dir = os.path.join(out_dir, region_name, var)
    # os.makedirs(region_out_dir, exist_ok=True)

    try:
        obs_ohe_all = load_obs_data(
            var=var,
            years=fyears,
            obs_dir=obs_dir,
            suffix='cate',
            var_suffix='obs_ohe'
        )
    except FileNotFoundError as e:
        logger.warning(str(e))
        return

    for yyyymm in yyyymm_list:
        logger.info(f"[PROB] Processing var={var}, init={yyyymm}")
        #init_date = pd.to_datetime(f"{yyyymm}01")

        prob_file = os.path.join(prob_dir, f"cate_prob_{var}_{yyyymm}.nc")
        if not os.path.isfile(prob_file):
            logger.warning(f"[PROB] Missing forecast prob file: {prob_file}")
            continue

        ds_prob = xr.open_dataset(prob_file)
        init_time = ds_prob['init'].values[0]

        fcst_time = ds_prob['time']
        fcst_prob_full = ds_prob[f"{var}_fcst_prob"].squeeze("init", drop=True)
        fcst_prob_full = fcst_prob_full.assign_coords(time=("lead", fcst_time.values)).swap_dims({"lead": "time"})
        fcst_prob_full = fcst_prob_full.transpose("time", "lat", "lon", "category")

        common_times = [t for t in fcst_time.values if t in obs_ohe_all.time.values]
        if len(common_times) == 0:
            logger.warning(f"[SKIP] {yyyymm}: No common time between forecast and obs")
            continue
        fcst_prob = fcst_prob_full.sel(time=common_times).reset_coords(drop=True)
        obs_ohe = obs_ohe_all.sel(time=common_times).reset_coords(drop=True)

        # 1 RPSS
        # calculated only once for Global
        if region_name == 'GL':
            rpss = compute_rpss_manual(obs_ohe, fcst_prob)
            rpss = rpss.expand_dims(dim={"init": 1})
            rpss = rpss.assign_coords(init=("init", [init_time]))
            ds_out = xr.Dataset({
                f"{var}_rpss": rpss,
            })
            out_path_rpss = os.path.join(out_dir, f"rpss_GL_{var}_{yyyymm}.nc")
            ds_out.to_netcdf(out_path_rpss)
            logger.info(f"[RPSS] save RPSS map {yyyymm} : {out_path_rpss}")
            del ds_out
        else:
            logger.info(f"[RPSS] Skipped RPSS computation for region={region_name}")
        
        # 2 ROC + AUC
        auc_da, all_roc_records = compute_roc_auc_all_categories(  
            fcst_prob=fcst_prob,
            obs_ohe=obs_ohe,
            init_time=init_time,
            region_name=region_name
        )

        ds_auc = xr.Dataset({f"{var}_auc": auc_da})
        out_auc_path = os.path.join(out_dir, f"auc_{var}_{region_name}_{yyyymm}.nc")
        ds_auc.to_netcdf(out_auc_path)
        print(f"[SAVED] AUC to {out_auc_path}")

        # ROC 저장 (CSV)
        df_roc = pd.DataFrame(all_roc_records)
        out_csv_path = os.path.join(out_dir, f"roc_{var}_{region_name}_{yyyymm}.csv")
        df_roc.to_csv(out_csv_path, index=False)
        print(f"[SAVED] ROC to {out_csv_path}")

        logger.info(f"[INFO] AUC and ROC files saved for {yyyymm}")
