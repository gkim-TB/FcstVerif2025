# Guidance 
# Real-time Seasonal Forecast Verification System

## 💡 Project Overview

This project develops an **automated verification system** to systematically evaluate the **real-time** forecast performance of seasonal prediction systems.  
The system aims to ingest operational forecast streams, run standardized verification workflows, and deliver interactive visualization and summary reports.

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
```

## Verification metrics — Mathematical definitions & implementation notes

This section documents the mathematical formulas used by the verification system and points to where each metric is implemented in the analysis code.

### Notation
- \(f(\mathbf{x},t)\) : forecast field (may be ensemble member or ensemble mean) at spatial location \(\mathbf{x}\) and time \(t\).  
- \(o(\mathbf{x},t)\) : observation field at \(\mathbf{x},t\).  
- spatial averaging over a domain \(D\) (lat/lon) is denoted \(\langle \cdot \rangle_D\).  
- For categorical/probabilistic verification, categories are indexed by \(k=1,\dots,K\) (here \(K=3\) for terciles: BN, NN, AN).  
- Ensemble size: \(N\). Ensemble members indexed by \(m=1,\dots,N\).  
- Time averaging is explicit where used (e.g., for index verification).

---

### 1) Anomaly Correlation Coefficient (ACC)

**Definition (spatial ACC for anomalies).**  
When forecasts and observations are already anomaly fields (mean-removed), ACC over domain \(D\) is computed as:

\[
\mathrm{ACC} = \frac{\langle f \cdot o \rangle_D}{\sqrt{\langle f^2 \rangle_D}\,\sqrt{\langle o^2 \rangle_D} + \epsilon}
\]

where \(\langle \cdot \rangle_D\) denotes the spatial mean over \((\text{lat},\text{lon})\) and \(\epsilon\) is a small constant to avoid division by zero (the code adds `1e-12`). Implementation: `calc_acc_vec` and the deterministic skill workflow. :contentReference[oaicite:0]{index=0}

**Notes**
- The system computes ACC both for each ensemble member and for the ensemble mean (ensemble mean is computed as \( \bar f(\mathbf{x},t)=\frac{1}{N}\sum_{m} f_m(\mathbf{x},t) \)). See `compute_deterministic_scores`. :contentReference[oaicite:1]{index=1}

---

### 2) Root Mean Square Error (RMSE)

**Definition (spatial RMSE).**

\[
\mathrm{RMSE} = \sqrt{\left\langle \bigl(f - o\bigr)^2 \right\rangle_D }
\]

This is evaluated per time/lead (and for ensemble members and ensemble mean). Implementation: `calc_rmse_vec` and used within deterministic scoring. :contentReference[oaicite:2]{index=2}

---

### 3) Index ACC and RMSE (e.g., ENSO / IOD)

For scalar indices (time series) the system computes:
- Pearson correlation (ACC for indices):

\[
\mathrm{ACC_{index}} = \frac{\sum_{t} (f_t - \bar f)(o_t - \bar o)}{\sqrt{\sum_t (f_t - \bar f)^2}\sqrt{\sum_t (o_t - \bar o)^2}}
\]

- Time-series RMSE:

\[
\mathrm{RMSE_{index}} = \sqrt{\frac{1}{T}\sum_{t} (f_t - o_t)^2}
\]

These are implemented in the index module (`calc_index_skill`) and index generation (`calcIndices.py`). :contentReference[oaicite:3]{index=3}

---

### 4) Probabilistic metrics — Tercile framework

#### a) Tercile categorization (thresholds)
- For variables assumed Gaussian-like (e.g., T2M), deterministic thresholds are computed as ±0.43 times the monthly standard deviation (\(\sigma\)). Thus:

\[
\text{lower threshold} = -0.43\,\sigma,\qquad \text{upper threshold} = +0.43\,\sigma
\]

- For precipitation the code uses **empirical quantiles** (33rd and 67th percentiles) computed from climatology files. Implementation: `categorizeTercile.py` (`_load_thresholds`, `categorize_obs_tercile`). :contentReference[oaicite:4]{index=4}

#### b) Probabilities from ensemble
Given ensemble forecasts \(f_m(\mathbf{x},t)\), the predicted probability for category \(k\) is:

\[
p_k(\mathbf{x},t) = \frac{1}{N}\sum_{m=1}^{N} \mathbf{1}\bigl(f_m(\mathbf{x},t)\ \text{in category }k\bigr)
\]

where \(\mathbf{1}(\cdot)\) is the indicator function. The code computes `prob_bn`, `prob_nn`, `prob_an` via ensemble-member counting. Implementation: `categorize_fcst_tercile_prob`. :contentReference[oaicite:5]{index=5}

---

### 5) Ranked Probability Score (RPS) and Ranked Probability Skill Score (RPSS)

**RPS (for a single grid point / time):**  
Let cumulative forecast probabilities for category thresholds be \(F_j = \sum_{k=1}^{j} p_k\) and cumulative observed vector \(O_j\) be the one-hot cumulative (0/1 cumulative). Then

\[
\mathrm{RPS} = \sum_{j=1}^{K} \bigl(F_j - O_j\bigr)^2.
\]

The implementation uses cumulative probabilities across the tercile categories. See `compute_rps_manual`. :contentReference[oaicite:6]{index=6}

**RPSS (ranked probability skill score) relative to a reference (here climatology):**

\[
\mathrm{RPSS} = 1 - \frac{\mathrm{RPS}}{\mathrm{RPS}_{\mathrm{clim}}}
\]

In the code, the climatology is taken as the uniform tercile distribution \(\{1/3,1/3,1/3\}\) for global RPSS computation. See `compute_rpss_manual`. :contentReference[oaicite:7]{index=7}

---

### 6) ROC curve / AUC (per category vs rest)

For each category \(k\), the forecast probability \(p_k\) is treated as a score and a binary ROC is constructed against the one-hot observed category indicator. The Area Under the ROC Curve (AUC) summarizes discrimination ability:

- Compute False Positive Rate (FPR) and True Positive Rate (TPR) at thresholds; integrate TPR over FPR to obtain AUC. Implementation: `compute_roc_auc_all_categories` which computes per-lead, per-category AUC and saves ROC records. :contentReference[oaicite:8]{index=8}

---

### 7) Multi-category deterministic verification (Hit rate / Accuracy, Heidke Skill Score)

When forecasts are converted to deterministic tercile categories (BN=0, NN=1, AN=2), verification uses contingency-table based metrics:

- Let \(C\) be the contingency matrix where \(C_{ij}\) counts occurrences observed in category \(i\) and forecast in category \(j\).  
- Total sample size: \(T=\sum_{i,j} C_{ij}\).  
- Hits (correct forecasts): \(H = \sum_i C_{ii}\).  
- **Accuracy (Hit Rate)**:

\[
\mathrm{ACC}_{\text{cat}} = \frac{H}{T}
\]

- **Heidke Skill Score (HSS):**

\[
\mathrm{HSS} = \frac{H - E}{T - E},\qquad E = \sum_{i} \frac{(\sum_j C_{ij})(\sum_j C_{ji})}{T}
\]

where \(E\) is the expected number of correct forecasts by chance (computed from row and column marginals). Implementation: `compute_multicategory_scores` in `verifyCategory.py` constructs the \(3\times3\) table and computes `acc` and `hss`. :contentReference[oaicite:9]{index=9}

---

### 8) Practical implementation notes & edge cases

- **Time alignment**: forecasts and observations are selected on common times before metric computation; missing-observations for certain target months are logged and skipped. See the deterministic / probabilistic modules for `common_times` handling. fileciteturn0file0:contentReference[oaicite:10]{index=10}
- **Masking**: regional/global masks (e.g., ocean masks for SST) are applied prior to spatial averaging. See mask usage in deterministic / probabilistic workflows. fileciteturn0file0:contentReference[oaicite:11]{index=11}
- **Numerical safety**: a small constant (`1e-12`) is added to the ACC denominator in the deterministic implementation to avoid divide-by-zero. :contentReference[oaicite:12]{index=12}
- **RPSS reference**: RPSS is computed against a climatological reference; the current implementation uses a uniform tercile climatology when computing global RPSS. See `compute_rpss_manual`. :contentReference[oaicite:13]{index=13}

---

### 9)
