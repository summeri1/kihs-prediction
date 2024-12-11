import streamlit as st
import pandas as pd
import os
from datetime import datetime
import matplotlib.pyplot as plt
import gdown
import matplotlib.font_manager as fm
font_path = f"Nanum_Gothic/NanumGothic-Bold.ttf"
fm.fontManager.addfont(font_path)
plt.rcParams['font.family'] = 'NanumGothic'

st.set_page_config(page_title="지점별 예측 결과", layout="wide", initial_sidebar_state="expanded")

# 상단 고정 타이틀 및 서브타이틀
st.title("한국수자원조사기술원 홍수위 예측")
st.write("※ 해당 자료는 A.I. 딥러닝을 통해 학습된 데이터를 기반으로 3시간, 6시간 이후의 수위를 예측한 모델링 자료로, 실제 수위와 차이가 발생할 수 있습니다.")

FILE_ID = "16g4Btk17vNHSTPy-b40kxCESY38g0cD-"
OUTPUT = "All_Locations_Prediction.xlsx"

def download_excel_from_google_drive(file_id, output):
    url = f"https://drive.google.com/uc?id={file_id}"
    gdown.download(url, output, quiet=True)

@st.cache_data
def load_data():
    # 구글드라이브에서 엑셀 다운로드
    download_excel_from_google_drive(FILE_ID, OUTPUT)
    xls = pd.ExcelFile(OUTPUT)
    sheets = xls.sheet_names
    return sheets, OUTPUT

# 사이드바 상단에 refresh 버튼
if st.sidebar.button("데이터 업데이트"):
    # 캐시 초기화 후 rerun
    st.cache_data.clear()
    st.rerun()

sheets, excel_file = load_data()

def plot_prediction_graph(df, sheet_name):
    # df에는 '일시', '실제수위', '예측 수위(3시간)', '예측 수위(6시간)' 컬럼 존재한다고 가정
    # 최근 30개 데이터 사용
    df_30 = df.sort_values('일시', ascending=False).head(30).sort_values('일시')  # 그래프는 시간오름차순으로 그리기 위해 정렬
    actual_times = df_30['일시']
    actual_levels = df_30['실제수위']
    predicted_times_3h = df_30['일시']
    predicted_levels_3h = df_30['예측 수위(3시간)']
    predicted_times_6h = df_30['일시']
    predicted_levels_6h = df_30['예측 수위(6시간)']
    plt.rcParams['font.size'] = 10  # 글씨 크기
    fig, ax = plt.subplots(figsize=(10, 5))  # 그래프 크기 확대
    ax.plot(predicted_times_3h, predicted_levels_3h, label='예측 수위(3시간)', linestyle='-', marker='o', markersize=4, linewidth=1.5, alpha=0.8, color='orange')
    ax.plot(predicted_times_6h, predicted_levels_6h, label='예측 수위(6시간)', linestyle='--', marker='^', markersize=4, linewidth=1.5, alpha=0.5, color='green')
    ax.plot(actual_times, actual_levels, label='실제 수위', marker='o', markersize=4, linewidth=1.5, color='red')
    ax.set_xlabel('시간')
    ax.set_ylabel('수위(h)m')
    ax.set_title(f"{sheet_name} 지점 수위 예측(1일)")
    ax.grid(True, linestyle='--', linewidth=0.5)
    plt.xticks(rotation=45)
    ax.legend()
    plt.tight_layout()

    ymin = min(min(actual_levels), min(predicted_levels_3h), min(predicted_levels_6h)) - 0.1
    ymax = max(max(actual_levels), max(predicted_levels_3h), max(predicted_levels_6h)) + 0.1
    y_range = ymax - ymin

    if y_range < 0.5:
        mid_point = (ymax + ymin) / 2
        ymin = mid_point - 0.25
        ymax = mid_point + 0.25

    plt.ylim(bottom=ymin, top=ymax)

    return fig

page_options = ["메인페이지"] + sheets
selected_sheet = st.sidebar.selectbox("지점 선택", page_options)

if selected_sheet == "메인페이지":
    st.subheader("전체 지점 1일 예측 그래프")
    # 2개씩 나열하기 위해 시트 목록을 순회하며 그래프 표시
    num_sheets = len(sheets)
    for i in range(0, num_sheets, 2):
        cols = st.columns(2)
        for j in range(2):
            if i + j < num_sheets:
                sheet = sheets[i + j]
                # 시트 데이터 읽기
                df_sheet = pd.read_excel(excel_file, sheet_name=sheet)
                code = sheet.split("_")[0]
                required_cols = ['일시', code, '예측 수위(3시간)', '예측 수위(6시간)']
                df_sheet = df_sheet[required_cols]
                df_sheet = df_sheet.rename(columns={code: '실제수위'})
                # 소수점 처리
                float_cols = ['실제수위', '예측 수위(3시간)', '예측 수위(6시간)']
                for col in float_cols:
                    df_sheet[col] = df_sheet[col].round(2)
                fig = plot_prediction_graph(df_sheet, sheet)
                cols[j].pyplot(fig)
else:
    # 지점별 페이지 로직
    # 선택한 sheet의 데이터 로드
    df = pd.read_excel(excel_file, sheet_name=selected_sheet)
    code = selected_sheet.split("_")[0]
    required_cols = ['일시', code, '예측 수위(3시간)', '예측 수위(6시간)']
    df = df[required_cols]

    # 컬럼명 변경
    df = df.rename(columns={code: '실제수위'})

    # 소수점 처리
    float_cols = ['실제수위', '예측 수위(3시간)', '예측 수위(6시간)']
    for col in float_cols:
        df[col] = df[col].round(2)

    # 일시 기준 내림차순 후 최근 30개
    df = df.sort_values('일시', ascending=False)
    df_30 = df.head(30).reset_index(drop=True)

    st.write(f"### {selected_sheet} 지점 최근 30개 데이터")
    st.dataframe(df_30, use_container_width=True)

    # 그래프 그리기
    df_30_asc = df_30.sort_values('일시').reset_index(drop=True)
    fig = plot_prediction_graph(df_30_asc, selected_sheet)
    st.write("### 1일 예측 그래프")
    st.pyplot(fig)
