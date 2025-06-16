#!/usr/bin/env python
import argparse
import os
import logging

from fcstverif.config import *
from fcstverif.src.data_prep import settingUpGloSea, settingUpOISST, settingUpERA5
from fcstverif.src.utils.logging_utils import init_logger


def parse_args():
    parser = argparse.ArgumentParser(description="Preprocessing for single var")
    parser.add_argument("--var", required=True, choices=variables, help="Variable to process")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging") 
    return parser.parse_args()

def run_model_preprocessing(var):
    if model != 'GS6':
        logger.warning("MODEL NOT SUPPORTED")
        return

    init_rule = input("Init‑date rule?  (l)ast  |  (m)id (9–17일 월요일)  [l]: ").strip().lower()
    init_rule = 'mid' if init_rule == 'm' else 'last'
    logger.info(f"[INFO] Init‑date rule = {init_rule}")

    logger.info(f"[INFO] === GloSea : {var} ===")
    forecast_range = dict(
        forecast_start=f'{year_start}-01-01',
        forecast_end=f'{year_end}-12-31',
        var=var,
        init_rule=init_rule
    )

    # 1. Hindcast
    settingUpGloSea.convert_monthly_hindcast(
        **forecast_range,
        data_dir=f'{model_raw_dir}/hindcast', 
        file_prefix='glos_conv_kma_hcst_6mon_mon_',
        out_dir=f'{model_out_dir}/hindcast'
    )

    # 2. Forecast
    settingUpGloSea.convert_monthly_forecast_from_mem(
        **forecast_range,
        data_dir=f'{model_raw_dir}/forecast',
        file_prefix='glos_conv_kma_fcst_6mon_mon_',
        out_dir=f'{model_out_dir}/forecast'
    )

    # 3. Anomaly
    logger.info(f"[INFO] Processing anomaly for variable: {var}")
    settingUpGloSea.compute_anomaly(
        var=var,
        year_start=year_start,
        year_end=year_end,
        hindcast_dir=f'{model_out_dir}/hindcast',
        forecast_dir=f'{model_out_dir}/forecast',
        out_dir=f'{model_out_dir}/anomaly'
    )

def run_obs_preprocessing(var):
    if var == 'sst':
        missing_years = [
            year for year in range(year_start, year_end + 1)
            if not os.path.exists(f"{sst_out_dir}/sst_anom_{year}.nc")
        ]
        regrid = 'y' if missing_years else 'n'
        logger.info(f"[INFO] Processing OISST regridding ({regrid}) ...")
        settingUpOISST.oisst_anomaly(regrid_option=regrid)
    else:
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

def main():
    args = parse_args()
    log_level = logging.DEBUG if args.debug else logging.INFO
    global logger
    logger = init_logger(level=log_level)
    var = args.var

    if input('Proceed model processing? [y/n] ').strip().lower() == 'y':
        run_model_preprocessing(var)

    if input('Proceed ERA5/OISST processing? [y/n] ').strip().lower() == 'y':
        run_obs_preprocessing(var)

if __name__ == '__main__':
    main()
