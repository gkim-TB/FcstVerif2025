import xarray as xr
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.patches as patches
from matplotlib.lines import Line2D
import matplotlib.cm as cmaps
import os
from config import *

def plot_skill_initialized_month(var, year, region_name, score='acc'):
    data_dir = os.path.join(verification_out_dir, region_name)

    months = range(1,13)

    for month in months:
        yyyymm = f"{year}{month:02d}"
        file_path = os.path.join(data_dir, f"score_{var}_{yyyymm}.nc")
        
        if not os.path.isfile(file_path):
            print(f"[WARN] {file_path} 없음.")
            continue
        
        ds = xr.open_dataset(file_path)
        
        leads = ds['lead'].values
        scores = ds[score].values
        
        plt.figure(figsize=(8, 5))
        plt.plot(leads, scores, '-o', color='royalblue')

        plt.xlabel('Lead Time (month)')
        plt.ylabel(score.upper())
        plt.title(f'{score.upper()} by Lead Time\n(Initialized: {yyyymm}, Region: {region_name}, Var: {var})')
        plt.grid(True, linestyle='--', color='lightgrey')
        plt.ylim([-1,1])

        save_fname = os.path.join(output_fig_dir, f"{score}_init_{var}_{region_name}_{yyyymm}.png")
        plt.savefig(save_fname, dpi=300, bbox_inches='tight')
        #plt.show()
        plt.close()

        print(f"[INFO] Saved: {save_fname}")


def plot_skill_heatmap_initialized_month(var, year, region_name, score='acc'):

    data_dir = os.path.join(verification_out_dir, region_name)

    # 데이터 준비
    months = range(1, 13)
    leads = range(1, 7)
    
    heatmap_data = np.full((len(months), len(leads)), np.nan)

    month_labels = [f"{year}-{m:02d}" for m in months]

    for i, month in enumerate(months):
        yyyymm = f"{year}{month:02d}"
        file_path = os.path.join(data_dir, f"score_{var}_{yyyymm}.nc")

        if not os.path.isfile(file_path):
            print(f"[WARN] {file_path} 없음.")
            continue

        ds = xr.open_dataset(file_path)

        for j, lead in enumerate(leads):
            try:
                heatmap_data[i, j] = ds[score].sel(lead=lead).item()
            except KeyError:
                print(f"[WARN] {yyyymm} Lead={lead} 없음")
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
    save_fname = os.path.join(output_fig_dir, f"{score}_heatmap_init_{var}_{region_name}_{year}.png")
    #plt.show()
    plt.savefig(save_fname, dpi=300, bbox_inches='tight', facecolor='w')
    plt.close()
    print(f"[INFO] Saved Heatmap: {save_fname}")

#    fig, ax = plt.subplots(figsize=(10, 8))
#    im = ax.imshow(heatmap_data, origin='lower',
#            vmin=-1, vmax=1, cmap='YlGn')
#    texts = annotate_heatmap(im, valfmt="{x:.1f}")
##    ax = sns.heatmap(
##        heatmap_data, 
##        annot=True, fmt=".2f", cmap='RdBu_r', center=0,
##        xticklabels=[f"Lead {lead}" for lead in leads],
##        yticklabels=month_labels,
##        cbar_kws={'label': score.upper()}
##    )
#
#    ax.set_xlabel('Lead Time (month)')
#    ax.set_ylabel('Initialized Month')
#    ax.set_title(f'{score.upper()} Heatmap\n(Region: {region_name}, Var: {var}, Year: {year})')
#
#    plt.tight_layout()
#    save_fname = os.path.join(output_fig_dir, f"{score}_heatmap_init_{var}_{region_name}_{year}.png")
#    plt.savefig(save_fname, dpi=300, bbox_inches='tight', facecolor='w')
#    plt.show()
#    plt.close()
#
#    print(f"[INFO] Saved Heatmap: {save_fname}")
#

def plot_skill_target_month(var, target_year, region_name, score='acc'):
    data_dir = os.path.join(verification_out_dir, region_name)
    target_months = range(1, 13)

    for target_month in target_months:
        target_date = pd.Timestamp(f"{target_year}-{target_month:02d}-01")

        lead_list = []
        score_list = []
        init_month_labels = []

        for lead in range(1, 7):
            init_date = target_date - pd.DateOffset(months=lead)
            init_yyyymm = init_date.strftime('%Y%m')
            file_path = os.path.join(data_dir, f"score_{var}_{init_yyyymm}.nc")

            if not os.path.isfile(file_path):
                print(f"[WARN] No file: {file_path}")
                continue

            ds = xr.open_dataset(file_path)

            try:
                score_val = ds[score].sel(lead=lead).item()
                score_list.append(score_val)
                lead_list.append(lead)
                init_month_labels.append(init_yyyymm)
            except KeyError:
                print(f"[WARN] No lead={lead} in {file_path}")
                continue

        # 값이 존재하면 그래프 그리기
        if score_list:
            plt.figure(figsize=(8, 5))
            plt.plot(lead_list, score_list, '-o', color='forestgreen')

            # 각 점에 initialized month 표기
            for i, txt in enumerate(init_month_labels):
                plt.text(lead_list[i], score_list[i], txt, fontsize=9,
                         ha='center', va='bottom', color='blue')

            plt.xlabel('Lead Time (month)')
            plt.ylabel(score.upper())
            plt.title(f'{score.upper()} by Lead Time\n(Target Month: {target_date.strftime("%Y-%m")}, Region: {region_name}, Var: {var})')
            plt.xticks([1,2,3,4,5,6])
            plt.grid(True)

            save_fname = os.path.join(
                output_fig_dir,
                f"{score}_target_{var}_{region_name}_{target_date.strftime('%Y%m')}.png"
            )

            plt.show()

            plt.savefig(save_fname, dpi=300, bbox_inches='tight')
            plt.close()

            print(f"[INFO] Saved: {save_fname}")
        else:
            print(f"[WARN] No data to plot for target month {target_date.strftime('%Y-%m')}")

def plot_skill_by_initialized_line(var, year_start, year_end, region_name, score='acc'):
    """

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
        file_path = os.path.join(data_dir, f"score_{var}_{yyyymm}.nc")
        if not os.path.isfile(file_path):
            continue

        ds = xr.open_dataset(file_path)
        target_dates = [init_date + pd.DateOffset(months=l) for l in leads]
        scores = []

        for l in leads:
            try:
                val = ds[score].sel(lead=l).item()
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

    save_fname = os.path.join(output_fig_dir, f"{score}_targetSeries_byInit_{var}_{region_name}_{year_start}_{year_end}.png")
    #plt.show()
    plt.savefig(save_fname, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"[INFO] Saved: {save_fname}")



if __name__=='__main__':

    for region_name, region_box in REGIONS.items():
        for var in variables:
            for year in fyears:
                #plot_skill_target_month(var='t2m', target_year=2022, region_name='EA', score='acc')
#                plot_skill_initialized_month(
#                        var=var,
#                        year=year,
#                        region_name=region_name,
#                        score='acc')
                
                plot_skill_heatmap_initialized_month(
                        var=var,
                        year=year,
                        region_name=region_name,
                        score='acc')
            plot_skill_by_initialized_line( 
                   var=var,    
                   year_start=year_start,
                   year_end=year_end,
                   region_name=region_name,
                   score='acc'
                   )
