#dmdl fcstverif/analysis/verifyCategoryDeterministic.py

import os
import numpy as np
import xarray as xr
import pandas as pd
from config import *
from src.utils.general_utils import generate_yyyymm_list, load_obs_data, clip_to_region
from src.utils.logging_utils import init_logger
logger = init_logger()

def compute_multicategory_scores(var, yyyymm, obs_dir, fcst_dir, region_box):
    """
    관측 vs 예측 삼분위 범주를 비교하여 Hit Rate, HSS 등 multi-category 검증 지표 계산
    """
    #year = int(yyyymm[:4])
    #month = int(yyyymm[4:])

    # 관측 파일: 연도별, 예측 파일: 월별
    try:
        obs_data = load_obs_data(var, fyears, obs_dir, suffix='cate', var_suffix=f"{var}_obs_cate")
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
            obs_cate = clip_to_region(obs_cate, region_box)
            fcst_cate = clip_to_region(fcst_cate, region_box)

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
            
            results.append({
                'yyyymm': yyyymm,
                'lead': int(lead),
                'target': target_str,
                'acc': acc,
                'hss': hss
            })
    print(results)
    #logger.info(f"[VERIFY] {yyyymm} ACC={np.nanmean([result['acc'] for result in results]):.3f}, HSS={np.nanmean([result['hss'] for result in results]):.3f}")
    return results

def run_verification_loop(var, region_name, obs_dir, fcst_dir):
    region_box = REGIONS[region_name]
    yyyymm_list = generate_yyyymm_list(year_start, year_end)

    results = []
    for yyyymm in yyyymm_list:
        result = compute_multicategory_scores(var, yyyymm, obs_dir, fcst_dir, region_box)
        if result:
            results.append(result)

    return results
