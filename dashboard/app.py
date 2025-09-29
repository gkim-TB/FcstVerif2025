from typing import Dict, List, Tuple, Optional
import streamlit as st

import os, sys
from datetime import datetime
from dateutil.relativedelta import relativedelta

# Sidebar configuration
st.set_page_config(layout="wide", initial_sidebar_state='expanded')
st.sidebar.title("Seasonal Forecast Verification Dashboard")

# Guidance page link
GUIDANCE_FILENAMES = ["GUIDANCE.md"]
st.sidebar.markdown(
    '<div style="margin-top:6px;">'
    '<a href="?page=guidance" style="text-decoration:none; font-weight:600;">📘 Guidance page</a>'
    '</div>',
    unsafe_allow_html=True,
)

params = st.experimental_get_query_params()
page = params.get("page", [""])[0]

def render_guidance():
    # app.py와 같은 디렉터리에서 파일 찾기
    base_dir = os.path.dirname(__file__) if "__file__" in globals() else os.getcwd()
    found = False
    for fname in GUIDANCE_FILENAMES:
        fpath = os.path.join(base_dir, fname)
        if os.path.exists(fpath):
            with open(fpath, "r", encoding="utf-8") as f:
                md = f.read()
            # 우측 메인 영역에 마크다운 렌더
            st.header("Guidance")
            st.markdown(md, unsafe_allow_html=True)
            found = True
            break

    if not found:
        st.header("Guidance")
        st.info(
            "GUIDANCE.md 파일을 찾을 수 없습니다. "
            "앱과 동일 경로에 'GUIDANCE.md'를 배치해 주시거나, GUIDANCE_FILENAMES 목록을 수정하세요."
        )

if page == "guidance":
    render_guidance()
    st.stop()
# Guidance page ends here

# ──────────────────────────────────────────────
# Sidebar instructions
import os, sys
from datetime import datetime
from dateutil.relativedelta import relativedelta

st.sidebar.markdown("Use the options below to customize plots")

# ✅ project root
# default is './' in Streamlit Cloud
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from fcstverif.config import fcst_start, fcst_end, REGIONS, model

# ✅ GitHub base raw URL
GITHUB_RAW_BASE: str = "https://raw.githubusercontent.com/gkim-TB/FcstVerif2025/main"

def get_fig_url(model: str, region: str, var: str, filename:str) -> str:
    return f"{GITHUB_RAW_BASE}/FIG/{model}/{region}/{var}/{filename}"

def get_yyyymm_for_plot(plot_type:str, selected_yyyymm:str) -> str:
    dt = datetime.strptime(selected_yyyymm, "%Y%m")
    if "byTarget" in plot_type:
        dt += relativedelta(months=1)
    return dt.strftime("%Y%m")


#st.set_page_config(layout="wide")
#st.title("Seasonal Forecast Verification Dashboard")

# ✅ Mapping for file names per plot type
PLOT_FILENAME_MAP: Dict[str, List[str]] = {
    "ACC_byInit":    ["acc_init_{var}_{region}_{yyyymm}.png"],
    "RMSE_byInit":   ["rmse_init_{var}_{region}_{yyyymm}.png"],
    "ACC_byTarget":  ["acc_target_{var}_{region}_{yyyymm}.png"],
    "RMSE_byTarget": ["rmse_target_{var}_{region}_{yyyymm}.png"],
    "Bias_byTarget": ["{var}_pattern_compare_{region}_{yyyymm}.png"],
    "RPSS_byInit":   ["rpss_map_{var}_{region}_{yyyymm}.png"],
    "ROC_byInit":    ["roc_curve_by_lead_{var}_{region}_{yyyymm}.png"],
    #"init_heatmap":   [f"det_heatmap_init_{{var}}_{{region}}_{{year_only}}.png"], <- default
    #"cate_heatmap":   ["det_ter_score_{var}_{region}_{year}.png"] <- default
}
# IDX_FILENAME_MAP={
#      "ENSO_index" :   ["ENSO_plum_{yyyymm}.png"],
#      "IOD_index" :    ["IOD_plum_{yyyymm}.png"],
#      "ENSO_hovmoller": ['hovmoller_nino34_{yyyymm}.png'],
#      "IOD_hovmoller": ['hovmoller_iod_{yyyymm}.png'],
# }

def get_image_urls(
        plot_type:str, var:str, region:str, 
        yyyymm: Optional[str] = None, year: Optional[int] = None, year_only: Optional[int]=None
    ) -> List[Tuple[str, str]]:
    templates: List[str] = PLOT_FILENAME_MAP.get(plot_type, [])
    urls: List[Tuple[str, str]] = []
    for tmpl in templates:
        fname = tmpl.format(var=var, region=region, yyyymm=yyyymm, year=year, year_only=year_only)
        url: str = get_fig_url(model, region, var, fname)
        urls.append((fname, url))
    return urls


# tab selection radio button
tab_selection = st.sidebar.radio("Select Mode:", ["📊 Overview", "🖼️ Detailed Plots", "📈 Indices"])

fcst_start_year = fcst_start//100
fcst_end_year = fcst_end//100

