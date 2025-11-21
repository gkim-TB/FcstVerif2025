import xarray as xr
import numpy as np
import os
import pandas as pd
from fcstverif.config import fyears, REGIONS
from fcstverif.src.utils.general_utils import load_obs_data, clip_to_region, get_combined_mask, match_common_times_by_month

import logging
from fcstverif.src.utils.logging_utils import init_logger, get_logger

def _clip_inputs(var: str, region: str, fcst: xr.DataArray, obs: xr.DataArray) -> tuple:
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
    return clip_to_region(fcst, region, var), clip_to_region(obs, region, var)

def calc_rmse_vec(var: str, region: str, fcst: xr.DataArray, obs: xr.DataArray) -> xr.DataArray:
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
    fcst_clip, obs_clip = _clip_inputs(var, region, fcst, obs)
    return np.sqrt(((fcst_clip - obs_clip)**2).mean(("lat","lon")))

def calc_acc_vec(var: str, region: str, fcst: xr.DataArray, obs: xr.DataArray) -> xr.DataArray:
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
    fcst_clip, obs_clip = _clip_inputs(var, region, fcst, obs)
    numerator = (fcst_clip * obs_clip).mean(("lat","lon"))
    denominator = np.sqrt((fcst_clip**2).mean(("lat","lon"))) * np.sqrt((obs_clip**2).mean(("lat","lon"))) + 1e-12
    return numerator / denominator

def compute_deterministic_scores(
        var: str,
        yyyymm_list: list,
        model_name: str,
        fcst_dir: str,
        obs_dir: str,
        out_dir: str,
        region_name: str,
        lsmask=None
        ):
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
    logger = logging.getLogger("fcstverif")
    logger.info(f"Calculating deterministic skill scores for var={var}, region={region_name}")
    
    # directory to save results
    # -> /OUT/{region_name}/{var}/ensScore_det_{var}_{yyyymm}.nc
    os.makedirs(out_dir, exist_ok=True)
    
    # load observation data
    try:
        oyears = fyears.tolist()
        oyears.append(max(oyears)+1) 
        # oyears: Extends the observation data period to the following year 
        #         to account for forecasts initialized in the second half of the year (July onward).
        obs_data = load_obs_data(
            var, oyears, obs_dir, 
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
            with xr.open_dataset(fcst_file) as ds_fcst:
                fcst_time = ds_fcst['time'] # (lead,) datetime64
                fcst_da = ds_fcst[var].squeeze("init", drop=True) # (ens, init, lead, lat, lon) -> (ens, lead, lat, lon)
                fcst_da = fcst_da.assign_coords(time=('lead', fcst_time.values)).swap_dims({'lead': 'time'})  # → (ens, time, lat, lon)

                # Subsetting common time points between forecast and observation
                logger.debug("fcst_time type: %s, dtype: %s, sample: %s", type(fcst_time), getattr(fcst_time, "dtype", None), fcst_time.values[:3])
                fc_idx, ob_idx, common_time = match_common_times_by_month(fcst_time, obs_data.time.values)
                fc_times = pd.to_datetime(fcst_time.values)
                missing_times = [pd.to_datetime(t) for i,t in enumerate(fc_times) if i not in fc_idx]
                logger.debug(f"MISSING MATCH: {missing_times}")
                if len(missing_times):
                    logger.warning(f"[OBS] Missing observation months for : {[str(pd.to_datetime(t).date()) for t in missing_times]}")

                if common_time.size == 0:
                    logger.warning(f"[SKIP] {yyyymm}: No data => skipping calculation")
                    continue

                # select by index then reassign normalized month-start timestamps for both arrays
                fcst_da = fcst_da.isel(time=fc_idx).assign_coords(time=("time", common_time))
                obs_sub  = obs_data.isel(time=ob_idx).assign_coords(time=("time", common_time))
                
                if len(common_time) == 0:
                    logger.warning(f"[SKIP] {yyyymm}: No data => skipping calculation")
                    continue
                    
                if lsmask is not None:
                    fcst_da = fcst_da.where(lsmask)
                    obs_sub = obs_sub.where(lsmask)
                    
                # Calculate skill score
                #logger.info("Calculating skill scores: ACC, RMSE, ...")
                acc  = calc_acc_vec(var, region_name, fcst_da, obs_sub)       # (ens, time)
                rmse = calc_rmse_vec(var, region_name, fcst_da, obs_sub)     # (ens, time)

                # calculate skill score for ensemble mean
                acc_mean = calc_acc_vec(var, region_name, fcst_da.mean("ens"), obs_sub)  # (ens, time)
                rmse_mean = calc_rmse_vec(var, region_name, fcst_da.mean("ens"), obs_sub) 
                
                
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
            source_out_file = os.path.join(out_dir, f"ensScore_det_{var}_{yyyymm}.nc")
            ds_out.to_netcdf(source_out_file)
            logger.info(f"[SAVE] Ensemble skill score (ACC, RMSE) saved to => {source_out_file}")