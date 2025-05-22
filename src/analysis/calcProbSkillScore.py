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

        # 모델 확률 예측 불러오기
        ds_prob   = xr.open_dataset(os.path.join(prob_dir, f"cate_prob_{var}_{yyyymm}.nc"))
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
        
        # 1) ROC curve
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

        # 1) RPSS map
        #   - observations: obs_ohe_lt (0/1 one-hot)
        #   - forecasts:    prob_lt    (확률 분포)
        #   - category_edges=None, input_distributions='p' 로 확률 분포 입력임을 표시
        # rpss = xs.rps(
        #     obs_ohe, 
        #     fcst_prob, 
        #     category_edges=None, 
        #     input_distributions='p', 
        #     )
        # print(rpss)
        # exit()

        # rpss_path = os.path.join(out_dir, f"rpss_{var}_{yyyymm}.nc")
        # rpss.to_netcdf(rpss_path)
        # logger.info(f"[PROB] Saved RPSS map {yyyymm} : {rpss_path}")

    
