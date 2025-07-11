# index_skill_relationship.py
import xarray as xr
import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
from scipy.stats import pearsonr


def calc_index_skill_acc_rmse(obs_index_file, fcst_index_file_pattern, outdir, index_name="ENSO"):
    """
    obs_index_file: 관측 인덱스 (NetCDF, 변수: ENSO, IOD 등)
    fcst_index_file_pattern: 예측 인덱스 파일 패턴 (e.g. "fcst_indices_*.nc")
    outdir: 결과 저장 디렉토리
    index_name: "ENSO" or "IOD"
    """
    os.makedirs(outdir, exist_ok=True)
    # 관측 인덱스 로드 (time 차원)
    ds_obs = xr.open_dataset(obs_index_file)
    obs = ds_obs[index_name]         # (time,)

    # 예측 인덱스 로드 (init, time, ens 또는 (time, ens) → 초기화월별 concat)
    ds_fcst = xr.open_mfdataset(fcst_index_file_pattern, combine="nested", concat_dim="init")
    # ds_fcst["init"] = ... # 필요시 초기화월을 coord로 부여
    fcst = ds_fcst[index_name]       # (init, time, ens) or (init, time) etc

    # 결과 누적 리스트
    records = []

    # Loop over initializations
    for i, init_val in enumerate(fcst.init.values):
        fcst_this_init = fcst.isel(init=i)
        # 앙상블 평균
        if "ens" in fcst_this_init.dims:
            fcst_mean = fcst_this_init.mean("ens")
        else:
            fcst_mean = fcst_this_init

        # 관측과 예측의 time 차원 일치 (공통기간)
        fcst_mean, obs_matched = xr.align(fcst_mean, obs, join="inner")
        times = fcst_mean.time.values

        # 리드타임 loop
        for t, time in enumerate(times):
            fcst_val = fcst_mean.isel(time=t).values
            obs_val = obs_matched.isel(time=t).values

            # ACC, RMSE 계산은 여기서는 리드타임별 단일값 (만약 리드-타임 전체시계열로 계산 원하면 reshape/분기)
            acc = np.nan  # 보통 여러 시점 필요, 단일 값에서는 nan
            rmse = np.abs(fcst_val - obs_val)
            records.append({
                "init": str(init_val),
                "time": str(time),
                "ACC": acc,  # lead타임이 충분히 쌓일 경우 ACC 계산 가능
                "RMSE": rmse
            })

        # 전체 time에 대해 ACC, RMSE 산출 (예측시계열 vs 관측시계열)
        if len(fcst_mean) >= 2:
            ACC_all = np.corrcoef(fcst_mean.values, obs_matched.values)[0, 1]
            RMSE_all = np.sqrt(np.nanmean((fcst_mean.values - obs_matched.values) ** 2))
        else:
            ACC_all = np.nan
            RMSE_all = np.nan
        # init별 전체 ACC, RMSE 추가 기록
        records.append({
            "init": str(init_val),
            "time": "ALL",
            "ACC": ACC_all,
            "RMSE": RMSE_all
        })

    # DataFrame 변환 및 저장
    df = pd.DataFrame(records)
    csv_path = os.path.join(outdir, f"{index_name}_index_skill_acc_rmse.csv")
    df.to_csv(csv_path, index=False)
    print(f"[INFO] Index ACC, RMSE 저장: {csv_path}")

    # 산점도 등 시각화 (선택)
    # 전체 예측성능 time-series plot 등 다양하게 확장 가능

    return df

# def plot_scatter():
#     # 5. 그림 (산점도)
#     plt.figure(figsize=(6,5))
#     plt.scatter(idx_skill_flat, var_skill_flat, alpha=0.5)
#     plt.xlabel(f"{index_name} {score_type}")
#     plt.ylabel(f"{var_name} {score_type}")
#     plt.title(f"Correlation: {corr:.2f} (p={pval:.3f})")
#     plt.grid(True)
#     plt.tight_layout()
#     plt.savefig(os.path.join(outdir, f"{index_name}_{var_name}_skillcorr_{score_type}.png"))
#     plt.close()
#     print(f"[분석] {index_name}-{var_name} {score_type} 상관계수: {corr:.3f} (p={pval:.3f})")
#     return corr, pval

