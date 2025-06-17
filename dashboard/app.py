import os, sys
from datetime import datetime
from dateutil.relativedelta import relativedelta

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

def get_yyyymm_for_plot(plot_type, selected_yyyymm):
    dt = datetime.strptime(selected_yyyymm, "%Y%m")
    if "byTarget" in plot_type:
        dt += relativedelta(months=1)
    return dt.strftime("%Y%m")

# ──────────────────────────────────────────────
#st.set_page_config(layout="wide")
#st.title("Seasonal Forecast Verification Dashboard")

plot_types = [
    "ACC_byTarget",
    "RMSE_byTarget"
    "ACC_byInit",
    "RMSE_byInit",
    "Bias_byTarget",
    "RPSS_byInit",
    "ROC_byInit"
]
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
st.sidebar.title("Seasonal Forecast Verification Dashboard")
st.sidebar.markdown("Use the options below to customize plots")

# tab selection radio button
tab_selection = st.sidebar.radio("Select Mode:", ["📊 Overview", "🖼️ Detailed Plots", "📈 Indices"])

var = st.sidebar.selectbox("Select variables:", ['t2m','prcp','sst'])
region = st.sidebar.selectbox("Select region:", list(REGIONS.keys()))

# 탭 선택에 따라 사이드바 옵션 바꾸기
if tab_selection == "📊 Overview":
    selected_year = st.sidebar.selectbox("Select Year:", list(range(year_start, year_end+1)))
elif tab_selection == "📈 Indice":
    st.sidebar.markdown("Select options for Indices")
    
elif tab_selection == "🖼️ Detailed Plots":  # Detailed
    selected_year_int = st.sidebar.selectbox("Forecast Year:", list(range(year_start, year_end+1)))
    selected_month_int = st.sidebar.selectbox("Forecast Month:", list(range(1,13)))
    selected_yyyymm = f"{selected_year_int}{selected_month_int:02d}"
    plot_types = list(PLOT_FILENAME_MAP.keys())
    selected_plots = st.sidebar.multiselect("Select Plot:", plot_types, default=plot_types)

st.sidebar.markdown("---")
st.sidebar.markdown(
    """
    <div style='font-size: 13px; text-align: center;'>
        Made with P;ㅜ by <b>Gaeun Kim</b> 
        @ APCC Testbed Team<br>
        📧 <a href='mailto:gkim@apcc21.org'>gkim@apcc21.org</a><br>
        🔗 <a href='https://github.com/gkim-TB' target='_blank'>GitHub: gkim-TB</a>
    </div>
    """, unsafe_allow_html=True
)
# ───────────────────────────────────────────────────────────────
if tab_selection == "📊 Overview":
    st.header("📊 Key Metrics Overview")

    st.image(get_fig_url(model, region, var,
        f"acc_targetSeries_byInit_{var}_{region}_{year_start}_{year_end}.png"),
        caption="ACC TargetSeries by Init", use_container_width=True)

    cols = st.columns(2)
    with cols[0]:
        st.image(get_fig_url(model, region, var,
            f"acc_heatmap_init_{var}_{region}_{selected_year}.png"),
            caption=f"ACC Init Heatmap ({selected_year})", use_container_width=True)
    with cols[1]:
        st.image(get_fig_url(model, region, var,
            f"det_ter_score_{var}_{region}_{selected_year}.png"),
            caption=f"Deterministic Tercile Score ({selected_year})")
        
elif tab_selection == "🖼️ Detailed Plots":  # Detailed Plots
    st.header("🖼️ Detailed Plots")
    cols = st.columns(2)
    i = 0
    for plot_type in selected_plots:
        yyyymm_to_use = get_yyyymm_for_plot(plot_type, selected_yyyymm)
        for fname, url in get_image_urls(plot_type, var, region, yyyymm=yyyymm_to_use):
            with cols[i % 2]:
                #st.subheader(f"{plot_type} – {fname}")
                st.image(url, caption=fname, use_container_width=True)
            i += 1

else:
    #st.header("🔧Under development...")
    st.markdown("""
    <div style='text-align: center; padding-top: 100px;'>
        <h1 style='font-size: 60px; color: #8A2BE2; font-weight: bold;'>
            ✨ Bibbidi-Bobbidi-Boo ✨
        </h1>
        <p style='font-size: 20px; color: #555;'>This page is under magical development...</p>
    </div>
    """, unsafe_allow_html=True)

