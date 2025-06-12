import xarray as xr
import numpy as np
import pandas as pd

from config import *

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
print(sst_interp)

sst_interp.to_netcdf(f'{base_dir}/OISST/sst.mon.mean.regrid.nc')