import numpy as np
import xarray as xr
import pandas as pd
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

def plot_index_plum_by_init(fcst, obs, idx, yyyymm, fig_dir):
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
    ax.axhspan(-0.5, 0.5, color='lightgrey', alpha=0.3)

    ax.grid(axis='y', linestyle=':', alpha=.7)
    ax.tick_params(axis='y', labelsize=14)
    ax.tick_params(axis='x', labelsize=12)

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

def calc_index_skill(fcst, obs):
    """
    fcst, obs: DataArray (time, [ens]) 또는 (time,)

    return: 
        ACC, RMSE in DataFrame (.csv)
    """
    if "ens" in fcst.dims:
        fcst_mean = fcst.mean("ens")
    else:
        fcst_mean = fcst

    # 시간축 맞추기
    fcst_mean, obs = xr.align(fcst_mean, obs, join="inner")

    if fcst_mean.size < 2 or obs.size < 2:
        return np.nan, np.nan

    acc = np.corrcoef(fcst_mean.values, obs.values)[0, 1]
    rmse = np.sqrt(np.mean((fcst_mean.values - obs.values) ** 2))
    return acc, rmse      

def plot_index_timeseries_all_init(mode, obs_index, fcst_index_dict, fig_dir):
    """
    관측 index와 초기화월별 예측 index 시계열을 한 그림에 플롯.

    Parameters
    ----------
    obs_index : xarray.DataArray
        전체 기간의 관측 index (time)
    fcst_index_dict : dict
        { yyyymm: fcst_index_da }, 각 초기화월별 예측 index DataArray(time, ens)
    fig_dir : str
        저장 경로
    """
    import matplotlib.dates as mdates
    from matplotlib.lines import Line2D

    fig, ax = plt.subplots(figsize=(14,6))

    # 관측값 플롯
    ax.plot(obs_index.time, obs_index.values, 'k-', label='OBS', linewidth=2)

    # 초기화월별 예측값 플롯
    cmap = plt.colormaps['tab20']
    month_colors = {m: cmap((m - 1) % 12) for m in range(1, 13)}

    for i, (yyyymm, fcst_da) in enumerate(sorted(fcst_index_dict.items())):
        if "ens" in fcst_da.dims:
            fcst_mean = fcst_da.mean("ens")
        else:
            fcst_mean = fcst_da

        color = month_colors[pd.to_datetime(yyyymm, format="%Y%m").month]
        ax.plot(fcst_mean.time, fcst_mean.values, color=color, alpha=1, linewidth=1.5, label=yyyymm)

        lead1_time = fcst_mean.time.values[0]
        lead1_value = fcst_mean.values[0]
        ax.plot(lead1_time, lead1_value, marker='o', color=color, markersize=6)


    # x축 포맷
    xticks = pd.date_range(
            start=min(pd.to_datetime(k, format="%Y%m") for k in fcst_index_dict),
            end=max(pd.to_datetime(k, format="%Y%m") + pd.DateOffset(months=6) for k in fcst_index_dict),
            freq='4MS'
        )
    ax.set_xticks(xticks)  # 예: 2개월 간격 tick
    ax.set_xticklabels(
            [d.strftime('%Y-%m') for d in xticks],
            ha='center', fontsize=12
        )

    ax.set_xlabel('Target Month', fontsize=14)
    ax.set_ylabel('Index (°C)', fontsize=14)
    ax.set_title(f'{mode} Trajectory by Init Month', fontsize=14, pad=41)

    ax.grid(True, linestyle=':', alpha=0.7)
    ax.axhline(0, linestyle='--', color='grey', alpha=.8)
    ax.axhspan(-0.5, 0.5, color='lightgrey', alpha=0.3)
    ax.set_ylim([-3,3])
    ax.tick_params(axis='y', labelsize=14)
    ax.tick_params(axis='x', labelsize=14)

    legend_elements = [
        Line2D([0], [0], color=month_colors[m], lw=2, label=f'Init {m:02d}')
        for m in range(1, 13)
    ]
    ax.legend(handles=legend_elements, #title="Initialized Month", 
               bbox_to_anchor=(0.5, 1.13), ncol=6, frameon=False,
               loc='upper center', fontsize=10)

    plt.tight_layout()
    figname = os.path.join(fig_dir, f'{mode}_index_timeseries_all_init.png')
    plt.savefig(figname, dpi=300)
    plt.close()


