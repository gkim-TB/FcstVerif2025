# dashboard/app.py

import streamlit as st
import os
from PIL import Image

from config import variables, REGIONS, output_fig_dir, model

st.set_page_config(layout="wide")
st.title("📊 Seasonal Forecast Verification Dashboard")

# 사이드바 구성
with st.sidebar:
    st.header("🔧 설정")
    var = st.selectbox("변수 (Variable)", variables)
    region = st.selectbox("검증 영역 (Region)", list(REGIONS.keys()))
    plot_type = st.selectbox("플롯 유형 (Plot Type)", [
        "init_line", "init_heatmap", "target_month", "target_pattern", "target_line",
        "cate_heatmap", "rpss_map", "roc_curve"
    ])
    st.markdown("---")
    show_caption = st.checkbox("설명 표시", value=True)

# 파일 경로 구성
def get_image_path(plot_type, var, region):
    """FIG 디렉토리 내 이미지 경로 구성"""
    fig_path = os.path.join(
        output_fig_dir,
        model,
        region,
        var,
        f"{plot_type}_{var}_{region}.png"
    )
    return fig_path

# 이미지 불러오기
img_path = get_image_path(plot_type, var, region)

# 본문 출력
col1, col2 = st.columns([4, 1])
with col1:
    if os.path.isfile(img_path):
        st.image(Image.open(img_path), use_column_width=True)
    else:
        st.warning(f"해당 그림이 존재하지 않습니다: `{img_path}`")

with col2:
    if show_caption:
        st.subheader("ℹ️ 설명")
        st.markdown(f"""
        - **변수**: `{var}`
        - **영역**: `{region}`
        - **그림 유형**: `{plot_type}`
        - 파일 경로: `{img_path}`
        """)

# 하단 링크
st.markdown("---")
st.markdown("📁 [GitHub Repository](https://github.com/jkanner/streamlit-dataview) 스타일 기반 대시보드 | 개발자: APEC Climate Center")
