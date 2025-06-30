#!/usr/bin/env python
from fcstverif.config import *
from fcstverif.data_prep import (
    settingUpGloSea, settingUpOISST, settingUpERA5, computeGloSeaAnomaly,

)
from fcstverif.utils.logging_utils import init_logger
logger = init_logger()

def main():
    
    model_option = input('Proceed model processing? [y/n] ').lower()
    if model_option == 'y' and model=='GS6':

        # ==========================================================
        # ❶ 초기화 날짜 규칙 선택
        # ----------------------------------------------------------
        init_rule = input("Init‑date rule?  (l)ast  |  (m)id (9–17일 월요일)  [l]: ").strip().lower()  
        init_rule = 'mid' if init_rule == 'm' else 'last'                                            
        logger.info(f"[INFO] Init‑date rule = {init_rule}")                                           

        # 1) GloSea
        for var in variables:
            logger.info(f"[INFO] === GloSea : {var} ===")
            # (1) Hindcast : 마지막 월요일(or mid‑rule) 단일‑멤버
            settingUpGloSea.convert_monthly_hindcast(                         
                forecast_start=f'{year_start}-01-01',
                forecast_end  =f'{year_end}-12-31',
                var           =var,
                data_dir      =f'{model_raw_dir}/hindcast',
                file_prefix   ='glos_conv_kma_hcst_6mon_mon_',
                out_dir       =f'{model_out_dir}/hindcast',
                init_rule     =init_rule)                     

            # (2) Forecast : *_mem.grb2 → ens 차원 NetCDF
            settingUpGloSea.convert_monthly_forecast_from_mem(               
                forecast_start=f'{year_start}-01-01',
                forecast_end  =f'{year_end}-12-31',
                var           =var,
                data_dir      =f'{model_raw_dir}/forecast',
                file_prefix   ='glos_conv_kma_fcst_6mon_mon_',
                out_dir       =f'{model_out_dir}/forecast',
                init_rule     =init_rule
                )             

            # 3. Forecast Anomaly from all ensembles
            logger.info(f"[INFO] Processing anomaly for variable: {var}")
            computeGloSeaAnomaly.compute_anomaly(
                var=var,
                year_start=year_start,
                year_end=year_end,
                hindcast_dir=f'{model_out_dir}/hindcast',
                forecast_dir=f'{model_out_dir}/forecast',
                out_dir=f'{model_out_dir}/anomaly'
            )

            

    # # 2) Reanalysis
    
    # ERA5_option = input('Proceed with ERA5/OISST processing? [y/n] ')
    # if ERA5_option == 'y':
    #     for var in variables:
    #         if var == 'sst': # OISST
    #             logger.info("[INFO] Processing OISST anomaly...")
    #             regrid_option = input('OISST regrid to GS grid ... proceed? [y/n]')
    #             if regrid_option.lower() == 'y':
    #                 settingUpOISST.oisst_anomaly(regrid_option)
    #             else:
    #                 logger.info("[INFO] OISST regrid skipped.")

    #         else: # ERA5
    #             logger.info(f"[INFO] Processing ERA5 for variable: {var}")
    #             settingUpERA5.compute_era5_clim_and_anom(
    #                 era5_base_dir=era5_base_dir,
    #                 var=var,
    #                 clim_start=1991,
    #                 clim_end=2020,
    #                 anom_start=year_start,
    #                 anom_end=year_end,
    #                 era5_out_dir=era5_out_dir,
    #                 # clim_out_dir=clim_out_dir,
    #                 # anom_out_dir=obs_anom_dir,
    #                 # tercile_out_dir=tercile_out_dir,
    #                 # std_out_dir=tercile_out_dir
    #             )
       

if __name__ == "__main__":

    main()
