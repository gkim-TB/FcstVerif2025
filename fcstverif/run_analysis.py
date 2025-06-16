#!/usr/bin/env python
import argparse
import os
import logging

from fcstverif.config import *
from fcstverif.src.analysis.calcDetermSkillScore import compute_deterministic_scores
from fcstverif.src.analysis.verifyCategory import run_cate_verification_loop
from fcstverif.src.utils.general_utils import generate_yyyymm_list, get_combined_mask
from fcstverif.src.utils.logging_utils import init_logger
from fcstverif.src.analysis.calcProbSkillScore import compute_probabilistic_scores

logger = init_logger()

def parse_args():
    parser = argparse.ArgumentParser(description="Analysis pipeline for single var/region")
    parser.add_argument("--var", required=True, choices=variables, help="Variable to analyze")
    parser.add_argument("--region", required=True, choices=list(REGIONS.keys()), help="Region name for verification")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging") 
    return parser.parse_args()

def run_deterministic_analysis(var, yyyymm_list, region_name, obs_dir, mask):
    logger.info("📌 Step 1: Deterministic Skill Scores")

    out_score_dir = f"{verification_out_dir}/SCORE/{region_name}/{var}"
    compute_deterministic_scores(
        var=var,
        yyyymm_list=yyyymm_list,
        model_name=model,
        fcst_dir=f"{model_out_dir}/anomaly",
        obs_dir=obs_dir,
        out_dir=out_score_dir,
        region_name=region_name,
        mask=mask
    )

    if var in ['t2m', 'prcp']:
        run_cate_verification_loop(
            var=var,
            yyyymm_list=yyyymm_list,
            region_name=region_name,
            obs_dir=obs_dir,
            fcst_dir=f"{verification_out_dir}/CATE/DET",
            out_dir=out_score_dir
        )

def run_probabilistic_analysis(var, yyyymm_list, region_name, obs_dir, mask):
    logger.info("📌 Step 2: Probabilistic Skill Scores")

    compute_probabilistic_scores(
        var=var,
        yyyymm_list=yyyymm_list,
        obs_dir=obs_dir,
        prob_dir=f"{verification_out_dir}/CATE/PROB",
        out_dir=f"{verification_out_dir}/SCORE/{region_name}/{var}",
        region_name=region_name,
        mask=mask
    )

def main():
    args = parse_args()
    var = args.var
    region_name = args.region
    log_level = logging.DEBUG if args.debug else logging.INFO
    global logger
    logger = init_logger(level=log_level)

    logger.info(f"🔍 Starting analysis: var={var}, region={region_name}")
    yyyymm_list = generate_yyyymm_list(year_start, year_end)

    obs_name = "OISST" if var == "sst" else "ERA5"
    obs_dir = sst_out_dir if var == "sst" else era5_out_dir
    mask = get_combined_mask(model_name=model, obs_name=obs_name) if var == "sst" else None

    if input('Process model Deterministic analysis? [y/n] ').strip().lower() == 'y':
        run_deterministic_analysis(var, yyyymm_list, region_name, obs_dir, mask)
    if input('Process model Probabilistic analysis? [y/n] ').strip().lower() == 'y':
        run_probabilistic_analysis(var, yyyymm_list, region_name, obs_dir, mask)

    logger.info("✅ Analysis completed successfully.")

if __name__ == "__main__":
    main()