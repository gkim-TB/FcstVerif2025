import pygrib
import xarray as xr
import numpy as np
import pandas as pd
import os

from config import *
from src.utils.general_utils import convert_prcp_to_mm_per_day, convert_geopotential_to_m
from src.utils.logging_utils import init_logger
logger = init_logger()

# ─────────────────────────────────────────────
# 0. Init‑date 헬퍼 : rule 인자 추가
# ─────────────────────────────────────────────
def _get_init_mondays(start: str, end: str, rule: str = 'last') -> list[pd.Timestamp]:
    """rule 에 따라 초기화 월요일 날짜 반환"""
    weekly = pd.date_range(start, end, freq='W-MON')

    def _rule_last(grps):
        return sorted({d.replace(day=1): d for d in grps}.values())

    def _rule_mid(grps):
        mids = []
        for g in grps:
            if 9 <= g.day <= 17:
                mids.append(g)
        # 월별 대표가 없으면 가장 가까운 월요일을 찾음
        out = {}
        for d in weekly:
            key = d.replace(day=1)
            cand = [m for m in mids if m.month == key.month and m.year == key.year]
            if cand:
                out[key] = cand[0]
            else:               # 보정: 9–17 범위 월요일이 없으면 마지막 월요일 사용
                out[key] = max([m for m in weekly if m.month == key.month and m.year == key.year])
        return sorted(out.values())

    rule_func = {'last': _rule_last, 'mid': _rule_mid}.get(rule)
    if rule_func is None:
        raise ValueError(f"지원하지 않는 rule → {rule}")
    return rule_func(weekly)
    
# ───────────────────────────────────────────────────────────────
# 1. _grib_messages_to_dataset  (헬퍼)  ★ once for all ★
# ───────────────────────────────────────────────────────────────
def _grib_messages_to_dataset(
        msgs         : list[pygrib.gribmessage],
        init_date    : pd.Timestamp,
        var          : str,
        stat_type    : str | None = None,
        rename_output: str | None = None
    ) -> xr.Dataset:
    """
    GRIB message list → climpred 호환 Dataset
      • 일반 / sigma : GRIB 6개   → lead 6
      • gaus / qntl  : GRIB 12개  → lead 6 × pert(100/101)

    모든 경우에 (init=1, lead, [pert], lat, lon) + time 좌표 포함.
    주요 속성(FillValue, units)도 그대로 보존.
    """
    #rename_var = GSvar2rename.get(var, var)
    out_name   = rename_output or f"{var}" + (f"_{stat_type}" if stat_type else "")

    nmsg = len(msgs)
    if   stat_type in (None, 'sigma') and nmsg != 6:
        raise ValueError(f"{stat_type or 'hindcast'}는 GRIB 6개가 필요 -> {nmsg}")
    if   stat_type in ('gaus', 'qntl') and nmsg != 12:
        raise ValueError(f"{stat_type}는 GRIB 12개가 필요 -> {nmsg}")

    # 공통 좌표 및 시간
    lats, lons = msgs[0].latlons()
    lead_coords  = np.arange(1, 7)
    valid_times  = pd.date_range(init_date + pd.DateOffset(months=1), periods=6, freq='MS')

    def _make_da(g):
        da = xr.DataArray(
            g.values,
            dims=('lat', 'lon'),
            coords={'lat': lats[:, 0], 'lon': lons[0, :]},
            attrs={
                'units'     : getattr(g, 'parameterUnits', None),
                '_FillValue': np.nan if np.isnan(getattr(g, 'missingValue', np.nan)) else g.missingValue
            }
        )
        return da

    # ── 일반‧sigma  (lead 6) ────────────────────────────────
    if stat_type in (None, 'sigma'):
        da = xr.concat([_make_da(g) for g in msgs], dim='lead')
        da = da.assign_coords(lead=('lead', lead_coords),
                              time=('lead', valid_times))

    # ── gaus‧qntl  (lead 6 × pert) ─────────────────────────
    else:
        above, below = [], []
        for g in msgs:
            (above if g.perturbationNumber == 100 else below).append(_make_da(g))
        if len(above) != 6 or len(below) != 6:
            raise ValueError(f"{stat_type}: pert 분리 오류 (100={len(above)}, 101={len(below)})")
        da = xr.concat([xr.concat(above, dim='lead'),
                        xr.concat(below, dim='lead')],
                       dim='pert')
        da = da.assign_coords(
                lead=('lead', lead_coords),
                pert=('pert', [100, 101]),
                time=('lead', valid_times))

    # init 차원 확장 및 Dataset 변환
    da = da.expand_dims('init').assign_coords(init=('init', [init_date]))
    da['lead'].attrs['units'] = 'months'
    ds = da.to_dataset(name=out_name).set_coords('time')
    return ds

