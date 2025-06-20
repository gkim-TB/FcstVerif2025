import pygrib
import xarray as xr
import numpy as np
import pandas as pd
import os
import logging

from fcstverif.config import *
from fcstverif.src.utils.general_utils import convert_prcp_to_mm_per_day, convert_geopotential_to_m
#from fcstverif.src.utils.logging_utils import init_logger
logger = logging.getLogger("fcstverif")

def _get_init_mondays(start: str, end: str, rule: str = 'last') -> list[pd.Timestamp]:
    weekly = pd.date_range(start, end, freq='W-MON')

    def _rule_last(grps):
        return sorted({d.replace(day=1): d for d in grps}.values())

    def _rule_mid(grps):
        mids = [g for g in grps if 9 <= g.day <= 17]
        out = {}
        for d in weekly:
            key = d.replace(day=1)
            cand = [m for m in mids if m.month == key.month and m.year == key.year]
            out[key] = cand[0] if cand else max([m for m in weekly if m.month == key.month and m.year == key.year])
        return sorted(out.values())

    rule_func = {'last': _rule_last, 'mid': _rule_mid}.get(rule)
    if rule_func is None:
        raise ValueError(f"지원하지 않는 rule → {rule}")
    return rule_func(weekly)

def _split_perturbations(msgs):
    above, below = [], []
    for g in msgs:
        if g.perturbationNumber == 100:
            above.append(g)
        elif g.perturbationNumber == 101:
            below.append(g)
    return above, below

def _convert_units(da, var, stat_type=None):
    if not isinstance(da, xr.DataArray):
        return da
    if var == 'prcp' and stat_type != 'qntl':
        return convert_prcp_to_mm_per_day(da, source='GS6')
    elif var in ['z', 'zg', 'geopotential']:
        return convert_geopotential_to_m(da, source='GS6')
    return da

def _grib_messages_to_dataset(
        msgs         : list[pygrib.gribmessage],
        init_date    : pd.Timestamp,
        var          : str,
        stat_type    : str | None = None,
        rename_output: str | None = None
    ) -> xr.Dataset:

    logger.debug(f"[DEBUG] stat_type={stat_type}, msgs={len(msgs)}")
    
    out_name = rename_output or f"{var}" + (f"_{stat_type}" if stat_type else "")
    lats, lons = msgs[0].latlons()
    lead_coords = np.arange(1, 7)
    valid_times = pd.date_range(init_date + pd.DateOffset(months=1), periods=6, freq='MS')

    def _make_da(g):
        return xr.DataArray(
            g.values,
            dims=('lat', 'lon'),
            coords={'lat': lats[:, 0], 'lon': lons[0, :]},
            attrs={
                'units': getattr(g, 'parameterUnits', None),
                '_FillValue': np.nan if np.isnan(getattr(g, 'missingValue', np.nan)) else g.missingValue
            }
        )

    if stat_type in (None, 'sigma'):
        if len(msgs) != 6:
            raise ValueError(f"{stat_type or 'hindcast'}는 GRIB 6개가 필요 → {len(msgs)}")
        da = xr.concat([_make_da(g) for g in msgs], dim='lead')
        da = da.assign_coords(lead=('lead', lead_coords), time=('lead', valid_times))

    elif stat_type in ('gaus', 'qntl'):
        if len(msgs) != 12:
            raise ValueError(f"{stat_type}는 GRIB 12개가 필요 → {len(msgs)}")
        above, below = _split_perturbations(msgs)
        if len(above) != 6 or len(below) != 6:
            raise ValueError(f"{stat_type}: pert 분리 오류 (100={len(above)}, 101={len(below)})")
        da = xr.concat([xr.concat([_make_da(g) for g in above], dim='lead'),
                        xr.concat([_make_da(g) for g in below], dim='lead')], dim='pert')
        #da = da.expand_dims({'time': valid_times, 'lead': lead_coords})
        da = da.assign_coords(lead=lead_coords, pert=('pert', [100, 101]), time=('lead', valid_times))

    else:
        raise ValueError(f"지원하지 않는 stat_type: {stat_type}")

    da = da.expand_dims('init').assign_coords(init=('init', [init_date]))
    da['lead'].attrs['units'] = 'months'
    logger.debug(f"[DEBUG] dims={da.dims}, shape={da.shape}")

    return da.to_dataset(name=out_name).set_coords('time')

