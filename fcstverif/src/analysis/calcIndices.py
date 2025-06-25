import numpy as np
import xarray as xr
from scipy.stats import pearsonr
from sklearn.metrics import mean_squared_error
import matplotlib.pyplot as plt
import os
from config import fyears

from src.utils.general_utils import get_combined_mask, load_obs_data

from src.utils.logging_utils import init_logger
logger = init_logger()

# Define ENSO and IOD regions
# region box: (latS, latN, lonL, lonR)
ENSO_BOX = (-5, 5, 190, 240)  # Niño 3.4 영역
IOD_WEST_BOX = (-10, 10, 50, 70)
IOD_EAST_BOX = (-10, 0, 90, 110)

def calculate_enso_index(sst, mask=None):
    """Calculate ENSO index based on SST anomalies in a specific region."""
    latS, latN, lonL, lonR = ENSO_BOX  # (lat_min, lat_max, lon_min, lon_max)
    sst_region = sst.sel(lat=slice(latS, latN), lon=slice(lonL, lonR))
    
    if mask is not None:
        mask_region = mask.sel(lat=slice(latS, latN), lon=slice(lonL, lonR))
        sst_region = sst_region.where(mask_region)  # 🔵 마스킹

    # 공간 평균만 계산하고 시간 차원은 유지
    dims_to_mean = [dim for dim in ['lat', 'lon'] if dim in sst_region.dims] # 공간 평균만 안정적으로 계산
    enso_index = sst_region.mean(dim=dims_to_mean, skipna=True, keep_attrs=True)
    
    #logger.info("Calculated ENSO index successfully.")
    return enso_index

def calculate_iod_index(sst, mask=None):
    """Calculate IOD index based on SST anomalies in two regions."""
    w_latS, w_latN, w_lonL, w_lonR = IOD_WEST_BOX
    e_latS, e_latN, e_lonL, e_lonR = IOD_EAST_BOX

    sst_west = sst.sel(lat=slice(w_latS, w_latN), lon=slice(w_lonL, w_lonR))
    sst_east = sst.sel(lat=slice(e_latS, e_latN), lon=slice(e_lonL, e_lonR))
    if mask is not None:
        sst_west = sst_west.where(mask.sel(lat=sst_west.lat, lon=sst_west.lon))
        sst_east = sst_east.where(mask.sel(lat=sst_east.lat, lon=sst_east.lon))

    dims_to_mean = [dim for dim in ['lat', 'lon'] if dim in sst_west.dims] # 공간 평균만 안정적으로 계산
    return sst_west.mean(dim=dims_to_mean, skipna=True, keep_attrs=True) - sst_east.mean(dim=dims_to_mean, skipna=True, keep_attrs=True)

def plot_index_plums(fcst, obs, idx, yyyymm, fig_dir):
    """
    ENSO/IOD 인덱스의 예측값과 관측값을 플롯합니다.
    
    Parameters
    ----------
    fcst : xarray.DataArray
        예측 인덱스
    obs : xarray.DataArray
        관측 인덱스
    idx : str
        'ENSO' 또는 'IOD'
    yyyymm : str
        초기화 시점
    """

    fig, ax = plt.subplots()
    for ens in range(len(fcst.ens)):
        ax.plot(fcst.time, fcst.isel(ens=ens).values, color='indianred', linestyle='--', linewidth=.5, alpha=.7)
    ax.plot(fcst.time, fcst.mean("ens").values, 'ro-')
    ax.plot(obs.time, obs.values, 'ko-')

    ax.set_title(f'{idx} Index (Init: {yyyymm})', fontsize=14)
    ax.set_xlabel('Time', fontsize=14)
    ax.set_ylabel('SST Anomaly (°C)', fontsize=14)
    ax.set_ylim([-4,4])
    ax.axhline(y=0, color='grey')
    ax.grid(axis='y', linestyle=':', alpha=.7)
    ax.tick_params(axis='y', labelsize=14)
    ax.tick_params(axis='x', labelsize=14)

    figname = os.path.join(fig_dir, f'{idx}_plum_{yyyymm}.png')
    plt.savefig(figname, dpi=300, bbox_inches='tight')
    #plt.show()
    plt.close()

def plot_spatial(fcst, obs, yyyymm):
    """
    SST spatial pattern

    Parameters
    ----------
    fcst : xarray.DataArray
        예측 SST 데이터
    obs : xarray.DataArray
        관측 SST 데이터
    yyyymm: str
    """
    pass

def calculate_indices(var, yyyymm_list, model, fcst_dir, obs_dir, fig_dir):
    
    try:
        obs_data = load_obs_data(
            var, fyears, obs_dir, 
            suffix='anom',
            var_suffix=var
            )
    except FileNotFoundError as e:
        logger.warning(str(e))
        return
    #print(obs_data)

    mask = get_combined_mask(model_name=model, obs_name='OISST')
    #print(mask)

    iod_index_obs = calculate_iod_index(obs_data, mask)
    enso_index_obs = calculate_enso_index(obs_data, mask)
    logger.debug(f"enso_index_obs.dims: {enso_index_obs.dims}")
    logger.info(f"[INFO] obs index calculated for {fyears}")

    # Loop through initialized months
    for yyyymm in yyyymm_list:

            fcst_file = os.path.join(fcst_dir, f"ensMem_sst_anom_{yyyymm}.nc")
            if not os.path.isfile(fcst_file):
                logger.warning(f"[WARN] Missing fcst file for {yyyymm}")
                continue

            ds_fcst = xr.open_dataset(fcst_file)
            fcst_time = ds_fcst['time']
            fcst_da = ds_fcst['sst'].squeeze()  # (lead, lat, lon)
            fcst_da = fcst_da.assign_coords(time=("lead", fcst_time.values)).swap_dims({"lead": "time"})
            
            
            # Calculate ENSO and IOD indices
            enso_index_fcst = calculate_enso_index(fcst_da, mask=mask)
            iod_index_fcst = calculate_iod_index(fcst_da, mask=mask)

            common_times = [t for t in fcst_time.values if t in obs_data.time.values]
            if len(common_times) == 0:
               logger.warning(f"[SKIP] {yyyymm}: No common time between forecast and obs")
               continue
            #print(common_times)
            #print(enso_index_fcst)
            #print(enso_index_obs)

            try:
                obs_enso_sel = enso_index_obs.sel(time=common_times)
                obs_iod_sel = iod_index_obs.sel(time=common_times)

                plot_index_plums(enso_index_fcst, obs_enso_sel, 'ENSO', yyyymm, fig_dir)
                plot_index_plums(iod_index_fcst, obs_iod_sel, 'IOD', yyyymm, fig_dir)
            except Exception as e:
                logger.info(f"[INFO] Init: {yyyymm} 관측데이터 업데이트 필요: {e}")
                logger.warning(f"[WARN] Skipping {yyyymm} due to missing data.")
                break

            
            

# if __name__ == "__main__":
#     calculate_indices(years=fyears)