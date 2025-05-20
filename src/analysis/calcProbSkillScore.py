# src/analysis/calcProbSkillScore.py
#!/usr/bin/env python
import os
import xarray as xr
import numpy as np
from config import *
from src.utils.general_utils import generate_yyyymm_list
from src.utils.logging_utils import init_logger
import xskillscore as xs
from sklearn.metrics import roc_curve
from sklearn.calibration import calibration_curve
import pandas as pd

logger = init_logger()

def compute_probabilistic_scores(var, years, region, obs_dir, prob_dir, out_dir):
    """
    확률예측 검증: ROC curve, Reliability diagram, RPSS(map) 계산 및 저장
    """
    os.makedirs(out_dir, exist_ok=True)
    yyyymm_list = generate_yyyymm_list(year_start, year_end)
    prob_list, obs_list = [], []

    for yyyymm in yyyymm_list:
        # 1) 예측 확률 불러오기
        ds_prob = xr.open_dataset(os.path.join(prob_dir, f"cate_prob_{var}_{yyyymm}.nc"))
        prob_list.append(ds_prob[f"{var}_fcst_prob"])

        # 2) 관측 카테고리 불러오기
        year = int(yyyymm[:4])
        ds_obs = xr.open_dataset(os.path.join(obs_dir, f"{var}_cate_{year}.nc"))
        obs_list.append(ds_obs[f"{var}_obs_cate"])

    # 시간 차원으로 연결
    prob = xr.concat(prob_list, dim='time')  # (time, lat, lon, category)
    obs  = xr.concat(obs_list, dim='time')   # (time, lat, lon)

    # --- RPSS map ---
    obs_ohe = xs.one_hot(obs, dim='category')
    rpss_map = xs.rpss(prob, obs_ohe, dim='time')  # (lat, lon)
    rpss_map.to_netcdf(os.path.join(out_dir, f"rpss_{var}.nc"))
    logger.info(f"[PROB] Saved RPSS map: {out_dir}/rpss_{var}.nc")

    # --- ROC curve (AN 이벤트) ---
    prob_an = prob.sel(category='AN')
    obs_an  = (obs == 2)
    p, y = prob_an.values.flatten(), obs_an.values.flatten().astype(int)
    fpr, tpr, thr = roc_curve(y, p)
    roc_df = pd.DataFrame({'fpr':fpr,'tpr':tpr,'threshold':thr})
    roc_df.to_csv(os.path.join(out_dir,f"roc_{var}.csv"), index=False)
    logger.info(f"[PROB] Saved ROC data: {out_dir}/roc_{var}.csv")

    # --- Reliability diagram ---
    prob_true, prob_pred = calibration_curve(y, p, n_bins=10)
    rel_df = pd.DataFrame({'prob_pred':prob_pred,'prob_true':prob_true})
    rel_df.to_csv(os.path.join(out_dir,f"reliability_{var}.csv"), index=False)
    logger.info(f"[PROB] Saved reliability data: {out_dir}/reliability_{var}.csv")
