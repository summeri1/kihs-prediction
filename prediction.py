import streamlit as st
import pandas as pd
import os
from datetime import datetime
import matplotlib.pyplot as plt
import gdown
import matplotlib.font_manager as fm

# 폰트 설정
font_path = f"Nanum_Gothic/NanumGothic-Bold.ttf"
fm.fontManager.addfont(font_path)
plt.rcParams['font.family'] = 'NanumGothic'

st.set_page_config(page_title="지점별 예측 결과", layout="wide", initial_sidebar_state="expanded")

# 상단 고정 타이틀 및 서브타이틀
st.title("한국수자원조사기술원 홍수위 예측")
st.text("1) 해당 자료는 A.I. 딥러닝을 통해 학습된 데이터를 기반으로 3시간, 6시간 이후의 수위를 예측한 모델링 자료입니다.")
st.text("2) 예측 데이터는 실제 발생 수위와 차이가 발생할 수 있으니 사용시 유의하시기 바랍니다.")

FILE_ID = "16g4Btk17vNHSTPy-b40kxCESY38g0cD-"
OUTPUT = "All_Locations_Prediction.xlsx"


def download_excel_from_google_drive(file_id, output):
    url = f"https://drive.google.com/uc?id={file_id}"
    gdown.download(url, output, quiet=True)

@st.cache_data(show_spinner="예측 데이터 기초 파일을 로딩중입니다...")
def load_data():
    # 구글드라이브에서 엑셀 다운로드
    download_excel_from_google_drive(FILE_ID, OUTPUT)
    xls = pd.ExcelFile(OUTPUT)
    sheets = xls.sheet_names
    return sheets, OUTPUT


# 캐싱된 데이터와 그래프를 저장할 세션 상태 초기화
if 'cached_sheet_data' not in st.session_state:
    st.session_state.cached_sheet_data = {}
if 'cached_sheet_figs' not in st.session_state:
    st.session_state.cached_sheet_figs = {}


@st.cache_data(show_spinner="지점별 데이터를 로딩중입니다...")
def load_sheet_data(excel_file, sheet):
    df_sheet = pd.read_excel(excel_file, sheet_name=sheet)
    code = sheet.split("_")[0]
    required_cols = ['일시', code, '예측 수위(3시간)', '예측 수위(6시간)']
    df_sheet = df_sheet[required_cols]
    df_sheet = df_sheet.rename(columns={code: '실제수위'})

    # 소수점 처리
    float_cols = ['실제수위', '예측 수위(3시간)', '예측 수위(6시간)']
    for col in float_cols:
        df_sheet[col] = df_sheet[col].round(2)

    return df_sheet


def plot_prediction_graph(df, sheet_name):
    # 그래프용 최근 30개 데이터
    df_30 = df.sort_values('일시', ascending=False).head(30).sort_values('일시')
    actual_times = df_30['일시']
    actual_levels = df_30['실제수위']
    predicted_times_3h = df_30['일시']
    predicted_levels_3h = df_30['예측 수위(3시간)']
    predicted_times_6h = df_30['일시']
    predicted_levels_6h = df_30['예측 수위(6시간)']

    plt.rcParams['font.size'] = 10
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(predicted_times_3h, predicted_levels_3h, label='예측 수위(3시간)',
            linestyle='-', marker='o', markersize=4, linewidth=1.5, alpha=0.8, color='orange')
    ax.plot(predicted_times_6h, predicted_levels_6h, label='예측 수위(6시간)',
            linestyle='--', marker='^', markersize=4, linewidth=1.5, alpha=0.5, color='green')
    ax.plot(actual_times, actual_levels, label='실제 수위',
            marker='o', markersize=4, linewidth=1.5, color='red')

    ax.set_xlabel('시간')
    ax.set_ylabel('수위(h)m')
    ax.set_title(f"{sheet_name} 지점 수위 예측(1일)")
    ax.grid(True, linestyle='--', linewidth=0.5)
    plt.xticks(rotation=45)
    ax.legend()
    plt.tight_layout()

    # Y축 범위 설정 로직
    ymin = min(min(actual_levels), min(predicted_levels_3h), min(predicted_levels_6h)) - 0.1
    ymax = max(max(actual_levels), max(predicted_levels_3h), max(predicted_levels_6h)) + 0.1
    y_range = ymax - ymin

    if y_range < 0.5:
        mid_point = (ymax + ymin) / 2
        ymin = mid_point - 0.25
        ymax = mid_point + 0.25

    plt.ylim(bottom=ymin, top=ymax)

    return fig

# 사이드바 상단에 업데이트 버튼
if st.sidebar.button("데이터 업데이트"):
    # 모든 캐시 데이터 삭제
    st.cache_data.clear()
    st.session_state.cached_sheet_data = {}
    st.session_state.cached_sheet_figs = {}
    st.experimental_rerun()
st.sidebar.markdown("---")

# 초기 데이터 로드
sheets, excel_file = load_data()

# 페이지 옵션 설정
st.sidebar.markdown("<div style='font-size: 20px; font-weight: bold;'>지점 선택</div>", unsafe_allow_html=True)
page_options = ["메인페이지"] + sheets
selected_sheet = st.sidebar.selectbox("", page_options)

if selected_sheet == "메인페이지":
    st.subheader("전체 지점 1일 예측 그래프")

    # 모든 그래프를 캐시에서 가져오거나 생성
    for sheet in sheets:
        if sheet not in st.session_state.cached_sheet_data:
            # 시트 데이터 캐시
            df_sheet = load_sheet_data(excel_file, sheet)
            st.session_state.cached_sheet_data[sheet] = df_sheet

            # 그래프 캐시
            fig = plot_prediction_graph(df_sheet, sheet)
            st.session_state.cached_sheet_figs[sheet] = fig

    # 그래프 출력
    num_sheets = len(sheets)
    for i in range(0, num_sheets, 2):
        cols = st.columns(2)
        for j in range(2):
            if i + j < num_sheets:
                sheet = sheets[i + j]
                fig = st.session_state.cached_sheet_figs[sheet]
                cols[j].pyplot(fig)

else:
    # 선택된 시트의 데이터와 그래프를 캐시에서 가져오거나 생성
    if selected_sheet not in st.session_state.cached_sheet_data:
        df = load_sheet_data(excel_file, selected_sheet)
        st.session_state.cached_sheet_data[selected_sheet] = df

        # 그래프 생성 및 캐시
        fig = plot_prediction_graph(df, selected_sheet)
        st.session_state.cached_sheet_figs[selected_sheet] = fig
    else:
        df = st.session_state.cached_sheet_data[selected_sheet]
        fig = st.session_state.cached_sheet_figs[selected_sheet]

    # 표 출력 (최근 174개)
    df_table = df.sort_values('일시', ascending=False).head(174).reset_index(drop=True)
    st.write(f"### {selected_sheet} 지점 최근 174개 데이터")
    st.dataframe(df_table, use_container_width=True)

    # 그래프 출력
    st.write("### 1일 예측 그래프")
    st.pyplot(fig)

st.sidebar.markdown("---")
st.sidebar.markdown("**프로그램 정보**")
st.sidebar.markdown("- 작성자 : 영산강조사실 이성호")
st.sidebar.markdown("- 문의 : 내선번호 937")
st.sidebar.markdown("- 최종 업데이트 : 2024-12-13")
st.sidebar.markdown("---")
st.sidebar.markdown("**데이터 로딩에는 기다림이 필요합니다.**")
