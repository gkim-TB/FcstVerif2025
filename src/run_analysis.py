#!/usr/bin/env python
import argparse
import os
import pandas as pd
import xarray as xr
from config import *

# 분석 함수 import
from src.analysis.calcIndices import calculate_indices
from src.analysis.calcDetermSkillScore import compute_regional_scores_from_ensemble
from src.analysis.categorizeTercile import categorize_obs_tercile, categorize_fcst_tercile_det, categorize_fcst_tercile_prob
from src.analysis.verifyCategory import run_verification_loop

from src.utils.general_utils import generate_yyyymm_list
from src.utils.logging_utils import init_logger
from src.analysis.calcProbSkillScore import compute_probabilistic_scores
logger = init_logger()

# 🔽 argparse 추가: var/region 단일 처리
parser = argparse.ArgumentParser(description="Analysis pipeline for single var/region")
parser.add_argument("--var", required=True, choices=variables, help="Variable to analyze")
parser.add_argument("--region", required=True, choices=list(REGIONS.keys()), help="Region name for verification")
args = parser.parse_args()
var = args.var
region_name = args.region
region_box = REGIONS[region_name]


def run_index_module():
    logger.info("[INFO] Step 1: Calculate ENSO/IOD indices ...")
    calculate_indices(years=fyears)


def run_deterministic_skill_module():
    logger.info("[INFO] Step 2: Compute deterministic skill scores ...")
    # 🔽 region 단일 처리
    if var == 'sst':
        obs_dir = sst_anom_dir
    else:
        obs_dir = era5_out_dir
    compute_regional_scores_from_ensemble(
        var=var,
        years=fyears,
        fcst_dir=f'{model_out_dir}/anomaly',
        obs_dir=obs_dir,
        out_dir=verification_out_dir,
        region_name=region_name,
        region=region_box
    )


def run_tercile_categorize():
    logger.info("[INFO] Step 3: Categorize tercile forecast ...")
    yyyymm_list = generate_yyyymm_list(year_start, year_end)

    # 관측 삼분위 분류
    categorize_obs_tercile(
        var=var,
        years=fyears,
        data_dir=era5_out_dir if var != 'sst' else sst_anom_dir
    )

    # 예측 삼분위 분류
    for yyyymm in yyyymm_list:
        if var == 't2m' or var =='prcp':
            categorize_fcst_tercile_det(
                var=var,
                yyyymm=yyyymm,
                fcst_dir=f'{model_out_dir}',
                stat_dir=f'{model_out_dir}/hindcast',
                out_dir=f'{verification_out_dir}/CATE/DET',
            )
        
        categorize_fcst_tercile_prob(
            var=var,
            yyyymm=yyyymm,
            fcst_dir=f'{model_out_dir}/forecast',
            stat_dir=f'{model_out_dir}/hindcast',
            out_dir=f'{verification_out_dir}/CATE/PROB',
        )

def run_tercile_verification():
    logger.info(f'[INFO] Step 4: Deterministic Tercile verification')
    # 검증 수행 및 저장 (lead별 결과 포함)
    results = run_verification_loop(
        var=var,
        region_name=region_name,
        obs_dir=era5_out_dir,
        fcst_dir=f'{verification_out_dir}/CATE/DET'
    )

    # DataFrame 및 CSV 저장
    df = pd.DataFrame(results)
    out_csv = os.path.join(verification_out_dir, "CATE", "DET", f"score_{var}_{region_name}.csv")
    df.to_csv(out_csv, index=False)
    logger.info(f"[SAVED] {out_csv}")

def run_probabilistic_skill_module():  
    logger.info("[INFO] Step 5: Compute probabilistic skill scores ...")  
    compute_probabilistic_scores(  
        var=var,  
        years=fyears,  
        region=region_box,  
        obs_dir=era5_out_dir,  
        prob_dir=f"{verification_out_dir}/CATE/PROB",  
        out_dir=f"{verification_out_dir}/{region_name}"  
    )

def main():
    model_option = input('Procced Analysis processing? [y/n] ').lower()
    if model_option == 'y':
        logger.info("=== Start Analysis Pipeline ===")
        if var == 'sst':
            run_index_module()
        #run_deterministic_skill_module()
        #run_tercile_categorize()
        run_tercile_verification()
        run_probabilistic_skill_module()
        logger.info("=== Done Analysis ===")

if __name__ == "__main__":
    main()