def convert_single_hindcast_file(
        init_date_str, 
        var, 
        stat_type, 
        data_dir, 
        file_prefix, 
        out_dir
    ):

    rename_var = GSvar2rename.get(var, var)
    date_tag = pd.to_datetime(init_date_str).strftime('%Y%m%d')
    stat_part = "" if stat_type is None else f"{stat_type}_"

    # hindcast data path [ modify if needed ]
    fpath = os.path.join(
        data_dir, rename_var, f"{file_prefix}{stat_part}{rename_var}_{date_tag}.grb2"
    )
    if not os.path.isfile(fpath):
        logger.warning(f"[HIND] {stat_type} 파일 없음: {fpath}")
        return

    grbs = pygrib.open(fpath)
    msgs = grbs.select(name=var2grib_name[rename_var])
    grbs.close()

    init_date = pd.to_datetime(init_date_str).replace(day=1)
    ds_out = _grib_messages_to_dataset(msgs, init_date, var, stat_type)

    for vname in ds_out.data_vars:
        if vname.startswith(var):
            ds_out[vname] = _convert_units(ds_out[vname], var, stat_type)

    yyyymm = init_date.strftime('%Y%m')
    out_nc = f"ensMean_{stat_type + '_' if stat_type else ''}{var}_{yyyymm}.nc"
    ds_out.to_netcdf(os.path.join(out_dir, out_nc))
    logger.info(f"[HIND] saved → {out_nc}")

def convert_monthly_hindcast(forecast_start, forecast_end, var, init_rule, data_dir, file_prefix, out_dir):
    '''
    convert the specified initialized date to monthly initialization
    e.g. if initialized date is 2022-01-01 --> 2022-01
    '''
    init_dates = _get_init_mondays(forecast_start, forecast_end, init_rule)
    stat_list = []
    stat_list.append(None)
    
    if var == 't2m':
        stat_list += ['sigma', 'gaus'] 
    elif var == 'prcp': 
        stat_list += ['qntl'] 
    else:
        stat_list += ['gaus']

    for date in init_dates:
        date_str = date.strftime('%Y-%m-%d')
        for stat_type in stat_list:
            convert_single_hindcast_file(
                date_str, var, stat_type, data_dir, file_prefix, out_dir)

def convert_monthly_forecast_from_mem(
        forecast_start : str,
        forecast_end : str,
        var : str,
        init_rule : str,
        data_dir : str,
        file_prefix : str,
        out_dir : str
    ):

    rename_var   = GSvar2rename.get(var, var)
    init_dates = _get_init_mondays(forecast_start, forecast_end, init_rule)

    for d in init_dates:
        date_tag   = d.strftime('%Y%m%d')
        # forecast data path [ modify if needed ]
        fpath = os.path.join(data_dir, rename_var,
                             f"{file_prefix}{rename_var}_{date_tag}_mem.grb2")
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
        for vname in ds_ens.data_vars:
            if vname.startswith(var):
                ds_ens[vname] = _convert_units(ds_ens[vname], var)
        # for vname in [v for v in ds_ens.data_vars if v.startswith(var)]:
        #     if var == 'prcp':
        #         ds_ens[vname] = convert_prcp_to_mm_per_day(ds_ens[vname], source='GS6')
        #     elif var in ['z', 'zg', 'geopotential']:
        #         ds_ens[vname] = convert_geopotential_to_m(ds_ens[vname], source='GS6')

        out_nc = os.path.join(out_dir, f"ensMem_{var}_{d:%Y%m}.nc")
        ds_ens.to_netcdf(out_nc)
        logger.info(f"[MEM] saved → {out_nc}")

def compute_anomaly(var, year_start, year_end, hindcast_dir, forecast_dir, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    dates = pd.date_range(start=f"{year_start}-01", end=f"{year_end}-12", freq="MS")

    for date in dates:
        yyyymm = date.strftime('%Y%m')

        hind_file = os.path.join(hindcast_dir, f"ensMean_{var}_{yyyymm}.nc")
        fcst_file = os.path.join(forecast_dir, f"ensMem_{var}_{yyyymm}.nc")
        
        # 두 파일이 모두 존재해야 anomaly를 계산
        if not os.path.isfile(hind_file):
            logger.warning(f"Hindcast file not found: {hind_file}")
            continue
        if not os.path.isfile(fcst_file):
            logger.warning(f"Forecast file not found: {fcst_file}")
            continue

        # 파일 열기
        ds_hind = xr.open_dataset(hind_file)
        ds_fcst = xr.open_dataset(fcst_file)

        # anomaly 계산
        ds_anom = ds_fcst - ds_hind
    
        # 예: "fcst - hind(1993~2016 mean)"라는 메타정보 기록
        ds_anom.attrs['description'] = f"{var} anomaly (forecast - hindcast 1993-2016 avg)"
        ds_anom.attrs['source_fcst'] = fcst_file
        ds_anom.attrs['source_hind'] = hind_file

        # 출력 파일 이름 (ex. "anom_t15m_202201.nc")
        out_fname = os.path.join(out_dir, f"ensMem_{var}_anom_{yyyymm}.nc")
        ds_anom.to_netcdf(out_fname)
        logger.info(f"Saved anomaly: {out_fname}")

    logger.info("Done. Anomaly files are in: %s", out_dir)