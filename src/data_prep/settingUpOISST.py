import xarray as xr
import pandas as pd
import numpy as np
from config import *
from src.utils.logging_utils import init_logger
logger = init_logger()


def oisst_anomaly(regrid_option):
    if regrid_option == 'y':

        logger.info("Starting OISST regrid ...")
        gridfile = f'{work_dir}/target_grid.nc'
        target = xr.open_dataset(gridfile)
        lat = target.lat
        lon = target.lon

        logger.debug(lat)
        logger.debug(lon) 

        sstfile = f'{base_dir}/OISST/sst.mon.mean.nc'
        sst = xr.open_dataset(sstfile)

        sst_interp = sst.interp(
            lat=lat,
            lon=lon,
            kwargs={"fill_value": "extrapolate"}
            )
        #print(sst_interp)
        sst_interp.to_netcdf(f'{base_dir}/OISST/sst.mon.mean.regrid.nc')
        del sst, sst_interp

        logger.info("OISST regrid completed.")

    regrid_file = f'{sst_dir}/sst.mon.mean.regrid.nc'
    oisst = xr.open_dataset(regrid_file)

    oisst_clim_subset = oisst.sel(time=slice('1991-01-01','2020-12-30'))
    oisst_clim = oisst_clim_subset.groupby('time.month').mean(("time"))
    oisst_std = oisst_clim_subset.groupby('time.month').std(("time"))
    logger.info("OISST climate and standard deviation calculated.")
    #print(oisst_clim)
    
    # std 저장 추가 (향후 활용 가능)
    std_file = f'{sst_dir}/sst_std_1991_2020.nc'
    oisst_std.to_netcdf(std_file)
    logger.info(f"OISST std saved => {std_file}")

    clim_file = f'{sst_dir}/sst_clim_1991_2020.nc'
    oisst_clim.to_netcdf(clim_file)
    logger.info(f"OISST clim saved => {clim_file}")

    for year in fyears:
        out_file = f'{sst_dir}/anom/sst_anom_{year}.nc'
        oisst_anom = oisst.sel(time=slice(f'{year}-01-01',f'{year}-12-31')).groupby('time.month') - oisst_clim
        oisst_anom.to_netcdf(out_file)
        logger.info(f"Saved OISST anomaly => {out_file}")


if __name__=='__main__':
    regrid_option = input('OISST regrid to GS grid ... proceed? [y/n]')
    oisst_anomaly(regrid_option)

