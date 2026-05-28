
import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
from datetime import date, timedelta

# 페이지 기본 설정
st.set_page_config(page_title="한/미 주식 비교 분석", layout="wide")

st.title("📈 한국 및 미국 주요 주식 수익률 비교")
st.markdown("yfinance를 활용하여 한국과 미국의 주요 주식 및 지수의 수익률과 차트를 비교해 보는 웹 애플리케이션입니다. 다양한 산업군의 기업들을 선택해보고 차이를 분석해 보세요!")

# 사이드바 설정 (입력부)
st.sidebar.header("⚙️ 분석 설정")
start_date = st.sidebar.date_input("시작일", date.today() - timedelta(days=365)) # 기본값: 1년 전
end_date = st.sidebar.date_input("종료일", date.today())

# 분석할 주요 주식 목록 대폭 확장 (분야 및 국가별 정리)
stocks_dict = {
    # --- 한국 시장 대표 지수 ---
    "KOSPI 지수": "^KS11",
    "KOSDAQ 지수": "^KQ11",
    
    # --- 한국 주요 주식 ---
    "삼성전자 (반도체/IT)": "005930.KS",
    "SK하이닉스 (반도체)": "000660.KS",
    "현대차 (자동차)": "005380.KS",
    "기아 (자동차)": "000270.KS",
    "NAVER (IT/플랫폼)": "035420.KS",
    "카카오 (IT/플랫폼)": "035720.KS",
    "LG에너지솔루션 (2차전지)": "373220.KS",
    "삼성바이오로직스 (바이오)": "207940.KS",
    "셀트리온 (바이오)": "068270.KS",
    "POSCO홀딩스 (철강/소재)": "005490.KS",
    "KB금융 (금융)": "105560.KS",

    # --- 미국 시장 대표 지수 ---
    "S&P 500 지수": "^GSPC",
    "NASDAQ 지수": "^IXIC",
    "다우 존스 지수": "^DJI",

    # --- 미국 주요 주식 ---
    "애플 (IT/기기)": "AAPL",
    "마이크로소프트 (소프트웨어)": "MSFT",
    "알파벳/구글 (IT/플랫폼)": "GOOGL",
    "아마존 (이커머스/클라우드)": "AMZN",
    "메타/페이스북 (SNS)": "META",
    "엔비디아 (반도체)": "NVDA",
    "테슬라 (전기차)": "TSLA",
    "넷플릭스 (엔터테인먼트)": "NFLX",
    "JPMorgan (금융)": "JPM",
    "존슨앤드존슨 (제약/헬스케어)": "JNJ",
    "비자 (금융/결제)": "V",
    "월마트 (유통)": "WMT"
}

# 다중 선택 기능 (사용자가 보고 싶은 종목만 선택)
selected_stocks = st.sidebar.multiselect(
    "비교할 주식 및 지수를 선택하세요",
    options=list(stocks_dict.keys()),
    default=["삼성전자 (반도체/IT)", "애플 (IT/기기)", "KOSPI 지수", "NASDAQ 지수"]
)

# 데이터 불러오기 함수 (캐싱 기능 적용하여 앱 속도 향상)
@st.cache_data
def load_data(tickers, start, end):
    # yfinance를 사용해 여러 티커의 데이터를 한 번에 다운로드하고 '종가(Close)'만 가져옵니다.
    data = yf.download(tickers, start=start, end=end)["Close"]
    
    # 1개 종목만 선택했을 경우 Series로 반환되므로 DataFrame으로 변환해줍니다.
    if isinstance(data, pd.Series):
        data = data.to_frame(name=tickers[0])
    return data

# 메인 화면 로직
if selected_stocks:
    # 선택된 이름들을 티커 심볼 리스트로 변환
    tickers = [stocks_dict[stock] for stock in selected_stocks]

    with st.spinner('방대한 데이터를 불러오는 중입니다. 잠시만 기다려주세요...'):
        df_close = load_data(tickers, start_date, end_date)

    # 결측치(휴장일 등) 처리: 이전 날짜의 종가로 채움 (한국과 미국의 휴장일이 다르기 때문에 필수적인 전처리입니다.)
    df_close.ffill(inplace=True)

    # 티커 심볼을 사용자가 알아보기 쉬운 한글 종목명으로 컬럼명 변경
    rename_dict = {ticker: name for name, ticker in stocks_dict.items()}
    df_close.rename(columns=rename_dict, inplace=True)

    st.subheader("📊 누적 수익률 비교 차트")
    st.markdown("선택한 기간의 첫 날짜를 **0%** 기준으로 잡고 변화한 수익률을 보여줍니다.")

    # 누적 수익률 계산 로직
    df_returns = (df_close / df_close.iloc[0] - 1) * 100

    # Plotly를 이용한 꺾은선형 차트 생성
    fig = px.line(df_returns, x=df_returns.index, y=df_returns.columns,
                  labels={'value': '누적 수익률 (%)', 'Date': '날짜', 'variable': '종목명'},
                  title="기간 내 누적 수익률 변화 추이")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("📋 주요 종목 수익률 요약표")
    st.markdown("선택한 기간 동안의 시작가, 종료가 및 최종 수익률을 수치로 확인합니다.")

    summary_data = []
    # 데이터프레임의 각 컬럼(종목)별로 순회하며 정보 추출
    for col in df_close.columns:
        start_price = df_close[col].iloc[0]
        end_price = df_close[col].iloc[-1]
        total_return = (end_price - start_price) / start_price * 100
        
        summary_data.append({
            "종목명": col,
            "시작가": round(start_price, 2),
            "종료가": round(end_price, 2),
            "최종 수익률 (%)": round(total_return, 2)
        })

    # 요약 데이터를 데이터프레임으로 만들어 출력, 수익률 기준으로 내림차순 정렬
    df_summary = pd.DataFrame(summary_data).sort_values(by="최종 수익률 (%)", ascending=False).reset_index(drop=True)
    st.dataframe(df_summary, use_container_width=True)

else:
    st.warning("👈 왼쪽 사이드바에서 비교할 주식을 하나 이상 선택해주세요.")
