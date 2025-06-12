import argparse
from config import *
from src.analysis.categorizeTercile import (
    categorize_obs_tercile, 
    categorize_fcst_tercile_det,
    categorize_fcst_tercile_prob
)
from src.utils.general_utils import generate_yyyymm_list
from src.utils.logging_utils import init_logger

logger = init_logger()

# 🔽 변수 인자 받기 (region은 필요 없음)
parser = argparse.ArgumentParser(description="Global Tercile Categorization (obs/fcst)")
parser.add_argument("--var", required=True, choices=variables)
args = parser.parse_args()
var = args.var

# ⚙️ 분석기간
yyyymm_list = generate_yyyymm_list(year_start, year_end)

def main():
    option = input('Procced categorization? [y/n] ').lower()
    if option == 'y':
        logger.info(f"[GLOBAL CATEGORIZATION] Start → var = {var}")

        # step 0. Global categorization (only once)
        logger.info("[1/2] Categorizing observed tercile...")
        categorize_obs_tercile(
            var=var,
            years=fyears,
            obs_dir=era5_out_dir if var != 'sst' else sst_out_dir
        )
        logger.info("[2/2] Running forecast categorization...")
        for yyyymm in yyyymm_list:
            if var == 't2m' or var =='prcp':
                logger.info("Determinisitc categorization proceeding...")
                categorize_fcst_tercile_det(
                    var=var,
                    yyyymm=yyyymm,
                    fcst_dir=f'{model_out_dir}',
                    stat_dir=f'{model_out_dir}/hindcast',
                    out_dir=f'{verification_out_dir}/CATE/DET',
                )
            else:
                logger.warning(f"Variable {var} not supported for deterministic categorization.")

            logger.info(f"Probabilistic categorization proceeding...")    
            categorize_fcst_tercile_prob(
                var=var,
                yyyymm=yyyymm,
                fcst_dir=f'{model_out_dir}/forecast',
                stat_dir=f'{model_out_dir}/hindcast',
                out_dir=f'{verification_out_dir}/CATE/PROB',
            )
            
            logger.info("[DONE] Forecast categorization completed.")

if __name__=="__main__":
    main()