# fcstverif/run_categorization.py

import argparse

import logging 
from fcstverif.src.utils.logging_utils import init_logger, get_logger
logger = logging.getLogger("fcstverif")

from fcstverif.config import (
    VARIABLES, model, verify_start, verify_end, fcst_start, fcst_end, 
    era5_out_dir, model_out_dir, verification_out_dir, fyears,
    log_path
)
from fcstverif.config import RUN_MODE as CONFIG_RUN_MODE

from fcstverif.src.analysis.categorizeTercile import (
    categorize_obs_tercile, 
    categorize_fcst_tercile_det,
    categorize_fcst_tercile_prob
)
from fcstverif.src.utils.general_utils import generate_yyyymm_list


def parse_args():
    parser = argparse.ArgumentParser(description="Global Tercile Categorization for Obs/Fcst")
    parser.add_argument("--var", required=True, choices=VARIABLES, help="Variable to categorize")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--run_mode", default=None, choices=["auto", "manual"], help="Execution mode (auto/manual)")
    return parser.parse_args()

def categorize_observation(var):
    logger.info("🔹 [1/2] Categorizing observed tercile...")

    try:
        categorize_obs_tercile(var=var, years=fyears, obs_dir=era5_out_dir)
    except Exception as e:
        logger.exception(f"Failed OBS categorization for var={var}: {e}")

def categorize_forecast(var, yyyymm_list):
    logger.info("🔹 [2/2] Categorizing forecast tercile...")

    for yyyymm in yyyymm_list:
        logger.info(f"📁 Processing {yyyymm}")

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
    var = args.var
    run_mode = args.run_mode if args.run_mode else CONFIG_RUN_MODE
    log_level = logging.DEBUG if args.debug else logging.INFO

    init_logger(logfile=log_path, level=log_level)
    global logger
    logger = get_logger()

    yyyymm_list = generate_yyyymm_list(fcst_start, fcst_end)

    if run_mode == "auto":
        categorize_observation(var)
        categorize_forecast(var, yyyymm_list)
    else:
        if input('Proceed OBS categorization? [y/n] ').strip().lower() == 'y':
            categorize_observation(var)
        if input('Proceed forecast categorization? [y/n] ').strip().lower() == 'y':
            categorize_forecast(var, yyyymm_list)

if __name__ == "__main__":
    main()