def calculate_index(var, yyyymm_list, model, fcst_dir, obs_dir, idx_dir, fig_dir, mode='ALL'):
    '''
    Calculate ENSO and IOD indices then validate obs vs. fcst indices (ACC, RMSE)

    mode : 'ENSO', 'IOD', 'ALL'

    '''
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

    # 관측 index 계산 
    iod_index_obs = calculate_iod_index(obs_data, mask)
    enso_index_obs = calculate_enso_index(obs_data, mask)
    #logger.debug(f"enso_index_obs.dims: {enso_index_obs.dims}")
    #logger.info(f"[INFO] obs index calculated for {fyears}")

    os.makedirs(idx_dir, exist_ok=True)
    obs_nc_path = os.path.join(idx_dir, "obs_indices.nc")
    ds_obs_indices = xr.Dataset(
        {"ENSO": enso_index_obs, "IOD": iod_index_obs}
    )
    ds_obs_indices.to_netcdf(obs_nc_path)
    logger.info(f"[INFO] Observed indices saved: {obs_nc_path}")


    # 스코어 누적 저장 리스트
    score_rows = []
    fcst_dict = {}

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
            if mode in ['ENSO', 'ALL']:
                enso_index_fcst = calculate_enso_index(fcst_da, mask=mask)
                fcst_dict[yyyymm] = enso_index_fcst

                # Save indices
                fcst_nc_path = os.path.join(idx_dir, f"fcst_ENSO_index_{yyyymm}.nc")
                enso_index_fcst.to_netcdf(fcst_nc_path)
                logger.info(f"[INFO] Forecast ENSO index saved: {fcst_nc_path}")

                # common time to verif
                common_times = [t for t in fcst_time.values if t in obs_data.time.values]
                if len(common_times) == 0:
                    logger.warning(f"[SKIP] {yyyymm}: No common time between forecast and obs")
                    continue

                obs_enso_sel = enso_index_obs.sel(time=common_times)
                
                # Plot plum
                plot_index_plum_by_init(enso_index_fcst, obs_enso_sel, 'ENSO', yyyymm, fig_dir)
                
                # Skill
                acc, rmse = calc_index_skill(enso_index_fcst, obs_enso_sel)
                score_rows.append({
                    "yyyymm": yyyymm,
                    "ACC_ENSO": acc,
                    "RMSE_ENSO": rmse,
                    })
                
            
            elif mode in ['IOD', 'ALL']:
                iod_index_fcst = calculate_iod_index(fcst_da, mask=mask)
                fcst_dict[yyyymm] = iod_index_fcst

                # Save indices
                fcst_nc_path = os.path.join(idx_dir, f"fcst_IOD_index_{yyyymm}.nc")
                iod_index_fcst.to_netcdf(fcst_nc_path)
                logger.info(f"[INFO] Forecast IOD index saved: {fcst_nc_path}")
            
                common_times = [t for t in fcst_time.values if t in obs_data.time.values]
                if len(common_times) == 0:
                    logger.warning(f"[SKIP] {yyyymm}: No common time between forecast and obs")
                    continue

                obs_iod_sel = iod_index_obs.sel(time=common_times)

                plot_index_plum_by_init(iod_index_fcst, obs_iod_sel, 'IOD', yyyymm, fig_dir)

                acc, rmse = calc_index_skill(iod_index_fcst, obs_iod_sel)
                score_rows.append({
                    "yyyymm": yyyymm,
                    "ACC_ENSO": acc,
                    "RMSE_ENSO": rmse,
                    })
                                           

    # time series all init
    if mode == "ENSO":
        plot_index_timeseries_all_init(mode, enso_index_obs, fcst_dict, fig_dir)
    elif mode == "IOD":
        plot_index_timeseries_all_init(mode, iod_index_obs, fcst_dict, fig_dir)

    # 결과 CSV로 저장
    if score_rows:
        df_score = pd.DataFrame(score_rows)
        #score_dir = f"{verification_out_dir}/SCORE/IDX/"
        os.makedirs(idx_dir, exist_ok=True)
        score_file = os.path.join(idx_dir, f"{mode}_index_skill_score_summary.csv")
        df_score.to_csv(score_file, index=False)
        logger.info(f"[INFO] Index skill summary saved: {score_file}")
    else:
        logger.warning("[WARN] No index skill scores computed.")


# if __name__ == "__main__":
#     calculate_indices(years=fyears)