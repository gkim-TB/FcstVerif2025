---

## Background

- Existing verification frameworks often focus on hindcast-based evaluation; **verification information for real-time forecasts is limited**.  
- Real-time forecast diagnostics are required to provide operationally relevant, timely feedback for model developers and stakeholders.

---

## Objectives

1. Provide systematic verification information for **real-time forecast** products.  
2. Build an **automated analysis pipeline** for routine diagnostic computation.  
3. Deliver efficient **visualization** and **information dissemination** for verification outputs.

---

## Key Features

- Automated ingestion of multiple operational model outputs (real-time forecast).  
- Standardized preprocessing (regridding, calendar alignment, lead-time handling).  
- Deterministic and probabilistic verification metrics (ACC, RMSE, RPSS, ROC curve, Bias, etc.).  
- Case selection and compositing workflow for event-/condition-based diagnostics.  
- Streamlit dashboard

---

## Requirements

- Python 3.10+  
- Required Python packages (representative):
  - `xarray`, `dask`, `pandas`, `numpy`
  - `xskillscore`, `climpred`, `scikit-learn`, `Pillow`
  - `xesmf`, `cfgrib` / `pygrib` (if GRIB inputs)
  - `matplotlib`, `cartopy`
  - `streamlit >= 1.35.0` (for dashboard)
- Optional: conda environment recommended for reproducibility.

---

## Installation (example)

```bash
# create environment (conda)
conda create -n fcstverif python=3.10 -y
conda activate fcstverif

# install core packages
pip install xarray dask[complete] xskillscore climpred xesmf cfgrib pygrib matplotlib cartopy streamlit pandas numpy scikit-learn Pillow streamlit