from typing import Dict, List, Tuple, Optional
import streamlit as st

import os, sys
from datetime import datetime
from dateutil.relativedelta import relativedelta

# Sidebar / page state 초기화
if 'page' not in st.session_state:
    st.session_state['page'] = ""          # "" 또는 "guidance"
if 'selected_tab' not in st.session_state:
    st.session_state['selected_tab'] = "📊 Overview"

# 콜백: 사이드바 라디오(탭)를 바꾸면 guidance 모드를 해제
def _on_tab_change():
    st.session_state['page'] = ""

# 콜백: Guidance 버튼 클릭시 guidance 모드로 전환
def _show_guidance():
    st.session_state['page'] = "guidance"

# Streamlit 페이지 설정
st.set_page_config(layout="wide", initial_sidebar_state='expanded')
st.sidebar.title("Seasonal Forecast Verification Dashboard")

# 사이드바: Guidance 버튼 (메인 화면만 전환, 사이드바는 유지)
st.sidebar.button("📘 Guidance", key="guidance_menu_button", on_click=_show_guidance)

st.sidebar.markdown('<div style="height:12px"></div>', unsafe_allow_html=True)

# 사이드바: 탭 라디오 (on_change 콜백으로 guidance 해제)
tab_selection = st.sidebar.radio(
    "Select Mode:", 
    ["📊 Overview", "🖼️ Detailed Plots", "📈 Indices"],
    key='selected_tab',
    on_change=_on_tab_change
)

# Guidance 파일명 설정
GUIDANCE_FILENAMES = ["GUIDANCE.md"]

def render_guidance():
    st.header("Guidance")
    base_dir = os.path.dirname(__file__) if "__file__" in globals() else os.getcwd()
    found = False
    for fname in GUIDANCE_FILENAMES:
        fpath = os.path.join(base_dir, fname)
        if os.path.exists(fpath):
            with open(fpath, "r", encoding="utf-8") as f:
                md = f.read()
            st.markdown(md, unsafe_allow_html=True)
            found = True
            break
    if not found:
        st.warning("GUIDANCE.md 파일이 앱 폴더에 없습니다. Guidance 파일을 업로드하거나 파일명을 확인해 주세요.")

# 만약 guidance 모드라면 우측 메인에 guidance만 표시하고 중단
if st.session_state.get('page', '') == "guidance":
    render_guidance()
    st.stop()

# ──────────────────────────────────────────────
# Sidebar instructions (나머지 기존 사이드바 옵션들)
st.sidebar.markdown("Use the options below to customize plots")

# 프로젝트 루트 설정
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from fcstverif.config import fcst_start, fcst_end, REGIONS, model

# GitHub base raw URL
GITHUB_RAW_BASE: str = "https://raw.githubusercontent.com/gkim-TB/FcstVerif2025/main"

def get_fig_url(model: str, region: str, var: str, filename:str) -> str:
    return f"{GITHUB_RAW_BASE}/FIG/{model}/{region}/{var}/{filename}"

def get_yyyymm_for_plot(plot_type:str, selected_yyyymm:str) -> str:
    dt = datetime.strptime(selected_yyyymm, "%Y%m")
    if "byTarget" in plot_type:
        dt += relativedelta(months=1)
    return dt.strftime("%Y%m")

PLOT_FILENAME_MAP: Dict[str, List[str]] = {
    "ACC_byInit":    ["acc_init_{var}_{region}_{yyyymm}.png"],
    "RMSE_byInit":   ["rmse_init_{var}_{region}_{yyyymm}.png"],
    "ACC_byTarget":  ["acc_target_{var}_{region}_{yyyymm}.png"],
    "RMSE_byTarget": ["rmse_target_{var}_{region}_{yyyymm}.png"],
    "Bias_byTarget": ["{var}_pattern_compare_{region}_{yyyymm}.png"],
    "RPSS_byInit":   ["rpss_map_{var}_{region}_{yyyymm}.png"],
    "ROC_byInit":    ["roc_curve_by_lead_{var}_{region}_{yyyymm}.png"],
}

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

# 탭별 사이드바 옵션 및 메인 컨텐츠용 변수
fcst_start_year = fcst_start//100
fcst_end_year = fcst_end//100

# 각 탭에서 선택지 표시
if tab_selection == "📊 Overview":
    var = st.sidebar.selectbox("Select variables:", ['t2m','prcp','z500','sst'])
    region = st.sidebar.selectbox("Select region:", list(REGIONS.keys()))
    selected_year = st.sidebar.selectbox("Select Year:", list(range(fcst_start_year, fcst_end_year + 1)))

elif tab_selection == "📈 Indices":
    st.sidebar.markdown("Select options for Indices")
    selected_year_int = st.sidebar.selectbox("Forecast Year:", list(range(fcst_start_year, fcst_end_year + 1)))
    selected_month_int = st.sidebar.selectbox("Forecast Month:", list(range(1,13)))
    selected_yyyymm = f"{selected_year_int}{selected_month_int:02d}"

elif tab_selection == "🖼️ Detailed Plots":  # Detailed
    var = st.sidebar.selectbox("Select variables:", ['t2m','prcp','z500','sst'])
    region = st.sidebar.selectbox("Select region:", list(REGIONS.keys()))
    selected_year_int = st.sidebar.selectbox("Forecast Year:", list(range(fcst_start_year, fcst_end_year + 1)))
    selected_month_int = st.sidebar.selectbox("Forecast Month:", list(range(1,13)))
    selected_yyyymm = f"{selected_year_int}{selected_month_int:02d}"
    plot_types = list(PLOT_FILENAME_MAP.keys())
    selected_plots = st.sidebar.multiselect("Select Plot:", plot_types, default=plot_types)

# footer / contact
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

# ───────────────────────────────────────────────────────────────
# 메인 컨텐츠: 현재 선택된 탭(tab_selection)에 따라 렌더
if tab_selection == "📊 Overview":
    st.header("📊 Key Metrics Overview")
    st.image(get_fig_url(model, region, var,
        f"targetSeries_byInit_{var}_{region}_traj_{fcst_start_year}_{fcst_end_year}.png"),
        caption="Trajectory by Init (with lead-1 ACC)", use_container_width=True)
    st.image(get_fig_url(model, region, var,
        f"targetSeries_byInit_{var}_{region}_skill_{fcst_start_year}_{fcst_end_year}.png"),
        caption="ACC skill by Init", use_container_width=True)

    cols = st.columns(2)
    with cols[0]:
        st.image(get_fig_url(model, region, var, 
            f"det_heatmap_init_{var}_{region}_{selected_year}.png"),
            caption=f"Deterministic Skill Score ({selected_year})", use_container_width=True)
    with cols[1]:
        st.image(get_fig_url(model, region, var,
            f"det_ter_score_{var}_{region}_{selected_year}.png"),
            caption=f"Deterministic Tercile Score ({selected_year})")

elif tab_selection == "🖼️ Detailed Plots":
    st.header("🖼️ Detailed Plots")
    cols = st.columns(2)
    i = 0
    for plot_type in selected_plots:
        yyyymm_to_use = get_yyyymm_for_plot(plot_type, selected_yyyymm)
        for fname, url in get_image_urls(plot_type, var, region, yyyymm=yyyymm_to_use):
            with cols[i % 2]:
                st.image(url, caption=fname, use_container_width=True)
            i += 1

else:  # "📈 Indices"
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
