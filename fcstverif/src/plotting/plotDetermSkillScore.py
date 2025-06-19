import xarray as xr
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.patches as patches
from matplotlib.lines import Line2D
import cmaps
import matplotlib.gridspec as gridspec
import cartopy.crs as ccrs
import os
from config import *
from src.utils.general_utils import generate_yyyymm_list, get_combined_mask
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

        # 멤버별 점선 (회색)
        if score in ds.data_vars:
            for e in ds['ens'].values:
                y_vals = [ds[score].sel(ens=e).sel(time=t).item() if t in ds['time'].values else np.nan
                          for t in ds['time'].values]
                plt.plot(lead_valid, y_vals, '--', color='gray', alpha=0.4, linewidth=0.8)

        # 앙상블 평균 (진한 파란색)
        mean_score_name = f"{score}_mean"
        if mean_score_name in ds.data_vars:
            y_vals = [ds[mean_score_name].sel(time=t).item() if t in ds['time'].values else np.nan
                      for t in ds['time'].values]
            plt.plot(lead_valid, y_vals, '-o', color='royalblue', label='Ensemble Mean')

        plt.xlabel('Lead Time (month)')
        plt.ylabel(score.upper())
        plt.title(f'{score.upper()} by Lead Time\n(Initialized: {yyyymm}, Region: {region_name}, Var: {var})')
        plt.grid(True, linestyle='--', color='lightgrey')
        plt.ylim([-1,1])
        plt.xticks(lead_full)
        #plt.xlim(0.9,6.1)
        plt.legend()

        save_fname = os.path.join(fig_dir, f"{score}_init_{var}_{region_name}_{yyyymm}.png")
        plt.savefig(save_fname, dpi=300, bbox_inches='tight')
        #plt.show()
        plt.close()

        logger.info(f"[INFO] Saved: {save_fname}")
        ds.close()


def plot_skill_heatmap_initialized_month(var, target_year, region_name, data_dir, fig_dir, score):
    # 데이터 준비
    months = range(1, 13)
    leads = range(1, 7)
    
    heatmap_data = np.full((len(months), len(leads)), np.nan)

    y_labels = [f"{target_year}-{m:02d}" for m in months]

    for i, month in enumerate(months):
        yyyymm = f"{target_year}{month:02d}"
        file_path = os.path.join(data_dir, f"ensScore_det_{var}_{yyyymm}.nc")

        if not os.path.isfile(file_path):
            logger.info(f"[WARN] {file_path} 없음.")
            continue

        ds = xr.open_dataset(file_path)

        for j, lead in enumerate(leads):
            try:
                time_idx = ds['lead'].values.tolist().index(lead)
                heatmap_data[i, j] = ds[f"{score}_mean"].isel(time=time_idx).item()
            except Exception:
                logger.info(f"[WARN] {yyyymm} Lead={lead} 없음")
                continue

    # colormap 설정(discrete levels)
    bounds = np.arange(-1,1.01, 0.2)
    cmap = plt.get_cmap('coolwarm', len(bounds)-1)
    norm = mcolors.BoundaryNorm(bounds, cmap.N)

    # 히트맵 그리기
    plt.figure(figsize=(5, len(y_labels)*0.5))
    im = plt.imshow(heatmap_data, cmap=cmap, norm=norm, aspect='auto')

    # grid 설정 (white borders)
    ax = plt.gca()
    for i in range(len(months)):
        for j in range(len(leads)):
            rect = patches.Rectangle((j-0.5, i-0.5), 1, 1, linewidth=1,
                                     edgecolor='white', facecolor='none')
            ax.add_patch(rect)

    # annotation
    for i in range(len(months)):
        for j in range(len(leads)):
            val = heatmap_data[i, j]
            if not np.isnan(val):
                ax.text(j, i, f"{val:.2f}", ha='center', va='center', color='black')

    # 축 설정
    ax.set_xticks(np.arange(len(leads)))
    ax.set_xticklabels([f"Lead {l}" for l in leads])
    ax.set_yticks(np.arange(len(months)))
    ax.set_yticklabels(y_labels)

    ax.set_xlabel('Lead Time (month)')
    ax.set_ylabel('Initialized Month')
    ax.set_title(f'{score.upper()} Heatmap\n(Region: {region_name}, Var: {var}, Year: {target_year})')

    # colorbar 설정
    cbar = plt.colorbar(im, ticks=bounds, spacing='proportional')
    cbar.set_label(score.upper())

    plt.tight_layout()
    save_fname = os.path.join(fig_dir, f"{score}_heatmap_init_{var}_{region_name}_{target_year}.png")
    #plt.show()
    plt.savefig(save_fname, dpi=300, bbox_inches='tight', facecolor='w')
    plt.close()
    logger.info(f"[INFO] Saved Heatmap: {save_fname}")


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
            plt.figure(figsize=(8, 5))

            # 💡 멤버별 회색 점선
            for e, values in member_score_dict.items():
                if len(values) == len(lead_list):
                    plt.plot(lead_list, values, '--', color='gray', alpha=0.4, linewidth=0.8)

            # 💡 앙상블 평균 진한 선
            plt.plot(lead_list, mean_score_list, '-o', color='forestgreen', label='Ensemble Mean')

            for i, txt in enumerate(init_month_labels):
                plt.text(lead_list[i], mean_score_list[i], txt, fontsize=9,
                         ha='center', va='bottom', color='blue')

            plt.xlabel('Lead Time (month)')
            plt.ylabel(score.upper())
            plt.ylim([-1,1]) # if score ACC
            plt.title(f'{score.upper()} by Lead Time\n(Target Month: {target_date.strftime("%Y-%m")}, Region: {region_name}, Var: {var})')
            plt.xticks([1, 2, 3, 4, 5, 6])
            plt.grid(True, linestyle='--', color='lightgrey')
            plt.legend()

            save_fname = os.path.join(fig_dir, f"{score}_target_{var}_{region_name}_{target_date.strftime('%Y%m')}.png")
            plt.savefig(save_fname, dpi=300, bbox_inches='tight')
            plt.close()

            logger.info(f"[INFO] Saved: {save_fname}")
        else:
            logger.info(f"[WARN] No data to plot for target month {target_date.strftime('%Y-%m')}")


