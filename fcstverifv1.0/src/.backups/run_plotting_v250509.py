#!/usr/bin/env python
import os
from fcstverif.config import *
from fcstverif.utils.logging_utils import init_logger
logger = init_logger()

from fcstverif.plotting.plotDetermSkillScore import (
    plot_skill_initialized_month,
    plot_skill_heatmap_initialized_month,
    plot_skill_target_month,
    plot_skill_by_initialized_line,
    plot_spatial_pattern_fcst_vs_obs
)

def main():
    print("[INFO] === Start Plotting Pipeline ===")
    for region_name, region_box in REGIONS.items():
        for var in variables:
             
            fig_dir = os.path.join(output_fig_dir, region_name)
            os.makedirs(fig_dir, exist_ok=True)
        
            print(f"[INFO] Plotting {var} for region {region_name}")

            # (1) 초기화 월별 리드타임 ACC plot
            for year in fyears:
                plot_skill_initialized_month(
                    var=var,
                    year=year,
                    region_name=region_name,
                    score='acc',  # 또는 'rmse', 'bias',
                    fig_dir=fig_dir
                )

            # (2) 초기화 월 vs 리드타임 heatmap
            for year in fyears:
                plot_skill_heatmap_initialized_month(
                    var=var,
                    year=year,
                    region_name=region_name,
                    score='acc',
                    fig_dir=fig_dir
                )

            # (3) 특정 target month에 도달하기 위한 초기월별 리드 타임 스킬
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


            # (4) target month를 x축으로 한 전체 초기월 시계열
            plot_skill_by_initialized_line(
                var=var,
                year_start=year_start,
                year_end=year_end,
                region_name=region_name,
                score='acc',
                fig_dir=fig_dir
            )

    logger.info("[INFO] === Done Plotting ===")

if __name__ == "__main__":
    main()
