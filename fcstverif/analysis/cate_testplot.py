import xarray as xr
import matplotlib.pyplot as plt
import numpy as np
# 파일 경로 (예시 경로 수정해서 사용하세요)
file_path = "/home/gkim/2025FcstVerif/ERA5_OUT/GS6_grid/cate_t2m_2022.nc"

# 1. 데이터 열기
ds = xr.open_dataset(file_path)

# 2. obs_cate 데이터 (변수 이름 확인 필요)
da = ds['t2m_obs_cate']  # 또는 ds[var + '_obs_cate']
print(da)
# 3. 1월인 시점만 선택


fig, axs = plt.subplots(3,4)
axs = axs.flatten()
# 4. 시각화
for i, ax in enumerate(axs):
    jan = da.isel(time=i).squeeze()
    jan.plot.contourf(ax=ax, cmap='bwr', levels=[-1,-0.5,0.5,1])
    
plt.show()


    
    
