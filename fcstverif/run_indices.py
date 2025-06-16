import argparse
from config import *
import logging

from src.analysis.calcIndices import calculate_indices
from src.utils.general_utils import generate_yyyymm_list
from fcstverif.src.utils.logging_utils import init_logger

def parse_args():
    parser = argparse.ArgumentParser(description="ENSO/IOD Index Calculation")
    parser.add_argument("--var", required=True, choices=variables, help="Variable to analyze")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    return parser.parse_args()

def run_index_analysis(var, yyyymm_list, fig_dir):
    logger.info(f"📌 Calculating ENSO/IOD index for var={var}")
    calculate_indices(
        var=var,
        yyyymm_list=yyyymm_list,
        model=model,
        fcst_dir=f"{model_out_dir}/anomaly",
        obs_dir=sst_out_dir,
        fig_dir=fig_dir
    )

def main():
    args = parse_args()
    log_level = logging.DEBUG if args.debug else logging.INFO
    global logger
    logger = init_logger(level=log_level)

    var = args.var
    yyyymm_list = generate_yyyymm_list(year_start, year_end)
    fig_dir = os.path.join(output_fig_dir, 'IDX')
    os.makedirs(fig_dir, exist_ok=True)

    run_index_analysis(var, yyyymm_list, fig_dir)

if __name__ == "__main__":
    main()
