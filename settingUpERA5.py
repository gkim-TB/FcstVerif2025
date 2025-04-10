import os
import xarray as xr
import pandas as pd

from config import era5_base_dir, clim_out_dir, tercile_out_dir, std_out_dir, obs_anom_dir, variables, ERAvar2rename, year_start, year_end, PRESSURE_VARS

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
    clim_out_dir,
    anom_out_dir,
    tercile_out_dir,
    std_out_dir,
):
    """
    1) (var) 월별 클라이모 계산
    2) tercile(삼분위) 계산
    3) (옵션) t2m이면 표준편차도 계산
    4) anom_start~anom_end 구간에서 anomaly 계산

    여기서 var가 'msl'이면 최종 파일 변수명은 'mslp',
                 'tp' 면 'prcp' 로 저장
    """

    rename_var = ERAvar2rename.get(var, var)

    os.makedirs(clim_out_dir, exist_ok=True)
    os.makedirs(anom_out_dir, exist_ok=True)
    os.makedirs(tercile_out_dir, exist_ok=True)
    os.makedirs(std_out_dir, exist_ok=True)

    subfolder = get_subfolder_for_var(var)  # 'surface' or 'pressure'
    var_dir = os.path.join(era5_base_dir, subfolder, rename_var)

    ##########
    # 1) 클라이모
    ##########
    clim_file = os.path.join(clim_out_dir, f"{var}_clim_{clim_start}_{clim_end}.nc")

    ds_list = []
    for year in range(clim_start, clim_end+1):
        fpath = os.path.join(var_dir, f"{rename_var}_{year}.nc")
        if os.path.isfile(fpath):
            ds_list.append(xr.open_dataset(fpath))
        else:
            print(f"[WARNING] {fpath} not found. skip.")

    if not ds_list:
        print(f"[ERROR] No files for {var} in {var_dir}, {clim_start}-{clim_end}")
        return

    ds_merged = xr.concat(ds_list, dim='time')
    da_merged = ds_merged[rename_var]
    # 월별 평균 (month=1..12)
    da_clim = da_merged.groupby('time.month').mean('time')
    ds_clim = da_clim.to_dataset(name=var)
    ds_clim.attrs['description'] = f"ERA5 {var} climatology {clim_start}-{clim_end}"
    ds_clim = ds_clim.rename({'LATITUDE': 'lat', 'LONGITUDE': 'lon'})
    ds_clim.to_netcdf(clim_file)
    print(f"[INFO] Climatology saved => {clim_file}")

    for ds_ in ds_list:
        ds_.close()
    ds_merged.close()

    #######################
    # 2) Tercile 계산
    #######################
    # 예: 33%, 67% 지점 => (month, quantile, lat, lon)
    # xarray의 quantile 기능 사용. groupby('time.month')로 년도를 축으로 0.33,0.67 percentiles
    # 그런데 위에서 이미 concat한 da_merged에 time차원이 있음
    # => 같은 da_merged에서 groupby('time.month').quantile()를 바로 수행
    #    (단, tercile을 구하기 위해서는 mean() 대신 raw 데이터 사용)
    #    만약 메모리 문제가 없다면 da_merged를 그대로 쓰면 됨
    #    아래는 da_merged 재활용 예시
    quantiles = [0.3333, 0.6667]  # 33%, 67%
    da_tercile = da_merged.groupby('time.month').quantile(quantiles, dim='time')
    # 결과 shape: (month, quantile, lat, lon)
    # quantile=2(0.3333, 0.6667)
    # rename coords
    da_tercile = da_tercile.rename({'quantile': 'tercile'})
    da_tercile.coords['tercile'] = ['tercile1', 'tercile2']

    # Dataset 변환
    ds_tercile = da_tercile.to_dataset(name=var)
    ds_tercile.attrs['description'] = f"ERA5 {var} tercile (33%,67%) {clim_start}-{clim_end}"
    ds_tercile = ds_tercile.rename({'LATITUDE': 'lat', 'LONGITUDE': 'lon'})

    tercile_file = os.path.join(tercile_out_dir, f"{var}_tercile_{clim_start}_{clim_end}.nc")
    ds_tercile.to_netcdf(tercile_file)
    print(f"[INFO] Tercile saved => {tercile_file}")

    #######################
    # (옵션) t2m이면 std 계산
    #######################
    if var == 't2m':
        # 월별 표준편차 => groupby('time.month').std('time')
        da_std = da_merged.groupby('time.month').std('time')
        ds_std = da_std.to_dataset(name='t2m')
        ds_std.attrs['description'] = f"ERA5 t2m monthly std {clim_start}-{clim_end}"
        ds_std = ds_std.rename({'LATITUDE': 'lat', 'LONGITUDE': 'lon'})

        std_file = os.path.join(std_out_dir, f"t2m_std_{clim_start}_{clim_end}.nc")
        ds_std.to_netcdf(std_file)
        print(f"[INFO] Standard Deviation saved => {std_file}")

    ##########
    # 3) 아노말리
    ##########
    ds_clim_open = xr.open_dataset(clim_file)
    da_clim_open = ds_clim_open[var]  # (month, lat, lon)

    for year in range(anom_start, anom_end+1):
        fcpath = os.path.join(var_dir, f"{rename_var}_{year}.nc")
        if not os.path.isfile(fcpath):
            print(f"[WARNING] {fcpath} not found for anomaly. skip.")
            continue

        ds_fc = xr.open_dataset(fcpath)
        da_fc = ds_fc[rename_var]
        da_fc = da_fc.rename({'LATITUDE': 'lat', 'LONGITUDE': 'lon'})

        da_anom = da_fc.groupby('time.month') - da_clim_open
        ds_anom = da_anom.to_dataset(name=var)
        ds_anom.attrs['description'] = f"ERA5 {var} anomaly from {clim_start}-{clim_end} clim"
        #ds_anom = ds_anom.rename({'LATITUDE': 'lat', 'LONGITUDE': 'lon'})

        out_anom_file = os.path.join(anom_out_dir, f"{var}_anom_{year}.nc")
        ds_anom.to_netcdf(out_anom_file)
        print(f"[INFO] Anomaly saved => {out_anom_file}")

        ds_fc.close()
    ds_clim_open.close()

if __name__ == '__main__':

    # 단순히 for 루프에서 함수 호출
    for var in variables:
        compute_era5_clim_and_anom(
            era5_base_dir=era5_base_dir,
            var=var,
            clim_start=1991,
            clim_end=2020,
            anom_start=year_start,
            anom_end=year_end,
            clim_out_dir=clim_out_dir,
            anom_out_dir=obs_anom_dir,
            tercile_out_dir=tercile_out_dir,
            std_out_dir=tercile_out_dir
        )

