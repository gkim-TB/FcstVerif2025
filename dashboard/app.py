import streamlit as st
import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from PIL import Image
from datetime import datetime

from fcstverif.config import year_start, year_end, REGIONS, model

st.set_page_config(layout="wide")
st.title("Seasonal Forecast Verification Dashboard")

# ✅ Mapping for file names per plot type
PLOT_FILENAME_MAP = {
    "init_line":      [f"acc_targetSeries_byInit_{{var}}_{{region}}_{year_start}_{year_end}.png", f"rmse_targetSeries_byInit_{{var}}_{{region}}_{{year}}.png"],
    #"init_heatmap":   ["acc_heatmap_init_{var}_{region}_{year_only}.png", "rmse_heatmap_init_{var}_{region}_{year_only}.png"],
    "target_month":   ["acc_target_{var}_{region}_{yyyymm}.png", "rmse_target_{var}_{region}_{yyyymm}.png"],
    "target_pattern": ["{var}_pattern_compare_{region}_{yyyymm}.png"],
    "target_line":    ["acc_init_{var}_{region}_{yyyymm}.png", "rmse_init_{var}_{region}_{yyyymm}.png"],
    #"cate_heatmap":   ["det_ter_score_{var}_{region}.png"],
    "rpss_map":       ["rpss_map_{var}_{region}_{yyyymm}.png"],
    "roc_curve":      ["roc_curve_by_lead_{var}_{region}_{yyyymm}.png"],
}

def get_image_paths(plot_type, var, region, yyyymm=None, year=None, year_only=None):
    fname_templates = PLOT_FILENAME_MAP.get(plot_type, [])
    fig_paths = []
    for tmpl in fname_templates:
        fname = tmpl.format(var=var, region=region, yyyymm=yyyymm, year=year, year_only=year_only)
        fig_path = os.path.join("..","FIG", region, var, fname)
        fig_paths.append((os.path.basename(fname), fig_path))
    return fig_paths

# Sidebar selections
variables = ['t2m','prcp','sst']
var = st.sidebar.selectbox("Select variable:", variables)
region = st.sidebar.selectbox("Select region:", list(REGIONS.keys()))

# Forecast date control type
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
selected_plots = st.sidebar.multiselect("Select plot types to view:", plot_types, default=[])  # ✅ 기본값 비워둠

# ✅ Landing page 기본 시각화 (first row: init_line, second row: init_heatmap by year)
st.markdown("## Key Metrics Overview")

# First row: fixed targetSeries_byInit
st.markdown("<h4 style='font-size:20px;'>ACC Target Series by Init</h4>", unsafe_allow_html=True)
fname = f"acc_targetSeries_byInit_{var}_{region}_{year_start}_{year_end}.png"
fig_path = os.path.join("..","FIG", region, var, fname)
if os.path.isfile(fig_path):
    st.image(Image.open(fig_path), caption=fname, use_container_width=True)
else:
    st.warning(f"Image not found: {fig_path}")

# Second row: yearly heatmaps side by side
st.markdown("<h4 style='font-size:20px;'>ACC Init Heatmap by Year</h4>", unsafe_allow_html=True)
heatmap_cols = st.columns(len(selected_years))
for i, y in enumerate(selected_years):
    fname = f"acc_heatmap_init_{var}_{region}_{y}.png"
    fig_path = os.path.join("..","FIG", region, var, fname)
    with heatmap_cols[i]:
        if os.path.isfile(fig_path):
            st.image(Image.open(fig_path), caption=fname, use_container_width=True)
        else:
            st.warning(f"Image not found: {fig_path}")

# Third row: cate_heatmap if applicable
if var in ["t2m", "prcp"]:
    st.markdown("<h4 style='font-size:20px;'>Deterministic Tercile Heatmap</h4>", unsafe_allow_html=True)
    cate_cols = st.columns(len(selected_years))
    for i, y in enumerate(selected_years):
        fname = f"det_ter_score_{var}_{region}_{y}.png"
        fig_path = os.path.join("..","FIG", region, var, fname)
        with cate_cols[i]:
            if os.path.isfile(fig_path):
                st.image(Image.open(fig_path), caption=fname, use_container_width=True)
            else:
                st.warning(f"Image not found: {fig_path}")

# Display selected images
st.markdown("## Detailed Plots")
cols = st.columns(2)
i = 0
for plot_type in selected_plots:
    if plot_type in ["target_month", "target_pattern", "target_line", "rpss_map", "roc_curve"]:
        for caption, img_path in get_image_paths(plot_type, var, region, yyyymm=selected_start):
            with cols[i % 2]:
                st.subheader(f"{plot_type} - {caption}")
                if os.path.isfile(img_path):
                    st.image(Image.open(img_path), caption=caption, use_container_width=True)
                else:
                    st.warning(f"Image not found: {img_path}")
            i += 1
    elif plot_type in ["init_line", "target_month", "target_line"]:
        for caption, img_path in get_image_paths(plot_type, var, region, yyyymm=selected_start, year=selected_year):
            with cols[i % 2]:
                st.subheader(f"{plot_type} - {caption}")
                if os.path.isfile(img_path):
                    st.image(Image.open(img_path), caption=caption, use_container_width=True)
                else:
                    st.warning(f"Image not found: {img_path}")
            i += 1
    elif plot_type == "init_heatmap":
        for y in selected_years:
            caption = f"acc_heatmap_init_{var}_{region}_{y}.png"
            img_path = os.path.join("..","FIG", region, var, fname)
            with cols[i % 2]:
                st.subheader(f"{plot_type} - {caption}")
                if os.path.isfile(img_path):
                    st.image(Image.open(img_path), caption=caption, use_container_width=True)
                else:
                    st.warning(f"Image not found: {img_path}")
            i += 1
    else:
        for caption, img_path in get_image_paths(plot_type, var, region):
            with cols[i % 2]:
                st.subheader(f"{plot_type} - {caption}")
                if os.path.isfile(img_path):
                    st.image(Image.open(img_path), caption=caption, use_container_width=True)
                else:
                    st.warning(f"Image not found: {img_path}")
            i += 1
