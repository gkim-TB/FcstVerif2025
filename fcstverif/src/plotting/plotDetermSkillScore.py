import xarray as xr
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
#import matplotlib.colors as mcolors
#import matplotlib.patches as patches
from matplotlib.lines import Line2D
import cmaps
#import matplotlib.gridspec as gridspec
import cartopy.crs as ccrs
import os
from config import *
from src.utils.general_utils import *
from src.utils.logging_utils import init_logger
logger = init_logger()

yyyymm_list = generate_yyyymm_list(year_start, year_end)

def no_data_panel(ax_fcst, ax_bias):
    for ax in [ax_fcst, ax_bias]:
        #ax.set_axis_off()
        ax.text(0.5, 0.5, 'No data', transform=ax.transAxes,
                ha='center', va='center', fontsize=14, color='gray')
          
def plot_skill_initialized_month(var, region_name, data_dir, fig_dir, score):
    
    for yyyymm in yyyymm_list:
        file_path = os.path.join(data_dir, f"ensScore_det_{var}_{yyyymm}.nc")
        if not os.path.isfile(file_path):
            logger.info(f"[WARN] {file_path} 없음.")
            continue
        
        ds = xr.open_dataset(file_path)
        lead_full = np.arange(1,7)
        lead_valid = ds['lead'].values

        fig, ax = plt.subplots(figsize=(5,4), constrained_layout=True)
        # 멤버별 점선 (회색)
        if score in ds.data_vars:
            for e in ds['ens'].values:
                y_vals = [ds[score].sel(ens=e).sel(time=t).item() if t in ds['time'].values else np.nan
                          for t in ds['time'].values]
                ax.plot(lead_valid, y_vals, '--', color='gray', alpha=0.4, linewidth=0.8)

        # 앙상블 평균 (진한 파란색)
        mean_score_name = f"{score}_mean"
        if mean_score_name in ds.data_vars:
            y_vals = [ds[mean_score_name].sel(time=t).item() if t in ds['time'].values else np.nan
                      for t in ds['time'].values]
            ax.plot(lead_valid, y_vals, '-o', color='royalblue', label='Ensemble Mean')

        ax.set_xlabel('Lead Time (month)')
        ax.set_ylabel(score.upper())
        ax.set_title(f'{score.upper()} by Lead Time\n(Initialized: {yyyymm}, Region: {region_name}, Var: {var})')
        ax.grid(True, linestyle='--', color='lightgrey')
        if score == 'acc':
            ax.set_ylim([-1,1])
        elif score == 'rmse':
            ax.set_ylim([0,6])
        ax.set_xticks(lead_full)
        #plt.xlim(0.9,6.1)
        ax.legend()

        save_fname = os.path.join(fig_dir, f"{score}_init_{var}_{region_name}_{yyyymm}.png")
        plt.savefig(save_fname, dpi=300 )#, bbox_inches='tight')
        #plt.show()
        plt.close()

        logger.info(f"[INFO] Saved: {save_fname}")
        ds.close()

