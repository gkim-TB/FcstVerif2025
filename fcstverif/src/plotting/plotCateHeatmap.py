# plotCateHeatmap.py

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.patches as patches
from config import *  # verify_start/verify_end, fyears 등
from src.utils.logging_utils import init_logger

logger = init_logger()


def _load_cate_rollup(data_dir: str, var: str, region_name: str) -> pd.DataFrame:
    """
    Load roll-up CSV for deterministic tercile category scores.
    Expected columns: yyyymm(str), lead(int), target(str), acc(float), hss(float)
    """
    # e.g., {data_dir}/Det_tercile_score_t2m_EA.csv
    fpath = os.path.join(data_dir, f"Det_tercile_score_{var}_{region_name}.csv")  # <<< CHANGED
    if not os.path.isfile(fpath):
        logger.warning(f"[CateHeatmap] Roll-up CSV not found: {fpath}")  # <<< CHANGED
        return pd.DataFrame(columns=["yyyymm", "lead", "target", "acc", "hss"])  # <<< CHANGED

    try:
        df = pd.read_csv(fpath)
    except Exception as e:
        logger.warning(f"[CateHeatmap] Failed to read roll-up CSV: {fpath} ({e})")  # <<< CHANGED
        return pd.DataFrame(columns=["yyyymm", "lead", "target", "acc", "hss"])  # <<< CHANGED

    # Normalize dtypes
    if "yyyymm" in df:
        df["yyyymm"] = df["yyyymm"].astype(str)  # <<< CHANGED
    if "lead" in df:
        df["lead"] = pd.to_numeric(df["lead"], errors="coerce").astype("Int64")  # <<< CHANGED
    # acc/hss could be missing for some cells
    for col in ["acc", "hss"]:
        if col in df:
            df[col] = pd.to_numeric(df[col], errors="coerce")  # <<< CHANGED

    return df  # <<< CHANGED


