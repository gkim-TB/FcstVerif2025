# src/analysis/calcProbSkillScore.py
#!/usr/bin/env python
import os
import xarray as xr
import numpy as np
from config import *
from src.utils.logging_utils import init_logger
import xskillscore as xs
from sklearn.metrics import roc_curve, roc_auc_score
from sklearn.calibration import calibration_curve

from src.utils.general_utils import load_obs_data
import pandas as pd

logger = init_logger()

def compute_probabilistic_scores(var, yyyymm_list, obs_dir, prob_dir, out_dir):
    """
    확률예측 검증: leadtime별 ROC curve, Reliability diagram, RPSS(map) 계산 및 저장
    """
    os.makedirs(out_dir, exist_ok=True)
    categories = ['BN', 'NN','AN']

    # 초기화 날짜별로 검증 수행
    for yyyymm in yyyymm_list:
        logger.info(f"[PROB] Processing {var} {yyyymm}")

        # 모델 확률 예측 불러오기
        prob_file = os.path.join(prob_dir, f"cate_prob_{var}_{yyyymm}.nc")
        if not os.path.isfile(prob_file):
            logger.warning(f"[PROB] Missing forecast probability file: {prob_file}")
            continue

        ds_prob   = xr.open_dataset(prob_file)
        fcst_time = ds_prob['time'] # (lead,) datetime64
        fcst_prob = ds_prob[f"{var}_fcst_prob"].squeeze("init", drop=True)  # (ens, lead, lat, lon)
        fcst_prob = fcst_prob.assign_coords(time=('lead', fcst_time.values)).swap_dims({'lead': 'time'})  # → (ens, time, lat, lon)
        fcst_prob = fcst_prob.transpose('time','lat','lon','category')

        # 관측 카테고리 불러오기
        obs_ohe_all = load_obs_data(
            var=var,
            years=fyears,  # config.py에서 불러온 전체 연도 범위
            obs_dir=obs_dir,
            suffix='cate',
            var_suffix='obs_ohe'
        )
        #print(obs_ohe)
        
        common_times = [t for t in fcst_time.values if t in obs_ohe_all.time.values]
        missing_times = [t for t in fcst_time.values if t not in obs_ohe_all.time.values]   
        if missing_times:
            logger.warning(
                f"[OBS] Missing observation times for : {[str(pd.to_datetime(t).date()) for t in missing_times]}"
                           )

        fcst_prob = fcst_prob.sel(time=common_times).reset_coords(drop=True)
        obs_ohe = obs_ohe_all.sel(time=common_times).reset_coords(drop=True)
        print(fcst_prob.time)
        print(obs_ohe.time)
        
        # 1) ROC + Reliability 
        for t_idx, lead_time in enumerate(fcst_prob.time.values):

            if lead_time not in obs_ohe.time.values:
                logger.warning(f"[TIME] Lead time {lead_time} not found in observations.")
                continue
            
            for cat in categories:
                try:
                    p_cat = fcst_prob.sel(category=cat).values.flatten()
                    y_cat = obs_ohe.sel(category=cat).values.flatten().astype(int)

                    valid = ~np.isnan(p_cat) & ~np.isnan(y_cat)
                    p_cat = p_cat[valid]
                    y_cat = y_cat[valid]

                    if len(np.unique(y_cat)) < 2:
                        logger.warning(f"[ROC] Skipped lead={lead_time} cat={cat} due to only one class.")
                        continue

                    fpr, tpr, thr = roc_curve(y_cat, p_cat)
                    auc = roc_auc_score(y_cat, p_cat)

                    df_roc = pd.DataFrame({
                        'fpr': fpr, 'tpr': tpr, 'threshold': thr, 'auc': auc
                    })
                    out_roc = os.path.join(
                        out_dir,
                        f"roc_{var}_{yyyymm}_lead{t_idx+1}_{cat}.csv"
                    )
                    df_roc.to_csv(out_roc, index=False)
                    logger.info(f"[PROB] {yyyymm} Saved ROC {cat} lead-{t_idx+1}: AUC={auc:.3f}")
                    
                    # 3) Reliability diagram
                    prob_true, prob_pred = calibration_curve(y_cat, p_cat, n_bins=10, strategy='uniform')

                    rel_df = pd.DataFrame({'prob_pred': prob_pred, 'prob_true': prob_true})
                    rel_path = os.path.join(out_dir, f"reliability_{var}_{yyyymm}_lead{t_idx+1}_{cat}.csv")
                    rel_df.to_csv(rel_path, index=False)

                    logger.info(f"[PROB] Saved reliability: lead={t_idx+1} cat={cat}")
                except Exception as e:
                    logger.warning(f"[REL] Error on lead={t_idx+1}, cat={cat}: {e}")

        # 2) RPSS
        logger.info(f"[RPS] Compute RPS Map for var={var}, yyyymm={yyyymm}")

        init_date = pd.to_datetime(f"{yyyymm}01")
        rps_list = []

        for lead in range(1, fcst_prob.sizes['lead'] + 1):
            target_date = init_date + pd.DateOffset(months=lead)
            try:
                obs_ohe = obs_ohe_all.sel(time=target_date)
            except KeyError:
                logger.warning(f"[RPS] No OBS for {target_date}")
                continue

            fcst_prob_lt = fcst_prob.sel(lead=lead)
            rps = xs.rps(obs_ohe, fcst_prob_lt, input_distributions='p')
            rps_list.append(rps.expand_dims(lead=[lead]))

        if rps_list:
            rps_all = xr.concat(rps_list, dim='lead')
            rps_all.name = f"rps_{var}"
            rps_all.attrs['description'] = "Ranked Probability Score per lead-time"
            rpss_out = os.path.join(out_dir, f"rpss_{var}_{yyyymm}.nc")
            rps_all.to_netcdf(rpss_out)
            logger.info(f"[RPS] Saved: {rpss_out}")
        else:
            logger.warning(f"[RPS] No valid RPS calculated for {yyyymm}")
