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
import matplotlib.cm as cmaps
import matplotlib.gridspec as gridspec
import cartopy.crs as ccrs
import os
from fcstverif.config import *
from fcstverif.utils.logging_utils import init_logger
logger = init_logger()

  
def plot_skill_initialized_month(var, year, region_name, score='acc', fig_dir=None):
    data_dir = os.path.join(verification_out_dir, region_name)

    months = range(1,13)

    for month in months:
        yyyymm = f"{year}{month:02d}"
        file_path = os.path.join(data_dir, f"ensScore_{var}_{yyyymm}.nc")
        
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


def plot_skill_heatmap_initialized_month(var, year, region_name, score='acc', fig_dir=None):

    data_dir = os.path.join(verification_out_dir, region_name)

    # 데이터 준비
    months = range(1, 13)
    leads = range(1, 7)
    
    heatmap_data = np.full((len(months), len(leads)), np.nan)

    month_labels = [f"{year}-{m:02d}" for m in months]

    for i, month in enumerate(months):
        yyyymm = f"{year}{month:02d}"
        file_path = os.path.join(data_dir, f"ensScore_{var}_{yyyymm}.nc")

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
    plt.figure(figsize=(6, 8))
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
    ax.set_yticklabels(month_labels)

    ax.set_xlabel('Lead Time (month)')
    ax.set_ylabel('Initialized Month')
    ax.set_title(f'{score.upper()} Heatmap\n(Region: {region_name}, Var: {var}, Year: {year})')

    # colorbar 설정
    cbar = plt.colorbar(im, ticks=bounds, spacing='proportional')
    cbar.set_label(score.upper())

    plt.tight_layout()
    save_fname = os.path.join(fig_dir, f"{score}_heatmap_init_{var}_{region_name}_{year}.png")
    #plt.show()
    plt.savefig(save_fname, dpi=300, bbox_inches='tight', facecolor='w')
    plt.close()
    logger.info(f"[INFO] Saved Heatmap: {save_fname}")


def plot_skill_target_month(var, target_year, region_name, score='acc', fig_dir=None):
    data_dir = os.path.join(verification_out_dir, region_name)
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
            file_path = os.path.join(data_dir, f"ensScore_{var}_{init_yyyymm}.nc")

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


def plot_skill_by_initialized_line(var, year_start, year_end, region_name, score='acc', fig_dir=None):
    """
    initialized month에 따라 12가지 색 시계열을 전체 검증기간에 대해 그림
    """
    data_dir = os.path.join(verification_out_dir, region_name)
    leads = range(1, 7)
    init_months = pd.date_range(start=f"{year_start}-01", end=f"{year_end}-12", freq='MS')

    # 12개 고유 색상 지정 (월별 색)
    cmap = plt.colormaps['tab20']
    month_colors = {month: cmap((month - 1) % 12) for month in range(1, 13)}


    # 결과를 저장할 dict: {init_month: [target_month1, ..., target_month6], [score1,..., score6]}
    series_by_init = {}

    for init_date in init_months:
        yyyymm = init_date.strftime('%Y%m')
        file_path = os.path.join(data_dir, f"ensScore_{var}_{yyyymm}.nc")
        if not os.path.isfile(file_path):
            continue

        ds = xr.open_dataset(file_path)
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

        series_by_init[init_date] = (target_dates, scores)

    # 시각화
    plt.figure(figsize=(14, 6))
    for init_date, (target_dates, scores) in series_by_init.items():
        month = init_date.month
        color = month_colors[month]
        label = init_date.strftime('%Y-%m')
        plt.plot(target_dates, scores, '-o', color=color)

    # 색상 범례용 (12개월)
    legend_elements = [
        Line2D([0], [0], color=month_colors[m], lw=2, label=f'Init {m:02d}')
        for m in range(1, 13)
    ]

    plt.axhline(0, color='gray', linestyle='--')
    plt.xlabel("Target Month")
    plt.ylabel(score.upper())
    plt.title(f"{score.upper()} by Target Month\nEach Line = One Initialized Month ({year_start}–{year_end}), Region: {region_name}, Var: {var}")
    plt.legend(handles=legend_elements, title="Initialized Month", bbox_to_anchor=(1.01, 1), loc='upper left')
    plt.grid(True, linestyle='--', color='lightgrey')
    plt.tight_layout()

    save_fname = os.path.join(fig_dir, f"{score}_targetSeries_byInit_{var}_{region_name}_{year_start}_{year_end}.png")
    #plt.show()
    plt.savefig(save_fname, dpi=300, bbox_inches='tight')
    plt.close()
    logger.info(f"[INFO] Saved: {save_fname}")
   