def plot_skill_by_initialized_line(var, year_start, year_end, region_name, score, data_dir, fig_dir):
    """
    initialized month에 따라 12가지 색 시계열을 전체 검증기간에 대해 그림
    """
    leads = range(1, 7)
    yyyymm_list = generate_yyyymm_list(year_start, year_end)
    #yyyymm =init_months = pd.date_range(start=f"{year_start}-01", end=f"{year_end}-12", freq='MS')

    # 12개 고유 색상 지정 (월별 색)
    cmap = plt.colormaps['tab20']
    month_colors = {month: cmap((month - 1) % 12) for month in range(1, 13)}


    # 결과를 저장할 dict: {init_month: [target_month1, ..., target_month6], [score1,..., score6]}
    series_by_init = {}

    #for init_date in init_months:
    for yyyymm in yyyymm_list:
        #yyyymm = init_date.strftime('%Y%m')
        file_path = os.path.join(data_dir, f"ensScore_det_{var}_{yyyymm}.nc")
        if not os.path.isfile(file_path):
            continue

        ds = xr.open_dataset(file_path)
        init_date = pd.to_datetime(f"{yyyymm}01")
        target_dates = [init_date + pd.DateOffset(months=l) for l in leads]
        scores = []

        for l in leads:
            try:
                time_idx = ds['lead'].values.tolist().index(l)
                # 💡 평균값만 사용
                val = ds[f"{score}_mean"].isel(time=time_idx).item()
            except Exception:
                val = np.nan
            scores.append(val)

        #series_by_init[init_date] = (target_dates, scores)
        series_by_init[yyyymm] = (target_dates, scores)

    # 시각화
    plt.figure(figsize=(14, 6))
    for yyyymm, (target_dates, scores) in series_by_init.items():
        init_date = pd.to_datetime(f"{yyyymm}01")
        month = init_date.month
        color = month_colors[month]
        #label = init_date.strftime('%Y-%m')
        label = yyyymm
        plt.plot(target_dates, scores, '-o', color=color)

    # 색상 범례용 (12개월)
    legend_elements = [
        Line2D([0], [0], color=month_colors[m], lw=2, label=f'Init {m:02d}')
        for m in range(1, 13)
    ]

    plt.axhline(0, color='gray', linestyle='--')
    plt.xlabel("Target Month", fontsize=14)
    plt.ylabel(score.upper(), fontsize=14)
    plt.title(f"{score.upper()} by Target Month\nEach Line = One Initialized Month ({year_start}–{year_end}), Region: {region_name}, Var: {var}", fontsize=15)
    plt.legend(handles=legend_elements, title="Initialized Month", bbox_to_anchor=(1.01, 1), loc='upper left', fontsize=14)
    plt.grid(True, linestyle='--', color='lightgrey')
    plt.tight_layout()

    save_fname = os.path.join(fig_dir, f"{score}_targetSeries_byInit_{var}_{region_name}_{year_start}_{year_end}.png")
    #plt.show()
    plt.savefig(save_fname, dpi=300, bbox_inches='tight')
    plt.close()
    logger.info(f"[INFO] Saved: {save_fname}")

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
    region_box = REGIONS[region_name]
    #print(region_box)
    
    for target_month in range(1, 13):
        target_date = pd.Timestamp(f"{target_year}-{target_month:02d}-01")

        # 0. plot attributions
        if region_name == "GL":
            figsize = (36, 10.5)
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
                no_data_panel(axs[1, 6-lead], axs[2, 6-lead])
                continue

            ds_fcst = xr.open_dataset(fcst_file)
            try:
                time_vals = ds_fcst['time'].values
                lead_idx = list(time_vals).index(np.datetime64(target_date))
            except ValueError:
                logger.warning(f"[SKIP] No forecast for {target_date} in {fcst_file}")
                no_data_panel(axs[1, lead-1], axs[2, lead-1])
                continue

            fcst = ds_fcst[var].isel(lead=lead_idx).mean("ens").squeeze()
            if var == 'sst':
                obs_name = "OISST"
                mask = get_combined_mask(model_name=model, obs_name=obs_name)
                if mask is not None:
                    mask = mask.astype(bool)
            
                    fcst = fcst.where(mask)

            bias = fcst - obs

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

        plt.suptitle(f"OBS vs FCST by LeadTime \n (Target Month: {target_date.strftime('%Y%m')}, Region: {region_name}, Var: {var})", fontsize=16)
    
        save_fname = os.path.join(fig_dir, f"{var}_pattern_compare_{region_name}_{target_date.strftime('%Y%m')}.png")
        plt.savefig(save_fname, dpi=300, bbox_inches='tight')
        plt.close()
        logger.info(f"[INFO] Saved pattern comparison figure: {save_fname}")

