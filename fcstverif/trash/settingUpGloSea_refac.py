import pygrib
import xarray as xr
import numpy as np
import pandas as pd
import os

from fcstverif.config import *
from fcstverif.src.utils.general_utils import convert_prcp_to_mm_per_day, convert_geopotential_to_m
from fcstverif.src.utils.logging_utils import init_logger
logger = init_logger()

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

def _convert_units(da, var, stat_type):
    if not isinstance(da, xr.DataArray):
        return da
    if var == 'prcp' and stat_type != 'qntl':
        return convert_prcp_to_mm_per_day(da, source='GS6')
    elif var in ['z', 'zg', 'geopotential']:
        return convert_geopotential_to_m(da, source='GS6')
    return da

def _grib_messages_to_dataset(msgs, init_date, var, stat_type=None, rename_output=None):
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
        da = da.assign_coords(lead=lead_coords, time=valid_times)

    elif stat_type in ('gaus', 'qntl'):
        if len(msgs) != 12:
            raise ValueError(f"{stat_type}는 GRIB 12개가 필요 → {len(msgs)}")
        above, below = _split_perturbations(msgs)
        if len(above) != 6 or len(below) != 6:
            raise ValueError(f"{stat_type}: pert 분리 오류 (100={len(above)}, 101={len(below)})")
        da = xr.concat([xr.concat([_make_da(g) for g in above], dim='lead'),
                        xr.concat([_make_da(g) for g in below], dim='lead')], dim='pert')
        da = da.assign_coords(lead=lead_coords, pert=('pert', [100, 101]), time=valid_times)

    else:
        raise ValueError(f"지원하지 않는 stat_type: {stat_type}")

    da = da.expand_dims('init').assign_coords(init=('init', [init_date]))
    da['lead'].attrs['units'] = 'months'
    return da.to_dataset(name=out_name).set_coords('time')

def convert_single_hindcast_file(init_date_str, var, stat_type, data_dir, file_prefix, out_dir):
    rename_var = GSvar2rename.get(var, var)
    date_tag = pd.to_datetime(init_date_str).strftime('%Y%m%d')
    stat_part = "" if stat_type is None else f"{stat_type}_"
    fpath = os.path.join(data_dir, rename_var, f"{file_prefix}{stat_part}{rename_var}_{date_tag}.grb2")

    if not os.path.isfile(fpath):
        logger.warning(f"[HIND] 파일 없음: {fpath}")
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
