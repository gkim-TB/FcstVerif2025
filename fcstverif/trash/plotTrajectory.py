import os
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import xarray as xr
from matplotlib.lines import Line2D
from src.analysis.calcIndices import calculate_enso_index, calculate_iod_index
from src.utils.general_utils import load_obs_data, generate_yyyymm_list, get_combined_mask, clip_to_region
from src.utils.logging_utils import init_logger
from config import REGIONS, year_start, year_end, fyears, model, sst_out_dir, era5_out_dir, model_out_dir, output_fig_dir
    
logger = init_logger()



def plot_trajectory4var(var: str, region_name: str, fig_dir: str, score_dir: str):
    """
    사용자 선택 변수에 대한 anomaly 시계열 (영역 평균 포함)
    """

    # 1️⃣ REGION 설정
    if region_name not in REGIONS:
        raise ValueError(f"[ERROR] Unknown region name: {region_name}")
    
    # 2️⃣ 관측 불러오기
    obs = load_obs_data(var, years=fyears, obs_dir=era5_out_dir, suffix="anom", var_suffix=var)
    obs_region = clip_to_region(obs, region_name)

    if var == 'sst':
        mask = get_combined_mask(model_name=model, obs_name="OISST")
        if mask is not None:
            mask_region = clip_to_region(mask, region_name)
            obs_region = obs_region.where(mask_region)
    
    obs_idx = obs_region.mean(dim=["lat","lon"], skipna=True)

    # 3️⃣ 예측 및 스코어 불러오기
    fcst_dir = os.path.join(model_out_dir, "anomaly")
    yyyymm_list = generate_yyyymm_list(year_start, year_end)

    fcst_dict={}
    acc_dict={}
    for yyyymm in yyyymm_list:
        file_path = os.path.join(fcst_dir, f"ensMem_{var}_anom_{yyyymm}.nc")
        acc_path = os.path.join(score_dir, f"ensScore_det_{var}_{yyyymm}.nc")
        
        if not os.path.isfile(file_path):
            logger.info(f"[WARN] {file_path} 없음.")
            continue
        
        # read fcst file
        try:
            with xr.open_dataset(file_path) as ds:
                da = ds[var].mean("ens", skipna=True).squeeze()
                da = da.assign_coords(time=("lead", ds["time"].values)).swap_dims({"lead": "time"})
                da_region = clip_to_region(da, region_name)
                if var == 'sst':
                    da_region = da_region.where(mask_region)
                fcst_dict[yyyymm] = da_region.mean(dim=["lat", "lon"], skipna=True).load()
        except Exception as e:
            logger.warning(f"[SKIP] Forecast load 실패: {file_path}, 이유: {e}")
            continue

        # read ACC file
        if os.path.isfile(acc_path):
            try:
                with xr.open_dataset(acc_path) as acc_ds:
                    acc_val = acc_ds["acc_mean"].sel(lead=1).values.item()
                    acc_dict[yyyymm] = acc_val
            except Exception:
                acc_dict[yyyymm] = np.nan

    # 4️⃣ 그림 생성
    fig, ax = plt.subplots(figsize=(12, 5))
    ax2 = ax.twinx()

    target_dates = pd.to_datetime(list(fcst_dict.values())[0].time.values)

    cmap = plt.colormaps['tab20']
    month_colors = {month: cmap((month - 1) % 12) for month in range(1, 13)}

    # OBS line
    obs_idx.plot(ax=ax, color="black", linewidth=2.5, label="OBS")

    # Fcst lines
    for init, series in fcst_dict.items():
        color = month_colors[pd.to_datetime(init).month]
        ax.plot(pd.to_datetime(series.time.values), series.values, 
                alpha=0.5, lw=1.0, 
                color=color, label=init[:7])
    
    # ACC bars
    bar_x = [pd.to_datetime(f"{k[:4]}-{k[4:]}") for k in acc_dict.keys()]
    bar_y = [acc_dict[k] for k in acc_dict.keys()]
    bar_colors = [month_colors[pd.to_datetime(k).month] for k in acc_dict.keys()]
    ax2.bar(bar_x, bar_y, color=bar_colors, alpha=0.6, width=20)

    legend_elements = [
        Line2D([0], [0], color=month_colors[m], lw=2, label=f'Init {m:02d}')
        for m in range(1, 13)
    ]

    ax.set_title(f"Forecast Trajectory with ACC\nEach Line = One Initialized Month ({year_start}–{year_end}), Region: {region_name}, Var: {var}", fontsize=15)
    ax.axhline(0, color="gray", linestyle="--", linewidth=0.8)
    ax.set_ylabel("Anomaly (℃)")
    ax.set_xlabel("Time")
    ax.set_xticks(target_dates)
    ax.set_xticklabels([d.strftime('%Y-%m') for d in target_dates], rotation=45, ha='right')
    ax.legend(handles=legend_elements, title="Initialized Month", bbox_to_anchor=(1.01, 1), loc='upper left', fontsize=14)
    
    plt.tight_layout()

    out_dir = os.path.join(fig_dir)
    os.makedirs(out_dir, exist_ok=True)
    save_fname = os.path.join(out_dir, f"traj_{var}_{region_name}.png")
    plt.savefig(save_fname, dpi=300, bbox_inches='tight')
    plt.close()
    logger.info(f"[INFO] Saved: {save_fname}")



