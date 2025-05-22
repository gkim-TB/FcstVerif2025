import numpy as np

# --- 기간 설정 ---
# == 검증하고자 하는 forecast 기간
year_start = 2024
year_end = 2024
fyears = np.arange(year_start, year_end+1)
# == hindcast 기간
clim_start = 1991
clim_end   = 2020

# --- 모델 ---
model = 'GS6'

# --- 주요 디렉토리 경로 ---
base_dir = '/home/gkim/2025FcstVerif'
work_dir = f'{base_dir}/FcstVerif_v2.1'

model_raw_dir = f'{base_dir}/{model}_KMApost_raw/'
model_out_dir = f'{base_dir}/{model}_KMApost_monthly'

era5_base_dir = f'{base_dir}/ERA5_monthly_{model}grid'
era5_out_dir =f'{base_dir}/ERA5_OUT/{model}_grid'
# clim_out_dir = f'{era5_out_dir}/clim'
# tercile_out_dir = f'{era5_out_dir}/tercile'
# std_out_dir = f'{era5_out_dir}/std'
# obs_anom_dir = f'{era5_out_dir}/anom'

sst_dir = f'{base_dir}/OISST'
sst_anom_dir = f'{sst_dir}/{model}_grid/anom'

verification_out_dir = f'{work_dir}/out/{model}'
output_fig_dir = f'{work_dir}/fig/{model}'

# --- 변수 목록 ---
variables = ['t2m']
#variables = ['t', 'z']

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

# --- 검증 영역 정의 ---
REGIONS = {
    "GL": (-90, 90, 0, 360),
    #"EA": (20, 50, 120, 150)
}

