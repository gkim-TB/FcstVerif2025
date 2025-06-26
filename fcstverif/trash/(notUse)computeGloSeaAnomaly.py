import os
import xarray as xr
import pandas as pd

from config import *
from src.utils.logging_utils import init_logger
logger = init_logger()


def compute_anomaly(
    var,
    year_start,
    year_end,
    hindcast_dir,
    forecast_dir,
    out_dir
):
    """
    이미 1993~2016 기간 평균된 hindcast(클라이모) 자료와
    특정 연-월 forecast 자료를 열어 anomaly = forecast - hindcast 계산 후 저장.

    파일 이름 예:
      - hindcast: {hindcast_dir}/ensMean_{var}_{YYYYMM}.nc
      - forecast: {forecast_dir}/ensMem_{var}_{YYYYMM}.nc
    """

    os.makedirs(out_dir, exist_ok=True)

    # year_start ~ year_end 범위의 월 목록 생성
    # ex) 2022-01 ~ 2022-03
    dates = pd.date_range(
        start=f"{year_start}-01",
        end=f"{year_end}-12",
        freq='MS'
    )

    for date in dates:
        yyyy = date.year
        mm = date.month
        yyyymm_str = f"{yyyy}{mm:02d}"

        # 파일 경로
        hind_file = os.path.join(hindcast_dir, f"ensMean_{var}_{yyyymm_str}.nc")
        fcst_file = os.path.join(forecast_dir, f"ensMem_{var}_{yyyymm_str}.nc")
        # if var == 'sst':
        #     hind_file = os.path.join(hindcast_dir, f"ensMean_{var}_{yyyymm_str}.nc")
        #     fcst_file = os.path.join(forecast_dir, f"ensMem_{var}_{yyyymm_str}.nc")

        # 두 파일이 모두 존재해야 anomaly를 계산
        if not os.path.isfile(hind_file):
            logger.warning(f"Hindcast file not found: {hind_file}")
            continue
        if not os.path.isfile(fcst_file):
            logger.warning(f"Forecast file not found: {fcst_file}")
            continue

        # 파일 열기
        ds_hind = xr.open_dataset(hind_file)
        ds_fcst = xr.open_dataset(fcst_file)

        # anomaly 계산
        ds_anom = ds_fcst - ds_hind
    
        # 예: "fcst - hind(1993~2016 mean)"라는 메타정보 기록
        ds_anom.attrs['description'] = f"{var} anomaly (forecast - hindcast 1993-2016 avg)"
        ds_anom.attrs['source_fcst'] = fcst_file
        ds_anom.attrs['source_hind'] = hind_file

        # 출력 파일 이름 (ex. "anom_t15m_202201.nc")
        out_fname = os.path.join(out_dir, f"ensMem_{var}_anom_{yyyymm_str}.nc")
        ds_anom.to_netcdf(out_fname)
        logger.info(f"Saved anomaly: {out_fname}")

    logger.info("Done. Anomaly files are in: %s", out_dir)

# if __name__ == '__main__':

#     for var in variables:    
#         compute_anomaly(        
#                 var=var,
#                 year_start=year_start,
#                 year_end=year_end,
#                 hindcast_dir=hindcast_dir,
#                 forecast_dir=forecast_dir,
#                 out_dir=fanomaly_dir
#                 )