def analyze_skill_vs_index_strength(index_anom_file, index_score_file, outdir, 
                                   index_name="Nino34", score_type="ACC"):
    """
    2. ENSO, IOD anomaly 크기에 따른 ENSO, IOD 예측성 변화 분석
    - index_anom_file: ENSO/IOD anomaly 시계열 (NetCDF, (time,))
    - index_score_file: ENSO/IOD 예측 ACC/RMSE (NetCDF, (time, lead))
    """
    os.makedirs(outdir, exist_ok=True)
    # 1. 파일 읽기
    ds_anom = xr.open_mfdataset(index_anom_file, combine='by_coords')
    ds_score = xr.open_mfdataset(index_score_file, combine='by_coords')
    anom = ds_anom[index_name]  # (time,)
    skill = ds_score[score_type]  # (time, lead)

    # 2. anomaly(월/lead별)와 skill 맞추기 (예: 초기화월별, lead별)
    anom, skill = xr.align(anom, skill, join="inner")
    # (time, lead) → 1D
    anom_tile = np.tile(anom.values, skill.shape[1])
    skill_flat = skill.values.flatten()

    # 3. 상관관계/회귀
    corr, pval = pearsonr(np.abs(anom_tile), skill_flat)  # 절대값 사용 가능

    # 4. 결과 저장 및 그림
    df = pd.DataFrame({"anom_abs": np.abs(anom_tile), "skill": skill_flat})
    df.to_csv(os.path.join(outdir, f"{index_name}_anom_vs_skill_{score_type}.csv"), index=False)

    plt.figure(figsize=(6,5))
    plt.scatter(np.abs(anom_tile), skill_flat, alpha=0.5)
    plt.xlabel(f"|{index_name} anomaly|")
    plt.ylabel(f"{index_name} {score_type}")
    plt.title(f"Corr(|anom|, {score_type}): {corr:.2f} (p={pval:.3f})")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(outdir, f"{index_name}_anom_vs_skill_{score_type}.png"))
    plt.close()
    print(f"[분석] {index_name} 강도-|anom|-{score_type} 상관계수: {corr:.3f} (p={pval:.3f})")
    return corr, pval

def analyze_var_skill_vs_index_strength(index_anom_file, var_score_file, outdir, 
                                       index_name="Nino34", var_name="t2m", score_type="ACC"):
    """
    3. ENSO, IOD anomaly 크기와 대기변수 예측성 상관분석
    - index_anom_file: ENSO/IOD anomaly (NetCDF, (time,))
    - var_score_file: 대기변수 예측스킬 (NetCDF, (time, lead))
    """
    os.makedirs(outdir, exist_ok=True)
    ds_anom = xr.open_mfdataset(index_anom_file, combine='by_coords')
    ds_var = xr.open_mfdataset(var_score_file, combine='by_coords')
    anom = ds_anom[index_name]  # (time,)
    var_skill = ds_var[score_type]  # (time, lead)

    # 2. align
    anom, var_skill = xr.align(anom, var_skill, join="inner")
    anom_tile = np.tile(anom.values, var_skill.shape[1])
    var_skill_flat = var_skill.values.flatten()

    # 3. 상관분석
    corr, pval = pearsonr(np.abs(anom_tile), var_skill_flat)
    df = pd.DataFrame({"anom_abs": np.abs(anom_tile), "var_skill": var_skill_flat})
    df.to_csv(os.path.join(outdir, f"{index_name}_anom_vs_{var_name}_skill_{score_type}.csv"), index=False)

    plt.figure(figsize=(6,5))
    plt.scatter(np.abs(anom_tile), var_skill_flat, alpha=0.5)
    plt.xlabel(f"|{index_name} anomaly|")
    plt.ylabel(f"{var_name} {score_type}")
    plt.title(f"Corr(|anom|, {var_name} {score_type}): {corr:.2f} (p={pval:.3f})")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(outdir, f"{index_name}_anom_vs_{var_name}_skill_{score_type}.png"))
    plt.close()
    print(f"[분석] {index_name} 강도-|anom|-{var_name}-{score_type} 상관계수: {corr:.3f} (p={pval:.3f})")
    return corr, pval