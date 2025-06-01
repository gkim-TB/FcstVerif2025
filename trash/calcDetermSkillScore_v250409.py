import xarray as xr
import numpy as np
import os
import pandas as pd

from fcstverif.config import *
from fcstverif.utils.logging_utils import init_logger
logger = init_logger()

# -----------------------------
# 영역평균 함수
# -----------------------------
def region_mean(data, region):
    """
    사용자 정의 영역 평균
    region = (lat_s, lat_n, lon_w, lon_e)
    """
    lat_s, lat_n, lon_w, lon_e = region
    return data.sel(lat=slice(lat_s, lat_n), lon=slice(lon_w, lon_e)).mean(dim=['lat', 'lon'])

# -----------------------------
# Bias 계산
# -----------------------------
def calc_bias(fcst, obs, region):
    logger.info("Calculating bias...")
    return region_mean(fcst - obs, region)

# -----------------------------
# RMSE 계산
# -----------------------------
def calc_rmse(fcst, obs, region):
    logger.info("Calculating RMSE...")
    return region_mean(np.sqrt((fcst - obs) ** 2), region)

# -----------------------------
# ACC 계산
# -----------------------------
def calc_acc(fcst, obs, region):
    logger.info("Calculating ACC...")
    numerator = region_mean(fcst * obs, region)
    denominator = np.sqrt(region_mean(fcst**2, region)) * np.sqrt(region_mean(obs**2, region)) + 1e-12
    return numerator / denominator

# -----------------------------
# 종합 스킬 계산 및 저장
# -----------------------------
def compute_regional_scores(var, years, fcst_dir, obs_dir, out_dir, region_name, region):
    """
    ACC, RMSE, Bias 영역평균 계산 후 저장

    Parameters
    ----------
    var : str
        변수명 (ex: t2m)
    years : list
        연도 리스트
    fcst_dir : str
        forecast anomaly 폴더
    obs_dir : str
        observation anomaly 폴더
    out_dir : str
        스킬 저장 폴더
    region : tuple
        (lat_s, lat_n, lon_w, lon_e) 영역
    """

    region_out_dir = os.path.join(out_dir, region_name)
    os.makedirs(region_out_dir, exist_ok=True)

    obs_files = [f"{obs_dir}/{var}_anom_{yyyy}.nc" for yyyy in years]
    if not all(os.path.isfile(obs_file) for obs_file in obs_files):
        logger.warning(f"[WARN] Missing obs file for one or more years in {years}")

    obs_list = []
    for obs_file in obs_files:
        da_obs = xr.open_dataset(obs_file)
        obs_list.append(da_obs)
    ds_obs = xr.concat(obs_list, dim='time')


    for yy in years:
        for mm in range(1, 13):
            yyyymm = f"{yy}{mm:02d}"

            fcst_file = os.path.join(fcst_dir, f"ensMem_{var}_anom_{yyyymm}.nc")
            if not os.path.isfile(fcst_file):
                print(f"[WARN] Missing fcst or obs file for {yyyymm}")
                continue

            logger.info(f"Processing forecast file: {fcst_file}")
            ds_fcst = xr.open_dataset(fcst_file)
            
            fcst_da = ds_fcst[var].squeeze()  # (lead, lat, lon) ensemble mean
            fcst_time = ds_fcst['time']
            lead_vals = fcst_da['lead'].values

            acc_ens, rmse_ens, bias_ens = [], [], []

            for e in range(fcst_da.sizes['ens']):
                acc_list, rmse_list, bias_list = [], [], []
                for lead_idx in range(fcst_da.sizes['lead']):
                    target_time = pd.to_datetime(fcst_time[lead_idx].values)

                    try:
                        obs_sel = ds_obs[var].sel(time=target_time)

                        # lat, lon shape 비교
                        if (obs_sel.lat.shape != fcst_da.lat.shape) or (obs_sel.lon.shape != fcst_da.lon.shape):
                            logger.info(f"[INFO] Interpolating obs grid to match forecast grid for {target_time}")
                            obs_interp = obs_sel.interp(
                            lat=fcst_da.lat,
                            lon=fcst_da.lon,
                            kwargs={"fill_value": "extrapolate"}
                            )
                        else:
                            obs_interp = obs_sel

                    except KeyError:
                        logger.warning(f"[WARN] obs에 {target_time}이 없습니다. ==> NaN 처리합니다.")
                        obs_interp = xr.full_like(fcst_da.isel(lead=lead_idx), np.nan)

                    fcst_single = fcst_da.isel(lead=lead_idx)

                    # ===== 스킬 계산 (영역평균) =====
                    acc = calc_acc(fcst_single, obs_interp, region)
                    rmse = calc_rmse(fcst_single, obs_interp, region)
                    bias = calc_bias(fcst_single, obs_interp, region)

                    acc_list.append(acc)
                    rmse_list.append(rmse)
                    bias_list.append(bias)
                    #print(acc_list)
    
                acc_ens.append(xr.concat(acc_list, dim='lead'))
                print(acc_ens)
                
                #rmse_ens.append(xr.DataArray(rmse_list, dims='lead', coords={'lead': lead_vals}))
                #bias_ens.append(xr.DataArray(bias_list, dims='lead', coords={'lead': lead_vals}))

            # 앙상블 평균 스코어
            acc_ens = xr.concat(acc_ens, dim='ens')#.mean('ens')
            print(acc_ens)
            exit()
            #rmse_mean = xr.concat(rmse_ens, dim='ens').mean('ens')
            #bias_mean = xr.concat(bias_ens, dim='ens').mean('ens')

            # ===== 결과 Dataset 저장 =====
            ds_out = xr.Dataset({
                'acc': xr.concat(acc_ens, dim='ens'),
                'rmse': xr.concat(rmse_ens, dim='ens'),
                'bias': xr.concat(bias_ens, dim='ens'),
                'acc_mean': acc_mean,
                'rmse_mean': rmse_mean,
                'bias_mean': bias_mean
            }, coords={'lead': lead_vals, 'ens': range(fcst_da.sizes['ens'])})

            out_file = os.path.join(region_out_dir, f"ensScore_{var}_{yyyymm}.nc")
            ds_out.to_netcdf(out_file)
            logger.info(f"[SAVE] Ensemble skill score saved to => {out_file}")

            ds_fcst.close()
    ds_obs.close()


# if __name__=='__main__':

#     for region_name, region_box in REGIONS.items():

#         for var in variables:

#             if var == 'sst':
#                 obs_dir = sst_anom_dir
#             else:
#                 obs_dir = obs_anom_dir
                
#             compute_regional_scores(
#                     var=var,
#                     years=fyears,
#                     fcst_dir=fanomaly_dir,
#                     obs_dir=obs_dir,
#                     out_dir=verification_out_dir,
#                     region_name=region_name,
#                     region=region_box
#                     )
