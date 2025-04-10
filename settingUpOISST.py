import xarray as xr
import pandas as pd
import numpy as np
from config import *

def oisst_anomaly(regrid_option):
    if regrid_option == 'y':
        gridfile = f'{base_dir}/FcstVerif_v2.0/target_grid.nc'
        target = xr.open_dataset(gridfile)
        lat = target.lat
        lon = target.lon

        print(lat)
        print(lon) 

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


    regrid_file = f'{sst_dir}/sst.mon.mean.regrid.nc'
    oisst = xr.open_dataset(regrid_file)

    oisst_clim_subset = oisst.sel(time=slice('1991-01-01','2020-12-30'))
    oisst_clim = oisst_clim_subset.groupby('time.month').mean(("time"))
    oisst_std = oisst_clim_subset.groupby('time.month').std(("time"))
    #print(oisst_clim)

    for year in fyears:
        out_file = f'{sst_dir}/anom/sst_anom_{year}.nc'
        oisst_anom = oisst.sel(time=slice(f'{year}-01-01',f'{year}-12-31')).groupby('time.month') - oisst_clim
        oisst_anom.to_netcdf(out_file)
        print(f"[INFO] Saved OISST anomaly => {out_file}")


if __name__=='__main__':
    regrid_option = input('OISST regrid to GS grid ... proceed? [y/n]')
    oisst_anomaly(regrid_option)

