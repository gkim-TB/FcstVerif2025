# fcstverif/src/utils/lon_utils.py

import xarray as xr

def is_lon_0360(ds_lon):
    """Return True if dataset longitudes are in 0–360, else False for -180–180."""
    try:
        lon_max = float(ds_lon.max())
    except Exception:
        lon_max = 180.0
    return lon_max > 180.0

def convert_lon_to_dataset(lon_val, ds_lon):
    """
    Convert an input lon (degE) to dataset's lon convention (0–360 or -180–180).
    lon_val can be any degE (e.g., 190, -170, 350, ...).
    """
    if is_lon_0360(ds_lon):
        return lon_val if lon_val >= 0 else lon_val + 360
    # dataset is -180–180
    return lon_val if lon_val <= 180 else lon_val - 360

def sel_lon_with_wrap(da, lonL, lonR):
    """
    Select lon slice from DataArray `da` with possible wrap-around.
    lonL/R must already be converted to the dataset's lon convention.
    """
    lon = da["lon"]
    if lonL <= lonR:
        return da.sel(lon=slice(lonL, lonR))
    # wrap-around: concat [L..max] U [min..R]
    left = da.sel(lon=slice(lonL, float(lon.max())))
    right = da.sel(lon=slice(float(lon.min()), lonR))
    return xr.concat([left, right], dim="lon")
