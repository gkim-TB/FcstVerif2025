#!/usr/bin/env python
import argparse
import os
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
from fcstverif.config import *
from fcstverif.utils.general_utils import generate_yyyymm_list, clip_to_region
from fcstverif.utils.logging_utils import init_logger
logger = init_logger()

# argparse 추가: var, region
parser = argparse.ArgumentParser(description="Plotting for single var/region")
parser.add_argument("--var", required=True, choices=variables, help="Variable to plot")
parser.add_argument("--region", required=True, choices=list(REGIONS.keys()), help="Region name for plotting")
args = parser.parse_args()
var = args.var
region_name = args.region
region_box = REGIONS[region_name]

# plotting 함수 import
from fcstverif.plotting.plotDetermSkillScore import (
    plot_skill_initialized_month,
    plot_skill_heatmap_initialized_month,
    plot_skill_target_month,
    plot_skill_by_initialized_line,
    plot_spatial_pattern_fcst_vs_obs
)


def main():
    print(f"[INFO] === Start Plotting Pipeline for var={var}, region={region_name} ===")
    fig_dir = os.path.join(output_fig_dir, region_name, var)
    os.makedirs(fig_dir, exist_ok=True)

    # # 초기화 월별 리드타임 ACC plot
    # for year in fyears:
    #     plot_skill_initialized_month(
    #         var=var,
    #         year=year,
    #         region_name=region_name,
    #         score='acc',
    #         fig_dir=fig_dir
    #     )

    # # 초기화 월 vs 리드타임 heatmap
    # for year in fyears:
    #     plot_skill_heatmap_initialized_month(
    #         var=var,
    #         year=year,
    #         region_name=region_name,
    #         score='acc',
    #         fig_dir=fig_dir
    #     )

    # 특정 target month에 도달하기 위한 초기월별 리드 타임 스킬 및 패턴 비교
    for year in fyears:
        # plot_skill_target_month(
        #     var=var,
        #     target_year=year,
        #     region_name=region_name,
        #     score='acc',
        #     fig_dir=fig_dir
        # )
        plot_spatial_pattern_fcst_vs_obs(
            var=var,
            target_year=year,
            region_name=region_name,
            fig_dir=fig_dir
        )

    # # target month를 x축으로 한 전체 초기월 시계열
    # plot_skill_by_initialized_line(
    #     var=var,
    #     year_start=year_start,
    #     year_end=year_end,
    #     region_name=region_name,
    #     score='acc',
    #     fig_dir=fig_dir
    # )

    logger.info(f"[INFO] === Done Plotting for var={var}, region={region_name} ===")

if __name__ == "__main__":
    main()
