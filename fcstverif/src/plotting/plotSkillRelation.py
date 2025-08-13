import xarray as xr
import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
from matplotlib.cm import get_cmap
from matplotlib.gridspec import GridSpec

def _pick_qual_colors(n):
    """리드 개수 n에 맞춰 qualitative 팔레트에서 색상 리스트 반환."""
    if n <= 10:
        cmap = get_cmap("tab10")
        return [cmap(i) for i in range(n)]
    else:
        cmap = get_cmap("tab20")
        return [cmap(i) for i in range(n)]

def plot_scatter_enso_with_var(
    var, yyyymm, fcst_score_dir, idx_dir, fig_dir, mode):

    # file path
    enso_file = f"{idx_dir}/fcst_{mode}_index_{yyyymm}.nc"
    score_file = f"{fcst_score_dir}/ensScore_det_{var}_{yyyymm}.nc"

    # check file existance
    if not os.path.isfile(enso_file):
        print(f"[WARN] ENSO index file not found: {enso_file}. Skip {yyyymm}.")
        return
    if not os.path.isfile(score_file):
        print(f"[WARN] Score file not found: {score_file}. Skip {yyyymm}.")
        return

    with xr.open_dataset(enso_file) as ds_enso, xr.open_dataset(score_file) as ds_score:
        sst = ds_enso["sst"]        # (ens, time)
        acc = ds_score["acc"]       # (ens, time)

        ntime = acc.sizes["time"]
        colors = _pick_qual_colors(ntime)

        os.makedirs(fig_dir, exist_ok=True)

        # 레이아웃: 상단/우측 마진축 + 메인 산점도
        fig = plt.figure(figsize=(8, 7))
        gs = GridSpec(4, 4, figure=fig, wspace=0.2, hspace=0.2)
        ax_scatter = fig.add_subplot(gs[1:, :3])
        ax_top = fig.add_subplot(gs[0, :3], sharex=ax_scatter)
        ax_right = fig.add_subplot(gs[1:, 3], sharey=ax_scatter)

         # 산점도 및 lead별 히스토그램
        for t in range(ntime):
            x = acc.isel(time=t).values
            y = sst.isel(time=t).values
            m = np.isfinite(x) & np.isfinite(y)
            if not m.any():
                continue

            # 산점도
            ax_scatter.scatter(x[m], y[m], s=18, color=colors[t], alpha=0.6, linewidths=0, label=f"Lead {t+1}")

            # 앙상블 평균
            xm, ym = np.nanmean(x), np.nanmean(y)
            if np.isfinite(xm) and np.isfinite(ym):
                ax_scatter.scatter(xm, ym, marker="X", s=72, color=colors[t], edgecolors="k", linewidths=0.6)

            # lead별 X축 히스토그램
            bins_x = np.histogram_bin_edges(x[m], bins="auto")
            cx, _ = np.histogram(x[m], bins=bins_x)
            centers_x = 0.5 * (bins_x[:-1] + bins_x[1:])
            ax_top.plot(centers_x, cx, lw=1.0, color=colors[t], alpha=0.8)

            # lead별 Y축 히스토그램
            bins_y = np.histogram_bin_edges(y[m], bins="auto")
            cy, _ = np.histogram(y[m], bins=bins_y)
            centers_y = 0.5 * (bins_y[:-1] + bins_y[1:])
            ax_right.plot(cy, centers_y, lw=1.0, color=colors[t], alpha=0.8)

        # 메인 축 설정
        ax_scatter.set_xlabel("ACC")
        ax_scatter.set_ylabel("SST anomaly (Nino3.4)")
        ax_scatter.set_title(f"SST vs ACC ({yyyymm})")
        ax_scatter.set_ylim(-3,3)
        ax_scatter.set_xlim(-1,1)
        ax_scatter.grid(True, alpha=0.3)

        # 위/오른쪽 축 스타일
        ax_top.tick_params(axis="x", labelbottom=False)
        ax_top.grid(True, alpha=0.2)
        ax_right.tick_params(axis="y", labelleft=False)
        ax_right.grid(True, alpha=0.2)

        # 범례
        ax_scatter.legend(frameon=True, fontsize=9, ncol=2, loc="lower right")

        plt.tight_layout()
        figname = os.path.join(fig_dir, f"{mode}_{var}_scatter_{yyyymm}.png")
        plt.savefig(figname, dpi=300)
        plt.close(fig)
        print(f"[OK] saved: {figname}")

def plot_scatter_by_lead(var, yyyymm_list, fcst_score_dir, idx_dir, fig_dir, mode):
    # lead별로 acc, sst 저장용 리스트
    lead_acc = {}
    lead_sst = {}

    for yyyymm in yyyymm_list:
        enso_file  = f"{idx_dir}/fcst_{mode}_index_{yyyymm}.nc"
        score_file = f"{fcst_score_dir}/ensScore_det_{var}_{yyyymm}.nc"
        if not (os.path.isfile(enso_file) and os.path.isfile(score_file)):
            print(f"[SKIP] missing file(s) for {yyyymm}")
            continue

        ds_enso  = xr.open_dataset(enso_file)
        ds_score = xr.open_dataset(score_file)
        sst = ds_enso["sst"]   # (ens, time)
        acc = ds_score["acc"]  # (ens, time)
        ntime = acc.sizes["time"]

        for t in range(ntime):
            xm = np.nanmean(acc.isel(time=t).values)  # 앙상블 평균
            ym = np.nanmean(sst.isel(time=t).values)
            if np.isfinite(xm) and np.isfinite(ym):
                lead_acc.setdefault(t+1, []).append(xm)
                lead_sst.setdefault(t+1, []).append(ym)

    # lead별 산점도 그림
    os.makedirs(fig_dir, exist_ok=True)
    cmap = get_cmap("tab20")
    colors = [cmap(i % 20) for i in range(len(yyyymm_list))]

    for lead in sorted(lead_acc.keys()):
        fig, ax = plt.subplots(figsize=(6, 5))
        ax.scatter(lead_acc[lead], lead_sst[lead],
                   color="tab:blue", alpha=0.7, edgecolors="k")
        ax.set_xlim(-1, 1)
        ax.set_ylim(-3, 3)
        ax.set_xlabel("ACC")
        ax.set_ylabel("SST anomaly (Nino3.4)")
        ax.set_title(f"Lead {lead} months: SST vs ACC ({mode}, {var})")
        ax.grid(True, alpha=0.3)

        figname = os.path.join(fig_dir, f"{mode}_{var}_scatter_lead{lead}.png")
        plt.tight_layout()
        plt.savefig(figname, dpi=300)
        plt.close()
        print(f"[OK] saved: {figname}")