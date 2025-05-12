import pygrib
import xarray as xr
import numpy as np
import pandas as pd
import os

from fcstverif.config import *
from fcstverif.utils.logging_utils import init_logger
logger = init_logger()

def open_kma_fcst_to_climpred_format(grib_file, init_date_str, var):
    """
    glos_conv_kma_fcst_6mon_mon_t15m_YYYYMMDD.grb2 (앙상블평균) 파일을 열어서
    climpred용 [init, lead, time, lat, lon] 형태로 변환 예시.
    lead는 1~6(6개월 예측), time은 init_date + (lead개월) 시점.
    """

    rename_var = GSvar2rename.get(var,var)

    # 1) pygrib로 파일 열기
    grbs = pygrib.open(grib_file)
    # t15m에 해당하는 grib name을 확인해 아래 변수명 수정
    if rename_var not in var2grib_name:
        raise ValueError(f"[ERROR] var='{var}'에 해당하는 GRIB name이 var2grib_name에 없습니다.")
    grb_var_name = var2grib_name[rename_var]
    
    # 2) GRIB 메시지 선택 (예: 리드 6개)
    selected_grbs = grbs.select(name=grb_var_name)
    n_grbs = len(selected_grbs)
    if n_grbs != 6:
        raise ValueError(f"기대한 리드 개수(6개)와 다릅니다. 실제 GRIB 메시지 수: {n_grbs}")
    
    # 3) init 및 time 계산
    init_date = pd.to_datetime(init_date_str).replace(day=1)
    # lead=1이면 init 후 1개월 시점, lead=2면 2개월 시점 등
    lead_coords = [1, 2, 3, 4, 5, 6]
    # time 좌표: 예) init 2022-01-03 → 2022-02-01, 2022-03-01, ...
    #  실제 예측 파일에서 start_date(초기달+1)와 정확히 맞추려면 상황에 따라 조정
    valid_times = pd.date_range(init_date + pd.DateOffset(months=1),
                                periods=n_grbs, freq='MS')

    # 4) lat/lon 추출 (첫 번째 메시지 기준)
    lats, lons = selected_grbs[0].latlons()

    # 5) lead별 DataArray 생성
    da_list = []
    for i, grb in enumerate(selected_grbs):

        # (1) missing value 확인
        #     GRIB마다 missingValue가 없을 수도 있으므로 try-except
        try:
            missing_value = grb.missingValue
        except AttributeError:
            missing_value = None

        # (2) parameterUnits로 단위 가져오기
        #     없을 수도 있으니 기본 None 처리
        try:
            param_units = grb.parameterUnits
        except AttributeError:
            param_units = None

        data = grb.values

        da = xr.DataArray(
            data,
            dims=['lat','lon'],
            coords={
                'lat': (['lat'], lats[:, 0]),
                'lon': (['lon'], lons[0, :])
            }
        )

        # (4) 속성 기록: FillValue, units 등
        #     xarray는 메모리 상에서 NaN을 missing으로 취급
        #     NetCDF 저장 시 '_FillValue'를 적용하려면 encoding 설정도 가능
        if missing_value is not None:
            da.attrs['_FillValue'] = np.nan  # xarray 관례상 NaN 사용
        if param_units is not None:
            da.attrs['units'] = param_units

        da_list.append(da)
    
    grbs.close()  # 파일 닫기

    # 6) lead 차원으로 concat
    #    shape → (lead=6, lat, lon)
    da_3d = xr.concat(da_list, dim='lead')
    da_3d = da_3d.assign_coords(
        lead=('lead', lead_coords),
        # time을 lead와 같은 길이를 갖는 별도의 좌표로 추가
        time=('lead', valid_times)
    )
    # time을 단순 좌표로 두되, 필요 시 main dimension으로 교체하려면
    #   da_3d = da_3d.swap_dims({'lead': 'time'})
    # 와 같이 사용 가능

    # 7) init 차원을 확장
    #    shape → (init=1, lead=6, lat, lon) + time(lead)
    da_4d = da_3d.expand_dims('init').assign_coords(init=('init', [init_date]))
    # climpred가 lead가 달 단위임을 알 수 있게 attrs를 부여
    da_4d['lead'].attrs['units'] = 'months'

    # 8) Dataset으로 변환 (변수명 t15m 가정)
    ds_out = da_4d.to_dataset(name=var)
    # time을 좌표로 유지하도록 명시
    ds_out = ds_out.set_coords('time')

    return ds_out

