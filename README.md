# FcstVerif2025

> **Operational verification framework for seasonal forecasts**  
> Model preprocessing → verification metrics (deterministic/probabilistic) → visualization

---

## Configuration

Please set the following items in `config.py` before running the pipeline.

### Required settings
- **Data paths**
  - `model_raw_dir`: directory containing raw model input files.
  - `model_out_dir`: directory where model preprocessing output will be written.
  - `era5_base_dir`: base directory for ERA5 input or processed files.
  - `oisst_dir` (or `oisst_out_dir`): directory for OISST input/outputs.
  - *(Adjust other path variables as needed for your environment.)*

- **Analysis / forecast period**
  - `fcst_start`: beginning of the forecast period (use ISO date format, e.g. `YYYY-MM-DD`).
  - `fcst_end`: end of the forecast period (ISO date).
  - `clim_start`: climatology start date (ISO date).
  - `clim_end`: climatology end date (ISO date).

- **Variable list**
  - `VARIABLES`: list of variables to process (examples: `sst`, `t2m`, `z500`).
  - Ensure variable naming matches the dataset conventions or add mapping rules in `config.py`.

- **Region definitions**
  - `REGIONS`: dictionary of named regions and their bounding boxes.
  - `REGION_OVERRIDE_BY_VAR`: optional overrides for specific variables (for example, limit `GL` latitude range to 60S–60N for `sst`).
  - Use consistent coordinate order and units (lat/lon in degrees) when defining extents.

### Notes and recommendations
- When you modify `config.py`, also verify the log and output path settings so that logs and generated files are written to the intended locations.
- Prefer absolute paths for data directories to avoid ambiguity. If relative paths are used, ensure the working directory is consistent when running scripts.
- Use ISO date strings (`YYYY-MM-DD`) for all date settings to prevent ambiguity and to ensure reliable time matching across modules.
- If your input model uses nonstandard variable names, add a mapping table in `config.py` (e.g., `MODEL_VAR_RENAME`) so the processing code can standardize names automatically.

---

## FcstVerif2025

> **Operational verification framework for seasonal forecasts**  
> Model preprocessing → verification metrics (deterministic/probabilistic) → visualization

---

## Overview
`FcstVerif2025` is a pipeline designed to perform **real-time and historical forecast verification** for seasonal forecast models (e.g., GloSea6) and observations (ERA5, OISST). The workflow automates preprocessing (`settingUp*`), metric calculations (`calc*`), tercile categorization (`categorizeTercile`), deterministic/probabilistic evaluation, and visualization (`run_plotting`).

**Current release:** `v1.2` (Release date: 2025-11-20)

---

## Highlights
- Standardization and regridding of model and observational data via `settingUpGloSea`, `settingUpERA5`, and `settingUpOISST`.  
- Automatic generation of model-specific target grids and land/sea masks (`generate_target_grid` / `generate_lsmask`).  
- Deterministic skill metrics (ACC, RMSE, etc.) and probabilistic skill (tercile-based) calculations.  
- Climate index computation modules (e.g., ENSO, IOD) via `calcIndices.py`.  
- Automated plotting scripts to produce reports (heatmaps, time series, spatial pattern plots).  
- Unified execution entry: `run_all.py`  
  - Sub-run scripts: `run_preprocessing.py`, `run_indices.py`, `run_analysis.py`, `run_plotting.py`.  
- Standardized logging and configuration management (`logging_utils.py`, `config.py`).

---

## Requirements
- **Recommended Python:** 3.10+ (Conda environment recommended)  
- **Core packages:** `xarray`, `pandas`, `numpy`, `xskillscore`, `netCDF4`, `matplotlib`, `scipy`, etc.  
- **Install dependencies:** use `requirements.txt` or `environment.yml`

```bash
# Example (conda)
conda create -n fcstverif python=3.10
conda activate fcstverif
pip install -r requirements.txt
or
pip install -e .

```

## Configuration

Please set the following items in `config.py` before running the pipeline.

### Required settings
- **Data paths**
  - `model_raw_dir`: directory containing raw model input files.
  - `model_out_dir`: directory where model preprocessing output will be written.
  - `era5_base_dir`: base directory for ERA5 input or processed files.
  - `oisst_dir` (or `oisst_out_dir`): directory for OISST input/outputs.
  - *(Adjust other path variables as needed for your environment.)*

- **Analysis / forecast period**
  - `fcst_start`: beginning of the forecast period (use ISO date format, e.g. `YYYY-MM-DD`).
  - `fcst_end`: end of the forecast period (ISO date).
  - `clim_start`: climatology start date (ISO date).
  - `clim_end`: climatology end date (ISO date).

- **Variable list**
  - `VARIABLES`: list of variables to process (examples: `sst`, `t2m`, `z500`).
  - Ensure variable naming matches the dataset conventions or add mapping rules in `config.py`.

- **Region definitions**
  - `REGIONS`: dictionary of named regions and their bounding boxes.
  - `REGION_OVERRIDE_BY_VAR`: optional overrides for specific variables (for example, limit `GL` latitude range to 60S–60N for `sst`).
  - Use consistent coordinate order and units (lat/lon in degrees) when defining extents.

### Notes and recommendations
- When you modify `config.py`, also verify the log and output path settings so that logs and generated files are written to the intended locations.
- Prefer absolute paths for data directories to avoid ambiguity. If relative paths are used, ensure the working directory is consistent when running scripts.
- Use ISO date strings (`YYYY-MM-DD`) for all date settings to prevent ambiguity and to ensure reliable time matching across modules.
- If your input model uses nonstandard variable names, add a mapping table in `config.py` (e.g., `MODEL_VAR_RENAME`) so the processing code can standardize names automatically.

