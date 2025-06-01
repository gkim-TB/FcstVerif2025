#fcstverif/analysis/verifyCategory.py

import os
import numpy as np
import xarray as xr
import pandas as pd
from config import *
from src.utils.general_utils import load_obs_data, clip_to_region
from src.utils.logging_utils import init_logger
logger = init_logger()

def compute_multicategory_scores(var, yyyymm, obs_dir, fcst_dir, region_name):
    """
    관측 vs 예측 삼분위 범주를 비교하여 Hit Rate, HSS 등 multi-category 검증 지표 계산
    """
    #year = int(yyyymm[:4])
    #month = int(yyyymm[4:])

    # 관측 파일: 연도별, 예측 파일: 월별
    try:
        obs_data = load_obs_data(var, fyears, obs_dir, suffix='cate', var_suffix=f"obs_cate")
    except FileNotFoundError as e:
        logger.warning(str(e))
        return None

    fcst_file = os.path.join(fcst_dir, f"cate_det_{var}_{yyyymm}.nc")
    if not os.path.isfile(fcst_file):
        logger.warning(f"[VERIFY] Missing file: {fcst_file}")
        return None

    ds_fcst = xr.open_dataset(fcst_file)

    results = []

    if "lead" in ds_fcst[f"{var}_fcst_det"].dims:
        for lead in ds_fcst["lead"].values:
            # 예측 초기값 + lead개월 = 타겟 월
            init_date = pd.to_datetime(f"{yyyymm}01")
            target_date = init_date + pd.DateOffset(months=int(lead))
            target_str = target_date.strftime("%Y-%m")

            try:
                obs_cate = obs_data.sel(time=target_str)
            except KeyError:
                logger.warning(f"[VERIFY] No OBS for {target_str}")
                continue

            fcst_cate = ds_fcst[f"{var}_fcst_det"].sel(lead=lead)

            # 지역 제한
            obs_cate = clip_to_region(obs_cate, region_name)
            fcst_cate = clip_to_region(fcst_cate, region_name)

            obs_idx = obs_cate.values.flatten()
            fcst_idx = fcst_cate.values.flatten()

            valid_mask = (~np.isnan(obs_idx)) & (~np.isnan(fcst_idx))
            obs_idx = obs_idx[valid_mask].astype(int)
            fcst_idx = fcst_idx[valid_mask].astype(int)

            table = np.zeros((3, 3), dtype=int)
            for o, f in zip(obs_idx, fcst_idx):
                table[o, f] += 1

            total = table.sum()
            hits = np.trace(table)
            acc = hits / total if total else np.nan

            row_sum = table.sum(axis=1)
            col_sum = table.sum(axis=0)
            expected = np.outer(row_sum, col_sum) / total if total else np.zeros_like(table)
            hss = (hits - expected.trace()) / (total - expected.trace()) if total else np.nan

            # pod_dict = {}
            # far_dict = {}
            # for c in range(3):  # BN=0, NN=1, AN=2
            #     obs_total = table[c, :].sum()
            #     fcst_total = table[:, c].sum()
            #     hit = table[c, c]

            #     pod = hit / obs_total if obs_total > 0 else np.nan
            #     far = (fcst_total - hit) / fcst_total if fcst_total > 0 else np.nan

            #     pod_dict[f'pod_{c}'] = pod
            #     far_dict[f'far_{c}'] = far
            
            results.append({
                'yyyymm': yyyymm,
                'lead': int(lead),
                'target': target_str,
                'hr': hr,
                'hss': hss,
            })
    #print(results)
    #logger.info(f"[VERIFY] {yyyymm} ACC={np.nanmean([result['acc'] for result in results]):.3f}, HSS={np.nanmean([result['hss'] for result in results]):.3f}")
    return results

def run_cate_verification_loop(
        var, yyyymm_list, 
        region_name, 
        obs_dir, fcst_dir, out_dir):
    results = []
    for yyyymm in yyyymm_list:
        result = compute_multicategory_scores(var, yyyymm, obs_dir, fcst_dir, region_name)
        if result:
            results.append(result)

    # DataFrame 및 CSV 저장
    df = pd.DataFrame(results)
    out_csv = os.path.join(
        out_dir, f"Det_tercile_score_{var}_{region_name}.csv"
    )
    df.to_csv(out_csv, index=False)
    logger.info(f"[SAVED] {out_csv}")