def plot_spatial_pattern_fcst_vs_obs(var, target_year, region_name, fig_dir, vmin=-3, vmax=3):
    """
    target month 기준, OBS vs FCST (lead 1~6), BIAS(FCST-OBS) 패턴을 3x6 패널로 그림
    """

    plot_settings = {
    't2m':   {'clevels': np.arange(-5,5.1,0.5), 'blevels': np.arange(-5, 5.1, 0.5), 'cmap': 'RdBu_r'},
    'prcp':  {'clevels': np.arange(-50,51,5), 'blevels': np.arange(-20,21,2), 'cmap': 'BrBG'},
    'mslp':  {'clevels': np.arange(-50,51,5), 'blevels': np.arange(-20,21,2), 'cmap': 'coolwarm'},
    'sst':   {'clevels': np.arange(-5,5.1,0.5), 'blevels': np.arange(-5, 5.1, 0.5), 'cmap': 'RdBu_r'},
}
    settings = plot_settings.get(var, {
    'clevels': np.linspace(-3, 3, 13),
    'blevels': np.linspace(-2, 2, 9),
    'cmap': 'RdBu_r'
})
    clevels, blevels, cmap = settings['clevels'], settings['blevels'], settings['cmap']

    # region 크기에 따른 figsize 자동 계산
    def compute_figsize(region_box, base_width=20):
        lon_min, lon_max, lat_min, lat_max = region_box
        lon_range = lon_max - lon_min
        lat_range = lat_max - lat_min
        aspect_ratio = lon_range / lat_range if lat_range != 0 else 1
        height = base_width / aspect_ratio
        return (base_width, height)

    region_box = REGIONS[region_name]
    figsize = compute_figsize(region_box)

    for target_month in range(1, 13):
        target_date = pd.Timestamp(f"{target_year}-{target_month:02d}-01")
        region_box = REGIONS[region_name]

        # 1. 관측 데이터 로드
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

        fig = plt.figure(figsize=(20,6), constrained_layout=True) #figsize=figsize,
        gs = gridspec.GridSpec(3, 6, figure=fig, hspace=0.1, wspace=0.1)
        axes = np.empty((3, 6), dtype=object)

        # OBS 패널 (0,0)
        ax_obs = fig.add_subplot(gs[0, 0], projection=ccrs.PlateCarree())
        im_obs = obs.plot(ax=ax_obs, cmap=cmap, levels=clevels, add_colorbar=False, extend='both')
        ax_obs.set_title("OBS", loc='left', fontsize=10)
        ax_obs.set_title(target_date.strftime("%Y-%m"), loc='right', fontsize=10)
        ax_obs.set_title('',loc='center')
        #ax_obs.set_extent(region_box, crs=ccrs.PlateCarree())
        ax_obs.coastlines()
        gl = ax_obs.gridlines(draw_labels=True)
        gl.right_labels = False
        gl.top_labels = False
        axes[0, 0] = ax_obs

        # 첫 번째 행의 나머지 5개 패널 숨김
        for i in range(1, 6):
            ax = fig.add_subplot(gs[0, i])
            ax.axis('off')
            axes[0, i] = ax

        # 2. 각 lead별 예측
        im_fcst, im_bias = None, None

        for lead in range(1, 7):
            init_date = target_date - pd.DateOffset(months=lead)
            init_yyyymm = init_date.strftime('%Y%m')
            fcst_file = os.path.join(fanomaly_dir, f"ensMem_{var}_anom_{init_yyyymm}.nc")

            if not os.path.isfile(fcst_file):
                logger.warning(f"[SKIP] {fcst_file} 없음.")
                continue

            ds_fcst = xr.open_dataset(fcst_file)
            if target_date not in ds_fcst['time'].values:
                print(f"[SKIP] No forecast for {target_date} in {fcst_file}")
                continue

            lead_idx = np.where(ds_fcst['time'].values == np.datetime64(target_date))[0]
            if len(lead_idx) == 0:
                print(f"[SKIP] No matching time in forecast: {target_date}")
                continue

            fcst = ds_fcst[var].isel(lead=lead_idx[0]).mean("ens").squeeze()
            bias = fcst - obs

            # FCST 패널
            ax_fcst = fig.add_subplot(gs[1, lead - 1], projection=ccrs.PlateCarree())
            im_fcst = fcst.plot(ax=ax_fcst, cmap=cmap, levels=clevels, add_colorbar=False, extend='both')
            ax_fcst.set_title(f"Lead -{lead}", loc='left', fontsize=10)
            ax_fcst.set_title(f"init: {init_yyyymm}", loc='right', fontsize=10)
            ax_fcst.set_title('')
            #ax_fcst.set_extent(region_box, crs=ccrs.PlateCarree())
            ax_fcst.coastlines()
            gl = ax_fcst.gridlines(draw_labels=True)
            gl.right_labels = False
            gl.top_labels = False
            axes[1, lead - 1] = ax_fcst

            # BIAS 패널
            ax_bias = fig.add_subplot(gs[2, lead - 1], projection=ccrs.PlateCarree())
            im_bias = bias.plot(ax=ax_bias, cmap='bwr', levels=blevels, add_colorbar=False, extend='both')
            ax_bias.set_title('', loc='center')
            ax_bias.set_title(f"Bias L-{lead}", loc='left', fontsize=10)
            #ax_bias.set_extent(region_box, crs=ccrs.PlateCarree())
            ax_bias.coastlines()
            gl = ax_bias.gridlines(draw_labels=True)
            gl.right_labels = False
            gl.top_labels = False
            axes[2, lead - 1] = ax_bias

        # Colorbar
        # OBS
        plt.colorbar(im_obs, ax=axes[0,-1], label=f'{var} Anomaly', shrink=.7)
        if axes[1,:].any():
            plt.colorbar(im_fcst, ax=axes[1,-1], label=f'{var} Anomaly', shrink=.7)
        if axes[2,:].any():
            plt.colorbar(im_bias, ax=axes[2,-1], label=f'{var} Bias', shrink=.7)

        save_fname = os.path.join(fig_dir, f"{var}_pattern_compare_{region_name}_{target_date.strftime('%Y%m')}.png")
        plt.savefig(save_fname, dpi=300, bbox_inches='tight')
        plt.close()
        logger.info(f"[INFO] Saved pattern comparison figure: {save_fname}")



# if __name__=='__main__':

#     for region_name, region_box in REGIONS.items():
#         for var in variables:
#             for year in fyears:
#                 #plot_skill_target_month(var='t2m', target_year=2022, region_name='EA', score='acc')
# #                plot_skill_initialized_month(
# #                        var=var,
# #                        year=year,
# #                        region_name=region_name,
# #                        score='acc')
                
#                 plot_skill_heatmap_initialized_month(
#                         var=var,
#                         year=year,
#                         region_name=region_name,
#                         score='acc')
#             plot_skill_by_initialized_line( 
#                    var=var,    
#                    year_start=year_start,
#                    year_end=year_end,
#                    region_name=region_name,
#                    score='acc'
#                    )