def plot_skill_heatmap_initialized_month(var, target_year, region_name, data_dir, fig_dir, score1='acc', score2='rmse'):
    import matplotlib.patches as patches
    import matplotlib.colors as mcolors

    # 설정
    months = range(1, 13)
    leads = range(1, 7)
    y_labels = [f"{target_year}-{m:02d}" for m in months]
    x_labels = list(leads)

    # 색상 및 colormap 설정
    cmap1 = plt.get_cmap('bwr', 10)    # 💡 ACC
    cmap2 = plt.get_cmap('Greys', 10)  # 💡 RMSE
    bounds1 = np.linspace(-1, 1, 11)     # ACC
    bounds2 = np.linspace(0, 4, 11)    # RMSE (적절히 조정 필요)
    norm1 = mcolors.BoundaryNorm(bounds1, cmap1.N)
    norm2 = mcolors.BoundaryNorm(bounds2, cmap2.N)

    # 빈 grid
    grid1 = np.full((len(y_labels), len(x_labels)), np.nan)
    grid2 = np.full((len(y_labels), len(x_labels)), np.nan)

    # 데이터 로드
    for i, month in enumerate(months):
        yyyymm = f"{target_year}{month:02d}"
        file_path = os.path.join(data_dir, f"ensScore_det_{var}_{yyyymm}.nc")

        if not os.path.isfile(file_path):
            logger.info(f"[WARN] {file_path} 없음.")
            continue

        ds = xr.open_dataset(file_path)

        for j, lead in enumerate(leads):
            try:
                time_idx = list(ds['lead'].values).index(lead)
                grid1[i, j] = ds[f"{score1}_mean"].isel(time=time_idx).item()
                grid2[i, j] = ds[f"{score2}_mean"].isel(time=time_idx).item()
            except Exception:
                logger.info(f"[WARN] {yyyymm} Lead={lead} 없음")
                continue

    # 그림 생성
    fig, ax = plt.subplots(figsize=(5, len(y_labels) * 0.5))

    for i in range(len(y_labels)):
        for j in range(len(x_labels)):
            x = j
            y = i
            val1 = grid1[i, j]
            val2 = grid2[i, j]

            if not np.isnan(val1):
                ax.add_patch(patches.Polygon(
                    [[x, y], [x+1, y], [x, y+1]],
                    facecolor=cmap1(norm1(val1)), edgecolor='white', lw=2
                ))
            if not np.isnan(val2):
                ax.add_patch(patches.Polygon(
                    [[x+1, y+1], [x+1, y], [x, y+1]],
                    facecolor=cmap2(norm2(val2)), edgecolor='white', lw=2
                ))

            if not np.isnan(val1) and not np.isnan(val2):
                color1 = 'white' if val1 >= 0.6 else 'black'
                color2 = 'white' if val2 >= 2 else 'black'
                ax.text(x + 0.3, y + 0.25, f'{val1:.2f}', ha='center', va='center', fontsize=7, color=color1)
                ax.text(x + 0.7, y + 0.75, f'{val2:.2f}', ha='center', va='center', fontsize=7, color=color2)

    # 축 설정
    ax.set_xticks(np.arange(len(x_labels)) + 0.5)
    ax.set_xticklabels([f'Lead {l}' for l in x_labels])
    ax.set_yticks(np.arange(len(y_labels)) + 0.5)
    ax.set_yticklabels(y_labels)
    ax.set_xlim(0, len(x_labels))
    ax.set_ylim(0, len(y_labels))
    ax.invert_yaxis()
    ax.set_xlabel("Lead Time")
    ax.set_ylabel("Initialized Month")
    ax.set_title(f"{score1.upper()} / {score2.upper()} Heatmap\n(Region: {region_name}, Var: {var}, Year: {target_year})")

    # colorbar
    fig.subplots_adjust(right=0.88)
    cax1 = fig.add_axes([0.90, 0.55, 0.015, 0.3])
    sm1 = plt.cm.ScalarMappable(cmap=cmap1, norm=norm1)
    sm1.set_array([])
    cbar1 = plt.colorbar(sm1, cax=cax1, ticks=bounds1)
    cbar1.set_label(score1.upper())

    cax2 = fig.add_axes([0.90, 0.15, 0.015, 0.3])
    sm2 = plt.cm.ScalarMappable(cmap=cmap2, norm=norm2)
    sm2.set_array([])
    cbar2 = plt.colorbar(sm2, cax=cax2, ticks=bounds2)
    cbar2.set_label(score2.upper())

    # 저장
    save_fname = os.path.join(fig_dir, f"det_heatmap_init_{var}_{region_name}_{target_year}.png")
    fig.savefig(save_fname, dpi=300, bbox_inches='tight')
    logger.info(f"[INFO] Saved Dual-Score Heatmap: {save_fname}")