def plot_det_cate_heatmap(   # <<< CHANGED: signature 통일 (연도별 1장)
    var: str,
    target_year: int,
    region_name: str,
    data_dir: str,
    fig_dir: str,
    score1: str = "acc",     # left triangle: HitRate(=acc)  # <<< CHANGED
    score2: str = "hss"      # right triangle: HSS           # <<< CHANGED
):
    """
    Deterministic tercile (AN/NN/BN) verification dual-score heatmap per year.
    - Style matches plot_det_skill_heatmap:
      x-axis: Lead 1..6, y-axis: Initialized Month (YYYY-01..YYYY-12)
    - Cells are split triangles: left=score1(ACC/HitRate), right=score2(HSS)
    - Missing yyyymm/lead remains blank (no polygon), just like skill heatmap.

    Parameters
    ----------
    var : str
    target_year : int
    region_name : str
    data_dir : str
        Directory containing the roll-up CSV 'Det_tercile_score_{var}_{region}.csv'.
    fig_dir : str
    score1 : str
        Column name for left triangle (default 'acc').
    score2 : str
        Column name for right triangle (default 'hss').
    """
    # 1) Load roll-up CSV (행 기반)  # <<< CHANGED
    df = _load_cate_rollup(data_dir, var, region_name)
    if df.empty:
        logger.info(f"[CateHeatmap] No data to plot (empty roll-up). year={target_year}")  # <<< CHANGED
        return

    # 2) Filter target year & basic axis labels  # <<< CHANGED
    df["year"] = df["yyyymm"].str[:4]
    df["month"] = pd.to_numeric(df["yyyymm"].str[4:6], errors="coerce").astype("Int64")

    df_year = df[df["year"] == str(target_year)].copy()  # <<< CHANGED
    if df_year.empty:
        logger.info(f"[CateHeatmap] No rows for year={target_year} in roll-up.")  # <<< CHANGED
        return

    months = list(range(1, 13))                 # fixed 1..12  # <<< CHANGED
    leads = list(range(1, 7))                   # fixed 1..6   # <<< CHANGED
    y_labels = [f"{target_year}-{m:02d}" for m in months]  # <<< CHANGED
    x_labels = [f"Lead {l}" for l in leads]     # <<< CHANGED

    # 3) Prepare grids (acc/hss)  # <<< CHANGED
    grid1 = np.full((len(months), len(leads)), np.nan)
    grid2 = np.full((len(months), len(leads)), np.nan)

    # Fill from df_year (each row = one (yyyymm, lead))
    for i, m in enumerate(months):
        yyyymm = f"{target_year}{m:02d}"
        rows_m = df_year[df_year["yyyymm"] == yyyymm]
        if rows_m.empty:
            continue
        for j, l in enumerate(leads):
            match = rows_m[rows_m["lead"] == l]
            if match.empty:
                continue
            # Fetch score values if present
            v1 = match.iloc[0][score1] if score1 in match.columns else np.nan
            v2 = match.iloc[0][score2] if score2 in match.columns else np.nan
            try:
                grid1[i, j] = float(v1)
            except Exception:
                pass
            try:
                grid2[i, j] = float(v2)
            except Exception:
                pass

    # 4) Colormaps & norms (카테고리 검증 팔레트 유지)  # <<< CHANGED
    cmap1 = plt.get_cmap("YlGn", 5)                 # HitRate
    cmap2 = plt.get_cmap("RdGy_r", 10)              # HSS
    bounds1 = np.linspace(0, 1, 6)
    bounds2 = np.linspace(-1, 1, 11)
    norm1 = mcolors.BoundaryNorm(bounds1, cmap1.N)
    norm2 = mcolors.BoundaryNorm(bounds2, cmap2.N)

    # 5) Plot  # <<< CHANGED
    fig, ax = plt.subplots(figsize=(5, len(y_labels) * 0.5))

    # triangles per cell
    for i in range(len(months)):
        for j in range(len(leads)):
            x, y = j, i
            v1, v2 = grid1[i, j], grid2[i, j]

            if not np.isnan(v1):
                ax.add_patch(
                    patches.Polygon(
                        [[x, y], [x + 1, y], [x, y + 1]],
                        facecolor=cmap1(norm1(v1)),
                        edgecolor="white",
                        lw=2,
                    )
                )
            if not np.isnan(v2):
                ax.add_patch(
                    patches.Polygon(
                        [[x + 1, y + 1], [x + 1, y], [x, y + 1]],
                        facecolor=cmap2(norm2(v2)),
                        edgecolor="white",
                        lw=2,
                    )
                )
            # optional numbers on cell
            if not np.isnan(v1) and not np.isnan(v2):
                ax.text(
                    x + 0.3, y + 0.25, f"{v1:.2f}",
                    ha="center", va="center",
                    fontsize=7, color=("white" if v1 >= 0.6 else "black"),
                )
                ax.text(
                    x + 0.7, y + 0.75, f"{v2:.2f}",
                    ha="center", va="center",
                    fontsize=7, color=("white" if abs(v2) >= 0.6 else "black"),
                )

    # axes, labels, title
    ax.set_xticks(np.arange(len(leads)) + 0.5)
    ax.set_xticklabels(x_labels)
    ax.set_yticks(np.arange(len(y_labels)) + 0.5)
    ax.set_yticklabels(y_labels)
    ax.set_xlim(0, len(leads))
    ax.set_ylim(0, len(y_labels))
    ax.invert_yaxis()
    ax.set_xlabel("Lead Time")
    ax.set_ylabel("Initialized Month")
    ax.set_title(f"HR/HSS Heatmap \n(Region:{region_name}, Var={var}, Year:{target_year})")

    # colorbars
    fig.subplots_adjust(right=0.88)
    cax1 = fig.add_axes([0.90, 0.55, 0.015, 0.3])
    sm1 = plt.cm.ScalarMappable(cmap=cmap1, norm=norm1)
    sm1.set_array([])
    cbar1 = plt.colorbar(sm1, cax=cax1, ticks=bounds1)
    cbar1.set_label("HitRate")

    cax2 = fig.add_axes([0.90, 0.15, 0.015, 0.3])
    sm2 = plt.cm.ScalarMappable(cmap=cmap2, norm=norm2)
    sm2.set_array([])
    cbar2 = plt.colorbar(sm2, cax=cax2, ticks=bounds2)
    cbar2.set_label("HSS")

    # save
    os.makedirs(fig_dir, exist_ok=True)
    save_fname = os.path.join(fig_dir, f"det_ter_score_{var}_{region_name}_{target_year}.png")  # <<< CHANGED
    fig.savefig(save_fname, dpi=300, bbox_inches="tight")
    logger.info(f"[SAVE] Category Score Heatmap: {save_fname}")
