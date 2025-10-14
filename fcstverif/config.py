# fcstverif/config.py

import numpy as np
import os

# ================ USER SETTINGS =================
RUN_MODE = "auto" # "manual" or "auto"

# --- 모델 ---
model = "GS6"

# === 전체 fcst 데이터 기간
fcst_start = 202201
fcst_end = 202412

# --- forecast to verify : initialized months---
verify_start = 202201
#verify_end = 202412
verify_end = fcst_end
fyears = np.arange(verify_start // 100, verify_end // 100 + 1)

# == obs hindcast period
clim_start = 1991
clim_end   = 2020

# --- List of variables to verify ---
""" list all variables in case manually select in command line"""
#VARIABLES = ["sst"]
#VARIABLES = ["t2m"]
#VARIABLES = ["z500"]
VARIABLES = ["z500", "t2m", "prcp", "sst"]
#VARIABLES = ["t", "z"]

# --- 검증 영역 정의 ---
REGIONS = {
    "GL": [0, 360, -90, 90], # default option
    # add addtional regions below
    # [lonL, lonR, latS, latN]
    "EA": [100, 150, 20, 50]
}
REGION_OVERRIDE_BY_VAR = {
    "sst": {
        "GL": [0, 360, -60, 60]
    }
}

# --- plot list ---
enabled_plots = [
    # -- detailed plots
    #"init_line",       # Timeseries of deterministic skill score by lead, every initialized month
    #"target_month",    # Timeseries of deterministic skill score by lead, every target month
    #"target_pattern",  # Spatial distribution comparison btw obs and fcst anomaly, every target month
    #"rpss_map",        # (Probabilistic skill score) RPSS map, every initialized month
    #"roc_curve",        # (Probabilistic skill score) ROC curve with AUC, every initialized month
    # -- overview plots
    "target_line",      # Timeseries of all forecast initialization (ACC)
    "traj_line",        # Trajectory lines of all forecast initialization
    #"init_heatmap",    # Deterministic skill score heatmap
    #"cate_heatmap",    # (only t2m, prcp) Deterministic Multi-category score heat map, every year
    # -- analytics plots
    #"skill_relation",   # Skill relation plot
    #"skill_relation_v2",
    "nino34_hovmoller", # works only for "sst"
    "iod_hovmoller", # works only for "sst"
    ]


# --- 주요 디렉토리 경로 ---
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
#root_dir =  "../" #"/home/gkim/2025FcstVerif/"
base_dir: str = f"{root_dir}/fcstverif/"

model_raw_dir: str = f"{root_dir}/{model}_KMApost_raw/"
model_out_dir: str = f"{root_dir}/{model}_KMApost_monthly"

era5_base_dir: str = f"{root_dir}/ERA5_monthly_{model}grid" # regridded to GSgrid
#era5_base_dir = f"/home/gkim/DATA/ERA5/Monthly" # ERA5 raw
era5_out_dir: str  = f"{root_dir}/ERA5_OUT/{model}_grid"

sst_base_dir: str = f"{root_dir}/OISST"
sst_out_dir: str  = era5_out_dir #f"{sst_base_dir}/{model}_grid/"

verification_out_dir: str = f"{base_dir}/OUT/{model}"
score_dir: str = f"{verification_out_dir}/SCORE/"
idx_dir: str = f"{verification_out_dir}/IDX/"
tercile_dir: str = f"{verification_out_dir}/CATE/"

output_fig_dir: str = os.path.join(root_dir, "fig", model)
#output_fig_dir = f"{root_dir}/fig/{model}"

# --- GRIB/NetCDF 변수명 매핑 ---
# universial : GS6
GSvar2rename = {
    "t2m": "t15m",
    "sst": "tsfc",
    "z": "h"
}

# universial : ERA5
ERAvar2rename = {
    "mslp":"msl",
    "prcp": "tp",
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

# --- 표층/기압면 변수 구분 ---
SURFACE_VARS = {"t2m", "prcp", "mslp", "tsfc"}
PRESSURE_VARS = {"u", "v", "t", "q", "z"}

# --- land sea mask ---
MODEL_MASKS = {
}  

OBS_MASKS = {
    "OISST": f"{base_dir}/MASK/oisst_mask_to_{model}.nc"
}

# Define ENSO and IOD regions
# region box: (latS, latN, lonL, lonR)
ENSO_BOX = (-5, 5, 190, 240)  # Niño 3.4 영역
IOD_WEST_BOX = (-10, 10, 50, 70)
IOD_EAST_BOX = (-10, 0, 90, 110)