def plot_skill_target_month(var, target_year, region_name, score, data_dir, fig_dir=None):
    target_months = range(1, 13)

    for target_month in target_months:
        target_date = pd.Timestamp(f"{target_year}-{target_month:02d}-01")

        lead_list = []
        mean_score_list = []
        member_score_dict = {}
        init_month_labels = []

        for lead in range(1, 7):
            init_date = target_date - pd.DateOffset(months=lead)
            init_yyyymm = init_date.strftime('%Y%m')
            file_path = os.path.join(data_dir, f"ensScore_det_{var}_{init_yyyymm}.nc")

            if not os.path.isfile(file_path):
                logger.info(f"[WARN] No file: {file_path}")
                continue

            ds = xr.open_dataset(file_path)

            try:
                time_idx = ds['lead'].values.tolist().index(lead)

                 # 💡 멤버 점선 추가
                if score in ds.data_vars:
                    for e in ds['ens'].values:
                        if e not in member_score_dict:
                            member_score_dict[e] = []
                        member_score_dict[e].append(ds[score].isel(ens=e, time=time_idx).item())

                # 💡 평균 실선 추가
                if f"{score}_mean" in ds.data_vars:
                    mean_score_list.append(ds[f"{score}_mean"].isel(time=time_idx).item())
                    lead_list.append(lead)
                    init_month_labels.append(init_yyyymm)


            except KeyError:
                logger.info(f"[WARN] No lead={lead} in {file_path}")
                continue

        if mean_score_list:
            fig, ax = plt.subplots(figsize=(5,4), constrained_layout=True)

            # 💡 멤버별 회색 점선
            for e, values in member_score_dict.items():
                if len(values) == len(lead_list):
                    ax.plot(lead_list, values, '--', color='gray', alpha=0.4, linewidth=0.8)

            # 💡 앙상블 평균 진한 선
            ax.plot(lead_list, mean_score_list, '-o', color='forestgreen', label='Ensemble Mean')

            for i, txt in enumerate(init_month_labels):
                ax.text(lead_list[i], mean_score_list[i], txt, fontsize=9,
                         ha='center', va='bottom', color='blue')

            ax.set_xlabel('Lead Time (month)')
            ax.set_ylabel(score.upper())
            if score == 'acc':
                ax.set_ylim([-1,1]) # if score ACC
            elif score == 'rmse':
                ax.set_ylim([0,6])
            ax.set_title(f'{score.upper()} by Lead Time\n(Target Month: {target_date.strftime("%Y-%m")}, Region: {region_name}, Var: {var})')
            ax.set_xticks([1, 2, 3, 4, 5, 6])
            ax.grid(True, linestyle='--', color='lightgrey')
            ax.legend()
            
            #plt.tight_layout()
            save_fname = os.path.join(fig_dir, f"{score}_target_{var}_{region_name}_{target_date.strftime('%Y%m')}.png")
            plt.savefig(save_fname, dpi=300)#, bbox_inches='tight')
            plt.close()

            logger.info(f"[INFO] Saved: {save_fname}")
        else:
            logger.info(f"[WARN] No data to plot for target month {target_date.strftime('%Y-%m')}")

