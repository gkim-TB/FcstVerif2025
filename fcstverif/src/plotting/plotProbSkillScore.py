# src/plotting/plotProbSkillScore.py

import os
import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
import cartopy.crs as ccrs

from config import *
from src.utils.logging_utils import init_logger
from src.utils.general_utils import generate_yyyymm_list

logger = init_logger()
yyyymm_list = generate_yyyymm_list(year_start, year_end)

def plot_rpss_map(var, yyyymm, region_name, fig_dir):
    """
    RPSS 지도 시각화 함수 - 각 리드타임별 RPSS 결과를 지도 형태로 subplot에 표현
    """
    rpss_file = os.path.join(verification_out_dir, 'SCORE', 'GL', var, f"rpss_GL_{var}_{yyyymm}.nc")
    if not os.path.isfile(rpss_file):
        logger.warning(f"[RPSS] 파일 없음: {rpss_file}")
        return

    ds = xr.open_dataset(rpss_file)
    varname = f"{var}_rpss"
    if varname not in ds:
        logger.warning(f"[RPSS] 변수 없음: {varname}")
        return

    rpss = ds[varname]  # dims: time(lead), lat, lon
    n_lead = rpss.sizes['time']
    ncol = 3 #min(3, n_lead)
    nrow = 2 #int(np.ceil(n_lead / ncol))

    if region_name == "GL":
        figsize = (ncol * 6, nrow * 3.5)
        centerLon = 150 # Pacific center
        fs=14 # fontsize
    elif region_name == "EA":
        figsize = (ncol * 4, nrow * 3)
        centerLon = 0
        fs =10
    else:
        figsize = (16, 9)
        centerLon = 0

    region_box = REGIONS[region_name]
    proj = ccrs.PlateCarree(central_longitude=centerLon)
    fig, axs = plt.subplots(nrow, ncol, figsize=figsize,
                            subplot_kw={'projection':proj},
                            constrained_layout=True)
    if not isinstance(axs, np.ndarray):
        axs = np.array([axs])
    axs = axs.flatten()

    bounds = np.arange(-0.2, 1.01, 0.2)
    cmap = plt.get_cmap('YlGnBu_r', len(bounds)-1)
    norm = plt.Normalize(vmin=bounds[0], vmax=bounds[-1])

    for i in range(n_lead):
        ax = axs[i]
        data = rpss.isel(time=i)
        im = data.plot(ax=ax, transform=ccrs.PlateCarree(), cmap=cmap, norm=norm, 
                       add_colorbar=False)
        ax.set_title(f"Lead {i+1}", fontsize=10, loc='left')
        ax.set_title('', loc='center')
        
        if region_name != 'GL':
            ax.set_extent(region_box, crs=proj)
        ax.coastlines()
        gl = ax.gridlines(draw_labels=True, linestyle=':')
        gl.right_labels=False
        gl.top_labels=False
        #gl.xlocator = plt.FixedLocator(np.arange(-180, 181, 30))
        #gl.ylocator = plt.FixedLocator(np.arange(-90, 91, 30))

    # disable the rest subplots
    for j in range(n_lead, len(axs)):
        axs[j].text(0.5, 0.5, 'No data', transform=axs[j].transAxes,
                ha='center', va='center', fontsize=14, color='gray')
        #axs[j].axis('off')

    # 공통 colorbar
    #cbar_ax = fig.add_axes([0.92, 0.25, 0.015, 0.5])
    cb = fig.colorbar(im, ax=axs, shrink=0.8, pad=0.02, extend='min')
    tick_labels = ['-inf' if b == -0.2 else f"{b:.1f}" for b in bounds]
    cb.ax.set_yticks(bounds)
    cb.ax.set_yticklabels(tick_labels)
    cb.set_label('RPSS')

    plt.suptitle(f"RPSS Map by LeadTime \n(Initialized: {yyyymm}, Region: {region_name}, Var: {var})", fontsize=14)
    #fig.subplots_adjust(left=0.05, right=0.88, top=0.9, bottom=0.05, wspace=0.3, hspace=0.3)

    # if fig_dir is None:
    #     fig_dir = os.path.join(output_fig_dir, region_name, var)
    # os.makedirs(fig_dir, exist_ok=True)
    save_path = os.path.join(fig_dir, f"rpss_map_{var}_{region_name}_{yyyymm}.png")
    plt.savefig(save_path, dpi=300)
    plt.close()
    logger.info(f"[SAVE] RPSS 지도 저장: {save_path}")

