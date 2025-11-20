# fcstverif/run_plotting.py

import argparse
import os

from fcstverif.config import (
    VARIABLES, REGIONS, verify_start, verify_end, fyears, 
    score_dir, idx_dir, sst_out_dir, tercile_dir, output_fig_dir, enabled_plots,
    log_path
)
from fcstverif.config import RUN_MODE as CONFIG_RUN_MODE

import logging
from fcstverif.src.utils.logging_utils import init_logger, get_logger
logger = logging.getLogger("fcstverif")

from fcstverif.src.utils.general_utils import generate_yyyymm_list

# plotting 함수 import
from fcstverif.src.plotting.plotDetermSkillScore import (
    plot_skill_initialized_month,
    plot_det_skill_heatmap,
    plot_skill_target_month,
    #plot_skill_by_initialized_line,
    plot_trajectory_w_acc_by_initialized_line,
    plot_spatial_pattern_fcst_vs_obs,
    plot_nino34_hovmoller,
    plot_iod_hovmoller,
)
from fcstverif.src.plotting.plotProbSkillScore import (
    plot_rpss_map,
    plot_roc_by_lead_per_init
)
from fcstverif.src.plotting.plotCateHeatmap import plot_det_cate_heatmap

from fcstverif.src.plotting.plotSkillRelation import plot_scatter_enso_with_var, plot_scatter_by_lead

def parse_args():
    parser = argparse.ArgumentParser(description="Plotting pipeline for var/region")
    parser.add_argument("--var", required=True, choices=VARIABLES, help="Variable to plot")
    parser.add_argument("--region", required=True, choices=list(REGIONS.keys()), help="Region to plot")
    parser.add_argument("--run_mode", default=None, choices=["auto", "manual"], help="Execution mode (auto/manual)")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    return parser.parse_args()

def define_plot_tasks(var, region_name, data_dir, idx_dir, fig_dir, yyyymm_list):
    return {
        "init_line": lambda: [
            plot_skill_initialized_month(
                var=var, yyyymm=yyyymm, 
                region_name=region_name, 
                data_dir=data_dir, fig_dir=fig_dir, score=score
            ) for yyyymm in yyyymm_list for score in ['acc', 'rmse']
        ],
        "init_heatmap": lambda: [
            plot_det_skill_heatmap(
                var=var, target_year=y, region_name=region_name,
                data_dir=data_dir, fig_dir=fig_dir, score1='acc', score2='rmse'
            ) for y in fyears
        ],
        "target_month": lambda: [
            plot_skill_target_month(
                var=var, target_year=y, region_name=region_name,
                score=score, data_dir=data_dir, fig_dir=fig_dir
            ) for y in fyears for score in ['acc', 'rmse']
        ],
        "traj_line": lambda: [
            plot_trajectory_w_acc_by_initialized_line(
                var=var,
                region=region_name,
                fig_dir=fig_dir,
                data_dir=data_dir,
                mode="trajectory"  # ✨ mode 지정
            )
        ],
        "target_line": lambda: [
            plot_trajectory_w_acc_by_initialized_line(
                var=var,
                region=region_name,
                fig_dir=fig_dir,
                data_dir=data_dir,
                mode="skill"  # ✨ mode 지정
            )
        ],
        "target_pattern": lambda: [
            plot_spatial_pattern_fcst_vs_obs(
                var=var, target_year=y, region_name=region_name, fig_dir=fig_dir
            ) for y in fyears
        ],
        "cate_heatmap": lambda: (
            [
            plot_det_cate_heatmap(
                var=var, target_year=y, region_name=region_name, 
                data_dir=data_dir, fig_dir=fig_dir
            ) for y in fyears 
            ] 
            if var in ['t2m', 'prcp'] 
            else logger.warning(
                f"[SKIP] {var} not supported for deterministic tercile heatmap."
            )
        ),
        "rpss_map": lambda: [
            plot_rpss_map(
                var=var, yyyymm=ym, region_name=region_name, fig_dir=fig_dir
            ) for ym in yyyymm_list
        ],
        "roc_curve": lambda: [
            plot_roc_by_lead_per_init(
                var=var, yyyymm=ym, region_name=region_name,
                data_dir=data_dir, fig_dir=fig_dir
            ) for ym in yyyymm_list
        ],
        "skill_relation": lambda: [
            plot_scatter_enso_with_var(
                var=var, yyyymm=ym,
                fcst_score_dir=data_dir,
                idx_dir=idx_dir,
                fig_dir=fig_dir,
                mode='IOD'
            ) for ym in yyyymm_list
        ],
        "skill_relation_v2": lambda :[
            plot_scatter_by_lead(
                var=var, yyyymm_list=yyyymm_list, 
                fcst_score_dir=data_dir, 
                idx_dir=idx_dir, 
                fig_dir=fig_dir,
                mode='IOD'
                )
        ],
        "nino34_hovmoller": lambda: [
             plot_nino34_hovmoller(
                 yyyymm=ym,
                ) for ym in yyyymm_list
         ] if (var =='sst' and region_name == 'GL') else logger.info(
             f"[SKIP] {var} not supported for Nino3.4 Hovmoller plot."
             ),
        "iod_hovmoller": lambda: [
            plot_iod_hovmoller(ym) for ym in yyyymm_list
        ] if (var == 'sst' and region_name == 'GL') else logger.info(
            f"[SKIP] Hovmöller runs only for var=sst & region=GL (got var={var}, region={region_name})."
        ),
    }

def run_plotting(var, region_name, yyyymm_list):

    data_dir = os.path.join(score_dir, region_name, var)
    fig_dir = os.path.join(output_fig_dir, region_name, var)
    os.makedirs(fig_dir, exist_ok=True)

    logger.info(f"📌 Start plotting for var={var}, region={region_name}")
    task_funcs = define_plot_tasks(var, region_name, data_dir, idx_dir, fig_dir, yyyymm_list)

    for task_name in enabled_plots:
        # if task_name.startswith("traj"):
        #     continue
        task_func = task_funcs.get(task_name)
        if task_func:
            logger.info(f"▶️ Running: {task_name}")
            task_func()
        else:
            logger.warning(f"[SKIP] Unknown task: {task_name}")
    
    logger.info(f"✅ Plotting completed for var={var}, region={region_name}")

def main():
    args = parse_args()
    run_mode = args.run_mode if args.run_mode else CONFIG_RUN_MODE
    log_level = logging.DEBUG if args.debug else logging.INFO

    if not any(isinstance(h, logging.FileHandler) for h in logging.getLogger("fcstverif").handlers):
        init_logger(logfile=log_path, level=log_level)
    logger = get_logger()

    var = args.var
    region_name = args.region
    yyyymm_list = generate_yyyymm_list(verify_start, verify_end)
    if run_mode == "auto":
        run_plotting(var, region_name, yyyymm_list)
    else:
        if input('Proceed plotting? [y/n] ').strip().lower() == 'y':
           run_plotting(var, region_name, yyyymm_list) 

if __name__ == "__main__":
    main()
