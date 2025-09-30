# 📘 Guidance 
# Real-time Seasonal Forecast Verification System


##  Project Overview

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
conda install -c conda-forge xarray dask[complete] xskillscore climpred xesmf cfgrib pygrib matplotlib cartopy streamlit pandas numpy scikit-learn Pillow streamlit
```

---

# Verification metrics 
## Mathematical definitions & implementation notes

This section documents the mathematical formulas used by the verification system and points to where each metric is implemented in the analysis code.

### Notation
- $f(\mathbf{x},\mathbf{y}, t)$ : forecast field (ensemble member or ensemble mean) at spatial location $\mathbf{x}$(longitude), $\mathbf{y}$(latitude), and time $t$.  
  _ASCII fallback:_ `f(x,y,t)`

- $o(\mathbf{x}, \mathbf{y}, t)$ : observation field at location $\mathbf{x}$(longitude), $\mathbf{y}$(latitude), and time $t$.  
  _ASCII fallback:_ `o(x,y,t)`

- Spatial/domain average over domain $D$ is denoted $\langle \cdot \rangle_D$.  
  _ASCII fallback:_ `< ... >_D`

- Ensemble members are indexed $m=1,\dots,N$, and the ensemble mean is
  $$
  \bar f(\mathbf{x},\mathbf{y},t) \;=\; \frac{1}{N}\sum_{m=1}^N f_m(\mathbf{x},\mathbf{y},t).
  $$
  _ASCII fallback:_ `f_bar(x,t) = (1/N) * sum_{m=1..N} f_m(x,t)`

- Time series (indices) use discrete time $t=1,\dots,T$ where needed.  
  _ASCII fallback:_ `t = 1..T`


### 1) Anomaly Correlation Coefficient (ACC)

**LaTeX (display):**

$$
\mathrm{ACC} \;=\; \frac{\langle f \cdot o \rangle_D}
{\sqrt{\langle f^2 \rangle_D}\,\sqrt{\langle o^2 \rangle_D} \;+\; \varepsilon}
$$

**ASCII (no-LaTeX):**  
ACC = ( < f * o >_D ) / ( sqrt(< f^2 >_D) * sqrt(< o^2 >_D) + eps )

---

### 2) Root Mean Square Error (RMSE)

**LaTeX (display):**

$$
\mathrm{RMSE} \;=\; \sqrt{ \bigl\langle \bigl(f - o\bigr)^2 \bigr\rangle_D }.
$$

**ASCII:**  
RMSE = sqrt( < (f - o)^2 >_D )

---

### 3) Index (time-series) correlation and RMSE

For scalar indices \(f_t\) and \(o_t\) over times \(t=1\ldots T\):

**Pearson correlation (index ACC):**
$$
\mathrm{ACC_{index}} = \frac{\sum_{t}(f_t-\bar f)(o_t-\bar o)}
{\sqrt{\sum_{t}(f_t-\bar f)^2}\sqrt{\sum_{t}(o_t-\bar o)^2} }.
$$

**Index RMSE:**
$$
\mathrm{RMSE_{index}} = \sqrt{\frac{1}{T}\sum_{t}(f_t - o_t)^2 }.
$$

---

### 4) Tercile categorization & ensemble probability

- **Tercile thresholds**: either empirical quantiles (33%, 67%) from climatology or fixed fraction of std (e.g., \(\pm0.43\sigma\)) depending on variable.

- **Ensemble probability for category \(k\):**
$$
p_k(\mathbf{x},t) \;=\; \frac{1}{N}\sum_{m=1}^{N} \mathbf{1}\{ f_m(\mathbf{x},t)\in \text{category }k\},
$$
where \(\mathbf{1}\{\cdot\}\) is the indicator function.

**ASCII:**  
p_k = (1/N) * sum_{m=1..N} 1{ f_m in category k }

---

### 5) Ranked Probability Score (RPS) & Ranked Probability Skill Score (RPSS)

- Let cumulative forecast probabilities be \(F_j = \sum_{k=1}^{j} p_k\) for \(j=1,\dots,K\).  
- Let cumulative observed vector \(O_j\) be the cumulative one-hot (0 or 1).

**RPS (single case / gridpoint):**
$$
\mathrm{RPS} = \sum_{j=1}^{K} (F_j - O_j)^2.
$$

**RPSS (relative to reference RPS\(_{\mathrm{ref}}\), e.g., climatology):**
$$
\mathrm{RPSS} = 1 - \frac{\mathrm{RPS}}{\mathrm{RPS}_{\mathrm{ref}}}.
$$

**ASCII:**  
RPS = sum_{j=1..K} (F_j - O_j)^2  
RPSS = 1 - RPS / RPS_ref

---

### 6) ROC / AUC (per category vs rest)

For category \(k\), treat \(p_k\) as classifier score and the binary observation \(y_k = 1\) if observed category is \(k\), else 0. Compute TPR and FPR across thresholds and integrate to get AUC.

**Notes (implementation):** use ranked thresholds on \(p_k\) or library routines (scikit-learn `roc_auc_score`) after flattening over samples.

---

### 7) Contingency-table metrics (accuracy, Heidke Skill Score)

Let contingency matrix \(C\) be \(K\times K\) with \(C_{ij}\) = count(obs = i, fcst = j). Total samples \(T=\sum_{i,j} C_{ij}\). Correct hits \(H=\sum_i C_{ii}\).

- **Accuracy (categorical hit rate):**
$$
\text{Accuracy} = \frac{H}{T}.
$$

- **Heidke Skill Score (HSS):**
First compute expected correct by chance
$$
E = \sum_{i=1}^K \frac{\left(\sum_j C_{ij}\right)\left(\sum_j C_{ji}\right)}{T},
$$
then
$$
\mathrm{HSS} = \frac{H - E}{T - E}.
$$

**ASCII:**  
Accuracy = H / T  
E = sum_i (row_i_sum * col_i_sum) / T  
HSS = (H - E) / (T - E)

---