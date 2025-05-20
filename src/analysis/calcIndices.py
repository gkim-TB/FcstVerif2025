import numpy as np
import xarray as xr
from scipy.stats import pearsonr
from sklearn.metrics import mean_squared_error
import matplotlib.pyplot as plt
import os
from config import *
from src.utils.logging_utils import init_logger
logger = init_logger()

# Define ENSO and IOD regions
enso_region = {'lat_min': -5, 'lat_max': 5, 'lon_min': 190, 'lon_max': 240}  # Example: Niño 3.4 region
iod_region = {
    'west_lat_min': -10, 'west_lat_max': 10, 'west_lon_min': 50, 'west_lon_max': 70,
    'east_lat_min': -10, 'east_lat_max': 0, 'east_lon_min': 90, 'east_lon_max': 110
}

def calculate_enso_index(sst, region):
    """Calculate ENSO index based on SST anomalies in a specific region."""
    sst_region = sst.sel(lat=slice(region['lat_min'], region['lat_max']),
                         lon=slice(region['lon_min'], region['lon_max']))
    # 공간 평균만 계산하고 시간 차원은 유지
    dims_to_mean = [dim for dim in ['lat', 'lon'] if dim in sst_region.dims]
    enso_index = sst_region.mean(dim=dims_to_mean)
   
    logger.info("Calculated ENSO index successfully.")
    return enso_index

def calculate_iod_index(sst, region):
    """Calculate IOD index based on SST anomalies in two regions."""
    sst_west = sst.sel(lat=slice(region['west_lat_min'], region['west_lat_max']),
                       lon=slice(region['west_lon_min'], region['west_lon_max']))
    sst_east = sst.sel(lat=slice(region['east_lat_min'], region['east_lat_max']),
                       lon=slice(region['east_lon_min'], region['east_lon_max']))
    
    # 공간 평균만 계산하고 시간 차원은 유지
    dims_to_mean = [dim for dim in ['lat', 'lon'] if dim in sst_west.dims]
    west_mean = sst_west.mean(dim=dims_to_mean)
    east_mean = sst_east.mean(dim=dims_to_mean)
    
    iod_index = west_mean - east_mean
   
    logger.info("Calculated IOD index successfully.")
    return iod_index

def plot_index_plums(fcst, obs, idx, yyyymm):
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
        ax.plot(fcst.time, fcst.isel(ens=ens).values, 'r--', linewidth=.5, alpha=.7)
    ax.plot(fcst.time, fcst.mean("ens").values, 'r-')
    ax.plot(obs.time, obs.values, 'ko-')

    ax.set_title(f'{idx} Index (Init: {yyyymm})')
    ax.set_xlabel('Time')
    ax.set_ylabel('SST Anomaly (°C)')
    ax.set_ylim([-4,4])
    ax.axhline(y=0, color='grey')
    ax.grid(axis='y', linestyle=':', alpha=.7)

    figname = os.path.join(output_fig_dir, f'{idx}_plum_{yyyymm}.png')
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
def calculate_indices(years):
    indices_out_dir = os.path.join(work_dir, "Indices")
    os.makedirs(indices_out_dir, exist_ok=True)

    obs_files = [f"{sst_anom_dir}/sst_anom_{yyyy}.nc" for yyyy in fyears]
    #if not os.path.isfile(obs_files):
    #    print(f"[WARN] Missing obs file for {yyyy}")
    #print(obs_files)

    obs_list = []
    for obs_file in obs_files:
        da_obs = xr.open_dataset(obs_file)
        obs_list.append(da_obs)
    ds_obs = xr.concat(obs_list, dim='time')

    iod_index_obs = calculate_iod_index(ds_obs.sst, iod_region)
    enso_index_obs = calculate_enso_index(ds_obs.sst, enso_region)

    # Loop through initialized months
    for yy in years:
        for mm in range(1, 13):
            yyyymm = f"{yy}{mm:02d}"

            fcst_file = os.path.join(f'{model_out_dir}/anomaly', f"sst_anom_{yyyymm}.nc")
            if not os.path.isfile(fcst_file):
                logger.warning(f"[WARN] Missing fcst or obs file for {yyyymm}")
                continue

            ds_fcst = xr.open_dataset(fcst_file)

            fcst_da = ds_fcst['sst'].squeeze()  # (lead, lat, lon)
            fcst_time = ds_fcst['time']

            # Calculate ENSO and IOD indices
            enso_index_fcst = calculate_enso_index(fcst_da, enso_region)
            iod_index_fcst = calculate_iod_index(fcst_da, iod_region)
            
            try:
                obs_enso_sel = enso_index_obs.sel(time=fcst_time)
                obs_iod_sel = iod_index_obs.sel(time=fcst_time)

                plot_index_plums(enso_index_fcst, obs_enso_sel, 'ENSO', yyyymm)
                plot_index_plums(iod_index_fcst, obs_iod_sel, 'IOD', yyyymm)
            except Exception as e:
                logger.info(f"[INFO] Init: {yyyymm} 관측데이터 업데이트 필요: {e}")
                logger.warning(f"[WARN] Skipping {yyyymm} due to missing data.")
                break

            
            

# if __name__ == "__main__":
#     calculate_indices(years=fyears)