def make_monthly_ensemble_forecast(
    forecast_start,
    forecast_end,
    var,
    data_dir,
    file_prefix,
    out_dir,
    grid_option=None
):
    """
    매주 월요일 초기화된 KMA 예측 GRIB2 파일들을 읽어,
    한 달 안의 자료를 앙상블로 묶어 월별 Dataset 생성 및 저장.

    Parameters
    ----------
    forecast_start : str
        예: '2022-01-01'
    forecast_end : str
        예: '2022-03-30'
    var : str
        예측 변수명. t15m, mslp, prcp 등
    data_dir : str
        GRIB2 상위 경로. ex) '/home/gkim/2025FcstVerif/GS6_KMApost_raw/hindcast'
    file_prefix : str
        파일 접두사. ex) 'glos_conv_kma_hcst_6mon_mon_' 또는 'glos_conv_kma_fcst_6mon_mon_'
    out_dir : str
        결과 NetCDF 저장 폴더. 기본값 '.' (현재 폴더)


    Returns
    -------
    None
    """

    rename_var = GSvar2rename.get(var, var)

    # 1) 매주 월요일 날짜 리스트
    weekly_mondays = pd.date_range(forecast_start, forecast_end, freq='W-MON')

    # 2) 월별 마지막 월요일 리스트 (거꾸로 순회하며 month 바뀌면 기록)
    current_month = None
    last_mondays = []
    for day in weekly_mondays[::-1]:
        if current_month != day.month:
            last_mondays.append(day)
            current_month = day.month
    last_mondays = sorted(last_mondays)

    logger.info(f"\n Processing var={var}, prefix={file_prefix}")
    logger.info(f"weekly_mondays: {weekly_mondays}")
    logger.info(f"last_mondays: {last_mondays}")

    # 한 달 치 월요일 자료(ensemble) 임시 저장
    monthly_ens_list = []

    for wmonday in weekly_mondays:
        # ex) glos_conv_kma_hcst_6mon_mon_t15m_20220103.grb2  (hindcast)
        #     glos_conv_kma_fcst_6mon_mon_t15m_20220103.grb2  (forecast)

        grib_file_path = os.path.join(
            data_dir,
            rename_var,
            f"{file_prefix}{rename_var}_{wmonday.strftime('%Y%m%d')}.grb2"
        )
        if not os.path.isfile(grib_file_path):
            logger.warning(f"[WARNING] File not found: {grib_file_path}")
            continue

        # 3) GRIB -> climpred 형식 DS 변환
        ds = open_kma_fcst_to_climpred_format(
                grib_file_path, 
                wmonday.strftime("%Y-%m-%d"), 
                var = var
                )

        # 4) 임시 리스트에 추가 (ens 멤버로 봄)
        monthly_ens_list.append(ds)

        # 5) 만약 이번 날짜가 그 달의 마지막 월요일이면 => ens 차원으로 concat & ens 평균
        if wmonday in last_mondays:
            # 예: 2022-01-31이면, 1월 마지막 월요일
            # monthly_ens_list에는 1월 월요일들의 ds가 들어 있음
            if not monthly_ens_list:
                logger.warning(f"No data accumulated for month={wmonday.month}")
                continue

            # (ens, init, lead, lat, lon), time 등
            ds_ens = xr.concat(monthly_ens_list, dim='ens')

            # 앙상블 전체(ens)도 저장
            out_fname = os.path.join(
                out_dir,
                f"ens_{var}_{wmonday.strftime('%Y%m')}.nc"
            )
            ds_ens.to_netcdf(out_fname)

            # 앙상블 평균 저장
            ds_ens_mean = ds_ens.mean(dim='ens')
            out_fname = os.path.join(
                out_dir,
                f"ensMean_{var}_{wmonday.strftime('%Y%m')}.nc"
            )
            logger.info(f" --> Save monthly ensemble mean to: {out_fname}")
            print(ds_ens_mean)

            # 최초 1회에 한해 위경도 정보를 target_grid.nc로 저장
            if grid_option and not os.path.isfile(os.path.join(work_dir, "target_grid.nc")):
                logger.info(" --> Saving target grid (lat/lon) to target_grid.nc")
                target_grid = ds_ens_mean[['lat', 'lon']]#.to_dataset()
                target_grid.to_netcdf(os.path.join(work_dir, "target_grid.nc"))

            # ds_ens_mean 저장
            ds_ens_mean.to_netcdf(out_fname)

            # 다음 달을 위해 리스트 초기화
            monthly_ens_list = []


