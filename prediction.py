import streamlit as st
import pandas as pd
import os
from datetime import datetime
import matplotlib.pyplot as plt
import gdown
import matplotlib.font_manager as fm

# ──────────────── Font Settings ────────────────
font_path = "Nanum_Gothic/NanumGothic-Bold.ttf"
fm.fontManager.addfont(font_path)
plt.rcParams['font.family'] = 'NanumGothic'

# ──────────────── Page Configuration ────────────────
st.set_page_config(
    page_title="KIHS 홍수위 예측", 
    layout="wide", 
    initial_sidebar_state="expanded"
)
st.title("한국수자원조사기술원 홍수위 예측")

# ──────────────── Constants ────────────────
FILE_ID     = "16g4Btk17vNHSTPy-b40kxCESY38g0cD-"
XLSX_PATH   = "All_Locations_Prediction.xlsx"
PARQUET_DIR = "parquet_cache"
USECOLS_TEMPLATE = ["일시", "{code}", "예측 수위(3시간)", "예측 수위(6시간)"]

# ──────────────── Utility Functions ────────────────
def download_excel_from_google_drive(file_id: str, output: str) -> str:
    """Download Excel once; skip if already present."""
    if not os.path.exists(output):
        url = f"https://drive.google.com/uc?id={file_id}"
        gdown.download(url, output, quiet=True)
    return output


def ensure_parquet(xlsx_path: str, sheet: str) -> str:
    """Ensure a Parquet cache exists for the given sheet; regenerate if Excel is newer."""
    os.makedirs(PARQUET_DIR, exist_ok=True)
    parquet_path = os.path.join(PARQUET_DIR, f"{sheet}.parquet")
    mtime_xls = os.path.getmtime(xlsx_path)
    if (not os.path.exists(parquet_path)) or (os.path.getmtime(parquet_path) < mtime_xls):
        # Read only required columns
        code = sheet.split("_")[0]
        usecols = [c.format(code=code) for c in USECOLS_TEMPLATE]
        df = pd.read_excel(
            xlsx_path,
            sheet_name=sheet,
            usecols=usecols,
            parse_dates=["일시"],
        )
        # Rename and round
        df = df.rename(columns={code: '실제수위'})
        for col in ['실제수위', '예측 수위(3시간)', '예측 수위(6시간)']:
            df[col] = df[col].round(2)
        df.to_parquet(parquet_path, index=False)
    return parquet_path

@st.cache_data(ttl=3600)
def load_sheet_data(xlsx_path: str, sheet: str) -> pd.DataFrame:
    """Load a sheet via Parquet cache, refreshing hourly or on demand."""
    pq = ensure_parquet(xlsx_path, sheet)
    return pd.read_parquet(pq)


def plot_prediction_graph(df: pd.DataFrame, sheet_name: str) -> plt.Figure:
    """Plot recent 30 points of actual vs. 3h/6h predicted levels."""
    df_30 = df.sort_values('일시', ascending=False).head(30).sort_values('일시')
    times = df_30['일시']
    actual = df_30['실제수위']
    pred3 = df_30['예측 수위(3시간)']
    pred6 = df_30['예측 수위(6시간)']

    plt.rcParams['font.size'] = 10
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(times, pred3, label='예측 수위(3시간)', linestyle='-', marker='o', markersize=4, linewidth=1.5, alpha=0.8)
    ax.plot(times, pred6, label='예측 수위(6시간)', linestyle='--', marker='^', markersize=4, linewidth=1.5, alpha=0.5)
    ax.plot(times, actual, label='실제 수위', linestyle='-', marker='s', markersize=4, linewidth=1.5, alpha=1.0)

    ax.set_xlabel('시간')
    ax.set_ylabel('수위 (m)')
    ax.set_title(f"{sheet_name} 지점 수위 예측(최근 30개)")
    ax.grid(True, linestyle='--', linewidth=0.5)
    plt.xticks(rotation=45)
    ax.legend()
    plt.tight_layout()

    # Y-axis padding
    ymin = min(actual.min(), pred3.min(), pred6.min()) - 0.1
    ymax = max(actual.max(), pred3.max(), pred6.max()) + 0.1
    ax.set_ylim(ymin, ymax)

    return fig

# ──────────────── Session State Initialization ────────────────
if 'cached_sheet_data' not in st.session_state:
    st.session_state.cached_sheet_data = {}
if 'cached_sheet_figs' not in st.session_state:
    st.session_state.cached_sheet_figs = {}

# ──────────────── Load Sheets ────────────────
# Ensure Excel exists and get sheet list
try:
    download_excel_from_google_drive(FILE_ID, XLSX_PATH)
    xls = pd.ExcelFile(XLSX_PATH)
    sheets = xls.sheet_names
except Exception as e:
    st.error(f"데이터 로딩 실패: {e}")
    st.stop()

# ──────────────── Sidebar ────────────────
st.sidebar.markdown("---")
st.sidebar.markdown("<div style='font-size:20px;font-weight:bold;'>지점 선택</div>", unsafe_allow_html=True)
page_options = ["메인페이지"] + sheets
selected_sheet = st.sidebar.selectbox("", page_options)

st.sidebar.markdown("---")
st.sidebar.markdown("**프로그램 정보**")
st.sidebar.markdown("- 개발자 : 영산강조사실 이성호")
st.sidebar.markdown("- 문의 : 내선번호 937")
st.sidebar.markdown("- 버전 : Ver 1.250516")

if st.sidebar.button("데이터 업데이트"):
    st.cache_data.clear()
    st.session_state.cached_sheet_data.clear()
    st.session_state.cached_sheet_figs.clear()
    st.experimental_rerun()

# ──────────────── Main / Sheet Views ────────────────
if selected_sheet == "메인페이지":
    st.markdown("**A.I. 딥러닝 기반 3시간/6시간 수위 예측 결과입니다.**")
    st.image("mainpage.gif", use_container_width=True)
else:
    st.markdown("**예측 데이터는 실제 발생 수위와 차이가 있을 수 있습니다.**")

    # Load data & cache figure
    if selected_sheet not in st.session_state.cached_sheet_data:
        df = load_sheet_data(XLSX_PATH, selected_sheet)
        st.session_state.cached_sheet_data[selected_sheet] = df
        fig = plot_prediction_graph(df, selected_sheet)
        st.session_state.cached_sheet_figs[selected_sheet] = fig
    else:
        df = st.session_state.cached_sheet_data[selected_sheet]
        fig = st.session_state.cached_sheet_figs[selected_sheet]

    # Data table (most recent 126 rows)
    df_table = df.sort_values('일시', ascending=False).head(126).reset_index(drop=True)
    st.write(f"### {selected_sheet} 예측 데이터 (최근 126개)")
    st.dataframe(df_table, use_container_width=True)

    # Graph (recent 24h)
    st.write("### 최근 24시간 그래프")
    st.pyplot(fig)