# 탭 선택에 따라 사이드바 옵션 바꾸기
if tab_selection == "📊 Overview":
    var = st.sidebar.selectbox("Select variables:", ['t2m','prcp','z500','sst'])
    region = st.sidebar.selectbox("Select region:", list(REGIONS.keys()))

    selected_year = st.sidebar.selectbox("Select Year:", list(range(fcst_start_year, fcst_end_year + 1)))
elif tab_selection == "📈 Indices":
    st.sidebar.markdown("Select options for Indices")
    selected_year_int = st.sidebar.selectbox("Forecast Year:", list(range(fcst_start_year, fcst_end_year + 1)))
    selected_month_int = st.sidebar.selectbox("Forecast Month:", list(range(1,13)))
    selected_yyyymm = f"{selected_year_int}{selected_month_int:02d}"
    #plot_types=list(IDX_FILENAME_MAP.keys())
    
elif tab_selection == "🖼️ Detailed Plots":  # Detailed
    var = st.sidebar.selectbox("Select variables:", ['t2m','prcp','z500','sst'])
    region = st.sidebar.selectbox("Select region:", list(REGIONS.keys()))
    selected_year_int = st.sidebar.selectbox("Forecast Year:", list(range(fcst_start_year, fcst_end_year + 1)))
    selected_month_int = st.sidebar.selectbox("Forecast Month:", list(range(1,13)))
    selected_yyyymm = f"{selected_year_int}{selected_month_int:02d}"
    plot_types = list(PLOT_FILENAME_MAP.keys())
    selected_plots = st.sidebar.multiselect("Select Plot:", plot_types, default=plot_types)


st.sidebar.markdown("---")
st.sidebar.markdown(
    """
    <div style='font-size: 13px; text-align: center;'>
        Made with ❤️ by <b>Gaeun Kim</b><br>
        @ APCC Testbed Team<br>
        📧 <a href='mailto:gkim@apcc21.org'>gkim@apcc21.org</a><br>
        🔗 <a href='https://github.com/gkim-TB' target='_blank'>GitHub: gkim-TB</a>
    </div>
    """, unsafe_allow_html=True
)

# # ───────────────────────────────────────────────────────────────
# # ---- Defaults for type checker (will be overwritten in each tab) ----
# var: str = None
# region: str = list(REGIONS.keys())[0]
# selected_year: int = fcst_start // 100
# selected_month_int: int = 1
# selected_yyyymm: str = f"{selected_year}{selected_month_int:02d}"
# selected_plots: List[str] = list(PLOT_FILENAME_MAP.keys())
# # ───────────────────────────────────────────────────────────────

if tab_selection == "📊 Overview":
    st.header("📊 Key Metrics Overview")

    st.image(get_fig_url(model, region, var,
        f"targetSeries_byInit_{var}_{region}_traj_{fcst_start_year}_{fcst_end_year}.png"),
        caption="Trajectory by Init (with lead-1 ACC)", use_container_width=True)
    st.image(get_fig_url(model, region, var,
        f"targetSeries_byInit_{var}_{region}_skill_{fcst_start_year}_{fcst_end_year}.png"),
        caption="ACC skill by Init", use_container_width=True)

    cols = st.columns(2) # type: ignore[reportUnknownArgumentType]

    with cols[0]:
        st.image(get_fig_url(model, region, var, 
            f"det_heatmap_init_{var}_{region}_{selected_year}.png"),
            caption=f"Deterministic Skill Score ({selected_year})", use_container_width=True)
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
    st.header("📈 Indices")
    st.image(f"{GITHUB_RAW_BASE}/FIG/{model}/IDX/ENSO_index_timeseries_all_init.png",
        caption="Trajectory ENSO by Init", use_container_width=True)
    st.image(f"{GITHUB_RAW_BASE}/FIG/{model}/IDX/IOD_index_timeseries_all_init.png",
        caption="Trajectory IOD index by Init", use_container_width=True)


    cols = st.columns(2)
    with cols[0]:
        st.image(f"{GITHUB_RAW_BASE}/FIG/{model}/IDX/ENSO_plum_{selected_yyyymm}.png",
            caption=f"ENSO plums initialized ({selected_yyyymm})", use_container_width=True)
        st.image(f"{GITHUB_RAW_BASE}/FIG/{model}/IDX/hovmoller_nino34_{selected_yyyymm}.png",
            caption="Hovmöller Nino3.4", use_container_width=True)  
    with cols[1]:
        st.image(f"{GITHUB_RAW_BASE}/FIG/{model}/IDX/IOD_plum_{selected_yyyymm}.png",
            caption=f"IOD plums initialized ({selected_yyyymm})", use_container_width=True)
        st.image(f"{GITHUB_RAW_BASE}/FIG/{model}/IDX/hovmoller_iod_{selected_yyyymm}.png",
            caption="Hovmöller IOD", use_container_width=True)  
        
    # st.markdown("""
    # <div style='text-align: center; padding-top: 100px;'>
    #     <h1 style='font-size: 60px; color: #8A2BE2; font-weight: bold;'>
    #         ✨ Bibbidi-Bobbidi-Boo ✨
    #     </h1>
    #     <p style='font-size: 20px; color: #555;'>This page is under magical development...</p>
    # </div>
    # """, unsafe_allow_html=True)

