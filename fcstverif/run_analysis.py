# fcstverif/run_analysis.py

import argparse
import os

import logging
from fcstverif.src.utils.logging_utils import init_logger, get_logger
logger = logging.getLogger("fcstverif")

from fcstverif.config import (
    VARIABLES, REGIONS, verify_start, verify_end,
    model, model_out_dir, sst_out_dir, era5_out_dir, verification_out_dir,
    log_path
)
from fcstverif.config import RUN_MODE as CONFIG_RUN_MODE

from fcstverif.src.analysis.calcDetermSkillScore import compute_deterministic_scores
from fcstverif.src.analysis.calcProbSkillScore import compute_probabilistic_scores
from fcstverif.src.analysis.verifyCategory import run_cate_verification_loop
from fcstverif.src.utils.general_utils import generate_yyyymm_list, get_combined_mask

def parse_args():
    parser = argparse.ArgumentParser(description="Analysis pipeline for single var/region")
    parser.add_argument("--var", required=True, choices=VARIABLES, help="Variable to analyze")
    parser.add_argument("--region", required=True, choices=list(REGIONS.keys()), help="Region name for verification")
    parser.add_argument("--run_mode", default=None, choices=["auto", "manual"], help="Execution mode (auto/manual)")
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
            out_dir=out_score_dir,
            # 필요 시 True (이미 만들어 둔 **shard(월별 CSV)**가 있어도 강제로 다시 계산·덮어쓰기)
            recompute=True,   
            # 필요 시 True (가용한 모든 월을 항상 계산)
            discover=False     )

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
    run_mode = args.run_mode if args.run_mode else CONFIG_RUN_MODE
    log_level = logging.DEBUG if args.debug else logging.INFO

    init_logger(logfile=log_path, level=log_level)
    global logger
    logger = get_logger()

    logger.info(f"🔍 Starting analysis: var={var}, region={region_name}")
    yyyymm_list = generate_yyyymm_list(verify_start, verify_end) # list of initialized months to verify

    obs_name = "OISST" if var == "sst" else "ERA5"
    obs_dir = sst_out_dir if var == "sst" else era5_out_dir
    mask = get_combined_mask(model_name=model, obs_name=obs_name) if var == "sst" else None

    if run_mode == "auto":
        run_deterministic_analysis(var, yyyymm_list, region_name, obs_dir, mask)
        run_probabilistic_analysis(var, yyyymm_list, region_name, obs_dir, mask)
    else:
        if input('Process model Deterministic analysis? [y/n] ').strip().lower() == 'y':
            run_deterministic_analysis(var, yyyymm_list, region_name, obs_dir, mask)
        if input('Process model Probabilistic analysis? [y/n] ').strip().lower() == 'y':
            run_probabilistic_analysis(var, yyyymm_list, region_name, obs_dir, mask)

    logger.info("✅ Analysis completed successfully.")

if __name__ == "__main__":
    main()