def plot_trajectory_w_acc_by_initialized_line(var: str, region: str, fig_dir: str, data_dir: str, mode: str = "trajectory"):
    """
    전체 예측기간에 대해 초기화월별 시계열 또는 스킬라인을 그리는 함수
    - mode='skill' : 단독 스킬 스코어 (e.g. ACC, RMSE)
    - mode='trajectory' : anomaly 시계열 + lead1 ACC bar
    """
    assert mode in ["skill", "trajectory"], f"Invalid mode: {mode}"
    mask = None

    # ✅ region 설정
    if region not in REGIONS:
        raise ValueError(f"[ERROR] Unknown region name: {region}")
    
    ANOM_RANGE_MAP= {
    "GL": {
        "t2m": [-0.2, 1.4],
        "sst": [-0.1, 1.0],
        "prcp": [-0.1, 0.1],
    },
    "EA": {
        "default": [-0.8, 2.0],
        "t2m":[-0.1, 2.5],
        "prcp":[-1, 1.5],
        "sst":[-1,2],

    }
}
    
    if region in ANOM_RANGE_MAP:
        if var in ANOM_RANGE_MAP[region]:
            anom_range = ANOM_RANGE_MAP[region][var]
        elif "default" in ANOM_RANGE_MAP[region]:
            anom_range = ANOM_RANGE_MAP[region]["default"]
        else:
            raise ValueError(f"[ERROR] No ACC range defined for region={region}, var={var}")
    else:
        raise ValueError(f"[ERROR] Unknown region: {region}")
    
    UNIT_LABELS = {
    "t2m": "Anomaly (℃, lines)",
    "sst": "Anomaly (℃, lines)",
    "prcp": "Anomaly (mm/day, lines)"
}
    if mode == "trajectory":
        xlabel = UNIT_LABELS.get(var, "Anomaly (lines)")
    else:
        xlabel = "ACC"
    
    # 📦 컬러 설정
    cmap = plt.colormaps['tab20']
    month_colors = {m: cmap((m - 1) % 12) for m in range(1, 13)}

    # 📥 초기화월 목록
    yyyymm_list = generate_yyyymm_list(year_start, year_end)

    # 📊 그림 준비
    fig, ax1 = plt.subplots(figsize=(14, 6))#, constrained_layout=True)
    ax2 = ax1.twinx() if mode == "trajectory" else None

    # ▶ trajectory 모드: 관측 불러오기
    if mode == "trajectory":
        obs = load_obs_data(var, years=fyears, obs_dir=era5_out_dir, suffix="anom", var_suffix=var)
        obs_region = clip_to_region(obs, region, var)
        if var == 'sst':
            mask = get_combined_mask(model_name=model, obs_name="OISST")
            if mask is not None:
                obs_region = obs_region.where(clip_to_region(mask, region, var))
            else:
                logger.warning(f"[WARN] No mask found")

        obs_idx = obs_region.mean(dim=["lat", "lon"], skipna=True).load()
        obs_idx.plot(ax=ax1, color="black", linewidth=2.5, label="OBS")

    # 🔁 초기화월별 선 그리기
    acc_dict = {}
    # fcst_dict = {}

    for yyyymm in yyyymm_list:
        fpath = os.path.join(model_out_dir, "anomaly", f"ensMem_{var}_anom_{yyyymm}.nc")
        acc_path = os.path.join(data_dir, f"ensScore_det_{var}_{yyyymm}.nc")

        color = month_colors[pd.to_datetime(yyyymm, format="%Y%m").month]

        # 1️⃣ trajectory 모드일 때만 예측 anomaly 데이터 읽기
        if mode == "trajectory":
            if not os.path.exists(fpath):
                continue
            try:
                with xr.open_dataset(fpath) as ds:
                    da = ds[var].mean("ens", skipna=True).squeeze()
                    da = da.assign_coords(time=("lead", ds["time"].values)).swap_dims({"lead": "time"})
                    da_region = clip_to_region(da, region, var)
                    if mask is not None:
                        da_region = da_region.where(clip_to_region(mask, region, var))
                    fanom = da_region.mean(dim=["lat", "lon"], skipna=True).load()
                    
                    lead_vals = fanom["lead"].values
                    init_date = pd.to_datetime(yyyymm, format="%Y%m")
                    target_dates = [init_date + pd.DateOffset(months=int(l)) for l in lead_vals]
                
                    ax1.plot(target_dates, fanom.values,
                             lw=1.0, alpha=0.9, color=color, label=yyyymm)
                    # fcst_dict[yyyymm] = fanom
            except Exception as e:
                print(f"[WARN] {yyyymm} forecast read error: {e}")
                continue

        # 2️⃣ acc 파일은 공통적으로 읽기
        if os.path.exists(acc_path):
            try:
                with xr.open_dataset(acc_path) as acc_ds:
                    # skill 모드: 전체 acc 라인 그리기
                    if mode == "skill":
                        acc_vals = acc_ds["acc_mean"].values
                        lead_vals = acc_ds["lead"].values
                        init_date = pd.to_datetime(yyyymm, format="%Y%m")
                        target_dates = [init_date + pd.DateOffset(months=int(l)) for l in lead_vals]
                
                        ax1.plot(target_dates, acc_vals, '-o', color=color)
                    # trajectory 모드 : lead-1 acc만 
                    elif mode == "trajectory":   
                        acc_val = acc_ds["acc_mean"].values[0]
                        acc_dict[yyyymm] = acc_val
                        logger.debug(f"[DEBUG] ACC value for target({target_dates[0].strftime('%Y%m')}): {np.round(acc_val,2)}")      
            except Exception:
                acc_dict[yyyymm] = np.nan

    # 🎯 bar plot (trajectory 전용)
    if mode == "trajectory" and ax2 is not None:
        bar_x = [pd.to_datetime(k, format="%Y%m") + pd.DateOffset(months=1) for k in acc_dict]
        bar_y = [acc_dict[k] for k in acc_dict]
        bar_colors = [month_colors[pd.to_datetime(k, format="%Y%m").month] for k in acc_dict]
        ax2.bar(bar_x, bar_y, color=bar_colors, alpha=0.3, width=20)
        ax2.set_ylabel("ACC (lead=1, bars)", fontsize=14)
        ax2.set_ylim(-1, 1) # ACC ylim
        ax2.axhline(0, linestyle="--", color="gray", lw=0.8)
        ax1.set_title(f"Trajectory by Initialization ({year_start}–{year_end})\n Line = One Initialized Month, bar = ACC@lead-1 , Region: {region}, Var: {var}", 
                      fontsize=14, pad=40)
        ax1.set_ylim(anom_range) # Anomaly ylim
        
        # for xticklabel setting
        xticks = pd.date_range(
            start=min(pd.to_datetime(k, format="%Y%m") for k in acc_dict),
            end=max(pd.to_datetime(k, format="%Y%m") + pd.DateOffset(months=6) for k in acc_dict),
            freq='4MS'
        )
        ax1.set_xticks(xticks)
        ax1.set_xticklabels(
            [d.strftime('%Y-%m') for d in xticks],
            ha='center', fontsize=12
        )
        ax2.tick_params(axis='y', labelsize=14)

    elif mode == 'skill':
        ax1.set_title(f"ACC Timeseries ({year_start}–{year_end})\nEach Line = One Initialized Month , Region: {region}, Var: {var}", 
                      fontsize=14, pad=40)
        ax1.axhline(0, linestyle="--", color="gray", lw=0.8)
    
    ax1.set_xlabel("Target Month", fontsize=14)
    ax1.set_ylabel(xlabel, fontsize=14)
    ax1.grid(True, linestyle='--', color='lightgrey')
    ax1.tick_params(axis='y', labelsize=14)
    ax1.tick_params(axis='x', labelsize=14)
     
    legend_elements = [
        Line2D([0], [0], color=month_colors[m], lw=2, label=f'Init {m:02d}')
        for m in range(1, 13)
    ]
    ax1.legend(handles=legend_elements, #title="Initialized Month", 
               bbox_to_anchor=(0.5, 1.13), ncol=6, frameon=False,
               loc='upper center', fontsize=10)

    plt.tight_layout()
    os.makedirs(fig_dir, exist_ok=True)
    fname = f"targetSeries_byInit_{var}_{region}_{'traj' if mode=='trajectory' else 'skill'}_{year_start}_{year_end}.png"
    plt.savefig(os.path.join(fig_dir, fname), dpi=300)
    plt.close()