# ─────────────────────────────────────────────
# 2‑1. convert_single_hindcast_file 
# ─────────────────────────────────────────────
def convert_single_hindcast_file(
        init_date_str : str,
        var           : str,
        stat_type     : str | None,
        data_dir      : str,
        file_prefix   : str,
        out_dir       : str
    ):
    """
    단일 초기화 날짜(YYYYMMDD)의 hindcast / sigma / gaus / qntl GRIB2 → NetCDF
    """
    rename_var = GSvar2rename.get(var, var)
    date_tag   = pd.to_datetime(init_date_str).strftime('%Y%m%d')
    stat_part  = "" if stat_type is None else f"{stat_type}_"
    fpath = os.path.join(
        data_dir, rename_var,
        f"{file_prefix}{stat_part}{rename_var}_{date_tag}.grb2"
    )

    if not os.path.isfile(fpath):
        logger.warning(f"[HIND] 파일 없음: {fpath}")
        return

    grbs = pygrib.open(fpath)
    msgs = grbs.select(name=var2grib_name[rename_var])
    grbs.close()

    init_date = pd.to_datetime(init_date_str).replace(day=1)
    ds_out    = _grib_messages_to_dataset(msgs, init_date, var, stat_type)

    # ▶ GS6 강수량 / 지위 단위 변환
    for vname in ds_out.data_vars:
        if not vname.startswith(var):
            continue
        if var == 'prcp' and stat_type != 'qntl':
            ds_out[vname] = convert_prcp_to_mm_per_day(ds_out[vname], source='GS6')
        elif var in ['z', 'zg', 'geopotential']:
            ds_out[vname] = convert_geopotential_to_m(ds_out[vname], source='GS6')

    yyyymm = init_date.strftime('%Y%m')
    out_nc = (f"ensMean_{var}_{yyyymm}.nc" if stat_type is None
              else f"ensMean_{stat_type}_{var}_{yyyymm}.nc")

    ds_out.to_netcdf(os.path.join(out_dir, out_nc))
    logger.info(f"[HIND] saved → {out_nc}")


# ─────────────────────────────────────────────
# 2‑2. 월별 hindcast 변환 (init_rule 적용)
# ─────────────────────────────────────────────
def convert_monthly_hindcast(                       
        forecast_start : str,
        forecast_end   : str,
        var            : str,
        data_dir       : str,
        file_prefix    : str,
        out_dir        : str,
        stats_dir      : str = f'{model_raw_dir}/stats',
        init_rule      : str = 'last' # last=마지막주 월, mid=9~17일 사이 월요일               
    ):

    #rename_var = GSvar2rename.get(var, var)
    init_dates = _get_init_mondays(forecast_start, forecast_end, init_rule)  

    stat_list = ['sigma', 'gaus'] if var == 't2m' else ['qntl'] if var == 'prcp' else ['gaus']

    for d in init_dates:
        dstr = d.strftime('%Y-%m-%d')
        # (1) hindcast 본체
        convert_single_hindcast_file(
            init_date_str=dstr,
            var=var,
            stat_type=None,
            data_dir=data_dir,
            file_prefix=file_prefix,
            out_dir=out_dir
        )
        # (2) sigma / gaus / qntl
        for st in stat_list:
            convert_single_hindcast_file(
                init_date_str=dstr,
                var=var,
                stat_type=st,
                data_dir=stats_dir,          # stats 전용 경로
                file_prefix=file_prefix,     
                out_dir=out_dir
            )                                



# ───────────────────────────────────────────────────────────────
# 3. forecast(_mem) 파일 → 월별 ens 차원 NetCDF 변환
# ───────────────────────────────────────────────────────────────
def convert_monthly_forecast_from_mem(
        forecast_start : str,
        forecast_end   : str,
        var            : str,
        data_dir       : str,
        file_prefix    : str,
        out_dir        : str,
        init_rule      : str
    ):
    """
    파일 패턴: glos_conv_kma_fcst_6mon_mon_t15m_YYYYMMDD_mem.grb2
    (lead 6 메시지가 ens 수만큼 반복)
    """
    rename_var   = GSvar2rename.get(var, var)
    init_dates = _get_init_mondays(forecast_start, forecast_end, init_rule)

    for d in init_dates:
        tag   = d.strftime('%Y%m%d')
        fpath = os.path.join(data_dir, rename_var,
                             f"{file_prefix}{rename_var}_{tag}_mem.grb2")
        if not os.path.isfile(fpath):
            logger.warning(f"[MEM] 파일 없음: {fpath}")
            continue

        grbs = pygrib.open(fpath)
        msgs = grbs.select(name=var2grib_name[rename_var])
        grbs.close()

        if len(msgs) % 6 != 0:
            logger.warning(f"[MEM] 메시지 수({len(msgs)})가 6의 배수가 아님 → skip")
            continue
        n_ens = len(msgs) // 6
        init_date = d.replace(day=1)

        ens_ds = []
        for e in range(n_ens):
            chunk = msgs[e*6:(e+1)*6]
            ens_ds.append(_grib_messages_to_dataset(chunk, init_date, var))

        ds_ens = xr.concat(ens_ds, dim='ens').set_coords('time')
        
        # ▶ GS6 강수량 / 지위 단위 변환
        for vname in [v for v in ds_ens.data_vars if v.startswith(var)]:
            if var == 'prcp':
                ds_ens[vname] = convert_prcp_to_mm_per_day(ds_ens[vname], source='GS6')
            elif var in ['z', 'zg', 'geopotential']:
                ds_ens[vname] = convert_geopotential_to_m(ds_ens[vname], source='GS6')

        out_nc = os.path.join(out_dir, f"ensMem_{var}_{d:%Y%m}.nc")
        ds_ens.to_netcdf(out_nc)
        logger.info(f"[MEM] saved → {out_nc}")
