#!/usr/bin/env python

from fcstverif.config import fyears, variables, REGIONS

# 분석 함수 import
from fcstverif.analysis.calcIndices import calculate_indices
from fcstverif.analysis.calcDetermSkillScore import compute_regional_scores_from_ensemble

from fcstverif.utils.logging_utils import init_logger
logger = init_logger()

def main():
    logger.info("=== Start Analysis Pipeline ===")

    # 1. ENSO/IOD index calculation from forecast & OISST
    logger.info("[INFO] Step 1: Calculate ENSO/IOD indices ...")
    calculate_indices(years=fyears)

    # 2. Deterministic verification scores (ACC, RMSE, Bias)
    logger.info("[INFO] Step 2: Compute deterministic skill scores ...")
    for region_name, region_box in REGIONS.items():
        for var in variables:
            if var == 'sst':
                from fcstverif.config import sst_anom_dir as obs_dir
            else:
                from fcstverif.config import era5_out_dir as obs_dir

            from fcstverif.config import fanomaly_dir as fcst_dir
            from fcstverif.config import verification_out_dir as out_dir

            compute_regional_scores_from_ensemble(
                var=var,
                years=fyears,
                fcst_dir=fcst_dir,
                obs_dir=obs_dir,
                out_dir=out_dir,
                region_name=region_name,
                region=region_box
            )

    logger.info("=== Done Analysis ===")

if __name__ == "__main__":
    main()
