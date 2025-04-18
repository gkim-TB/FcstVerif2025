#!/usr/bin/env python
from fcstverif.config import *
from fcstverif.data_prep import (
    settingUpGloSea, settingUpOISST, settingUpERA5, computeGloSeaAnomaly,

)
from fcstverif.utils.logging_utils import init_logger
logger = init_logger()

def main():
    
    model_option = input('Proceed model processing? [y/n] ')
    if model_option == 'y':
        # 1) GloSea
        for var in variables:
            logger.info(f"[INFO] Processing GloSea for variable: {var}")
            # settingUpGloSea.make_monthly_ensemble_forecast(
            #     forecast_start=f'{year_start}-01-01',
            #     forecast_end=f'{year_end}-12-31',
            #     var=var,
            #     data_dir=f'{base_dir}/GS6_KMApost_raw/hindcast/',
            #     file_prefix='glos_conv_kma_hcst_6mon_mon_',
            #     out_dir=hindcast_dir,
            #     grid_option=True
            #     )
            
            # settingUpGloSea.make_monthly_ensemble_forecast(
            #     forecast_start=f'{year_start}-01-01',
            #     forecast_end=f'{year_end}-12-31',
            #     var=var,
            #     data_dir=f'{base_dir}/GS6_KMApost_raw/forecast/',
            #     file_prefix='glos_conv_kma_fcst_6mon_mon_',
            #     out_dir=hindcast_dir,
            #     grid_option=True
            # )

            # 1. Hindcast - 마지막 주 월요일만 사용
            settingUpGloSea.make_monthly_ensemble_hindcast_last_monday_only(
                forecast_start=f'{year_start}-01-01',
                forecast_end=f'{year_end}-12-31',
                var=var,
                data_dir=f'{base_dir}/GS6_KMApost_raw/hindcast/',
                file_prefix='glos_conv_kma_hcst_6mon_mon_',
                out_dir=hindcast_dir,
                grid_option=True
            )
            
            # 2. Forecast - *_mem.grb2 사용
            settingUpGloSea.make_monthly_ensemble_forecast_from_mem(
                forecast_start=f'{year_start}-01-01',
                forecast_end=f'{year_end}-12-31',
                var=var,
                data_dir=f'{base_dir}/GS6_KMApost_raw/forecast/',
                file_prefix='glos_conv_kma_fcst_6mon_mon_',
                out_dir=forecast_dir
            )
            # 3. Forecast Anomaly from all ensembles
            logger.info(f"[INFO] Processing anomaly for variable: {var}")
            computeGloSeaAnomaly.compute_anomaly(
                var=var,
                year_start=year_start,
                year_end=year_end,
                hindcast_dir=hindcast_dir,
                forecast_dir=forecast_dir,
                out_dir=fanomaly_dir
            )
       
    # 2) Reanalysis
    
    ERA5_option = input('Proceed with ERA5/OISST processing? [y/n] ')
    if ERA5_option == 'y':
        for var in variables:
            if var == 'sst': # OISST
                logger.info("[INFO] Processing OISST anomaly...")
                regrid_option = input('OISST regrid to GS grid ... proceed? [y/n]')
                if regrid_option.lower() == 'y':
                    settingUpOISST.oisst_anomaly(regrid_option)
                else:
                    logger.info("[INFO] OISST regrid skipped.")

            else: # ERA5
                logger.info(f"[INFO] Processing ERA5 for variable: {var}")
                settingUpERA5.compute_era5_clim_and_anom(
                    era5_base_dir=era5_base_dir,
                    var=var,
                    clim_start=1991,
                    clim_end=2020,
                    anom_start=year_start,
                    anom_end=year_end,
                    era5_out_dir=era5_out_dir,
                    # clim_out_dir=clim_out_dir,
                    # anom_out_dir=obs_anom_dir,
                    # tercile_out_dir=tercile_out_dir,
                    # std_out_dir=tercile_out_dir
                )
       

if __name__ == "__main__":

    main()
