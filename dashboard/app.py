import os, sys
from datetime import datetime

import streamlit as st
st.set_page_config(layout="wide")

# ✅ project root
# default is './' in Streamlit Cloud
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from fcstverif.config import year_start, year_end, REGIONS, model

# ✅ GitHub base raw URL
GITHUB_RAW_BASE = "https://raw.githubusercontent.com/gkim-TB/FcstVerif2025/main"

def get_fig_url(model, region, var, filename):
    return f"{GITHUB_RAW_BASE}/FIG/{model}/{region}/{var}/{filename}"

# ──────────────────────────────────────────────
st.set_page_config(layout="wide")
#st.title("Seasonal Forecast Verification Dashboard")

# ✅ Mapping for file names per plot type
PLOT_FILENAME_MAP = {
    #"init_line":      [f"acc_targetSeries_byInit_{{var}}_{{region}}_{year_start}_{year_end}.png"],
    "ACC_byInit":    ["acc_init_{var}_{region}_{yyyymm}.png"],
    "RMSE_byInit":   ["rmse_init_{var}_{region}_{yyyymm}.png"],
    "ACC_byTarget":  ["acc_target_{var}_{region}_{yyyymm}.png"],
    "RMSE_byTarget": ["rmse_target_{var}_{region}_{yyyymm}.png"],
    "Bias_byTarget": ["{var}_pattern_compare_{region}_{yyyymm}.png"],
    "RPSS_byInit":   ["rpss_map_{var}_{region}_{yyyymm}.png"],
    "ROC_byInit":    ["roc_curve_by_lead_{var}_{region}_{yyyymm}.png"],
    #"init_heatmap":   [f"acc_heatmap_init_{{var}}_{{region}}_{{year_only}}.png"],
    #"cate_heatmap":   ["det_ter_score_{var}_{region}_{year}.png"]
}

def get_image_urls(plot_type, var, region, yyyymm=None, year=None, year_only=None):
    templates = PLOT_FILENAME_MAP.get(plot_type, [])
    urls = []
    for tmpl in templates:
        fname = tmpl.format(var=var, region=region, yyyymm=yyyymm, year=year, year_only=year_only)
        url = get_fig_url(model, region, var, fname)
        urls.append((fname, url))
    return urls

# ───────────────────────────────────────────────────────────────

# 사이드바: '탭처럼' 사용될 라디오 버튼
tab_selection = st.sidebar.radio("무엇을 보고 싶으신가요?", ["📊 Overview", "🖼️ Detailed Plots"])

# 탭 선택에 따라 사이드바 옵션 바꾸기
var = st.sidebar.selectbox("변수 선택:", ['t2m','prcp','sst'])
region = st.sidebar.selectbox("지역 선택:", list(REGIONS.keys()))

if tab_selection == "📊 Overview":
    selected_year = st.sidebar.selectbox("연도 선택:", list(range(year_start, year_end+1)))
else:  # Detailed
    selected_year_int = st.sidebar.selectbox("Forecast Year:", list(range(year_start, year_end+1)))
    selected_month_int = st.sidebar.selectbox("Forecast Month:", list(range(1,13)))
    selected_yyyymm = f"{selected_year_int}{selected_month_int:02d}"
    plot_types = list(PLOT_FILENAME_MAP.keys())
    selected_plots = st.sidebar.multiselect("시각화 선택:", plot_types)

# ───────────────────────────────────────────────────────────────
if tab_selection == "📊 Overview":
    st.header("📊 Key Metrics Overview")
    cols = st.columns(2)
    with cols[0]:
        st.image(get_fig_url(model, region, var,
            f"acc_targetSeries_byInit_{var}_{region}_{year_start}_{year_end}.png"),
            caption="ACC TargetSeries by Init", use_container_width=True)
    with cols[1]:
        st.image(get_fig_url(model, region, var,
            f"acc_heatmap_init_{var}_{region}_{selected_year}.png"),
            caption=f"ACC Init Heatmap ({selected_year})", use_container_width=True)

else:  # Detailed Plots
    st.header("🖼️ Detailed Plots")
    cols = st.columns(2)
    i = 0
    for plot_type in selected_plots:
        for fname, url in get_image_urls(plot_type, var, region, yyyymm=selected_yyyymm):
            with cols[i % 2]:
                st.subheader(f"{plot_type} – {fname}")
                st.image(url, caption=fname, use_container_width=True)
            i += 1


