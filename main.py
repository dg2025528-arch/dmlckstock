import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import feedparser
from bs4 import BeautifulSoup
from datetime import date, timedelta

st.set_page_config(page_title="한/미 경제 및 뉴스 대시보드", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    h1, h2, h3 { color: #1f2937; font-weight: 700; }
    [data-testid="stMetric"] {
        background-color: #f8fafc; border: 1px solid #e2e8f0;
        padding: 20px; border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
</style>
""", unsafe_allow_html=True)

st.title("📊 글로벌 마켓 & 경제 대시보드")
st.markdown("당곡고 학생들을 위한 프리미엄 경제 분석 툴입니다.")

st.sidebar.header("⚙️ 데이터 설정")
start_date = st.sidebar.date_input("최초 시작일", date(2010, 1, 1))
end_date = st.sidebar.date_input("최초 종료일", date.today())

# 종목 리스트 대폭 확장 (한국, 미국, 암호화폐)
stocks_dict = {
    "원/달러 환율": "KRW=X",
    "비트코인 (BTC)": "BTC-USD",
    "이더리움 (ETH)": "ETH-USD",
    "KOSPI 지수": "^KS11",
    "KOSDAQ 지수": "^KQ11",
    "삼성전자 (반도체)": "005930.KS",
    "SK하이닉스 (반도체)": "000660.KS",
    "현대차 (자동차)": "005380.KS",
    "기아 (자동차)": "000270.KS",
    "NAVER (플랫폼)": "035420.KS",
    "카카오 (플랫폼)": "035720.KS",
    "셀트리온 (바이오)": "068270.KS",
    "삼성바이오로직스 (바이오)": "207940.KS",
    "LG에너지솔루션 (2차전지)": "373220.KS",
    "POSCO홀딩스 (철강)": "005490.KS",
    "KB금융 (금융)": "105560.KS",
    "S&P 500 지수": "^GSPC",
    "NASDAQ 지수": "^IXIC",
    "다우 존스 지수": "^DJI",
    "애플 (IT/기기)": "AAPL",
    "마이크로소프트 (SW)": "MSFT",
    "엔비디아 (AI/반도체)": "NVDA",
    "테슬라 (전기차)": "TSLA",
    "알파벳/구글 (플랫폼)": "GOOGL",
    "아마존 (이커머스)": "AMZN",
    "메타 (SNS)": "META",
    "AMD (반도체)": "AMD",
    "넷플릭스 (엔터)": "NFLX",
    "JPMorgan (금융)": "JPM",
    "월마트 (유통)": "WMT"
}

# 💡 [핵심 UI 개선] 화면을 차지하던 선택창을 깔끔한 팝오버(버튼) 안으로 숨겼습니다!
with st.sidebar.popover("👇 분석할 주식을 선택하세요 (클릭)"):
    selected_stocks = st.multiselect(
        "비교할 항목을 골라주세요",
        options=list(stocks_dict.keys()),
        default=["원/달러 환율", "KOSPI 지수", "삼성전자 (반도체)", "S&P 500 지수", "애플 (IT/기기)"],
        label_visibility="collapsed" # 위의 제목 숨기기
    )

@st.cache_data
def load_data(tickers, start, end):
    data = yf.download(tickers, start=start, end=end)["Close"]
    if isinstance(data, pd.Series):
        data = data.to_frame(name=tickers[0])
    return data

if selected_stocks:
    tickers = [stocks_dict[stock] for stock in selected_stocks]

    with st.spinner('방대한 데이터를 분석 중입니다. 잠시만 기다려주세요...'):
        df_close = load_data(tickers, start_date, end_date)

    df_close.ffill(inplace=True)
    df_close.bfill(inplace=True)
    
    rename_dict = {ticker: name for name, ticker in stocks_dict.items()}
    df_close.rename(columns=rename_dict, inplace=True)
    
    min_date = df_close.index.min().date()
    max_date = df_close.index.max().date()

    st.markdown("---")
    
    selected_range = st.slider(
        "🕹️ 마우스로 양 끝을 움직여 분석할 정확한 기간을 조절하세요:",
        min_value=min_date, max_value=max_date, value=(min_date, max_date), format="YYYY-MM-DD"
    )

    mask = (df_close.index.date >= selected_range[0]) & (df_close.index.date <= selected_range[1])
    df_filtered = df_close.loc[mask].copy()

    if not df_filtered.empty:
        fx_col = "원/달러 환율"
        if fx_col in df_filtered.columns:
            start_fx = df_filtered[fx_col].iloc[0]
            current_fx = df_filtered[fx_col].iloc[-1]
            fx_diff = current_fx - start_fx
            
            # 단위(원) 명시
            st.metric(
                label=f"💵 원/달러 환율 (기준일: {selected_range[1]})", 
                value=f"{current_fx:,.1f} 원 (KRW)", 
                delta=f"{fx_diff:,.1f} 원 (선택 기간 첫날 대비)"
            )
            st.markdown("<br>", unsafe_allow_html=True)

        col_chart, col_news = st.columns([7, 3])

        with col_chart:
            if fx_col in df_filtered.columns:
                fig_fx = px.line(df_filtered, x=df_filtered.index, y=fx_col)
                fig_fx.update_layout(title="원/달러 환율 추이", height=200, margin=dict(t=30, b=10, l=0, r=0), plot_bgcolor="white")
                fig_fx.update_traces(line_color='#94a3b8')
                st.plotly_chart(fig_fx, use_container_width=True)

            stock_cols = [col for col in df_filtered.columns if col != fx_col]
            if stock_cols:
                df_stocks = df_filtered[stock_cols]
                first_valid_prices = df_stocks.bfill().iloc[0] 
                df_returns = (df_stocks / first_valid_prices - 1) * 100
                
                fig_stocks = px.line(df_returns, x=df_returns.index, y=df_returns.columns,
                                     labels={'value': '누적 수익률 (%)', 'Date': '날짜', 'variable': '종목명'},
                                     title="📈 주요 종목 누적 수익률 비교")
                fig_stocks.update_layout(height=500, plot_bgcolor="white", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
                st.plotly_chart(fig_stocks, use_container_width=True)

        with col_news:
            st.subheader("📰 실시간 경제 뉴스")
            
            # 💡 [핵심 버그 수정] 코드가 깨지지 않도록 스트림릿 고유 기능(st.image, st.markdown) 사용
            try:
                rss_url = "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=ko&gl=KR&ceid=KR:ko"
                feed = feedparser.parse(rss_url)
                
                for entry in feed.entries[:8]:
                    title = entry.title
                    link = entry.link
                    img_url = "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=100&q=80"
                    
                    try:
                        soup = BeautifulSoup(entry.description, 'html.parser')
                        img_tag = soup.find('img')
                        if img_tag and 'src' in img_tag.attrs:
                            img_url = img_tag['src']
                    except:
                        pass
                    
                    # HTML 주입 대신 깔끔하게 컬럼으로 이미지와 텍스트 배치
                    n_col1, n_col2 = st.columns([1, 4])
                    with n_col1:
                        st.image(img_url, use_column_width=True)
                    with n_col2:
                        st.markdown(f"**[{title}]({link})**")
                    st.write("---") # 구분선
                    
            except Exception as e:
                st.error("현재 뉴스 서버와 연결이 원활하지 않습니다.")
else:
    st.info("👈 왼쪽 사이드바에서 분석을 원하는 항목을 선택해주세요.")
