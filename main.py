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
        padding: 15px; border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        margin-bottom: 15px;
    }
</style>
""", unsafe_allow_html=True)

st.title("📊 글로벌 마켓 & 경제 대시보드")
st.markdown("기준 통화를 변경하며 환율이 내 자산에 미치는 영향(환노출)을 직접 분석해 보세요.")

st.sidebar.header("⚙️ 데이터 설정")
start_date = st.sidebar.date_input("최초 시작일", date(2010, 1, 1))
end_date = st.sidebar.date_input("최초 종료일", date.today())

# 💡 [핵심 추가 기능] 기준 통화 선택 토글 버튼
st.sidebar.markdown("---")
currency_choice = st.sidebar.radio(
    "💵 기준 통화 선택", 
    options=["원화 (KRW)", "달러 (USD)"],
    help="선택한 통화로 모든 자산의 가격과 수익률 차트를 변환하여 보여줍니다."
)
st.sidebar.markdown("---")

stocks_dict = {
    "원/달러 환율": "KRW=X",
    "비트코인 (BTC)": "BTC-USD",
    "이더리움 (ETH)": "ETH-USD",
    "KOSPI 지수": "^KS11",
    "NASDAQ 지수": "^IXIC",
    "삼성전자 (반도체)": "005930.KS",
    "SK하이닉스 (반도체)": "000660.KS",
    "현대차 (자동차)": "005380.KS",
    "NAVER (플랫폼)": "035420.KS",
    "카카오 (플랫폼)": "035720.KS",
    "LG에너지솔루션 (2차전지)": "373220.KS",
    "S&P 500 지수": "^GSPC",
    "애플 (IT/기기)": "AAPL",
    "마이크로소프트 (SW)": "MSFT",
    "엔비디아 (AI/반도체)": "NVDA",
    "테슬라 (전기차)": "TSLA",
    "알파벳/구글 (플랫폼)": "GOOGL"
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
    # 💡 [컴퓨터 공학 관점] 사용자가 환율을 선택하지 않아도, 변환을 위해 무조건 환율 데이터를 함께 다운로드합니다.
    raw_tickers = [stocks_dict[s] for s in selected_stocks]
    fetch_tickers = list(set(raw_tickers + ["KRW=X"])) 

    with st.spinner('환율을 적용하여 데이터를 변환 중입니다...'):
        df_close = load_data(fetch_tickers, start_date, end_date)

    df_close.ffill(inplace=True)
    df_close.bfill(inplace=True)
    
    # 딕셔너리의 키와 값을 뒤집어서 티커 심볼을 다시 한글 이름으로 변경
    inv_stocks_dict = {v: k for k, v in stocks_dict.items()}
    df_close.rename(columns=inv_stocks_dict, inplace=True)
    
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
        
        # 💡 [핵심 연산] 환율 변환 로직 (벡터 연산)
        df_converted = df_filtered.copy()
        fx_series = df_filtered["원/달러 환율"] # 그날그날의 환율 데이터
        
        for col_name in df_converted.columns:
            if col_name == "원/달러 환율":
                continue # 환율 자체는 변환하지 않음
                
            ticker_symbol = stocks_dict[col_name]
            # 한국 자산인지 미국 자산인지 판별
            is_krw_native = ticker_symbol.endswith('.KS') or ticker_symbol.endswith('.KQ') or ticker_symbol == '^KS11'
            
            if currency_choice == "원화 (KRW)":
                if not is_krw_native:
                    # 미국 주식일 경우: 달러 주가 * 당일 환율 = 원화 환산 주가
                    df_converted[col_name] = df_converted[col_name] * fx_series
            else: # 달러 (USD)를 선택했을 때
                if is_krw_native:
                    # 한국 주식일 경우: 원화 주가 / 당일 환율 = 달러 환산 주가
                    df_converted[col_name] = df_converted[col_name] / fx_series

        # --- 메트릭(가격표) 섹션 ---
        st.subheader(f"💰 선택 기간 내 종목별 가치 변화 (기준: {currency_choice})")
        
        metric_cols = st.columns(4)
        
        # 💡 화면에 보여줄 때는 사용자가 처음 선택한 'selected_stocks' 목록만 순회합니다.
        for idx, col_name in enumerate(selected_stocks):
            # 1. 포맷팅 설정
            if col_name == "원/달러 환율":
                curr_symbol, unit, num_format = "", "원", ",.1f"
            elif currency_choice == "원화 (KRW)":
                curr_symbol, unit, num_format = "₩", "원", ",.0f"
            else:
                curr_symbol, unit, num_format = "$", "달러", ",.2f"
            
            # 2. 가격 계산 (변환이 완료된 df_converted 사용)
            start_price = df_converted[col_name].bfill().iloc[0]
            end_price = df_converted[col_name].iloc[-1]
            price_diff = end_price - start_price
            percent_diff = (price_diff / start_price) * 100
            
            # 3. 화면 출력
            with metric_cols[idx % 4]:
                st.metric(
                    label=f"{col_name}", 
                    value=f"{curr_symbol}{end_price:{num_format}}", 
                    delta=f"{price_diff:{num_format}} {unit} ({percent_diff:.2f}%)"
                )

        st.markdown("<hr style='margin-top: 5px; margin-bottom: 25px;'>", unsafe_allow_html=True)

        # --- 차트 및 뉴스 섹션 ---
        col_chart, col_news = st.columns([7, 3])

        with col_chart:
            # 환율 보조 차트 (사용자가 환율을 선택했을 때만 표시)
            if "원/달러 환율" in selected_stocks:
                fig_fx = px.line(df_converted, x=df_converted.index, y="원/달러 환율")
                fig_fx.update_layout(title="원/달러 환율 추이", height=200, margin=dict(t=30, b=10, l=0, r=0), plot_bgcolor="white")
                fig_fx.update_traces(line_color='#94a3b8')
                st.plotly_chart(fig_fx, use_container_width=True)

            # 💡 통화가 통일된 주식 수익률 메인 차트
            stock_cols = [col for col in selected_stocks if col != "원/달러 환율"]
            if stock_cols:
                df_stocks = df_converted[stock_cols]
                first_valid_prices = df_stocks.bfill().iloc[0] 
                
                # 변환된 가격을 바탕으로 누적 수익률 계산
                df_returns = (df_stocks / first_valid_prices - 1) * 100
                
                fig_stocks = px.line(df_returns, x=df_returns.index, y=df_returns.columns,
                                     labels={'value': f'누적 수익률 (%) - {currency_choice} 기준', 'Date': '날짜', 'variable': '종목명'},
                                     title=f"📈 주요 종목 누적 수익률 비교 (환율 반영)")
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
