import os
import xarray as xr
import pandas as pd
import logging

from fcstverif.config import *
from fcstverif.src.utils.general_utils import (
    parse_var_level,
    convert_prcp_to_mm_per_day, 
    convert_geopotential_to_m,
    generate_target_grid
)

logger = logging.getLogger("fcstverif")

def rename_dims_coords(da: xr.DataArray) -> xr.DataArray:
    """
    Rename dimension or coordinate names of a DataArray conditionally:
    - 'LATITUDE' or 'latitude' → 'lat'
    - 'LONGITUDE' or 'longitude' → 'lon'
    - 'pressure_level' → 'level'
    """
    rename_dict = {}

    if 'LATITUDE' in da.dims or 'LATITUDE' in da.coords:
        rename_dict['LATITUDE'] = 'lat'
    elif 'latitude' in da.dims or 'latitude' in da.coords:
        rename_dict['latitude'] = 'lat'

    if 'LONGITUDE' in da.dims or 'LONGITUDE' in da.coords:
        rename_dict['LONGITUDE'] = 'lon'
    elif 'longitude' in da.dims or 'longitude' in da.coords:
        rename_dict['longitude'] = 'lon'

    if 'pressure_level' in da.dims or 'pressure_level' in da.coords:
        rename_dict['pressure_level'] = 'level'

    if 'valid_time' in da.dims or 'valid_time' in da.coords:
        rename_dict['valid_time'] = 'time'

    if rename_dict:
        da = da.rename(rename_dict)

    return da

def compute_era5_clim_and_anom(
    era5_base_dir : str,
    var : str,
    clim_start : int,
    clim_end : int,
    anom_start: int,
    anom_end : int,
    era5_out_dir : str,
):
    """
    1) (var) 월별 클라이모 계산
    2) (옵션) 월별 tercile(삼분위) 계산
    3) (var) 월별 표준편차 계산
    4) anom_start~anom_end 구간에서 anomaly 계산

    여기서 var가 'msl'이면 최종 파일 변수명은 'mslp',
                 'tp' 면 'prcp' 로 저장
    """
    os.makedirs(era5_out_dir, exist_ok=True)
    
    # === target grid to regrid OBS ===
    logger.info(f"Checking target grid .....")
    # check if target grid exists; if not, create it
    target_grid_path = f"{model_out_dir}/target_grid.nc"
    if not os.path.isfile(target_grid_path):
        logger.info("[INFO] Target grid not found. Creating target grid ...")
        generate_target_grid(
            nc_file=f"{model_out_dir}/hindcast/ensMem_{var}_anom_{fyears[0]}.nc",
        )
    else:
        logger.info("[INFO] Target grid found.")

        with xr.open_dataset(target_grid_path) as target:
            target_lat, target_lon = target.lat, target.lon
            #print(len(target_lat), len(target_lon))
        if len(target_lat) == 0 or len(target_lon) == 0:
            logger.error("Target grid dimensions are invalid.")
            return

    base, lvl = parse_var_level(var)
    rename_var = ERAvar2rename.get(base, base)
    if lvl is not None:
        var_dir = os.path.join(era5_base_dir, "pressure", base) 
    else:
        var_dir = os.path.join(era5_base_dir, 'surface', rename_var)  
    #print(rename_var)
    # subfolder = get_subfolder_for_var(rename_var)  # 'surface' or 'pressure'
    
    # === read raw data include rename === 
    da_list = []
    for year in range(clim_start, clim_end+1):

        fpath = os.path.join(var_dir, f"{rename_var}_{year}.nc")
        if not os.path.isfile(fpath):
            logger.warning(f"{fpath} not found. skip.")
            continue

        with xr.open_dataset(fpath) as ds:
            # 1) pick the ERA5 field by its token name
            da = ds[rename_var]

            # 2) normalize coordinate/dimension names (e.g., lat/lon, level)
            da = rename_dims_coords(da)

            # 3) for pressure-level variables, slice the requested level (e.g., 500, 300)
            if lvl is not None:
                da = da.sel(level=lvl)

            da.name = rename_var # change ERA5 variable name to universal name
        da_list.append(da)

    if not da_list:
        logger.error(f"No files for {var} in {var_dir}, {clim_start}-{clim_end}")
        return

    # === merge and interpolation ===
    da_merged = xr.concat(da_list, dim='time')
    del da_list
    da_interp = da_merged.interp(lat=target_lat, lon=target_lon, kwargs={"fill_value": "extrapolate"})
    #print(da_interp)
    del da_merged

    # === convert units ===
    if var == 'prcp':
        # ERA5 prcp: m → mm/day
        da_proc = convert_prcp_to_mm_per_day(da_interp, source='ERA5')
        da_proc.attrs['units'] = 'mm/day'
    elif base == 'z':
        # ERA5 geopotential: m2/s2 → m
        da_proc = convert_geopotential_to_m(da_interp, source='ERA5')
        da_proc.attrs['units'] = 'm'
    else:
        da_proc = da_interp
    #print(da_proc)

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
        #print(ds_tercile[var])
        
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

        for year in range(anom_start//100, anom_end//100 + 1):
            # 1) read raw ERA5 of the year
            fcpath = os.path.join(var_dir, f"{rename_var}_{year}.nc")
            if not os.path.isfile(fcpath):
                logger.warning(f"{fcpath} not found for anomaly. skip.")
                continue

            with xr.open_dataset(fcpath) as ds_f:
                da_f = ds_f[rename_var]
                da_f = rename_dims_coords(da_f)

                # slice pressure level if needed
                if lvl is not None:
                    da_f = da_f.sel(level=lvl)
                    
                # remove expver
                if "expver" in da_f.dims:
                    da_f = da_f.sel(expver=1).squeeze(drop=True)

                logger.debug(da_f)

            # 2) interpolation to model grid
            da_f_interp = da_f.interp(lat=target_lat, lon=target_lon, kwargs={"fill_value": "extrapolate"})

            if var == 'prcp':
                da_f_proc = convert_prcp_to_mm_per_day(da_f_interp, source='ERA5')
                da_f_proc.attrs['units'] = 'mm/day'
            elif base == 'z':
                da_f_proc = convert_geopotential_to_m(da_f_interp, source='ERA5')
                da_f_proc.attrs['units'] = 'm'
            else:
                da_f_proc = da_f_interp
        
            # 4) month-wise anomaly using monthly climatology
            da_anom = da_f_proc.groupby('time.month') - da_ref
            ds_anom = da_anom.to_dataset(name=var)
            ds_anom.attrs['description'] = f"ERA5 {var} anomaly from {clim_start}-{clim_end} clim"
            ds_anom[var].attrs['units'] = da_f_proc.attrs.get('units', '')
            
            out_anom_file = os.path.join(era5_out_dir, f"{var}_anom_{year}.nc")
            ds_anom.to_netcdf(out_anom_file)
            logger.info(f"Anomaly saved => {out_anom_file}")
            ds_anom.close()

            # 5) (prcp only) save total field after unit conversion
            if var == 'prcp':
                ds_total = da_f_proc.to_dataset(name=var)

                ds_total.attrs['description'] = f"ERA5 prcp total field (converted from tp)"
                ds_total.attrs['units'] = da_f_proc.attrs.get('units', '')

                total_file = os.path.join(era5_out_dir, f"{var}_total_{year}.nc")
                ds_total.to_netcdf(total_file)
                logger.info(f"Total precipitation saved => {total_file}")
                ds_total.close()