# # ──────────────────────────────────────────────
# # Sidebar
# variables = ['t2m', 'prcp', 'sst']
# st.sidebar.title("Seasonal Forecast Verification Dashboard")
# st.sidebar.markdown("Use the options below to customize plots")
# var = st.sidebar.selectbox("Select variable:", variables)
# region = st.sidebar.selectbox("Select region:", list(REGIONS.keys()))

# # Forecast date mode
# date_mode = st.sidebar.radio("Select forecast date mode:", ["Range", "Single"])
# start_date = datetime(year_start, 1, 1)
# end_date = datetime(year_end, 12, 1)

# if date_mode == "Range":
#     date_range = st.sidebar.slider("Forecast date range:", min_value=start_date, max_value=end_date,
#                                    value=(datetime(2022, 1, 1), datetime(2024, 12, 1)), format="YYYY.MM")
#     selected_start = date_range[0].strftime("%Y%m")
#     selected_end = date_range[1].strftime("%Y%m")
#     selected_years = list(range(date_range[0].year, date_range[1].year + 1))
#     selected_year = str(date_range[0].year)
#     selected_year_only = str(date_range[0].year)
# else:
#     selected_year_int = st.sidebar.selectbox("Select forecast year:", list(range(year_start, year_end + 1)))
#     selected_month_int = st.sidebar.selectbox("Select forecast month:", list(range(1, 13)))
#     single_date = datetime(selected_year_int, selected_month_int, 1)
#     selected_start = single_date.strftime("%Y%m")
#     selected_end = selected_start
#     selected_year = str(single_date.year)
#     selected_year_only = str(single_date.year)
#     selected_years = [single_date.year]

# # Plot type selection
# plot_types = list(PLOT_FILENAME_MAP.keys())
# selected_plots = st.sidebar.multiselect("Select plot types to view:", plot_types, default=[])

# # ──────────────────────────────────────────────
# tab1, tab2 = st.tabs(["📊 Key Metrics Overview", "🖼️ Detailed Plots by month"])

# with tab1:
#     #st.markdown("## Key Metrics Overview")

#     # First row: init_line (target series)
#     st.markdown("#### ACC TimeSeries by Init")
#     for fname, url in get_image_urls("init_line", var, region):
#         st.image(url, caption=fname, use_container_width=True)

#     # Second row: yearly heatmaps (init_heatmap)
#     st.markdown("#### ACC Heatmap")
#     heatmap_cols = st.columns(len(selected_years))
#     for i, y in enumerate(selected_years):
#         fname = f"acc_heatmap_init_{var}_{region}_{y}.png"
#         url = get_fig_url(model, region, var, fname)
#         with heatmap_cols[i]:
#             st.image(url, caption=fname, use_container_width=True)

#     # Third row: cate_heatmap (for t2m, prcp only)
#     if var in ["t2m", "prcp"]:
#         st.markdown("#### Deterministic Tercile Heatmap")
#         cate_cols = st.columns(len(selected_years))
#         for i, y in enumerate(selected_years):
#             fname = f"det_ter_score_{var}_{region}_{y}.png"
#             url = get_fig_url(model, region, var, fname)
#             with cate_cols[i]:
#                 st.image(url, caption=fname, use_container_width=True)

# # ──────────────────────────────────────────────
# # Detailed selected plots
# with tab2:
#     #st.markdown("## Detailed Plots")
#     cols = st.columns(2)
#     i = 0
#     for plot_type in selected_plots:
#         if plot_type in ["ACC_byInit", "ACC_byTarget", "Bias_byTarget", "RPSS_byInit", "ROC_byInit"]:
#             for fname, url in get_image_urls(plot_type, var, region, yyyymm=selected_start):
#                 with cols[i % 2]:
#                     #st.subheader(f"{plot_type} - {fname}")
#                     st.image(url, caption=fname, use_container_width=True)
#                 i += 1
#         else:
#             for fname, url in get_image_urls(plot_type, var, region):
#                 with cols[i % 2]:
#                     #st.subheader(f"{plot_type} - {fname}")
#                     st.image(url, caption=fname, use_container_width=True)
#                 i += 1
