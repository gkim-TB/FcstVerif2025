#!/usr/bin/env python
import os
import pandas as pd
from fcstverif.config import *

# 분석 함수 import
from fcstverif.analysis.calcIndices import calculate_indices
from fcstverif.analysis.calcDetermSkillScore import compute_regional_scores_from_ensemble
from fcstverif.analysis.categorizeTercile import categorize_obs_tercile, categorize_fcst_tercile_deterministic
from fcstverif.analysis.verifyCategory import run_verification_loop
from fcstverif.utils.general_utils import generate_yyyymm_list
from fcstverif.utils.logging_utils import init_logger
logger = init_logger()

def run_index_module():
    logger.info("[INFO] Step 1: Calculate ENSO/IOD indices ...")
    calculate_indices(years=fyears)

def run_deterministic_skill_module():
    logger.info("[INFO] Step 2: Compute deterministic skill scores ...")
    for region_name, region_box in REGIONS.items():
        for var in variables:
            if var == 'sst':
                from fcstverif.config import sst_anom_dir as obs_dir
            else:
                from fcstverif.config import era5_out_dir as obs_dir

            compute_regional_scores_from_ensemble(
                var=var,
                years=fyears,
                fcst_dir=f'{model_out_dir}/anomaly',
                obs_dir=obs_dir,
                out_dir=verification_out_dir,
                region_name=region_name,
                region=region_box
            )

def run_deterministic_tercile_verification():
    logger.info("[INFO] Step 3: Categorize and verify deterministic tercile forecast ...")
    yyyymm_list = generate_yyyymm_list(year_start, year_end)

    for var in variables:
        # # 관측 삼분위 분류
        # categorize_obs_tercile(
        #     var=var,
        #     years=fyears,
        #     data_dir=era5_out_dir if var != 'sst' else sst_anom_dir
        # )

        # # 예측 삼분위 분류
        # for yyyymm in yyyymm_list:
        #     categorize_fcst_tercile_deterministic(
        #         var=var,
        #         yyyymm=yyyymm,
        #         fcst_anom_dir=f'{model_out_dir}/anomaly',
        #         fcst_stat_dir=f'{model_out_dir}/hindcast',
        #         out_dir=f'{verification_out_dir}/CATE/DET'
        #     )

        # 검증 수행 및 저장
        for region_name in REGIONS:
            results = run_verification_loop(
                var=var,
                region_name=region_name,
                obs_dir=era5_out_dir,
                fcst_dir=f'{verification_out_dir}/CATE/DET'
            )

            df = pd.DataFrame(results)
            out_csv = os.path.join(verification_out_dir, "CATE", "DET", f"score_{var}_{region_name}.csv")
            df.to_csv(out_csv, index=False)
            logger.info(f"[SAVED] {out_csv}")

def main():
    logger.info("=== Start Analysis Pipeline ===")
    #run_index_module()
    #run_deterministic_skill_module()
    run_deterministic_tercile_verification()
    logger.info("=== Done Analysis ===")

if __name__ == "__main__":
    main()
