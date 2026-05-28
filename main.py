import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import feedparser
from bs4 import BeautifulSoup
from datetime import date, timedelta

st.set_page_config(page_title="한/미 경제 및 뉴스 대시보드", layout="wide", initial_sidebar_state="expanded")

# CSS를 활용한 디자인 커스텀
st.markdown("""
<style>
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    h1, h2, h3 { color: #1f2937; font-weight: 700; }
    [data-testid="stMetric"] {
        background-color: #f8fafc; border: 1px solid #e2e8f0;
        padding: 15px; border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        margin-bottom: 15px;
    }
</style>
""", unsafe_allow_html=True)

st.title("📊 글로벌 마켓 & 경제 대시보드")
st.markdown("당곡고 학생들을 위한 프리미엄 경제 분석 툴입니다.")

# --- 사이드바 및 설정 ---
st.sidebar.header("⚙️ 데이터 설정")
start_date = st.sidebar.date_input("최초 시작일", date(2010, 1, 1))
end_date = st.sidebar.date_input("최초 종료일", date.today())

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

with st.sidebar.popover("👇 분석할 주식을 선택하세요 (클릭)"):
    selected_stocks = st.multiselect(
        "비교할 항목을 골라주세요",
        options=list(stocks_dict.keys()),
        default=["원/달러 환율", "KOSPI 지수", "삼성전자 (반도체)", "애플 (IT/기기)"],
        label_visibility="collapsed"
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
        
        # 💡 [핵심 추가 기능] 선택한 모든 종목의 현재 가격과 변동을 보여주는 카드 섹션
        st.subheader("💰 선택 기간 내 종목별 가치 변화")
        st.caption(f"조이스틱으로 설정한 시작일({selected_range[0]}) 대비 종료일({selected_range[1]})의 가격 변화입니다.")
        
        # 4개의 열(Column)을 만들어 데이터를 분배할 준비
        metric_cols = st.columns(4)
        
        # 선택한 종목들을 순회하며 가격 계산 및 화면 출력
        for idx, col_name in enumerate(df_filtered.columns):
            ticker_symbol = stocks_dict[col_name]
            
            # 티커 심볼을 보고 원화인지 달러인지 똑똑하게 구분
            if ticker_symbol == "KRW=X":
                curr_symbol = ""
                unit = "원"
                num_format = ",.1f"
            elif ticker_symbol.endswith(".KS") or ticker_symbol.endswith(".KQ"):
                curr_symbol = "₩"
                unit = "원"
                num_format = ",.0f"
            else:
                curr_symbol = "$"
                unit = "달러"
                num_format = ",.2f"
            
            # 슬라이더 기간 내의 첫날 가격과 마지막 날 가격 계산
            start_price = df_filtered[col_name].bfill().iloc[0]
            end_price = df_filtered[col_name].iloc[-1]
            price_diff = end_price - start_price
            percent_diff = (price_diff / start_price) * 100
            
            # 순서대로 4개의 열에 번갈아가며 박스(Metric) 배치
            with metric_cols[idx % 4]:
                st.metric(
                    label=f"{col_name}", 
                    value=f"{curr_symbol}{end_price:{num_format}}", 
                    delta=f"{price_diff:{num_format}} {unit} ({percent_diff:.2f}%)"
                )

        st.markdown("<hr style='margin-top: 5px; margin-bottom: 25px;'>", unsafe_allow_html=True)

        # --- 메인 차트 및 뉴스 섹션 ---
        col_chart, col_news = st.columns([7, 3])

        with col_chart:
            # 환율 그래프 분리 출력
            fx_col = "원/달러 환율"
            if fx_col in df_filtered.columns:
                fig_fx = px.line(df_filtered, x=df_filtered.index, y=fx_col)
                fig_fx.update_layout(title="원/달러 환율 추이", height=200, margin=dict(t=30, b=10, l=0, r=0), plot_bgcolor="white")
                fig_fx.update_traces(line_color='#94a3b8')
                st.plotly_chart(fig_fx, use_container_width=True)

            # 주식 수익률 비교 메인 차트
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
                    
                    n_col1, n_col2 = st.columns([1, 4])
                    with n_col1:
                        st.image(img_url, use_column_width=True)
                    with n_col2:
                        st.markdown(f"**[{title}]({link})**")
                    st.write("---")
                    
            except Exception as e:
                st.error("현재 뉴스 서버와 연결이 원활하지 않습니다.")
else:
    st.info("👈 왼쪽 사이드바에서 분석을 원하는 항목을 선택해주세요.")