def make_monthly_ensemble_forecast_from_mem(
        forecast_start, 
        forecast_end, 
        var, 
        data_dir, 
        file_prefix, 
        out_dir
        ):
    
    rename_var = GSvar2rename.get(var, var)
    weekly_mondays = pd.date_range(forecast_start, forecast_end, freq='W-MON')

    current_month = None
    last_mondays = []
    for day in weekly_mondays[::-1]:
        if current_month != day.month:
            last_mondays.append(day)
            current_month = day.month
    last_mondays = sorted(last_mondays)

    logger.info(f"[MEM] Processing var={var}, prefix={file_prefix}")

    for wmonday in last_mondays:
        grib_file_path = os.path.join(data_dir, rename_var, f"{file_prefix}{rename_var}_{wmonday.strftime('%Y%m%d')}_mem.grb2")
        if not os.path.isfile(grib_file_path):
            logger.warning(f"[MEM] File not found: {grib_file_path}")
            continue

        grbs = pygrib.open(grib_file_path)
        grb_var_name = var2grib_name[rename_var]
        selected_grbs = grbs.select(name=grb_var_name)
        logger.info(f"{file_prefix}{rename_var}_{wmonday.strftime('%Y%m%d')}_mem.grb2 => Selected GRIB messages count: {len(selected_grbs)}")
        grbs.close()

        # if len(selected_grbs) != 252:
        #     logger.warning(f"[MEM] Unexpected number of GRIB messages: {len(selected_grbs)}. Skipping.")
        #     continue

        init_date = wmonday.replace(day=1)
        leads = [1, 2, 3, 4, 5, 6]
        times = pd.date_range(init_date + pd.DateOffset(months=1), periods=6, freq='MS')

        lead_per_member = 6
        n_total = len(selected_grbs)

        # 예외 처리: 메시지 수가 6으로 나누어떨어지지 않으면 경고
        if n_total % lead_per_member != 0:
           logger.warning(f"[MEM] Total GRIB message count {n_total} is not divisible by {lead_per_member}")
           return
        
        n_ens = n_total // lead_per_member
        logger.info(f"[MEM] Detected {n_ens} ensemble members")

        ens_members = []
        for e in range(n_ens):
            member_grbs = selected_grbs[e*lead_per_member:(e+1)*lead_per_member]

            da_list = []
            for grb in member_grbs:
                data = grb.values
                lats, lons = grb.latlons()
                da = xr.DataArray(data, dims=['lat','lon'], coords={'lat': lats[:, 0], 'lon': lons[0, :]})
                da_list.append(da)
            
            da_3d = xr.concat(da_list, dim='lead')
            da_3d = da_3d.assign_coords(lead=('lead', leads), time=('lead', times))
            da_4d = da_3d.expand_dims('init').assign_coords(init=('init', [init_date]))
            ens_members.append(da_4d)

        ds_ens = xr.concat(ens_members, dim='ens')
        ds_ens.name = var
        ds_ens = ds_ens.to_dataset()
        ds_ens = ds_ens.set_coords('time')

        out_fname_ens = os.path.join(out_dir, f"ensMem_{var}_{wmonday.strftime('%Y%m')}.nc")
        #out_fname_mean = os.path.join(out_dir, f"ensMeanMEM_{var}_{wmonday.strftime('%Y%m')}.nc")

        ds_ens.to_netcdf(out_fname_ens)
        logger.info(f"[MEM] Saved full ensemble: {out_fname_ens}")

        #ds_ens_mean = ds_ens.mean(dim='ens')
        #ds_ens_mean.to_netcdf(out_fname_mean)
        #logger.info(f"[MEM] Saved ensemble mean: {out_fname_mean}")

