import xarray as xr
import numpy as np
import pandas as pd
import os
import logging

from fcstverif.config import *
from fcstverif.src.utils.general_utils import (
     generate_yyyymm_list,
     convert_prcp_to_mm_per_day,
     convert_geopotential_to_m,
     parse_var_level,
     generate_target_grid
)

logger = logging.getLogger("fcstverif")

def _resolve_MME_rename(var: str):
    """ 
    take universial name variable from config.py
    """
    base, lvl = parse_var_level(var)
    if lvl is not None:
        return MMEvar2rename.get(base, var), lvl
    return MMEvar2rename.get(var, var), None

def _rearange_hcst_data_(data, init_val, stat_type):

    data = data.mean(("ens")) # hindcast ensemble mean

    nlead = data.sizes['month'] # hindcast data are processed 'groupby('time.month')
    lat_vals = data['lat'].values
    lon_vals = data['lon'].values

    if stat_type in ['clm', 'std']:
        data_expanded = data.data[None,:,:,:].astype('float32')

        coords = {
                'init': [init_val],
                'lead': np.arange(1, nlead+1, dtype='int64'),
                'lat': lat_vals,
                'lon': lon_vals,
                }

        dims = ('init','lead','lat','lon')

        new_data = xr.DataArray(
                data_expanded,
                dims= dims,
                coords= coords,
                attrs= data.attrs
                )
    
        return new_data

def _rearange_fcst_data_(data, init_val):

    nlead = data.sizes['time']
    ens_vals = data['ens'].astype('int32').values
    lat_vals = data['lat'].values
    lon_vals = data['lon'].values
    time_vals = data['time'].values

    ## set initialized month
    ## MME model has directory name in momth format which is lead-1m
    #init_val = pd.to_datetime(time_vals[0]) - pd.DateOffset(months=1)

    data_t = data.transpose('ens','time','lat','lon')

    data_expanded = data_t.data[:,None,:,:,:].astype('float32')

    coords = {
            'ens': ens_vals,
            'init': [init_val],
            'lead': np.arange(1, nlead+1, dtype='int64'),
            'lat': lat_vals,
            'lon': lon_vals,
            }

    dims = ('ens','init','lead','lat','lon')

    new_data = xr.DataArray(
            data_expanded,
            dims= dims,
            coords= coords,
            attrs= data.attrs
            )

    new_data = new_data.assign_coords(time=('lead', time_vals))
    return new_data

#def generate_target_grid(data):
#    grid_out = f"{model_out_dir}/target_grid.nc"
#
#    grid_ds = xr.Dataset({"lat": data.lat, "lon":data.lon})
#    grid_ds.to_netcdf(grid_out)
#    logger.info(f"[INFO] grid file saved -> {grid_out}")

