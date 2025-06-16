import argparse
from config import *
import logging 

from src.analysis.categorizeTercile import (
    categorize_obs_tercile, 
    categorize_fcst_tercile_det,
    categorize_fcst_tercile_prob
)
from src.utils.general_utils import generate_yyyymm_list
from src.utils.logging_utils import init_logger

logger = init_logger()

def parse_args():
    parser = argparse.ArgumentParser(description="Global Tercile Categorization for Obs/Fcst")
    parser.add_argument("--var", required=True, choices=variables, help="Variable to categorize")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    return parser.parse_args()

def categorize_observation(var):
    logger.info("🔹 [1/2] Categorizing observed tercile...")
    categorize_obs_tercile(var=var, years=fyears, obs_dir=era5_out_dir)

def categorize_forecast(var, yyyymm_list):
    logger.info("🔹 [2/2] Categorizing forecast tercile...")
    for yyyymm in yyyymm_list:
        if var in ['t2m', 'prcp']:
            logger.info(f"📁 {yyyymm} → Deterministic categorization")
            categorize_fcst_tercile_det(
                var=var,
                yyyymm=yyyymm,
                fcst_dir=f"{model_out_dir}",
                stat_dir=f"{model_out_dir}/hindcast",
                out_dir=f"{verification_out_dir}/CATE/DET"
            )
        else:
            logger.warning(f"⚠️  Skipping deterministic categorization for var={var}")

        logger.info(f"📁 {yyyymm} → Probabilistic categorization")
        categorize_fcst_tercile_prob(
            var=var,
            yyyymm=yyyymm,
            fcst_dir=f"{model_out_dir}/forecast",
            stat_dir=f"{model_out_dir}/hindcast",
            out_dir=f"{verification_out_dir}/CATE/PROB"
        )

def main():
    args = parse_args()
    log_level = logging.DEBUG if args.debug else logging.INFO
    global logger
    logger = init_logger(level=log_level)

    var = args.var
    yyyymm_list = generate_yyyymm_list(year_start, year_end)

    if input('Proceed OBS categorization? [y/n] ').strip().lower() == 'y':
        categorize_observation(var)
    if input('Proceed forecast categorization? [y/n] ').strip().lower() == 'y':
        categorize_forecast(var, yyyymm_list)

if __name__ == "__main__":
    main()