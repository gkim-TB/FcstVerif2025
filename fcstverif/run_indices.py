# fcstverif/run_indices.py

import argparse
import os

from fcstverif.config import (
    VARIABLES, REGIONS, model, verify_start, verify_end, fcst_start, fcst_end, 
    model_out_dir, sst_out_dir, output_fig_dir, verification_out_dir,
    log_path
)
from fcstverif.config import RUN_MODE as CONFIG_RUN_MODE
from fcstverif.src.analysis.calcIndices import calculate_index
from fcstverif.src.utils.general_utils import generate_yyyymm_list

import logging
from fcstverif.src.utils.logging_utils import init_logger, get_logger
logger = logging.getLogger("fcstverif")

def parse_args():
    parser = argparse.ArgumentParser(description="ENSO/IOD Index Calculation")
    parser.add_argument("--var", required=True, choices=VARIABLES, help="Variable to analyze")
    parser.add_argument("--region", choices=list(REGIONS.keys()), help="Region name for verification")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--run_mode", default=None, choices=["auto", "manual"], help="Execution mode (auto/manual)")
    return parser.parse_args()

def run_index_analysis(var, yyyymm_list, fig_dir):
    logger.info(f"📌 Calculating ENSO/IOD index and skillscore")

    calculate_index(
        var=var,
        yyyymm_list=yyyymm_list,
        model=model,
        fcst_dir=f"{model_out_dir}/anomaly",
        obs_dir=sst_out_dir,
        idx_dir=f"{verification_out_dir}/IDX/",
        #score_dir=f"{verification_out_dir}/SCORE/IDX/"
        fig_dir=fig_dir,
        mode='ENSO'
    )

    calculate_index(
        var=var,
        yyyymm_list=yyyymm_list,
        model=model,
        fcst_dir=f"{model_out_dir}/anomaly",
        obs_dir=sst_out_dir,
        idx_dir=f"{verification_out_dir}/IDX/",
        #score_dir=f"{verification_out_dir}/SCORE/IDX/"
        fig_dir=fig_dir,
        mode='IOD'
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
    fig_dir = os.path.join(output_fig_dir, 'IDX')
    os.makedirs(fig_dir, exist_ok=True)

    if run_mode == "auto":
        run_index_analysis(var, yyyymm_list, fig_dir)
        
    else: 
        if input('Proceed Indices? [y/n] ').strip().lower() == 'y':
            run_index_analysis(var, yyyymm_list, fig_dir)
            

if __name__ == "__main__":
    main()
