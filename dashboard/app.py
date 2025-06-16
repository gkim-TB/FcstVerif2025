import streamlit as st
import os, sys
from datetime import datetime
from fcstverif.config import year_start, year_end, REGIONS, model

# ✅ project root
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
    
# ✅ GitHub base raw URL
GITHUB_RAW_BASE = "https://raw.githubusercontent.com/gkim-TB/FcstVerif2025/main"

def get_fig_url(model, region, var, filename):
    return f"{GITHUB_RAW_BASE}/FIG/{model}/{region}/{var}/{filename}"

# ──────────────────────────────────────────────
st.set_page_config(layout="wide")
st.title("Seasonal Forecast Verification Dashboard")

# ✅ Mapping for file names per plot type
PLOT_FILENAME_MAP = {
    "init_line":      [f"acc_targetSeries_byInit_{{var}}_{{region}}_{year_start}_{year_end}.png"],
    "target_month":   ["acc_target_{var}_{region}_{yyyymm}.png", "rmse_target_{var}_{region}_{yyyymm}.png"],
    "target_pattern": ["{var}_pattern_compare_{region}_{yyyymm}.png"],
    "target_line":    ["acc_init_{var}_{region}_{yyyymm}.png", "rmse_init_{var}_{region}_{yyyymm}.png"],
    "rpss_map":       ["rpss_map_{var}_{region}_{yyyymm}.png"],
    "roc_curve":      ["roc_curve_by_lead_{var}_{region}_{yyyymm}.png"],
    "init_heatmap":   [f"acc_heatmap_init_{{var}}_{{region}}_{{year_only}}.png"],
    "cate_heatmap":   ["det_ter_score_{var}_{region}_{year}.png"]
}

def get_image_urls(plot_type, var, region, yyyymm=None, year=None, year_only=None):
    templates = PLOT_FILENAME_MAP.get(plot_type, [])
    urls = []
    for tmpl in templates:
        fname = tmpl.format(var=var, region=region, yyyymm=yyyymm, year=year, year_only=year_only)
        url = get_fig_url(model, region, var, fname)
        urls.append((fname, url))
    return urls

# ──────────────────────────────────────────────
# Sidebar
variables = ['t2m', 'prcp', 'sst']
var = st.sidebar.selectbox("Select variable:", variables)
region = st.sidebar.selectbox("Select region:", list(REGIONS.keys()))

# Forecast date mode
date_mode = st.sidebar.radio("Select forecast date mode:", ["Range", "Single"])
start_date = datetime(year_start, 1, 1)
end_date = datetime(year_end, 12, 1)

if date_mode == "Range":
    date_range = st.sidebar.slider("Forecast date range:", min_value=start_date, max_value=end_date,
                                   value=(datetime(2022, 1, 1), datetime(2024, 12, 1)), format="YYYY.MM")
    selected_start = date_range[0].strftime("%Y%m")
    selected_end = date_range[1].strftime("%Y%m")
    selected_years = list(range(date_range[0].year, date_range[1].year + 1))
    selected_year = str(date_range[0].year)
    selected_year_only = str(date_range[0].year)
else:
    selected_year_int = st.sidebar.selectbox("Select forecast year:", list(range(year_start, year_end + 1)))
    selected_month_int = st.sidebar.selectbox("Select forecast month:", list(range(1, 13)))
    single_date = datetime(selected_year_int, selected_month_int, 1)
    selected_start = single_date.strftime("%Y%m")
    selected_end = selected_start
    selected_year = str(single_date.year)
    selected_year_only = str(single_date.year)
    selected_years = [single_date.year]

# Plot type selection
plot_types = list(PLOT_FILENAME_MAP.keys())
selected_plots = st.sidebar.multiselect("Select plot types to view:", plot_types, default=[])

# ──────────────────────────────────────────────
st.markdown("## Key Metrics Overview")

# First row: init_line (target series)
st.markdown("#### ACC Target Series by Init")
for fname, url in get_image_urls("init_line", var, region):
    st.image(url, caption=fname, use_container_width=True)

# Second row: yearly heatmaps (init_heatmap)
st.markdown("#### ACC Init Heatmap by Year")
heatmap_cols = st.columns(len(selected_years))
for i, y in enumerate(selected_years):
    fname = f"acc_heatmap_init_{var}_{region}_{y}.png"
    url = get_fig_url(model, region, var, fname)
    with heatmap_cols[i]:
        st.image(url, caption=fname, use_container_width=True)

# Third row: cate_heatmap (for t2m, prcp only)
if var in ["t2m", "prcp"]:
    st.markdown("#### Deterministic Tercile Heatmap")
    cate_cols = st.columns(len(selected_years))
    for i, y in enumerate(selected_years):
        fname = f"det_ter_score_{var}_{region}_{y}.png"
        url = get_fig_url(model, region, var, fname)
        with cate_cols[i]:
            st.image(url, caption=fname, use_container_width=True)

# ──────────────────────────────────────────────
# Detailed selected plots
st.markdown("## Detailed Plots")
cols = st.columns(2)
i = 0
for plot_type in selected_plots:
    if plot_type in ["target_month", "target_pattern", "target_line", "rpss_map", "roc_curve"]:
        for fname, url in get_image_urls(plot_type, var, region, yyyymm=selected_start):
            with cols[i % 2]:
                st.subheader(f"{plot_type} - {fname}")
                st.image(url, caption=fname, use_container_width=True)
            i += 1
    elif plot_type == "init_heatmap":
        for y in selected_years:
            fname = f"acc_heatmap_init_{var}_{region}_{y}.png"
            url = get_fig_url(model, region, var, fname)
            with cols[i % 2]:
                st.subheader(f"{plot_type} - {fname}")
                st.image(url, caption=fname, use_container_width=True)
            i += 1
    elif plot_type == "cate_heatmap" and var in ["t2m", "prcp"]:
        for y in selected_years:
            fname = f"det_ter_score_{var}_{region}_{y}.png"
            url = get_fig_url(model, region, var, fname)
            with cols[i % 2]:
                st.subheader(f"{plot_type} - {fname}")
                st.image(url, caption=fname, use_container_width=True)
            i += 1
    else:
        for fname, url in get_image_urls(plot_type, var, region):
            with cols[i % 2]:
                st.subheader(f"{plot_type} - {fname}")
                st.image(url, caption=fname, use_container_width=True)
            i += 1