def make_monthly_ensemble_hindcast_last_monday_only(
    forecast_start,
    forecast_end,
    var,
    data_dir,
    file_prefix,
    out_dir,
    grid_option=None
):
    
    rename_var = GSvar2rename.get(var, var)
    weekly_mondays = pd.date_range(forecast_start, forecast_end, freq='W-MON')

    # 각 월의 마지막 월요일만 추출
    current_month = None
    last_mondays = []
    for day in weekly_mondays[::-1]:
        if current_month != day.month:
            last_mondays.append(day)
            current_month = day.month
    last_mondays = sorted(last_mondays)

    logger.info(f"[HIND] Last-Monday-only mode activated for var={var}")

    for wmonday in last_mondays:
        grib_file_path = os.path.join(
            data_dir,
            rename_var,
            f"{file_prefix}{rename_var}_{wmonday.strftime('%Y%m%d')}.grb2"
        )
        if not os.path.isfile(grib_file_path):
            logger.warning(f"[HIND] File not found: {grib_file_path}")
            continue

        # GRIB → DS
        ds = open_kma_fcst_to_climpred_format(
            grib_file_path,
            wmonday.strftime("%Y-%m-%d"),
            var=var
        )
        # 차원: (init=1, lead=6, lat, lon), time=lead개 좌표

        out_fname_mean = os.path.join(
            out_dir,
            f"ensMean_{var}_{wmonday.strftime('%Y%m')}.nc"
        )
        logger.info(f"[HIND] Saving single-member hindcast => {out_fname_mean}")

        # 저장
        ds.to_netcdf(out_fname_mean)

        # 최초 1회 lat/lon 저장
        if grid_option and not os.path.isfile(os.path.join(work_dir, "target_grid.nc")):
            logger.info(" --> Saving target grid (lat/lon) to target_grid.nc")
            target_grid = ds[['lat', 'lon']]
            target_grid.to_netcdf(os.path.join(work_dir, "target_grid.nc"))

 
#if __name__ == '__main__':
#
#    # Hindcast 
#    for var in variables:
#        make_monthly_ensemble_forecast(
#            forecast_start=f'{year_start}-01-01',
#            forecast_end=f'{year_end}-12-31',
#            var=var,
#            data_dir=f'{base_dir}/GS6_KMApost_raw/hindcast/',
#            file_prefix='glos_conv_kma_hcst_6mon_mon_',
#            out_dir=hindcast_dir,
#            grid_option=True
#        )

    # Forecast
#    for var in variables:
#        make_monthly_ensemble_forecast(
#            forecast_start=f'{year_start}-01-01',
#            forecast_end=f'{year_end}-12-31',
#            var=var,
#            data_dir=f'{base_dir}/GS6_KMApost_raw/forecast/',
#            file_prefix='glos_conv_kma_fcst_6mon_mon_',
#            out_dir=forecast_dir
#        )

