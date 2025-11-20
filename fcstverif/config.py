# fcstverif/config.py

import numpy as np
import os
from datetime import datetime
ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

# ================ USER SETTINGS =================
# --- 실행 모드 ---
RUN_MODE = "auto" #"manual" or "auto"
log_path = f"./logs/run_{ts}.log"
# --- 재계산 옵션 ---
recompute = True # 필요 시 True (이미 만들어 둔 **shard(월별 CSV)**가 있어도 강제로 다시 계산·덮어쓰기)
discover = False # 필요 시 True (가용한 모든 월을 항상 계산)

# --- 모델 ---
#model = "SCOPS"
model = "GS6"

model_leadtime = 6 # in months

# === forecast data available period (initialized month)===
fcst_start = 202201 
fcst_end = 202412
hcst_styr = 1991
hcst_enyr = 2010

# --- forecast to verify : initialized months---
# verification is done for all months between verify_start and verify_end
# (but only for initialized months available in the forecast data directory)
# e.g., if verify_start = 202201 and verify_end = 202212,
#       verification will be done for all initialized months from Jan 2022 to Dec 2022
verify_start = fcst_start
verify_end = 202504 # extend to the last forecast target month of last initialized month
fyears = np.arange(verify_start // 100, verify_end // 100 + 1)

# == obs hindcast period
clim_start = 1991
clim_end   = 2020

#=============== Fixed SETTINGS =================
# --- List of variables to verify ---
# list all variables in case manually select in command line
VARIABLES = ["z500", "t2m", "prcp", "sst"]


# --- Regions to verify ---
REGIONS = {
    "GL": [0, 360, -90, 90], # default option
    # add addtional regions below
    # [lonL, lonR, latS, latN]
    "EA": [100, 150, 20, 50],
    #"TP": [65, 105, 25, 50],
}

# --- Directory Path ---
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..")) # working directory
base_dir: str = f"{root_dir}/fcstverif/" # base directory for fcstverif (source code + checkpointing files)

model_raw_dir: str = f"{root_dir}/{model}/" # raw forecast data directory
model_out_dir: str = f"{root_dir}/MODEL_OUT/{model}" # regridded forecast data directory

era5_base_dir: str = f"{root_dir}/ERA5_monthly_{model}grid" # raw ERA5 data directory
#era5_base_dir: str = f"/data/TBDB/ERA5/Monthly/" # raw ERA5 data directory
era5_out_dir: str  = f"{root_dir}/ERA5_OUT/{model}_grid" # regridded ERA5 data directory

sst_base_dir: str = f"{root_dir}/OISST" # raw OISST data directory
#sst_base_dir: str = f"/data/TBDB/OISST/Monthly/" # raw OISST data directory
sst_out_dir: str  = era5_out_dir #f"{sst_base_dir}/{model}_grid/" # regridded OISST data directory

verification_out_dir: str = f"{base_dir}/OUT/{model}" # output directory for verification results
score_dir: str = f"{verification_out_dir}/SCORE/" # score output directory
idx_dir: str = f"{verification_out_dir}/IDX/" # index output directory
tercile_dir: str = f"{verification_out_dir}/CATE/"  # tercile category output directory

output_fig_dir: str = os.path.join(root_dir, "FIG", model) # figure output directory

GITHUB_RAW_BASE: str = "https://raw.githubusercontent.com/gkim-TB/FcstVerif2025/main"
#GITHUB_RAW_BASE: str = None

# --- Plot list ---
enabled_plots = [
    # -- detailed plots
    "init_line",       # Timeseries of deterministic skill score by lead, every initialized month
    "target_line",    # Timeseries of deterministic skill score by lead, every target month
    "target_pattern",  # Spatial distribution comparison btw obs and fcst anomaly, every target month
    "rpss_map",        # (Probabilistic skill score) RPSS map, every initialized month
    "roc_curve",        # (Probabilistic skill score) ROC curve with AUC, every initialized month
    # -- overview plots
    "traj_skill",      # Timeseries of all forecast initialization (ACC)
    "traj_line",        # Trajectory lines of all forecast initialization
    "init_heatmap",    # Deterministic skill score heatmap
    "cate_heatmap",    # (only t2m, prcp) Deterministic Multi-category score heat map, every year
    # -- analytics plots
    ######"skill_relation",   # Skill relation plot ( not used )
    ######"skill_relation_v2", # (not used)
    "nino34_hovmoller", # works only for "sst"
    "iod_hovmoller", # works only for "sst"
    ]


# --- mapping variable names  ---
# match data variable names in different data sources to universial names used in this project

# universial : ERA5
ERAvar2rename = {
    "mslp":"msl",
    "prcp": "tp",
}

# universial : GS6
GSvar2rename = {
    "t2m": "t15m",
    "sst": "tsfc",
    "z": "h"
}

var2grib_name = {
    "tsfc": "Skin temperature",
    "mslp": "Mean sea level pressure",
    "t15m": "2 metre temperature",
    "prcp": "Precipitation rate",
    "h": "Geopotential height",
    "q": "Specific humidity",
    "t": "Temperature",
    "u": "U component of wind",
    "v": "V component of wind"
}

# universial : MME participating models
# MME model data is copied from /lfs/apccdb/Prediction/Seasonal/
MMEvar2rename = {
        'prcp':'prec',
        }

# --- variable groups --- 
SURFACE_VARS = {"t2m", "prcp", "mslp", "tsfc"}
PRESSURE_VARS = {"u", "v", "t", "q", "z"}

# Define ENSO and IOD regions in list format
# region BOX = [lonL, lonR, latS, latN]
ENSO_BOX = [190, 240, -5, 5]  # Niño 3.4 영역
IOD_WEST_BOX = [50, 70, -10, 10]
IOD_EAST_BOX = [90, 110, -10, 0]


# --- variable-specific region override ---
REGION_OVERRIDE_BY_VAR = {
    "sst": {
        "GL": [0, 360, -60, 60] # sst global region
    }
}
# =================================================
