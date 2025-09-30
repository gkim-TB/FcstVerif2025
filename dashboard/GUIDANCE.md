# 📘 Guidance 
# Real-time Seasonal Forecast Verification System

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

- **Pearson correlation (index ACC)** — for scalar index series $f_t$ and $o_t$ over $t=1,\dots,T$:

  Inline LaTeX:
  $$
  \mathrm{ACC_{index}} \;=\; \frac{\sum_{t=1}^T (f_t-\bar f)(o_t-\bar o)}
  {\sqrt{\sum_{t=1}^T (f_t-\bar f)^2}\;\sqrt{\sum_{t=1}^T (o_t-\bar o)^2}}.
  $$

  ASCII fallback:  
  `ACC_index = sum_t (f_t - f_bar)(o_t - o_bar) / ( sqrt(sum_t (f_t - f_bar)^2) * sqrt(sum_t (o_t - o_bar)^2) )`

- **Index RMSE**:

  Inline LaTeX:
  $$
  \mathrm{RMSE_{index}} \;=\; \sqrt{\frac{1}{T}\sum_{t=1}^T (f_t - o_t)^2 }.
  $$

  ASCII fallback:  
  `RMSE_index = sqrt( (1/T) * sum_t (f_t - o_t)^2 )`


---

### 4) Tercile categorization & ensemble probability

- **Tercile thresholds**: use empirical quantiles (33%, 67%) from climatology or fixed fraction of standard deviation (e.g., $\pm 0.43\sigma$) depending on variable.

  ASCII fallback:  
  `thresholds = { lower = 33rd percentile, upper = 67th percentile }  OR  { -0.43*sigma, +0.43*sigma }`

- **Ensemble probability for category $k$** (ensemble members $m=1..N$):

  Inline LaTeX:
  $$
  p_k(\mathbf{x},t) \;=\; \frac{1}{N}\sum_{m=1}^{N} \mathbf{1}\{ f_m(\mathbf{x},t)\in \text{category }k\},
  $$

  ASCII fallback:  
  `p_k(x,t) = (1/N) * sum_{m=1..N} 1{ f_m(x,t) in category k }`


---

### 5) Ranked Probability Score (RPS) & Ranked Probability Skill Score (RPSS)

- Define cumulative forecast probabilities $F_j = \sum_{k=1}^{j} p_k$ for $j=1,\dots,K$, and cumulative observed vector $O_j$ (0/1 cumulative).

- **RPS (per case / gridpoint)**:

  Inline LaTeX:
  $$
  \mathrm{RPS} \;=\; \sum_{j=1}^{K} \bigl(F_j - O_j\bigr)^2.
  $$

  ASCII fallback:  
  `RPS = sum_{j=1..K} ( F_j - O_j )^2`

- **RPSS (relative to reference RPS_ref, e.g., climatology)**:

  Inline LaTeX:
  $$
  \mathrm{RPSS} \;=\; 1 \;-\; \frac{\mathrm{RPS}}{\mathrm{RPS}_{\mathrm{ref}}}.
  $$

  ASCII fallback:  
  `RPSS = 1 - RPS / RPS_ref`


---

### 6) ROC / AUC (per category vs rest)

- For each category $k$, define binary observation $y^{(k)} = 1$ if observed category is $k$, else $0$. Use forecast probability $p_k$ as score.

- Compute TPR (true positive rate) and FPR (false positive rate) across decision thresholds $\tau$ and integrate the ROC curve to obtain AUC:

  Inline (conceptual):
  $$
  \mathrm{AUC}_k \;=\; \int_0^1 \mathrm{TPR}_k(\mathrm{FPR})\, d(\mathrm{FPR}).
  $$

  ASCII fallback:  
  `AUC_k = area under ROC curve computed by varying threshold on p_k and plotting TPR vs FPR`

- **Implementation note:** flatten samples over time/space as configured, or compute per-region/time-window then aggregate. Use library routine (e.g., `sklearn.metrics.roc_auc_score`) where available.


---

### 7) Contingency-table metrics (accuracy, Heidke Skill Score)

- Build contingency matrix $C$ of size $K\times K$ where $C_{ij}$ = count(obs = i, fcst = j). Total samples $T=\sum_{i,j} C_{ij}$.

- **Accuracy (categorical hit rate)**:
  
  Inline LaTeX:
  $$
  \text{Accuracy} \;=\; \frac{\sum_{i=1}^K C_{ii}}{T}.
  $$

  ASCII fallback:  
  `Accuracy = H / T   where H = sum_i C_{ii}`

- **Heidke Skill Score (HSS)**:
  
  Expected correct by chance:
  $$
  E \;=\; \sum_{i=1}^K \frac{\left(\sum_{j=1}^K C_{ij}\right)\left(\sum_{j=1}^K C_{ji}\right)}{T}.
  $$

  HSS:
  $$
  \mathrm{HSS} \;=\; \frac{\sum_{i=1}^K C_{ii} - E}{T - E}.
  $$

  ASCII fallback:  
  `E = sum_i ( row_sum_i * col_sum_i ) / T`  
  `HSS = (H - E) / (T - E)`

---