import numpy as np
import os

# ================ USER SETTINGS =================

# --- 검증하고자 하는 forecast 기간 ---
year_start = 2022
year_end = 2024
fyears = np.arange(year_start, year_end+1)

# == obs hindcast 기간
clim_start = 1991
clim_end   = 2020

# --- 변수 목록 ---
variables = ['t2m', 'sst', 'prcp']
#variables = ['t', 'z']

# --- 검증 영역 정의 ---
REGIONS = {
    "GL": [0, 360, -90, 90], # default option
    # add addtional regions below
    # [lonL, lonR, latS, latN]
    "EA": [100, 160, 10, 55]
}

# --- 모델 ---
model = 'GS6'

# --- plot list ---
enabled_plots = [
    #"init_line",
    "init_heatmap",
    #"target_month",
    #"target_pattern",
    "target_line",
    "cate_heatmap", # only for t2m, prcp
    #"rpss_map",
    #"roc_curve"
]
#================================================


# --- 주요 디렉토리 경로 ---
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
#root_dir =  '../' #'/home/gkim/2025FcstVerif/'
base_dir = f'{root_dir}/fcstverif/'

model_raw_dir = f'{root_dir}/{model}_KMApost_raw/'
model_out_dir = f'{root_dir}/{model}_KMApost_monthly'

era5_base_dir = f'{root_dir}/ERA5_monthly_{model}grid'
era5_out_dir =f'{root_dir}/ERA5_OUT/{model}_grid'

sst_base_dir = f'{root_dir}/OISST'
sst_out_dir = era5_out_dir #f'{sst_base_dir}/{model}_grid/'

verification_out_dir = f'{base_dir}/OUT/{model}'
output_fig_dir = os.path.join(root_dir, "fig", model)
#output_fig_dir = f'{root_dir}/fig/{model}'

# --- GRIB/NetCDF 변수명 매핑 ---
GSvar2rename = {
    't2m': 't15m',
    'sst': 'tsfc',
}

ERAvar2rename = {
    'mslp':'msl',
    'prcp': 'tp',
}

var2grib_name = {
    'tsfc': 'Skin temperature',
    'mslp': 'Mean sea level pressure',
    't15m': '2 metre temperature',
    'prcp': 'Precipitation rate',
    'h': 'Geopotential height',
    'q': 'Specific humidity',
    't': 'Temperature',
    'u': 'U component of wind',
    'v': 'V component of wind'
}

# --- 표층/기압면 변수 구분 ---
SURFACE_VARS = {'t2m', 'prcp', 'mslp', 'tsfc'}
PRESSURE_VARS = {'u', 'v', 't', 'q', 'z'}

# --- land sea mask ---
MODEL_MASKS = {

}  

OBS_MASKS = {
    'OISST': f'{base_dir}/MASK/oisst_mask_to_{model}.nc'
}