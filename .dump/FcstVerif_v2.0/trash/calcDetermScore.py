import xarray as xr
import numpy as np
import pandas as pd
import os

def calc_rmse(fcst, obs):
    """RMSE 계산"""
    valid_mask = ~np.isnan(fcst) & ~np.isnan(obs)
    fcst = fcst.where(valid_mask)
    obs = obs.where(valid_mask)

    rmse = np.sqrt((fcst - obs) ** 2)
    return rmse

def calc_acc(fcst, obs):
    """ACC 계산"""

    x_flat = fcst.stack(points=('lat','lon'))
    y_flat = obs.stack(points=('lat','lon'))
    

    results = xr.apply_ufunc(
        pearsonr(x, y),
        x_flat,
        y_flat,
        input_core_dims=[['points'], ['points']],
        output_core_dims = [[], []],
        vectorize=True,
    )


    return acc

def calc_msss(fcst, obs, eps=1e-6):
    """
    Gridpoint-wise MSSS 계산
    hindcast가 이미 climatology이므로 climatology anomaly는 0으로 간주함

    Parameters
    ----------
    fcst : xarray.DataArray (lat, lon)
        forecast anomaly
    obs : xarray.DataArray
        obs anomaly (lat, lon)
    eps : float, optional
        division 안정성을 위한 최소값 (default=1e-6)

    Returns
    -------
    msss : xarray.DataArray (lat, lon)
        gridpoint-wise MSSS
    """

    valid_mask = ~np.isnan(fcst) & ~np.isnan(obs)
    fcst = fcst.where(valid_mask)
    obs = obs.where(valid_mask)

    # MSE(fcst, obs)
    mse_fcst = ((fcst - obs)**2)

    mse_ref = (obs**2)
    mse_ref = mse_ref.where(mse_ref > eps, eps)

    msss_val = 1 - (mse_fcst / mse_ref)
    return msss_val

def compute_score_for_years(var, years, fcst_dir, obs_dir, out_dir):
    results = {}

    for yy in years:
        for mm in range(1, 4):  # 1월 ~ 12월
            yyyymm = f"{yy}{mm:02d}"

            fcst_file = os.path.join(fcst_dir, f"{var}_anom_{yyyymm}.nc")
            obs_file  = os.path.join(obs_dir,  f"{var}_anom_{yy}.nc")
            #print(fcst_file)
            print(obs_file)

            if not os.path.isfile(fcst_file) or not os.path.isfile(obs_file):
                print(f"[WARN] Missing fcst or obs file for {yyyymm}")
                continue

            ds_fcst = xr.open_dataset(fcst_file)
            ds_obs  = xr.open_dataset(obs_file)
           # print(ds_fcst)
            print(ds_obs)

            # fcst: time=해당 월 하나만 있음
            fcst_da = ds_fcst[var].squeeze()  # (time=1, lead, lat, lon)
            fcst_time = ds_fcst['time']         # (lead=6)

            msss_list = []
            acc_list = []
            rmse_list = []
            # lead별 계산
            for lead_idx in range(fcst_da.sizes['lead']):
                lead_val = int(fcst_da['lead'][lead_idx].values)
                target_time = pd.to_datetime(fcst_time[lead_idx].values)

                try:
                    obs_sel = ds_obs[var].sel(time=target_time)
                except KeyError:
                    print(f"[WARN] obs에 {target_time}이 없습니다.")
                    continue

                # obs → fcst grid로 보간
                obs_interp = obs_sel.interp(lat=fcst_da.lat, lon=fcst_da.lon, kwargs={"fill_value": "extrapolate"})

                # 해당 lead에 대한 fcst
                fcst_single = fcst_da.isel(lead=lead_idx)
                print(obs_interp)
                #print(fcst_single)

                print("fcst min/max:", fcst_single.min().values, fcst_single.max().values)
                print("obs min/max:", obs_interp.min().values, obs_interp.max().values)
                print("obs interp NaN 갯수:", np.isnan(obs_interp).sum().values)
                print("obs interp NaN 갯수:", np.isnan(obs_interp).sum().values)
                print("mse_ref <= 0 grid 갯수:", ((obs_interp**2) <= 0).sum().values)

                # MSSS 계산
#               msss = calc_msss(fcst_single, obs_interp)
                acc  = calc_acc(fcst_single, obs_interp)
                rmse = calc_rmse(fcst_single, obs_interp)

                # msss_list.append(msss)
                acc_list.append(acc)
                rmse_list.append(rmse)

            if acc_list:
                da_acc = xr.concat(acc_list, dim='lead').assign_coords(lead=fcst_da['lead'])
                da_acc.name = 'acc'
                acc_file = os.path.join(out_dir, "ACC", f"acc_{var}_{yyyymm}.nc")
                print(acc_file)
                da_acc.to_netcdf(acc_file)
                print(f"[INFO] Saved ACC file => {acc_file}")

                da_rmse = xr.concat(rmse_list, dim='lead').assign_coords(lead=fcst_da['lead'])
                da_rmse.name = 'rmse'
                rmse_file = os.path.join(out_dir, "RMSE", f"rmse_{var}_{yyyymm}.nc")
                da_rmse.to_netcdf(rmse_file)
                print(f"[INFO] Saved RMSE file => {rmse_file}")

                # msss save if need
                #
                #
                #
                #
                #


if __name__ == '__main__':

    variables = ['t2m']#, 'prcp','mslp']
    years = [2022]

    fcst_dir = '/home/gkim/2025FcstVerif/GS6_KMApost_monthly/anomaly/'
    obs_dir  = '/home/gkim/2025FcstVerif/ERA5_monthly_GSgrid/anom/'
    out_dir  = '/home/gkim/2025FcstVerif/FcstVerif_v2.0/OUT/'

    for var in variables:
        scores =  compute_score_for_years(var=var, years=years,
                                           fcst_dir=fcst_dir, obs_dir=obs_dir, out_dir=out_dir)

