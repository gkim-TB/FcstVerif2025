import xarray as xr
import os

# 🔧 사용자 설정
nc_file = "/home/gkim/2025FcstVerif//GS6_KMApost_monthly/anomaly/ensMem_sst_anom_202412.nc"  # 예: 첫 변환된 GloSea6 NetCDF 파일
output_path = "./target_grid.nc"       # 저장 경로

# 🔍 파일 열기
if not os.path.isfile(nc_file):
    raise FileNotFoundError(f"NetCDF 파일을 찾을 수 없습니다: {nc_file}")

ds = xr.open_dataset(nc_file)

# ⚠️ 좌표 추출
try:
    lat = ds["lat"]
    lon = ds["lon"]
except KeyError:
    raise KeyError("lat 또는 lon 좌표가 NetCDF 파일에 없습니다.")

# 📦 좌표만 따로 저장
grid_ds = xr.Dataset({"lat": lat, "lon": lon})
grid_ds.to_netcdf(output_path)
print(f"[SAVED] Target grid → {output_path}")