def plot_roc_by_lead_per_init(var, yyyymm, region_name, data_dir, fig_dir):
    """
    ROC 그래프를 초기화 월 기준으로 리드타임별 subplot에 그림 (각 subplot: AN/NN/BN)
    AUC 값은 subplot 우측 상단에 텍스트로 표시
    """
    import pandas as pd
    import matplotlib.pyplot as plt
    import seaborn as sns

    roc_csv = os.path.join(data_dir, f"roc_{var}_{region_name}_{yyyymm}.csv")
    auc_file = os.path.join(data_dir, f"auc_{var}_{region_name}_{yyyymm}.nc")

    if not os.path.isfile(roc_csv) or not os.path.isfile(auc_file):
        logger.warning(f"[ROC] Missing files for {yyyymm}")
        return

    df = pd.read_csv(roc_csv)
    ds_auc = xr.open_dataset(auc_file)[f"{var}_auc"].squeeze()  # (time, category)

    leads = sorted(df['lead'].unique())
    categories = ['BN', 'NN', 'AN']
    nrow = 2 #int(np.ceil(len(leads) / 3))
    ncol = 3 #min(3, len(leads))

    fig, axs = plt.subplots(nrow, ncol, figsize=(ncol*5, nrow*4), constrained_layout=True)
    if not isinstance(axs, np.ndarray):
        axs = np.array([axs])
    axs = axs.flatten()

    color_map = {'BN': 'steelblue', 'NN': 'gray', 'AN': 'firebrick'}

    for i, lead in enumerate(leads):
        ax = axs[i]
        df_lead = df[df['lead'] == lead]

        for cat in categories:
            sub = df_lead[df_lead['category'] == cat]
            if not sub.empty:
                ax.plot(sub['fpr'], sub['tpr'], label=f'{cat}', color=color_map[cat])

            try:
                lead_time = np.unique(sub['time'])[0]
                auc_val = ds_auc.sel(time=lead_time, category=cat).item()
                ax.text(0.95, 0.05 + 0.08 * categories.index(cat),
                        f"{cat} AUC={auc_val:.2f}", transform=ax.transAxes,
                        ha='right', va='bottom', fontsize=9, color=color_map[cat])
            except Exception:
                logger.warning(f"[AUC WARN] {yyyymm} Lead={lead} Cat={cat} AUC not found.")
                continue

        ax.plot([0,1],[0,1], linestyle='--', color='lightgray', linewidth=1)
        ax.set_xlim([0,1])
        ax.set_ylim([0,1])
        ax.set_title(f"Lead {lead}")
        ax.set_xlabel("False Positive Rate")
        ax.set_ylabel("Ture Positive Rate")
        ax.legend()

    # 남은 subplot 비활성화
    for j in range(i+1, len(axs)):
        #ax.set_title(f"Lead {lead}")
        ax.text(0.5, 0.5, "No Data", transform=ax.transAxes,
                ha="center", va="center", fontsize=12, color="gray")
        ax.set_xticks([])
        ax.set_yticks([])
        #ax.set_frame_on(False)  # 경계선 없애기 (선택)
    #    axs[j].axis('off')

    plt.suptitle(f"ROC Curves by Lead Time\n(Initialized: {yyyymm}, Region: {region_name}, Var: {var})", fontsize=14)

    # if fig_dir is None:
    #     fig_dir = os.path.join(output_fig_dir, region_name, var)
    # os.makedirs(fig_dir, exist_ok=True)

    save_path = os.path.join(fig_dir, f"roc_curve_by_lead_{var}_{region_name}_{yyyymm}.png")
    plt.savefig(save_path, dpi=300)
    plt.close()
    logger.info(f"[SAVE] ROC Curve by Lead: {save_path}")

    
