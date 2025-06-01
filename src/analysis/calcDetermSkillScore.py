import xarray as xr
import numpy as np
import os
import pandas as pd
from config import fyears, REGIONS
from src.utils.general_utils import load_obs_data, clip_to_region
from src.utils.logging_utils import init_logger
logger = init_logger()

def _clip_inputs(fcst, obs, region):
    """
    Clip both forecast and observation DataArrays to a given spatial region.

    Parameters
    ----------
    fcst : xarray.DataArray
        Forecast data with dimensions including 'lat' and 'lon'.
    obs : xarray.DataArray
        Observation data with dimensions including 'lat' and 'lon'.
    region : str or tuple
        Region name (e.g., "GL") or bounding box tuple (lat_min, lat_max, lon_min, lon_max).

    Returns
    -------
    fcst_clip, obs_clip : xarray.DataArray
        Region-clipped forecast and observation.
    """
    return clip_to_region(fcst, region), clip_to_region(obs, region)

def calc_rmse_vec(fcst, obs, region):
    """
    Calculate RMSE (Root Mean Square Error) between forecast and observation
    over a specified region.

    Returns RMSE as a spatial average over lat-lon grid.

    Parameters
    ----------
    fcst : xarray.DataArray
    obs : xarray.DataArray
    region : str or tuple

    Returns
    -------
    xarray.DataArray
        RMSE over region (dims other than lat/lon preserved).
    """
    fcst_clip, obs_clip = _clip_inputs(fcst, obs, region)
    return np.sqrt(((fcst_clip - obs_clip)**2).mean(("lat","lon")))

def calc_acc_vec(fcst, obs, region):
    """
    Calculate Anomaly Correlation Coefficient (ACC) between forecast and observation
    over a specified region.

    Assumes fcst and obs are already anomalies (mean-removed).

    Parameters
    ----------
    fcst : xarray.DataArray
    obs : xarray.DataArray
    region : str or tuple

    Returns
    -------
    xarray.DataArray
        ACC value per dimension excluding lat/lon.
    """
    fcst_clip, obs_clip = _clip_inputs(fcst, obs, region)
    numerator = (fcst_clip * obs_clip).mean(("lat","lon"))
    denominator = np.sqrt((fcst_clip**2).mean(("lat","lon"))) * np.sqrt((obs_clip**2).mean(("lat","lon"))) + 1e-12
    return numerator / denominator

def compute_deterministic_scores(var, yyyymm_list, fcst_dir, obs_dir, out_dir, region_name):
    """
    Compute deterministic skill scores (ACC, RMSE, Bias) using ensMem_*.nc files
    over a specified region, 
    for each initialized month and save the result as NetCDF.

    Parameters
    ----------
    var : str
        Variable name (e.g., 't2m')
    yyyymm_list : list of str
        List of initialized forecast months (e.g., ['202201', '202202', ...])
    fcst_dir : str
        Directory containing forecast ensemble anomaly files
    obs_dir : str
        Directory containing observation anomaly files
    out_dir : str
        Root output directory for skill scores
    region_name : str
        Name of spatial region to evaluate (must match REGIONS)
    """

    # directory to save results
    # -> /OUT/{region_name}/{var}/ensScore_det_{var}_{yyyymm}.nc
    os.makedirs(out_dir, exist_ok=True)
    # region_out_dir = os.path.join(out_dir, region_name, var)
    # os.makedirs(region_out_dir, exist_ok=True)
    
    # load observation data
    try:
        obs_data = load_obs_data(
            var, fyears, obs_dir, 
            suffix='anom',
            var_suffix=var
            )
    except FileNotFoundError as e:
        logger.warning(str(e))
        return

    # main loop for verification
    for yyyymm in yyyymm_list:
            # load forecast ensemble data
            fcst_file = os.path.join(fcst_dir, f"ensMem_{var}_anom_{yyyymm}.nc")
            if not os.path.isfile(fcst_file):
                logger.warning(f"[SKIP] {fcst_file} not found.")
                continue

            logger.info(f"[ENS FCST] Processing : {fcst_file}")
            ds_fcst = xr.open_dataset(fcst_file)
            fcst_time = ds_fcst['time'] # (lead,) datetime64
            fcst_da = ds_fcst[var].squeeze("init", drop=True) # (ens, init, lead, lat, lon) -> (ens, lead, lat, lon)
            fcst_da = fcst_da.assign_coords(time=('lead', fcst_time.values)).swap_dims({'lead': 'time'})  # → (ens, time, lat, lon)

            # Subsetting common time
            common_times = [t for t in fcst_time.values if t in obs_data.time.values]
            missing_times = [t for t in fcst_time.values if t not in obs_data.time.values]   
            if missing_times:
                logger.warning(
                    f"[OBS] Missing observation times for : {[str(pd.to_datetime(t).date()) for t in missing_times]}"
                            )

            fcst_da = fcst_da.sel(time=common_times)#.reset_coords(drop=True)
            obs_sub = obs_data.sel(time=common_times)#.reset_coords(drop=True)
            #print(fcst_da.time)
            #print(obs_sub.time)

            if len(common_times) == 0:
                logger.warning(f"[SKIP] {yyyymm}: No data => skipping calculation")
                continue
                
            # Calculate skill score
            #logger.info("Calculating skill scores: ACC, RMSE, ...")
            acc  = calc_acc_vec(fcst_da, obs_sub, region_name)       # (ens, time)
            rmse = calc_rmse_vec(fcst_da, obs_sub, region_name)     # (ens, time)

            # calculate skill score for ensemble mean
            acc_mean = calc_acc_vec(fcst_da.mean("ens"), obs_sub, region_name)
            rmse_mean = calc_rmse_vec(fcst_da.mean("ens"), obs_sub, region_name)
            
            
            # Results Dataset -> save scores
            ds_out = xr.Dataset({
                "acc": acc,
                "rmse": rmse,
                "acc_mean": acc_mean,
                "rmse_mean": rmse_mean,
            }, coords={"time": ("time", fcst_time.values),
                       "lead": ("lead", ds_fcst['lead'].values),
                       "ens": acc.ens
                       }
            )

            # remove unnecessary variables
            if "month" in ds_out:
                ds_out = ds_out.drop_vars("month")

            #lead_vals = fcst_da['lead'].values
            #ds_out = ds_out.assign_coords(lead=('lead', lead_vals))

            # save output file
            scoure_out_file = os.path.join(out_dir, f"ensScore_det_{var}_{yyyymm}.nc")
            ds_out.to_netcdf(scoure_out_file)
            logger.info(f"[SAVE] Ensemble skill score (ACC, RMSE) saved to => {scoure_out_file}")
