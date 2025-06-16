import os
import xarray as xr
import pandas as pd
import logging

from config import *
from src.utils.general_utils import convert_prcp_to_mm_per_day, convert_geopotential_to_m
logger = logging.getLogger("fcstverif")

def get_subfolder_for_var(var):
    if var in PRESSURE_VARS:
        return 'pressure'
    else:
        return 'surface'

def compute_era5_clim_and_anom(
    era5_base_dir,
    var,
    clim_start,
    clim_end,
    anom_start,
    anom_end,
    era5_out_dir,
):
    """
    1) (var) 월별 클라이모 계산
    2) (옵션) 월별 tercile(삼분위) 계산
    3) (var) 월별 표준편차 계산
    4) anom_start~anom_end 구간에서 anomaly 계산

    여기서 var가 'msl'이면 최종 파일 변수명은 'mslp',
                 'tp' 면 'prcp' 로 저장
    """

    rename_var = ERAvar2rename.get(var, var)

    os.makedirs(era5_out_dir, exist_ok=True)

    subfolder = get_subfolder_for_var(var)  # 'surface' or 'pressure'
    var_dir = os.path.join(era5_base_dir, subfolder, rename_var)

    # === target grid ===
    logger.info(f"Checking target grid .....")
    with xr.open_dataset(f'{root_dir}/target_grid.nc') as target:
        target_lat, target_lon = target.lat, target.lon
        print(len(target_lat), len(target_lon))
    
    # === read raw data include rename === 
    da_list = []
    for year in range(clim_start, clim_end+1):

        fpath = os.path.join(var_dir, f"{rename_var}_{year}.nc")
        if not os.path.isfile(fpath):
            logger.warning(f"{fpath} not found. skip.")
            continue
        with xr.open_dataset(fpath) as ds:
            da = ds[rename_var]
            da = da.rename({'LATITUDE': 'lat', 'LONGITUDE': 'lon'})
            da.name = rename_var # change ERA5 variable name to universal name
        da_list.append(da)

    if not da_list:
        logger.error(f"No files for {var} in {var_dir}, {clim_start}-{clim_end}")
        return

    # === merge and interpolation ===
    da_merged = xr.concat(da_list, dim='time')
    da_interp = da_merged.interp(lat=target_lat, lon=target_lon, kwargs={"fill_value": "extrapolate"})
    #print(da_interp)
    del da_merged, da_list

    # === convert units ===
    if var == 'prcp':
        # ERA5 prcp: m → mm/day
        da_proc = convert_prcp_to_mm_per_day(da_interp, source='ERA5')
        da_proc.attrs['units'] = 'mm/day'
    elif var in ['z','zg','geopotential']:
        # ERA5 geopotential: m2/s2 → m
        da_proc = convert_geopotential_to_m(da_interp, source='ERA5')
        da_proc.attrs['units'] = 'm'
    else:
        da_proc = da_interp
    print(da_proc)

    # --- climatology ---
    # === average by month (month=1..12) ===
    ds_clim = da_proc.groupby('time.month').mean('time').to_dataset(name=var)
    ds_clim.attrs['description'] = f"ERA5 {var} climatology {clim_start}-{clim_end}"
    
    clim_file = os.path.join(era5_out_dir, f"{var}_clim_{clim_start}_{clim_end}.nc")
    ds_clim.to_netcdf(clim_file)
    logger.info(f"Climatology saved => {clim_file}")
    ds_clim.close()

    # --- statistics --- 
    # if precipiation => from total field (da_merged_interp) => (month, quantile, lat, lon)
    # if t2m or any other variables => from total field (da_merged_interp) => (month, std, lat, lon)
    if var != 'prcp':
        ds_std = da_proc.groupby('time.month').std('time').to_dataset(name=var)
        ds_std.attrs['description'] = f"ERA5 {var} monthly std {clim_start}-{clim_end}"  
        ds_std[var].attrs['units'] = da_proc.attrs.get('units', '')

        std_file = os.path.join(era5_out_dir, f"{var}_std_{clim_start}_{clim_end}.nc")
        ds_std.to_netcdf(std_file)
        logger.info(f"Standard Deviation saved => {std_file}")
        ds_std.close()

    if var == 'prcp':
        da_tercile = da_proc.groupby('time.month').quantile([0.3333, 0.6667], dim='time')
        da_tercile = da_tercile.rename({'quantile': 'tercile'})
        da_tercile.coords['tercile'] = ['lower', 'upper'] # lower = 33.33%, upper = 66.67%

        ds_tercile = da_tercile.to_dataset(name=var)
        ds_tercile.attrs['description'] = f"ERA5 {var} tercile (33%,67%) {clim_start}-{clim_end}"
        ds_tercile[var].attrs['units'] = da_proc.attrs.get('units', '')
        print(ds_tercile[var])
        
        tercile_file = os.path.join(era5_out_dir, f"{var}_tercile_{clim_start}_{clim_end}.nc")
        ds_tercile.to_netcdf(tercile_file)
        logger.info(f"Tercile saved => {tercile_file}")
        ds_tercile.close()
   
        # # 가우시안 분위수 기준값: μ ± 0.43σ ≈ 33.33%, 66.67%
        # lower = ds_clim[var] - 0.43 * ds_std[var]
        # upper = ds_clim[var] + 0.43 * ds_std[var]

        # # (month, gaus, lat, lon) 형태로 생성
        # da_gaus = xr.concat([lower, upper], dim='gaus')
        # da_gaus = da_gaus.assign_coords(gaus=['lower', 'upper'])

        # ds_gaus = da_gaus.to_dataset(name=var)
        # ds_gaus.attrs['description'] = f"ERA5 {var} gaussian-based tercile (mean±0.43σ) {clim_start}-{clim_end}"
        
        # gaus_file = os.path.join(era5_out_dir, f"{var}_gaus_{clim_start}_{clim_end}.nc")
        # ds_gaus.to_netcdf(gaus_file)
        # logger.info(f"Gaussian-based tercile saved => {gaus_file}")
    
    # --- anomaly & total precipitation --- 
    with xr.open_dataset(clim_file) as ds_ref:
        da_ref = ds_ref[var]

        for year in range(anom_start, anom_end+1):
            # === read raw data by year ===
            fcpath = os.path.join(var_dir, f"{rename_var}_{year}.nc")
            if not os.path.isfile(fcpath):
                logger.warning(f"{fcpath} not found for anomaly. skip.")
                continue
            with xr.open_dataset(fcpath) as ds_f:
                da_f = ds_f[rename_var].rename({'LATITUDE': 'lat', 'LONGITUDE': 'lon'})
            # === interpolation to model grid ===
            da_f_interp = da_f.interp(lat=target_lat, lon=target_lon, kwargs={"fill_value": "extrapolate"})

            if var == 'prcp':
                da_f_proc = convert_prcp_to_mm_per_day(da_f_interp, source='ERA5')
                da_f_proc.attrs['units'] = 'mm/day'
            elif var in ['z','zg','geopotential']:
                da_f_proc = convert_geopotential_to_m(da_f_interp, source='ERA5')
                da_f_proc.attrs['units'] = 'm'
            else:
                da_f_proc = da_f_interp
        
            # === calulate anomaly ===
            da_anom = da_f_proc.groupby('time.month') - da_ref
            ds_anom = da_anom.to_dataset(name=var)
            ds_anom.attrs['description'] = f"ERA5 {var} anomaly from {clim_start}-{clim_end} clim"
            ds_anom[var].attrs['units'] = da_f_proc.attrs.get('units', '')
            
            out_anom_file = os.path.join(era5_out_dir, f"{var}_anom_{year}.nc")
            ds_anom.to_netcdf(out_anom_file)
            logger.info(f"Anomaly saved => {out_anom_file}")
            ds_anom.close()

            # === save precipitation total file ===
            if var == 'prcp':
                ds_total = da_f_proc.to_dataset(name=var)

                ds_total.attrs['description'] = f"ERA5 prcp total field (converted from tp)"
                ds_total.attrs['units'] = da_f_proc.attrs.get('units', '')

                total_file = os.path.join(era5_out_dir, f"{var}_total_{year}.nc")
                ds_total.to_netcdf(total_file)
                logger.info(f"Total precipitation saved => {total_file}")
                ds_total.close()



