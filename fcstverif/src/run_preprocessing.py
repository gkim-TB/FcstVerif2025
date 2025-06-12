#!/usr/bin/env python
import argparse
from config import *
from src.data_prep import (
    settingUpGloSea, settingUpOISST, settingUpERA5,
)
from src.utils.logging_utils import init_logger
logger = init_logger()

# 🔽 argparse 
parser = argparse.ArgumentParser(description="Preprocessing for single var")
parser.add_argument("--var", required=True, help="Variable to process", choices=variables)
args = parser.parse_args()
var = args.var

def main():
    model_option = input('Proceed model processing? [y/n] ').lower()
    if model_option == 'y' and model=='GS6':

        # 초기화 규칙 선택 (interactive 유지)
        init_rule = input("Init‑date rule?  (l)ast  |  (m)id (9–17일 월요일)  [l]: ").strip().lower()
        init_rule = 'mid' if init_rule == 'm' else 'last'
        logger.info(f"[INFO] Init‑date rule = {init_rule}")

        # 🔽 var loop 대신 단일 var 처리
        logger.info(f"[INFO] === GloSea : {var} ===")
        # (1) Hindcast
        settingUpGloSea.convert_monthly_hindcast(
            forecast_start=f'{year_start}-01-01',
            forecast_end  =f'{year_end}-12-31',
            var           =var,
            data_dir      =f'{model_raw_dir}/hindcast',
            file_prefix   ='glos_conv_kma_hcst_6mon_mon_',
            out_dir       =f'{model_out_dir}/hindcast',
            init_rule     =init_rule
        )

        # (2) Forecast
        settingUpGloSea.convert_monthly_forecast_from_mem(
            forecast_start=f'{year_start}-01-01',
            forecast_end  =f'{year_end}-12-31',
            var           =var,
            data_dir      =f'{model_raw_dir}/forecast',
            file_prefix   ='glos_conv_kma_fcst_6mon_mon_',
            out_dir       =f'{model_out_dir}/forecast',
            init_rule     =init_rule
        )

        # (3) Anomaly
        logger.info(f"[INFO] Processing anomaly for variable: {var}")
        settingUpGloSea.compute_anomaly(
            var=var,
            year_start=year_start,
            year_end=year_end,
            hindcast_dir=f'{model_out_dir}/hindcast',
            forecast_dir=f'{model_out_dir}/forecast',
            out_dir=f'{model_out_dir}/anomaly'
        )
    elif model_option == 'y' and model!='GS6':
        print("MODEL NOT SUPPORTED")

    # 2) ERA5/OISST processing
    era5_option = input('Proceed ERA5/OISST processing? [y/n] ').strip().lower()
    if era5_option == 'y':
        if var == 'sst':
            # OISST
            #regrid_option = input('OISST regrid to GS grid? [y/n] ').strip().lower()
            if any(not os.path.exists(f"{sst_out_dir}/sst_anom_{year}.nc") for year in range(year_start, year_end+1)):
                logger.info(f"[INFO] Processing OISST regridding ...")
                settingUpOISST.oisst_anomaly(regrid_option='y')
            else:
                settingUpOISST.oisst_anomaly(regrid_option='n')
        else:
            # ERA5
            logger.info(f"[INFO] Processing ERA5 for variable: {var}")
            settingUpERA5.compute_era5_clim_and_anom(
                era5_base_dir=era5_base_dir,
                var=var,
                clim_start=clim_start,
                clim_end=clim_end,
                anom_start=year_start,
                anom_end=year_end,
                era5_out_dir=era5_out_dir
            )

if __name__ == '__main__':
    main()