def plot_spatial_pattern_fcst_vs_obs(var, target_year, region_name, fig_dir):
    """
    target month 기준, OBS vs FCST (lead 1~6), BIAS(FCST-OBS) 패턴을 3x6 패널로 그림
    """

    plot_settings = {
    't2m':   {'clevels': np.arange(-5,5.1,0.5), 'blevels': np.arange(-5, 5.1, 0.5), 'cmap': 'RdBu_r'},
    'prcp':  {'clevels': np.arange(-5,5.1,0.5), 'blevels': np.arange(-5,5.1,0.5), 'cmap': 'BrBG'},
    'mslp':  {'clevels': np.arange(-50,51,5), 'blevels': np.arange(-20,21,2), 'cmap': 'coolwarm'},
    'sst':   {'clevels': np.arange(-5,5.1,0.5), 'blevels': np.arange(-5, 5.1, 0.5), 'cmap': 'RdBu_r'},
}
    settings = plot_settings.get(var, {
    'clevels': np.linspace(-3, 3, 13),
    'blevels': np.linspace(-2, 2, 9),
    'cmap': 'RdBu_r'
})
    clevels, blevels, cmap = settings['clevels'], settings['blevels'], settings['cmap']
    region_box = get_region_extent(region_name, var)
    #print(region_box)
    
    for target_month in range(1, 13):
        target_date = pd.Timestamp(f"{target_year}-{target_month:02d}-01")

        # 0. plot attributions
        if region_name == "GL":
            figsize = (36, 11)
            centerLon = 150 # Pacific center
            fs=14 # fontsize
        elif region_name == "EA":
            figsize = (14, 6)
            centerLon = 0
            fs =10
        else:
            figsize = (16, 9)
            centerLon = 0

        proj = ccrs.PlateCarree(central_longitude=centerLon)
        nrows, ncols = 3, 6
        fig, axs = plt.subplots(nrows, ncols, figsize=figsize,
                                constrained_layout=True,
                                subplot_kw={'projection': proj})
        #print(convert_lon_360_to_180(region_box))

        # 1. 관측 데이터 로드
        if var == 'sst':
            obs_file = os.path.join(sst_out_dir, f"{var}_anom_{target_year}.nc")
        else:
            obs_file = os.path.join(era5_out_dir, f"{var}_anom_{target_year}.nc")
        if not os.path.isfile(obs_file):
            print(f"[WARN] Missing OBS file: {obs_file}")
            continue

        ds_obs = xr.open_dataset(obs_file)
        try:
            obs = ds_obs[var].sel(time=target_date)
        except KeyError:
            print(f"[WARN] No OBS for {target_date}")
            continue
        # print(ds_obs.lon) 0...360

        if var == 'sst' and region_name == 'GL':
            obs = obs.where((obs.lat >= -60) & (obs.lat <= 60))

        # OBS 패널 (0,-1)
        ax_obs = axs[0,-1]
        im_obs = obs.plot(ax=ax_obs, cmap=cmap, levels=clevels, add_colorbar=False, extend='both', transform=ccrs.PlateCarree())
        ax_obs.set_title("OBS", loc='left', fontsize=fs)
        ax_obs.set_title(target_date.strftime("%Y-%m"), loc='right', fontsize=fs)
        ax_obs.set_title('',loc='center')
        ax_obs.coastlines()
        gl = ax_obs.gridlines(draw_labels=True, linestyle=':')
        gl.right_labels = False
        gl.top_labels = False
        if region_name != 'GL':
            ax_obs.set_extent(region_box, crs=proj)

        # 첫 번째 행의 나머지 5개 패널 숨김
        for i in range(0, 5):
            axs[0,i].axis('off')
  
        # 2. 각 lead별 예측
        im_fcst, im_bias = None, None

        for lead in range(1, 7):
            init_date = target_date - pd.DateOffset(months=lead)
            init_yyyymm = init_date.strftime('%Y%m')
            fcst_file = os.path.join(f'{model_out_dir}/anomaly', f"ensMem_{var}_anom_{init_yyyymm}.nc")

            if not os.path.isfile(fcst_file):
                 logger.warning(f"[SKIP] {fcst_file} 없음.")
                 no_data_panel(axs[1, 6-lead], axs[2, 6-lead]) # fcst pattern row no data
                 continue

            ds_fcst = xr.open_dataset(fcst_file)
            try:
                time_vals = ds_fcst['time'].values
                lead_idx = list(time_vals).index(np.datetime64(target_date))
            except ValueError:
                logger.warning(f"[SKIP] No forecast for {target_date} in {fcst_file}")
                no_data_panel(axs[1, 6-lead], axs[2, 6-lead]) # fcst pattern row no data
                continue

            fcst = ds_fcst[var].isel(lead=lead_idx).mean("ens").squeeze()
            if var == 'sst':
                obs_name = "OISST"
                mask = get_combined_mask(model_name=model, obs_name=obs_name)
                if mask is not None:
                    mask = mask.astype(bool)
            
                    fcst = fcst.where(mask)
            
            if var == 'sst' and region_name == 'GL':
                fcst = fcst.where((fcst.lat >= -60) & (fcst.lat <= 60))

            bias = fcst - obs
            if var == 'sst' and region_name == 'GL':
                bias = bias.where((bias.lat >= -60) & (bias.lat <= 60))
                
            # FCST 패널
            ax_fcst = axs[1, 6-lead]
            im_fcst = fcst.plot(ax=ax_fcst, cmap=cmap, levels=clevels, add_colorbar=False, extend='both', transform=ccrs.PlateCarree())
            ax_fcst.set_title(f"Lead -{lead}", loc='left', fontsize=fs)
            ax_fcst.set_title(f"init: {init_yyyymm}", loc='right', fontsize=fs)
            ax_fcst.set_title('')
            if region_name != 'GL':
                ax_fcst.set_extent(region_box, crs=proj)
            ax_fcst.coastlines()
            gl = ax_fcst.gridlines(draw_labels=True, linestyle=':')
            gl.right_labels = False
            gl.top_labels = False


            # BIAS 패널
            if var != 'prcp':
                bcmap = cmaps.temp_diff_18lev
            else:
                bcmap = cmaps.MPL_BrBG

            ax_bias = axs[2, 6-lead]
            im_bias = bias.plot(ax=ax_bias, cmap=bcmap, levels=blevels, add_colorbar=False, extend='both', transform=ccrs.PlateCarree())
            ax_bias.set_title('', loc='center')
            ax_bias.set_title(f"Bias L-{lead}", loc='left', fontsize=fs)
            if region_name != 'GL':
                ax_bias.set_extent(region_box, crs=proj)
            ax_bias.coastlines()
            gl = ax_bias.gridlines(draw_labels=True, linestyle=':')
            gl.right_labels = False
            gl.top_labels = False
            
        # Colorbar
        # OBS
        plt.colorbar(im_obs, ax=axs[0,-1], label=f'{var} Anomaly', shrink=.7)
        if im_fcst is not None:
            plt.colorbar(im_fcst, ax=axs[1,-1], label=f'{var} Anomaly', shrink=.7)
        if im_bias is not None:
            plt.colorbar(im_bias, ax=axs[2,-1], label=f'{var} Bias', shrink=.7)

        plt.suptitle(f"OBS vs FCST by LeadTime \n (Target Month: {target_date.strftime('%Y%m')}, Region: {region_name}, Var: {var})", fontsize=20)
    
        save_fname = os.path.join(fig_dir, f"{var}_pattern_compare_{region_name}_{target_date.strftime('%Y%m')}.png")
        plt.savefig(save_fname, dpi=300, bbox_inches='tight')
        plt.close()
        logger.info(f"[INFO] Saved pattern comparison figure: {save_fname}")

