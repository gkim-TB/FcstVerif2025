#!/usr/bin/env python
import argparse
import os
import pandas as pd
import xarray as xr
from config import *

# 분석 함수 import
from src.analysis.calcIndices import calculate_indices
from src.analysis.calcDetermSkillScore import compute_deterministic_scores
from src.analysis.categorizeTercile import categorize_obs_tercile, run_categorize_forecast_loop
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

yyyymm_list = generate_yyyymm_list(year_start, year_end)

def main():
    model_option = input('Procced Analysis processing? [y/n] ').lower()
    if model_option == 'y':
        logger.info("=== Start Analysis Pipeline ===")
    
        logger.info("[INFO] Step 1: Calculate ENSO/IOD indices ...")
        if var == 'sst':
            calculate_indices(years=fyears)
        else:
            logger.info("[SKIP]")

        logger.info("[INFO] Step 2: Compute deterministic skill scores ...")
        if var == 'sst':
            obs_dir = sst_anom_dir
        else:
            obs_dir = era5_out_dir
        compute_deterministic_scores(
            var=var,
            yyyymm_list=yyyymm_list,
            fcst_dir=f'{model_out_dir}/anomaly',
            obs_dir=obs_dir,
            out_dir=verification_out_dir,
            region_name=region_name,
        )

        logger.info("[INFO] Step 3: Categorize observation tercile (t2m/prcp)...")
        categorize_obs_tercile(
            var=var,
            years=fyears,
            data_dir=era5_out_dir if var != 'sst' else sst_anom_dir
        )

        logger.info("[INFO] Step 4: Categorize forecast Deterministic terciles & Probabilistic forecast...")
        run_categorize_forecast_loop(var, yyyymm_list)

        logger.info(f'[INFO] Step 5: Deterministic Tercile verification')
        run_verification_loop(
            var=var,
            yyyymm_list=yyyymm_list,
            region_name=region_name,
            obs_dir=era5_out_dir,
            fcst_dir=f'{verification_out_dir}/CATE/DET'
        )

        logger.info("[INFO] Step 6: Compute probabilistic skill scores ...")  
        compute_probabilistic_scores(  
            var, 
            yyyymm_list,
            obs_dir=era5_out_dir,  
            prob_dir=f"{verification_out_dir}/CATE/PROB",  
            out_dir=f"{verification_out_dir}",
            region_name = region_name,
        )

    logger.info("=== Done Analysis ===")

if __name__ == "__main__":
    main()
