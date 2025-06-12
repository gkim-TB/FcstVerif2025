import numpy as np

# --- 기간 설정 ---
year_start = 2022
year_end = 2024
fyears = np.arange(year_start, year_end+1)

# --- 주요 디렉토리 경로 ---
base_dir = '/home/gkim/2025FcstVerif'
work_dir = f'{base_dir}/FcstVerif_v2.0'

era5_base_dir = f'{base_dir}/ERA5_monthly_GSgrid'
hindcast_dir = f'{base_dir}/GS6_KMApost_monthly/hindcast'
forecast_dir = f'{base_dir}/GS6_KMApost_monthly/forecast'
fanomaly_dir = f'{base_dir}/GS6_KMApost_monthly/anomaly'

clim_out_dir = f'{era5_base_dir}/clim'
tercile_out_dir = f'{era5_base_dir}/tercile'
std_out_dir = f'{era5_base_dir}/tercile'
obs_anom_dir = f'{era5_base_dir}/anom'

sst_dir = f'{base_dir}/OISST'
sst_anom_dir = f'{sst_dir}/anom'

verification_out_dir = f'{work_dir}/OUT'
output_fig_dir = f'{work_dir}/FIG'

# --- 변수 목록 ---
variables = ['sst']
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
    "EA": (20, 50, 120, 150)
}

