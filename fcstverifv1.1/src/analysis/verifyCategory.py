#fcstverif/analysis/verifyCategory.py

import os
import glob  # <<< CHANGED
import numpy as np
import xarray as xr
import pandas as pd
from fcstverif.config import *
from fcstverif.src.utils.general_utils import load_obs_data, clip_to_region

import logging
logger = logging.getLogger("fcstverif")

def _obs_years_for_verif():  # 보조 함수 (관측 연장 규칙)
    oyears = fyears.tolist()
    if len(oyears):
        oyears.append(max(oyears) + 1)
    return oyears

def _shard_dir(out_dir, region_name, var): 
    return os.path.join(out_dir, "DET_CATE", "shards", region_name, var)

def _shard_path(out_dir, region_name, var, yyyymm):  
    return os.path.join(_shard_dir(out_dir, region_name, var),
                        f"cateScore_det_{var}_{region_name}_{yyyymm}.csv")

def _write_monthly_shard(df_rowwise, out_dir, region_name, var, yyyymm):  # <<< CHANGED
    os.makedirs(_shard_dir(out_dir, region_name, var), exist_ok=True)
    fpath = _shard_path(out_dir, region_name, var, yyyymm)
    df_rowwise.to_csv(fpath, index=False)
    logger.info(f"[SHARD] saved: {fpath}")

def _build_rollup_from_shards(out_dir, region_name, var): 
    shard_pattern = os.path.join(_shard_dir(out_dir, region_name, var),
                                 f"cateScore_det_{var}_{region_name}_*.csv")
    files = sorted(glob.glob(shard_pattern))
    if not files:
        logger.warning(f"[ROLLUP] No shards found for {region_name}/{var}")
        return None

    parts = []
    for f in files:
        try:
            parts.append(pd.read_csv(f))
        except Exception as e:
            logger.warning(f"[ROLLUP] skip broken shard: {f} ({e})")
    if not parts:
        return None

    df = pd.concat(parts, ignore_index=True).drop_duplicates(subset=["yyyymm","lead"])  # 안정성  # <<< CHANGED
    # 정렬: yyyymm, lead
    df = df.sort_values(by=["yyyymm","lead"])
    return df

def compute_multicategory_scores(var, yyyymm, obs_dir, fcst_dir, region_name):
    """
    관측 vs 예측 삼분위 범주를 비교하여 Hit Rate, HSS 등 multi-category 검증 지표 계산
    반환: pd.DataFrame (columns: yyyymm, lead, target, acc, hss)  # <<< CHANGED
    """
    # 관측: 연도별, 예측: 월별
    try:
        obs_data = load_obs_data(
            var, _obs_years_for_verif(), obs_dir,
            suffix='cate', var_suffix=f"obs_cate"
        )
    except FileNotFoundError as e:
        logger.warning(str(e))
        return pd.DataFrame(columns=["yyyymm","lead","target","acc","hss"])  # <<< CHANGED

    fcst_file = os.path.join(fcst_dir, f"cate_det_{var}_{yyyymm}.nc")
    if not os.path.isfile(fcst_file):
        logger.warning(f"[Cate Det VERIFY] Missing file: {fcst_file}")
        return pd.DataFrame(columns=["yyyymm","lead","target","acc","hss"])  # <<< CHANGED

    with xr.open_dataset(fcst_file) as ds_fcst:

        rows = []  # <<< CHANGED
        if "lead" in ds_fcst[f"{var}_fcst_det"].dims:
            for lead in ds_fcst["lead"].values:
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
                obs_cate = clip_to_region(obs_cate, region_name, var)
                fcst_cate = clip_to_region(fcst_cate, region_name, var)

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

                rows.append({  # <<< CHANGED
                    'yyyymm': yyyymm,
                    'lead': int(lead),
                    'target': target_str,
                    'acc': acc,
                    'hss': hss,
                })

    return pd.DataFrame(rows)  # <<< CHANGED

def run_cate_verification_loop(
        var, yyyymm_list,
        region_name,
        obs_dir, fcst_dir, out_dir,
        recompute=False,           # <<< CHANGED: True면 shards를 강제 재계산
        discover=False             # <<< CHANGED: True면 fcst_dir 스캔으로 yyyymm 자동 추출
    ):
    """
    증분 계산 + 월별 shard 저장 + 롤업 CSV 생성
    - 결과 롤업 CSV: {out_dir}/Det_tercile_score_{var}_{region_name}.csv
    """
    # yyyymm 후보군 결정
    if discover:  # <<< CHANGED
        patt = os.path.join(fcst_dir, f"cate_det_{var}_*.nc")
        files = sorted(glob.glob(patt))
        yyyymm_list = [os.path.basename(f).split("_")[-1].split(".")[0] for f in files]
        logger.info(f"[DISCOVER] found {len(yyyymm_list)} months in fcst_dir")

    # 월별 계산(증분)
    for yyyymm in yyyymm_list:
        shard_fp = _shard_path(out_dir, region_name, var, yyyymm)
        if (not recompute) and os.path.isfile(shard_fp):  # <<< CHANGED
            logger.info(f"[SKIP] shard exists: {shard_fp}")
            continue

        df_month = compute_multicategory_scores(var, yyyymm, obs_dir, fcst_dir, region_name)
        if df_month is None or df_month.empty:
            logger.info(f"[SKIP] empty month: {yyyymm}")
            continue

        _write_monthly_shard(df_month, out_dir, region_name, var, yyyymm)  # <<< CHANGED

    # 롤업 재구성
    df_rollup = _build_rollup_from_shards(out_dir, region_name, var)  # <<< CHANGED
    if df_rollup is not None:
        out_csv = os.path.join(out_dir, f"Det_tercile_score_{var}_{region_name}.csv")
        df_rollup.to_csv(out_csv, index=False)
        logger.info(f"[ROLLUP] saved: {out_csv}")
    else:
        logger.warning(f"[ROLLUP] nothing to save for {region_name}/{var}")
