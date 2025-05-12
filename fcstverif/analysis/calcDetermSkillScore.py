import xarray as xr
import numpy as np
import os
import pandas as pd
from fcstverif.utils.general_utils import load_obs_data
from fcstverif.utils.logging_utils import init_logger
logger = init_logger()

def region_mean(data, region):
    lat_s, lat_n, lon_w, lon_e = region
    return data.sel(lat=slice(lat_s, lat_n), lon=slice(lon_w, lon_e)).mean(dim=["lat", "lon"])

def calc_rmse_vec(fcst, obs, region):
    return np.sqrt(region_mean((fcst - obs)**2, region))

def calc_bias_vec(fcst, obs, region):
    return region_mean(fcst - obs, region)

def calc_acc_vec(fcst, obs, region):
    f_anom = fcst - region_mean(fcst, region)
    o_anom = obs - region_mean(obs, region)
    num = region_mean(f_anom * o_anom, region)
    denom = np.sqrt(region_mean(f_anom**2, region)) * np.sqrt(region_mean(o_anom**2, region)) + 1e-12
    return num / denom

def compute_regional_scores_from_ensemble(var, years, fcst_dir, obs_dir, out_dir, region_name, region):
    """
    벡터화된 방식으로 ensMem_*.nc 파일을 기반으로 ACC, RMSE, Bias 계산
    결과 저장: (ens, lead) + 평균 (lead)
    """
    region_out_dir = os.path.join(out_dir, region_name)
    os.makedirs(region_out_dir, exist_ok=True)

    # obs_list = []
    # for yyyy in years:
    #     obs_file = f"{obs_dir}/{var}_anom_{yyyy}.nc"
    #     if os.path.isfile(obs_file):
    #         obs_list.append(xr.open_dataset(obs_file))
    #     else:
    #         logger.warning(f"[WARN] Obs file missing: {obs_file}")
    # ds_obs = xr.concat(obs_list, dim='time')
    try:
        ds_obs = load_obs_data(var, years, obs_dir, suffix='anom')
    except FileNotFoundError as e:
        logger.warning(str(e))
        return

    for yy in years:
        for mm in range(1, 13):
            yyyymm = f"{yy}{mm:02d}"
            fcst_file = os.path.join(fcst_dir, f"ensMem_{var}_anom_{yyyymm}.nc")

            if not os.path.isfile(fcst_file):
                logger.warning(f"[SKIP] {fcst_file} 없음.")
                continue

            logger.info(f"[ENS] Processing forecast file: {fcst_file}")
            ds_fcst = xr.open_dataset(fcst_file)
            fcst_da = ds_fcst[var]  # (ens, init, lead, lat, lon) -> (ens, lead, lat, lon)
            
            # 1. lead → time 변환 (기존 coord)
            fcst_time = ds_fcst['time'] # (lead,) datetime64
            fcst_da = fcst_da.squeeze("init", drop=True)  # (ens, lead, lat, lon)
            fcst_da = fcst_da.assign_coords(time=('lead', fcst_time.values)).swap_dims({'lead': 'time'})  # → (ens, time, lat, lon)

            # 2. obs도 time 기준으로 맞춤
            obs_sub = ds_obs[var].reindex(time=fcst_time.values)  # → (time, lat, lon)

            # 누락된 시점 확인 (optional)
            missing_times = fcst_time.to_index().difference(ds_obs.time.to_index())
            if len(missing_times) > 0:
                logger.warning(f"[WARN] obs에 {missing_times.strftime('%Y-%m-%d').tolist()} 이 누락되어 NaN 처리됨")

            # === 스킬 계산 (벡터 연산) ===
            logger.info("Calculating ACC (vectorized)...")
            acc = calc_acc_vec(fcst_da, obs_sub, region)       # (ens, time)
            logger.info("Calculating RMSE (vectorized)...")
            rmse = calc_rmse_vec(fcst_da, obs_sub, region)     # (ens, time)
            logger.info("Calculating Bias (vectorized)...")
            bias = calc_bias_vec(fcst_da, obs_sub, region)     # (ens, time)
            #print(acc)

            # 앙상블 평균
            acc_mean = calc_acc_vec(fcst_da.mean("ens"), obs_sub, region)
            rmse_mean = rmse.mean("ens")
            bias_mean = bias.mean("ens")

            # 결과 Dataset
            ds_out = xr.Dataset({
                "acc": acc,
                "rmse": rmse,
                "bias": bias,
                "acc_mean": acc_mean,
                "rmse_mean": rmse_mean,
                "bias_mean": bias_mean
            }, coords={"time": ("time", fcst_time.values),
                       "lead": ("lead", ds_fcst['lead'].values),
                       "ens": acc.ens
                       }
            )

            if "month" in ds_out:
                ds_out = ds_out.drop_vars("month")


            lead_vals = fcst_da['lead'].values
            ds_out = ds_out.assign_coords(lead=('lead', lead_vals))

            out_file = os.path.join(region_out_dir, f"ensScore_{var}_{yyyymm}.nc")
            ds_out.to_netcdf(out_file)
            logger.info(f"[SAVE] Ensemble skill score saved to => {out_file}")

            ds_fcst.close()

    ds_obs.close()
