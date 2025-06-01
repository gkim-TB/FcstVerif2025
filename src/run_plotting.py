#!/usr/bin/env python
import argparse
import os
from config import *
from src.utils.logging_utils import init_logger
from src.utils.general_utils import generate_yyyymm_list

# plotting 함수 import
from src.plotting.plotDetermSkillScore import (
    plot_skill_initialized_month,
    plot_skill_heatmap_initialized_month,
    plot_skill_target_month,
    plot_skill_by_initialized_line,
    plot_spatial_pattern_fcst_vs_obs
)
from src.plotting.plotProbSkillScore import (
    plot_rpss_map,
    plot_roc_by_lead_per_init
)
from src.plotting.plotCateHeatmap import plot_det_cate_heatmap

logger = init_logger()

# argparse 추가: var, region
parser = argparse.ArgumentParser(description="Plotting for single var/region")
parser.add_argument("--var", required=True, choices=variables, help="Variable to plot")
parser.add_argument("--region", required=True, choices=list(REGIONS.keys()), help="Region name for plotting")
args = parser.parse_args()
var = args.var
region_name = args.region

data_dir = os.path.join(verification_out_dir, 'SCORE', region_name, var)
fig_dir = os.path.join(output_fig_dir, region_name, var)
os.makedirs(fig_dir, exist_ok=True)
yyyymm_list = generate_yyyymm_list(year_start, year_end)

# =======================
# 📌 각 plot task 함수 정의
# =======================
def task_init_line():
    plot_skill_initialized_month(
        var, region_name=region_name, data_dir=data_dir, fig_dir=fig_dir, score='acc'
        )

def task_init_heatmap():
    for y in fyears:
        plot_skill_heatmap_initialized_month(
            var, target_year=y, region_name=region_name, data_dir=data_dir, fig_dir=fig_dir, score='acc'
            )

def task_target_month():
    for y in fyears:
        plot_skill_target_month(
            var, target_year=y, region_name=region_name, data_dir=data_dir, fig_dir=fig_dir, score='acc'
        )

def task_target_line():
    plot_skill_by_initialized_line(
        var, year_start, year_end, region_name, score='acc', data_dir=data_dir, fig_dir=fig_dir
        )

def task_target_pattern():
    for y in fyears:
        plot_spatial_pattern_fcst_vs_obs(
            var, target_year=y, region_name=region_name, fig_dir=fig_dir
            )
        # obs와 fcst를 함수 내에서 직접 call 하기 때문에 data_dir 필요없음

def task_cate_heatmap():
    plot_det_cate_heatmap(
        var, years=fyears, region_name=region_name, data_dir=data_dir, fig_dir=fig_dir
    )

def task_rpss_map():
    # rpss score는 GL에서 한번만 생산 -> data_dir 지정 X
    for ym in yyyymm_list:
        plot_rpss_map(var, ym, region_name=region_name, fig_dir=fig_dir)

def task_roc_curve():
    for ym in yyyymm_list:
        plot_roc_by_lead_per_init(var, ym, region_name=region_name, data_dir=data_dir, fig_dir=fig_dir)

# =======================
# 📌 Task 목록 매핑
# =======================
PLOT_TASKS = {
    "init_line": task_init_line,
    "init_heatmap": task_init_heatmap,
    "target_month": task_target_month,
    "target_pattern": task_target_pattern,
    "target_line": task_target_line,
    "cate_heatmap": task_cate_heatmap,
    "rpss_map": task_rpss_map,
    "roc_curve": task_roc_curve,
}

# =======================
# 📌 Main 함수
# =======================
def main():
    print(f"[INFO] === Start Plotting Pipeline for var={var}, region={region_name} ===")

    for task_name in enabled_plots:
        task_func = PLOT_TASKS.get(task_name)
        if task_func:
            print(f"[INFO] Running: {task_name}")
            task_func()
        else:
            print(f"[WARN] Unknown task: {task_name}")

    logger.info(f"[INFO] === Done Plotting for var={var}, region={region_name} ===")

if __name__ == "__main__":
    main()