def MME_model_preprocess(
        forecast_start : str,
        forecast_end : str,
        var : str,
        data_dir : str, 
        file_prefix : str,
        out_dir : str
        ):

    rename_var, level = _resolve_MME_rename(var)
    logger.info(f"var= {rename_var}, level={level}")

    init_dates = pd.date_range(forecast_start, forecast_end, freq='MS')
    #print(init_dates)

    for c, d in enumerate(init_dates):

        init = pd.to_datetime(d)

        # MME folder name == lead-1m, initialzed month is 1month before the folder name
        initdir = init + pd.DateOffset(months=1)
        month_abbr = initdir.strftime('%b').upper()
        logger.info(f"lead-1month = {month_abbr}")

        #=== Re-formatting forecast data
        # time x level (=ens) x lat x lon --> init x lead x lat x lon x time
        fpath = f"{data_dir}/forecast/{month_abbr}/{initdir.strftime('%Y')}/{rename_var}.nc"
        logger.debug(fpath)
        fda = xr.open_dataset(fpath)[rename_var]
        #logger.debug(fda.values)
        fda = fda.rename({'level':'ens'})
        nens = fda.ens.size

        if c == 0:
            generate_target_grid(fda)

        new_fa  = _rearange_fcst_data_(fda, init)
        logger.debug(new_fa)#.values)

        os.makedirs(f'{out_dir}/forecast/', exist_ok=True)
        ds_out = new_fa.to_dataset(name=var)
        out_file = f"{out_dir}/forecast/ensMem_{var}_{init.strftime('%Y%m')}.nc"
        ds_out.to_netcdf(out_file)
        logger.info(f"[Fcst Mem] saved -> {out_file}")
        del out_file

        #=== Re-formatting hindcast data
        hpath = [f"{data_dir}/hindcast/{month_abbr}/{yr}/{rename_var}.nc" for yr in range(hcst_styr,hcst_enyr+1)]
        #logger.debug(hpath)
        
        ds = []
        for f in hpath: 
            da = xr.open_dataset(f)[rename_var]
            ds.append(da)
        ds = xr.concat(ds, dim='time')
        ds = ds.rename({'level':'ens'}) 
        #logger.debug(ds)

        clm = ds.groupby('time.month').mean(("time")) # calculate climatology
        std = ds.groupby('time.month').std(("time")) # calculate sigma # * 0,43
        logger.debug(clm)
        #logger.debug(std)
   
        expected_months = pd.DatetimeIndex(new_fa.time.values).month.tolist()
        logger.debug(f"[DEBUG] expected months (lead order) = {expected_months}")

        clm = clm.reindex(month=expected_months)
        std = std.reindex(month=expected_months)
        logger.debug(f"[DEBUG] clm.month after reorder: {clm['month'].values}")

        new_clm = _rearange_hcst_data_(clm, init, 'clm')
        new_clm = new_clm.assign_coords(time=('lead',new_fa.time.values))
        logger.debug(new_clm)

        os.makedirs(f'{out_dir}/hindcast/', exist_ok=True)

        clm_out = new_clm.to_dataset(name=var)
        out_file = f"{out_dir}/hindcast/ensMean_{var}_{init.strftime('%Y%m')}.nc"
        clm_out.to_netcdf(out_file)
        logger.info(f"[Hcst ensMean] saved -> {out_file}")
        del out_file 

        new_std = _rearange_hcst_data_(std, init, 'std') * 0.4305
        new_std = new_std.assign_coords(time=('lead', new_fa.time.values))

        if var == 't2m':
            std_out = new_std.to_dataset(name=f"{var}_sigma")
            out_file = f"{out_dir}/hindcast/ensMean_sigma_{var}_{init.strftime('%Y%m')}.nc"
            std_out.to_netcdf(out_file)
            logger.info(f"[Hcst t2m sigma] saved -> {out_file}")
            del out_file
        

        stat_idx = pd.Index([100,101], name='pert')
        combined = xr.concat([new_clm+new_std, new_clm-new_std], dim=stat_idx)
        combined = combined.assign_coords(pert=stat_idx)
        combined['pert'].attrs = {'long_name':'gaussian statistic', 'description':'climatology +/- 0.4305std'}
        combined = combined.transpose('init','pert',...)
        #print(combined)

        gaus_out = combined.to_dataset(name=f"{var}_gaus")
        out_file = f"{out_dir}/hindcast/ensMean_gaus_{var}_{init.strftime('%Y%m')}.nc"
        gaus_out.to_netcdf(out_file)
        logger.info(f"[Hcst gaus] saved -> {out_file}")
        del out_file

        # calculate anomaly
        anom = new_fa - new_clm
        
        os.makedirs(f'{out_dir}/anomaly/', exist_ok=True)

        anom_out = anom.to_dataset(name=var)
        out_file = f"{out_dir}/anomaly/ensMem_{var}_anom_{init.strftime('%Y%m')}.nc"
        anom_out.to_netcdf(out_file)
        logger.info(f"[Anom] saved -> {out_file}")
        del out_file
