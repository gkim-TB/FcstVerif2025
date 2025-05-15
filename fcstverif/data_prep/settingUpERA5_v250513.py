import os
import xarray as xr
import pandas as pd

from fcstverif.config import *
from fcstverif.utils.general_utils import convert_prcp_to_mm_per_day, convert_geopotential_to_m
from fcstverif.utils.logging_utils import init_logger
logger = init_logger()

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
    # clim_out_dir = era5_out_dir
    # anom_out_dir = era5_out_dir
    # tercile_out_dir = era5_out_dir
    # std_out_dir = era5_out_dir
    # os.makedirs(tercile_out_dir, exist_ok=True)
    # os.makedirs(std_out_dir, exist_ok=True)

    subfolder = get_subfolder_for_var(var)  # 'surface' or 'pressure'
    var_dir = os.path.join(era5_base_dir, subfolder, rename_var)

    # === target grid ===
    gridfile = f'{work_dir}/target_grid.nc'
    target = xr.open_dataset(gridfile)
    target_lat = target.lat
    target_lon = target.lon
    

    ##########
    # 1) 클라이모
    ##########
    clim_file = os.path.join(era5_out_dir, f"{var}_clim_{clim_start}_{clim_end}.nc")

    ds_list = []
    for year in range(clim_start, clim_end+1):
        fpath = os.path.join(var_dir, f"{rename_var}_{year}.nc")
        if os.path.isfile(fpath):
            ds_list.append(xr.open_dataset(fpath))
        else:
            logger.warning(f"{fpath} not found. skip.")

    if not ds_list:
        logger.error(f"No files for {var} in {var_dir}, {clim_start}-{clim_end}")
        return

    ds_merged = xr.concat(ds_list, dim='time')
    da_merged = ds_merged[rename_var]
    da_merged = da_merged.rename({'LATITUDE': 'lat', 'LONGITUDE': 'lon'})

    for ds_ in ds_list:
        ds_.close()
    ds_merged.close()

    # === 복간 ===
    da_merged_interp = da_merged.interp(lat=target_lat, lon=target_lon, kwargs={"fill_value": "extrapolate"})

    # 월별 평균 (month=1..12)
    da_clim = da_merged_interp.groupby('time.month').mean('time')
    ds_clim = da_clim.to_dataset(name=var)
    ds_clim.attrs['description'] = f"ERA5 {var} climatology {clim_start}-{clim_end}"

    if var == 'prcp':
        # ERA5 prcp: m → mm/day
        ds_clim[var] = convert_prcp_to_mm_per_day(ds_clim[var], source='ERA5')
    elif var in ['z','zg','geopotential']:
        # ERA5 geopotential: m2/s2 → m
        ds_clim[var] = convert_geopotential_to_m(ds_clim[var], source='ERA5')

    ds_clim.to_netcdf(clim_file)
    logger.info(f"Climatology saved => {clim_file}")


    #######################
    # 2) Tercile 계산
    #######################
    # 예: 33%, 67% 지점 => (month, quantile, lat, lon)
    # xarray의 quantile 기능 사용. groupby('time.month')로 년도를 축으로 0.33,0.67 percentiles
    # 그런데 위에서 이미 concat한 da_merged에 time차원이 있음
    # => 같은 da_merged에서 groupby('time.month').quantile()를 바로 수행
    #    (단, tercile을 구하기 위해서는 mean() 대신 raw 데이터 사용)
    if var == 'prcp':
        quantiles = [0.3333, 0.6667]  # 33%, 67%
        da_tercile = da_merged_interp.groupby('time.month').quantile(quantiles, dim='time')
        # 결과 shape: (month, quantile, lat, lon)
        # quantile=2(0.3333, 0.6667)
        # rename coords
        da_tercile = da_tercile.rename({'quantile': 'tercile'})
        da_tercile.coords['tercile'] = ['tercile1', 'tercile2'] # tercile1 = 33.33%, tercile2 = 66.67%

        # Dataset 변환
        ds_tercile = da_tercile.to_dataset(name=var)
        ds_tercile.attrs['description'] = f"ERA5 {var} tercile (33%,67%) {clim_start}-{clim_end}"
        #ds_tercile = ds_tercile.rename({'LATITUDE': 'lat', 'LONGITUDE': 'lon'})

        if var == 'prcp':
            ds_tercile[var] = convert_prcp_to_mm_per_day(ds_tercile[var], source='ERA5')
        elif var in ['z','zg','geopotential']:
            ds_tercile[var] = convert_geopotential_to_m(ds_tercile[var], source='ERA5')

        tercile_file = os.path.join(era5_out_dir, f"{var}_tercile_{clim_start}_{clim_end}.nc")
        ds_tercile.to_netcdf(tercile_file)
        logger.info(f"Tercile saved => {tercile_file}")

    #######################
    # std 계산
    #######################
    #if var == 't2m':
    # 월별 표준편차 => groupby('time.month').std('time')
    da_std = da_merged_interp.groupby('time.month').std('time')
    ds_std = da_std.to_dataset(name=var)
    ds_std.attrs['description'] = f"ERA5 {var} monthly std {clim_start}-{clim_end}"  # Updated description to match variable

    if var == 'prcp':
        ds_std[var] = convert_prcp_to_mm_per_day(ds_std[var], source='ERA5')
    elif var in ['z','zg','geopotential']:
        ds_std[var] = convert_geopotential_to_m(ds_std[var], source='ERA5')

    std_file = os.path.join(era5_out_dir, f"{var}_std_{clim_start}_{clim_end}.nc")
    ds_std.to_netcdf(std_file)
    logger.info(f"Standard Deviation saved => {std_file}")

    ##########
    # 3) 아노말리
    ##########
    ds_clim_open = xr.open_dataset(clim_file)
    da_clim_open = ds_clim_open[var]  # (month, lat, lon)

    for year in range(anom_start, anom_end+1):
        fcpath = os.path.join(var_dir, f"{rename_var}_{year}.nc")
        if not os.path.isfile(fcpath):
            logger.warning(f"{fcpath} not found for anomaly. skip.")
            continue

        ds_fc = xr.open_dataset(fcpath)
        da_fc = ds_fc[rename_var]
        da_fc = da_fc.rename({'LATITUDE': 'lat', 'LONGITUDE': 'lon'})

        # === 복간 ===
        da_fc_interp = da_fc.interp(lat=target_lat, lon=target_lon, kwargs={"fill_value": "extrapolate"})

        if var == 'prcp':
            da_fc_interp = convert_prcp_to_mm_per_day(da_fc_interp, source='ERA5')
        elif var in ['z','zg','geopotential']:
            da_fc_interp = convert_geopotential_to_m(da_fc_interp, source='ERA5')
    
        da_anom = da_fc_interp.groupby('time.month') - da_clim_open
        ds_anom = da_anom.to_dataset(name=var)
        ds_anom.attrs['description'] = f"ERA5 {var} anomaly from {clim_start}-{clim_end} clim"
        #ds_anom = ds_anom.rename({'LATITUDE': 'lat', 'LONGITUDE': 'lon'})

        
        out_anom_file = os.path.join(era5_out_dir, f"{var}_anom_{year}.nc")
        ds_anom.to_netcdf(out_anom_file)
        logger.info(f"Anomaly saved => {out_anom_file}")

        ds_fc.close()
    ds_clim_open.close()

# if __name__ == '__main__':

#     # 단순히 for 루프에서 함수 호출
#     for var in variables:
#         compute_era5_clim_and_anom(
#             era5_base_dir=era5_base_dir,
#             var=var,
#             clim_start=1991,
#             clim_end=2020,
#             anom_start=year_start,
#             anom_end=year_end,
#             clim_out_dir=clim_out_dir,
#             anom_out_dir=obs_anom_dir,
#             tercile_out_dir=tercile_out_dir,
#             std_out_dir=tercile_out_dir
#         )

