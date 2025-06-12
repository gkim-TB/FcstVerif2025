#!/usr/bin/env python
import os
import pandas as pd
from fcstverif.config import *

# 분석 함수 import
from fcstverif.analysis.calcIndices import calculate_indices
from fcstverif.analysis.calcDetermSkillScore import 1
from fcstverif.analysis.categorizeTercile import categorize_obs_tercile, categorize_fcst_tercile_deterministic#create_catMask_det, create_catMask_prob

from fcstverif.utils.logging_utils import init_logger
logger = init_logger()

def main():
    logger.info("=== Start Analysis Pipeline ===")

    # 1. ENSO/IOD index calculation from forecast & OISST
    logger.info("[INFO] Step 1: Calculate ENSO/IOD indices ...")
    calculate_indices(years=fyears)

    # 2. Deterministic verification scores (ACC, RMSE, Bias)
    logger.info("[INFO] Step 2: Compute deterministic skill scores ...")
    # for region_name, region_box in REGIONS.items():
    #     for var in variables:
    #         if var == 'sst':
    #             from fcstverif.config import sst_anom_dir as obs_dir
    #         else:
    #             from fcstverif.config import era5_out_dir as obs_dir

    #         #from fcstverif.config import fanomaly_dir as fcst_dir
    #         from fcstverif.config import verification_out_dir as out_dir

    #         compute_regional_scores_from_ensemble(
    #             var=var,
    #             years=fyears,
    #             fcst_dir=f'{model_out_dir}/anomaly',
    #             obs_dir=obs_dir,
    #             out_dir=out_dir,
    #             region_name=region_name,
    #             region=region_box
    #         )

    
    mask_det_dir  = os.path.join(verification_out_dir, "CATE", "MASK", "DET")
    mask_prob_dir = os.path.join(verification_out_dir, "CATE", "MASK", "PROB")
 
    yyyymm_list = pd.date_range(start=f"{year_start}-01", end=f"{year_end}-12", freq="MS").strftime("%Y%m").tolist()
    print(yyyymm_list)

    for var in variables:
        categorize_obs_tercile(
                var=var,
                years=fyears,
                data_dir=era5_out_dir if var != 'sst' else sst_anom_dir
            )
        
        
        for yyyymm in yyyymm_list: 
            categorize_fcst_tercile_deterministic(
                var = var,
                yyyymm = yyyymm,
                fcat_anom_dir= f'{model_out_dir}/anomaly',
                fcst_stat_dir= f'{model_out_dir}/hindcast',
                out_dir= f'{verification_out_dir}/CAT/DET',
            )
    
    # for var in ['t2m','prcp']:
        
        

    #     create_catMask_det(
    #         var, 
    #         fyears, 
    #         f'{model_out_dir}/anomaly', 
    #         era5_out_dir, 
    #         f'{model_out_dir}/hindcast', 
    #         mask_det_dir)
    #     create_catMask_prob(
    #         var, 
    #         fyears, 
    #         f'{model_out_dir}/anomaly', 
    #         era5_out_dir, 
    #         f'{model_out_dir}/hindcast', 
    #         mask_prob_dir)


    logger.info("=== Done Analysis ===")

if __name__ == "__main__":
    main()