def plot_trajectory4idx():
    """
    ENSO 및 IOD 인덱스에 대한 시계열 예측 플롯
    """
    ENSO_BOX = (-5, 5, 190, 240)  # Niño 3.4
    IOD_WEST_BOX = (-10, 10, 50, 70)
    IOD_EAST_BOX = (-10, 0, 90, 110)
    idx_names = [ENSO_BOX, IOD_WEST_BOX, IOD_EAST_BOX]

    for idx_name, func in zip(idx_names, [calculate_enso_index, calculate_iod_index, calculate_iod_index, calculate_iod_index]):
        obs = load_obs_data("sst", years=fyears, obs_dir=sst_out_dir, suffix="anom", var_suffix="sst")
        mask = get_combined_mask(model_name=model, obs_name="OISST")
        obs_idx = func(obs, mask=mask)

        fcst_dir = os.path.join(model_out_dir, "anomaly")
        yyyymm_list = sorted([
            f.name[-11:-3] for f in os.scandir(fcst_dir)
            if f.name.startswith("ensMem_sst_anom_")
        ])
        fcst_dict = {}
        for yyyymm in yyyymm_list:
            fpath = os.path.join(fcst_dir, f"ensMem_sst_anom_{yyyymm}.nc")
            if not os.path.exists(fpath):
                continue
            ds = xr.open_dataset(fpath)
            da = ds["sst"].mean("ens", skipna=True)
            da = da.assign_coords(time=("lead", ds["time"].values)).swap_dims({"lead": "time"})
            fcst_dict[yyyymm] = func(da, mask=mask)

        fig, ax = plt.subplots(figsize=(12, 5))
        obs_idx.plot(ax=ax, color="black", linewidth=2.5, label="OBS")
        for init, series in fcst_dict.items():
            ax.plot(pd.to_datetime(series.time.values), series.values, alpha=0.5, lw=1.0, label=init[:7])
        ax.set_title(f"{idx_name} Index Forecast Trajectory")
        ax.axhline(0, color="gray", linestyle="--", linewidth=0.8)
        ax.set_ylabel("SST Anomaly (℃)")
        ax.set_xlabel("Time")
        ax.legend(loc="upper left", fontsize="x-small", ncol=2)
        plt.tight_layout()
        out_dir = os.path.join(output_fig_dir, "IDX")
        os.makedirs(out_dir, exist_ok=True)
        plt.savefig(os.path.join(out_dir, f"traj_{idx_name}.png"), dpi=300)
        plt.close()