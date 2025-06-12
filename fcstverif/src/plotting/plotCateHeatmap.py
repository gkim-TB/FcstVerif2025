import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.patches as patches
import os

from config import *
from src.utils.logging_utils import init_logger
logger = init_logger()

def flatten_nested_csv(nested_df):
    records = []
    for _, row in nested_df.iterrows():
        for col in row.dropna():
            if isinstance(col, str):
                try:
                    col = eval(col)
                except Exception:
                    continue
            records.append(col)
    return pd.DataFrame(records)

def plot_det_cate_heatmap(var, years, region_name, data_dir, fig_dir, score1='acc', score2='hss'):
    df_nested = pd.read_csv(f"{data_dir}/Det_tercile_score_{var}_{region_name}.csv") # Deterministic Tercile Scores (HR, HSS)
    df_flat = flatten_nested_csv(df_nested)
    df_flat['yyyymm'] = df_flat['yyyymm'].astype(str)
    df_flat['year'] = df_flat['yyyymm'].str[:4]
    df_flat['month'] = df_flat['yyyymm'].str[4:6]

    cmap1 = plt.get_cmap('YlGn', 5)
    cmap2 = plt.get_cmap('RdGy_r', 10)
    bounds1 = np.linspace(0, 1, 6)
    bounds2 = np.linspace(-1, 1, 11)
    norm1 = mcolors.BoundaryNorm(bounds1, cmap1.N)
    norm2 = mcolors.BoundaryNorm(bounds2, cmap2.N)


    for year in years:
        df_year = df_flat[df_flat['year'] == str(year)].copy()
        if df_year.empty:
            continue

        # 월 기준으로 y축 정렬
        df_year['month'] = df_year['yyyymm'].str[4:6]
        y_labels = sorted(df_year['yyyymm'].unique(), key=lambda x: int(x[4:6]))
        x_labels = sorted(df_year['lead'].unique())

        grid1 = np.full((len(y_labels), len(x_labels)), np.nan)
        grid2 = np.full((len(y_labels), len(x_labels)), np.nan)

        for i, yyyymm in enumerate(y_labels):
            for j, lead in enumerate(x_labels):
                match = df_year[(df_year['yyyymm'] == yyyymm) & (df_year['lead'] == lead)]
                if not match.empty:
                    grid1[i, j] = match[score1].values[0]
                    grid2[i, j] = match[score2].values[0]

        fig, ax = plt.subplots(figsize=(5, len(y_labels)*0.5))

        for i in range(len(y_labels)):
            for j in range(len(x_labels)):
                x = j
                y = i
                val1 = grid1[i, j] # ACC
                val2 = grid2[i, j] # HSS

                if not np.isnan(val1):
                    ax.add_patch(patches.Polygon(
                        [[x, y], [x+1, y], [x, y+1]],
                        facecolor=cmap1(norm1(val1)), edgecolor='white', lw=2,
                    ))
                if not np.isnan(val2):
                    ax.add_patch(patches.Polygon(
                        [[x+1, y], [x+1, y+1], [x, y+1]],
                        facecolor=cmap2(norm2(val2)), edgecolor='white', lw=2,
                    ))

                if not np.isnan(val1) and not np.isnan(val2):
                    color1 = 'white' if val1 >= 0.6 else 'black'
                    color2 = 'white' if abs(val2) >= 0.6 else 'black'
                    ax.text(x + 0.3, y + 0.25, f'{val1:.2f}', ha='center', va='center', fontsize=7, color=color1) # ACC
                    ax.text(x + 0.7, y + 0.75, f'{val2:.2f}', ha='center', va='center', fontsize=7, color=color2) # HSS

        ax.set_xticks(np.arange(len(x_labels)) + 0.5)
        ax.set_xticklabels([f'Lead {l}' for l in x_labels])
        ax.set_yticks(np.arange(len(y_labels)) + 0.5)
        ax.set_yticklabels(y_labels)
        ax.set_xlim(0, len(x_labels))
        ax.set_ylim(0, len(y_labels))
        ax.invert_yaxis()
        ax.set_xlabel("Lead Time")
        ax.set_ylabel("Initialized Month")
        ax.set_title(f"HR/HSS Heatmap \n(Region:{region_name}, Var={var}, Year: {year})")

        fig.subplots_adjust(right=0.88)
        cax1 = fig.add_axes([0.90, 0.55, 0.015, 0.3])
        sm1 = plt.cm.ScalarMappable(cmap=cmap1, norm=norm1)
        sm1.set_array([])
        cbar1 = plt.colorbar(sm1, cax=cax1, ticks=bounds1)
        cbar1.set_label('HitRate')

        cax2 = fig.add_axes([0.90, 0.15, 0.015, 0.3])
        sm2 = plt.cm.ScalarMappable(cmap=cmap2, norm=norm2)
        sm2.set_array([])
        cbar2 = plt.colorbar(sm2, cax=cax2, ticks=bounds2)
        cbar2.set_label('HSS')
        #plt.tight_layout(rect=[0,0,0.88,1])
        save_fname = os.path.join(fig_dir, f"det_ter_score_{var}_{region_name}_{year}.png")
        fig.savefig(save_fname, dpi=300, bbox_inches='tight')


    
