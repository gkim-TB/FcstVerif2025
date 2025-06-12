import xarray as xr
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import os

def plot_spatial(data, title, cmap='RdBu_r', vmin=None, vmax=None):
    """MSSS spatial pattern"""
    plt.figure(figsize=(6,5))
    ax = plt.axes(projection=ccrs.PlateCarree())
    data.plot(ax=ax, transform=ccrs.PlateCarree(), cmap=cmap, levels=np.arange(-1,1.1,0.2), cbar_kwargs={'shrink':0.8})
    ax.coastlines()
    ax.add_feature(cfeature.BORDERS, linewidth=0.5)
    ax.set_title(title)
    plt.show()


def domain_average(data, region=None):
    """전체 또는 영역 평균"""
    if region is None:
        return data.mean()
    else:
        lat_s, lat_n, lon_w, lon_e = region
        return data.sel(lat=slice(lat_s, lat_n), lon=slice(lon_w, lon_e)).mean()


def plot_msss_case1(msss_file, region=None):
    """Case 1: 월별 초기날짜에 대한 시각화"""
    ds = xr.open_dataset(msss_file)
    da = ds['msss']  # (lead, lat, lon)

    # -------------------------------
    # Spatial Pattern (lead=1~6) subplot
    # -------------------------------
    fig, axes = plt.subplots(2, 3, figsize=(15, 8), subplot_kw={'projection': ccrs.PlateCarree()})
    axes = axes.flatten()

    for i, lead in enumerate(da.lead.values):
        ax = axes[i]
        da.sel(lead=lead).plot(
            ax=ax,
            transform=ccrs.PlateCarree(),
            cmap='RdBu_r',
            levels=np.arange(-10,11,2),
    #        vmin=vmin, vmax=vmax,
            cbar_kwargs={'shrink': 0.7, 'label': 'MSSS'}
        )
        ax.coastlines()
        ax.add_feature(cfeature.BORDERS, linewidth=0.5)
        ax.set_title(f"Lead {int(lead)}")

    plt.suptitle("Spatial MSSS (Lead 1~6)", fontsize=16)
    plt.tight_layout()
    plt.show()

    # -------------------------------
    # Domain 평균 MSSS vs Lead plot
    # -------------------------------
    msss_mean = []
    for lead in da.lead.values:
        avg = domain_average(da.sel(lead=lead), region=region)
        msss_mean.append(avg.values)

    plt.figure(figsize=(6,4))
    plt.plot(da.lead.values, msss_mean, marker='o')
    plt.xlabel("Lead Time (months)")
    plt.ylabel("Domain-averaged MSSS")
    plt.title("Domain-averaged MSSS vs Lead Time")
    plt.grid()
    plt.show()


def plot_msss_case2(msss_dir, var, target_year, target_month, init_months, region=None):
    """Case 2: target month에 대한 lead별 시각화"""
    lead_list, msss_list, init_list = [], [], []

    for init in init_months:
        yyyymm = f"{init}"
        msss_file = os.path.join(msss_dir, f"msss_{var}_{yyyymm}.nc")
        if not os.path.isfile(msss_file):
            print(f"[WARN] file not found: {msss_file}")
            continue

        ds = xr.open_dataset(msss_file)
        da = ds['msss']

        # target month에 대응하는 lead 계산
        init_date = pd.to_datetime(yyyymm, format="%Y%m")
        target_date = pd.Timestamp(f"{target_year}-{target_month:02d}-01")
        lead = (target_date.year - init_date.year) * 12 + (target_date.month - init_date.month) + 1

        if 1 <= lead <= 6:
            msss_target = da.sel(lead=lead)
            lead_list.append(lead)
            msss_list.append(msss_target)
            init_list.append(init_date)

    # Spatial Plot
    for i, msss in enumerate(msss_list):
        plot_spatial(msss, f"Target: {target_year}-{target_month:02d}, Init: {init_list[i].strftime('%Y-%m')}, Lead={lead_list[i]}")

    # MSSS Time Series (초기월 별)
    msss_mean = [domain_average(m, region=region).values for m in msss_list]
    plt.figure()
    plt.plot(init_list, msss_mean, marker='o')
    plt.xlabel("Forecast Start Month")
    plt.ylabel("Domain-averaged MSSS")
    plt.title(f"Target = {target_year}-{target_month:02d} MSSS")
    plt.grid()
    plt.show()

if __name__ == "__main__":

    # -----------------
    # Case 선택
    # -----------------
    case = 'case1'    # case1 또는 case2
    var = 't2m'       # 변수명
    msss_dir = './OUT/MSSS/'  # MSSS 파일 폴더

    # Case1 설정
    yyyymm = '202201'  # forecast 시작월 (Case1 전용)

    # Case2 설정
    target_year = 2022
    target_month = 5
    init_months = ['202201', '202202', '202203', '202204']

    # (Optional) Region 설정 (lat_s, lat_n, lon_w, lon_e)
    region = None
    # region = (20, 50, 120, 150)  # 영역 평균을 쓸 경우

    # -----------------
    # Case1 실행
    # -----------------
    if case == 'case1':
        msss_file = os.path.join(msss_dir, f"msss_{var}_{yyyymm}.nc")
        plot_msss_case1(msss_file, region=region)

    # -----------------
    # Case2 실행
    # -----------------
    elif case == 'case2':
        plot_msss_case2(
            msss_dir=msss_dir,
            var=var,
            target_year=target_year,
            target_month=target_month,
            init_months=init_months,
            region=region
        )

    else:
        print("case를 'case1' 또는 'case2'로 설정하세요.")
