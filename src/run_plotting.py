#!/usr/bin/env python
import argparse
import os
from config import *
from src.utils.logging_utils import init_logger
from src.utils.general_utils import generate_yyyymm_list
logger = init_logger()

# argparse 추가: var, region
parser = argparse.ArgumentParser(description="Plotting for single var/region")
parser.add_argument("--var", required=True, choices=variables, help="Variable to plot")
parser.add_argument("--region", required=True, choices=list(REGIONS.keys()), help="Region name for plotting")
args = parser.parse_args()
var = args.var
region_name = args.region

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


def main():
    print(f"[INFO] === Start Plotting Pipeline for var={var}, region={region_name} ===")
    fig_dir = os.path.join(output_fig_dir, region_name, var)
    os.makedirs(fig_dir, exist_ok=True)

    # 초기화 월별 리드타임 ACC plot
    plot_skill_initialized_month(
            var=var,
            region_name=region_name,
            score='acc',
            fig_dir=fig_dir
    )

    # 초기화 월 vs 리드타임 heatmap
    for year in fyears:
        plot_skill_heatmap_initialized_month(
            var=var,
            year=year,
            region_name=region_name,
            score='acc',
            fig_dir=fig_dir
        )

    # 특정 target month에 도달하기 위한fho 초기월별 리드 타임 스킬 및 패턴 비교
    for year in fyears:
        plot_skill_target_month(
            var=var,
            target_year=year,
            region_name=region_name,
            score='acc',
            fig_dir=fig_dir
        )
        plot_spatial_pattern_fcst_vs_obs(
            var=var,
            target_year=year,
            region_name=region_name,
            fig_dir=fig_dir
        )

    # target month를 x축으로 한 전체 초기월 시계열
    plot_skill_by_initialized_line(
        var=var,
        year_start=year_start,
        year_end=year_end,
        region_name=region_name,
        score='acc',
        fig_dir=fig_dir
    )
   
    # Deterministic Multi-Category Skill Score
    # - plot type : yearly heatmap
    plot_det_cate_heatmap(
        var=var,
        years=fyears, 
        region=region_name
        )

    # Probabilistic Skill Score plots 
    # - plot type : plot by initialized month (subplots : lead-time)
    yyyymm_list = generate_yyyymm_list(year_start, year_end)
    for yyyymm in yyyymm_list:
        plot_rpss_map(var, yyyymm, region_name, fig_dir)
        plot_roc_by_lead_per_init(var, yyyymm, region_name, fig_dir)


    logger.info(f"[INFO] === Done Plotting for var={var}, region={region_name} ===")

if __name__ == "__main__":
    main()
