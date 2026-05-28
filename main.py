import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
from datetime import date, timedelta

# 페이지 기본 설정
st.set_page_config(page_title="한/미 주식 및 환율 분석", layout="wide")

st.title("📈 한국 및 미국 주요 주식/환율 분석기")
st.markdown("당곡고등학교 학생들의 데이터 분석을 위한 웹앱입니다. 주식 수익률과 환율의 상관관계를 분석하고, 시간에 따른 추세를 확인해 보세요!")

# 사이드바 설정 (입력부)
st.sidebar.header("⚙️ 분석 설정")
start_date = st.sidebar.date_input("시작일", date.today() - timedelta(days=365)) # 기본값: 1년 전
end_date = st.sidebar.date_input("종료일", date.today())

# 분석할 주요 주식 및 환율 목록
stocks_dict = {
    # --- 환율 (추가된 부분) ---
    "원/달러 환율 (USD/KRW)": "KRW=X",
    
    # --- 한국 시장 ---
    "KOSPI 지수": "^KS11",
    "삼성전자 (반도체)": "005930.KS",
    "현대차 (자동차)": "005380.KS",
    "NAVER (IT/플랫폼)": "035420.KS",
    
    # --- 미국 시장 ---
    "S&P 500 지수": "^GSPC",
    "NASDAQ 지수": "^IXIC",
    "애플 (IT/기기)": "AAPL",
    "마이크로소프트 (소프트웨어)": "MSFT",
    "엔비디아 (반도체)": "NVDA",
    "테슬라 (전기차)": "TSLA"
}

# 다중 선택 기능
selected_stocks = st.sidebar.multiselect(
    "비교할 종목 및 환율을 선택하세요",
    options=list(stocks_dict.keys()),
    default=["원/달러 환율 (USD/KRW)", "삼성전자 (반도체)", "애플 (IT/기기)"]
)

# 시간에 따른 추세선(이동평균선) 설정 (추가된 부분)
st.sidebar.markdown("---")
st.sidebar.subheader("📉 시간 흐름(추세) 분석")
show_ma = st.sidebar.checkbox("이동평균선(추세선) 적용하여 보기", value=False)
if show_ma:
    ma_days = st.sidebar.slider("이동평균 기간 (일)", min_value=5, max_value=120, value=20, step=5)
    st.sidebar.caption(f"선택한 {ma_days}일 동안의 평균을 계산하여 일시적인 변동성을 줄여줍니다.")

# 데이터 불러오기 함수 캐싱
@st.cache_data
def load_data(tickers, start, end):
    data = yf.download(tickers, start=start, end=end)["Close"]
    if isinstance(data, pd.Series):
        data = data.to_frame(name=tickers[0])
    return data

# 메인 화면 로직
if selected_stocks:
    tickers = [stocks_dict[stock] for stock in selected_stocks]

    with st.spinner('데이터를 분석 중입니다...'):
        df_close = load_data(tickers, start_date, end_date)

    # 결측치 처리 (휴장일 보정)
    df_close.ffill(inplace=True)

    # 컬럼명을 한글로 변경
    rename_dict = {ticker: name for name, ticker in stocks_dict.items()}
    df_close.rename(columns=rename_dict, inplace=True)

    st.subheader("📊 누적 수익률 및 환율 변화 차트")
    
    # 누적 수익률(%) 계산
    df_returns = (df_close / df_close.iloc[0] - 1) * 100

    # 이동평균선(MA) 적용 로직 (시간의 변화 추세 파악)
    if show_ma:
        # 판다스의 rolling 기능을 사용하여 이동평균 계산
        df_returns = df_returns.rolling(window=ma_days).mean()
        st.info(f"💡 **{ma_days}일 이동평균선**이 적용되었습니다. (평균을 내기 위한 초기 {ma_days-1}일의 데이터는 그래프에 표시되지 않습니다.)")
    else:
        st.markdown("선택한 기간의 첫 날짜를 **0%** 기준으로 잡고 변화한 수치를 보여줍니다. 하단의 **타임 슬라이더**를 조절해 특정 기간을 확대해 보세요.")

    # 차트 그리기
    fig = px.line(df_returns, x=df_returns.index, y=df_returns.columns,
                  labels={'value': '변화율 (%)', 'Date': '날짜', 'variable': '종목명'},
                  title="기간 내 변화율 추이 (주식 수익률 및 환율)")
    
    # 하단에 시간을 조절할 수 있는 범위 슬라이더(Range Slider) 추가
    fig.update_xaxes(rangeslider_visible=True)
    
    st.plotly_chart(fig, use_container_width=True)

    # 요약표 출력
    st.subheader("📋 주요 종목 수치 요약표")
    summary_data = []
    
    for col in df_close.columns:
        start_price = df_close[col].dropna().iloc[0] # 결측치 제외 후 첫 데이터
        end_price = df_close[col].dropna().iloc[-1]  # 결측치 제외 후 마지막 데이터
        total_return = (end_price - start_price) / start_price * 100
        
        summary_data.append({
            "항목명": col,
            "시작값": round(start_price, 2),
            "종료값": round(end_price, 2),
            "최종 변화율 (%)": round(total_return, 2)
        })

    df_summary = pd.DataFrame(summary_data).sort_values(by="최종 변화율 (%)", ascending=False).reset_index(drop=True)
    st.dataframe(df_summary, use_container_width=True)

else:
    st.warning("👈 왼쪽 사이드바에서 비교할 항목을 하나 이상 선택해주세요.")
