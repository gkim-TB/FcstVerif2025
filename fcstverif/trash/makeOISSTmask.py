import xarray as xr
import numpy as np

# (1) OISST 파일 경로 설정
oisst_file = f"/mnt/d/2025FcstVerif/OISST/GS6_grid/sst.mon.mean.regrid.nc"  # ← 파일 경로 수정 필요

# (2) 데이터 열기
ds = xr.open_dataset(oisst_file)
sst = ds['sst'].isel(time=0)  # 첫 시점만 사용

# (3) NaN이 아닌 곳(True) = 바다 / NaN인 곳(False) = 육지 또는 해빙
land_sea_mask = ~np.isnan(sst)
land_sea_mask.name = "land_sea_mask"

# (4) 저장
output_path = "/mnt/d/2025FcstVerif/OISST/OISST_lsm_to_GS6.nc"  # 저장 파일명 변경 가능
land_sea_mask.to_netcdf(output_path)

print(f"✅ Land/sea mask saved to: {output_path}")