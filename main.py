import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import feedparser
from datetime import date, timedelta

# 페이지 기본 설정
st.set_page_config(page_title="한/미 주식 및 경제 분석", layout="wide")

st.title("📈 종합 경제 분석 대시보드 (주식·환율·뉴스)")
st.markdown("당곡고등학교 학생들을 위한 심화 데이터 분석 앱입니다. 기간 슬라이더를 움직여 차트를 조작하고, 최신 경제 뉴스를 함께 확인하여 시장의 흐름을 읽어보세요.")

# --- 1. 사이드바 설정 (데이터 다운로드 기준) ---
st.sidebar.header("⚙️ 데이터 불러오기 설정")
st.sidebar.caption("먼저 전체 데이터를 다운로드할 큰 기간을 설정하세요.")
# 슬라이더 조작을 위해 기본 다운로드 기간을 넉넉하게 3년으로 설정
start_date = st.sidebar.date_input("최초 시작일", date.today() - timedelta(days=365*3))
end_date = st.sidebar.date_input("최초 종료일", date.today())

stocks_dict = {
    "원/달러 환율 (USD/KRW)": "KRW=X",
    "KOSPI 지수": "^KS11",
    "삼성전자 (반도체)": "005930.KS",
    "현대차 (자동차)": "005380.KS",
    "S&P 500 지수": "^GSPC",
    "애플 (IT/기기)": "AAPL",
    "엔비디아 (반도체)": "NVDA"
}

selected_stocks = st.sidebar.multiselect(
    "분석할 종목 및 환율을 선택하세요",
    options=list(stocks_dict.keys()),
    default=["원/달러 환율 (USD/KRW)", "KOSPI 지수", "삼성전자 (반도체)", "S&P 500 지수", "애플 (IT/기기)"]
)

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

    with st.spinner('데이터를 불러오고 있습니다...'):
        df_close = load_data(tickers, start_date, end_date)

    # 결측치 처리 (휴장일 보정)
    df_close.ffill(inplace=True)
    
    # 컬럼명을 한글로 변경
    rename_dict = {ticker: name for name, ticker in stocks_dict.items()}
    df_close.rename(columns=rename_dict, inplace=True)
    
    # 인덱스(시간)에서 날짜만 추출 (슬라이더에서 사용하기 위함)
    min_date = df_close.index.min().date()
    max_date = df_close.index.max().date()

    st.markdown("---")
    st.subheader("🕹️ 분석 기간 조절 (조이스틱)")
    st.markdown("양 끝의 점을 마우스로 드래그하여 분석하고 싶은 정확한 기간을 설정하세요.")
    
    # 스트림릿 슬라이더 (조이스틱 역할)
    selected_range = st.slider(
        "날짜를 선택하세요",
        min_value=min_date,
        max_value=max_date,
        value=(min_date, max_date),
        format="YYYY-MM-DD"
    )

    # 슬라이더에서 선택된 기간으로 데이터프레임 자르기 (Filtering)
    mask = (df_close.index.date >= selected_range[0]) & (df_close.index.date <= selected_range[1])
    df_filtered = df_close.loc[mask]

    # 화면을 두 칸으로 나누기 (차트 영역 / 뉴스 영역)
    col1, col2 = st.columns([2, 1]) # 2:1 비율로 분할

    with col1:
        st.subheader("📊 경제 지표 및 주식 차트")
        
        # 환율 컬럼명 정의
        fx_col = "원/달러 환율 (USD/KRW)"
        
        # 1. 환율 그래프 (환율이 선택되었을 때만 별도로 그림)
        if fx_col in df_filtered.columns:
            st.markdown(f"**💵 {fx_col} 변동 추이 (단위: 원)**")
            fig_fx = px.line(df_filtered, x=df_filtered.index, y=fx_col,
                             labels={'value': '환율 (원)', 'Date': '날짜'})
            fig_fx.update_traces(line_color='green')
            st.plotly_chart(fig_fx, use_container_width=True)
        
        # 2. 주식 수익률 그래프
        # 환율을 제외한 나머지 주식들만 추출
        stock_cols = [col for col in df_filtered.columns if col != fx_col]
        
        if stock_cols:
            st.markdown("**📈 주요 주식 및 지수 누적 수익률 (단위: %)**")
            df_stocks = df_filtered[stock_cols]
            # 조이스틱으로 설정한 시작일을 0% 기준으로 다시 계산
            df_returns = (df_stocks / df_stocks.iloc[0] - 1) * 100
            
            fig_stocks = px.line(df_returns, x=df_returns.index, y=df_returns.columns,
                                 labels={'value': '누적 수익률 (%)', 'Date': '날짜', 'variable': '종목명'})
            st.plotly_chart(fig_stocks, use_container_width=True)

    with col2:
        st.subheader("📰 실시간 경제 주요 뉴스")
        st.markdown("구글 뉴스(Google News) 제공")
        
        # 구글 경제 뉴스 RSS 피드 파싱
        # RSS란 웹사이트의 최신 콘텐츠를 기계가 읽기 쉬운 형태로 제공하는 데이터 포맷입니다.
        try:
            rss_url = "https://news.google.com/rss/search?q=경제&hl=ko&gl=KR&ceid=KR:ko"
            feed = feedparser.parse(rss_url)
            
            # 상위 10개의 뉴스만 출력
            for entry in feed.entries[:10]:
                st.info(f"[{entry.title}]({entry.link})")
                
        except Exception as e:
            st.error("뉴스를 불러오는 중 오류가 발생했습니다.")

else:
    st.warning("👈 왼쪽 사이드바에서 비교할 항목을 하나 이상 선택해주세요.")
