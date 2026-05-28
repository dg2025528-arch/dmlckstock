import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import feedparser
from bs4 import BeautifulSoup
from datetime import date, timedelta

# 페이지 기본 설정
st.set_page_config(page_title="한/미 경제 및 뉴스 대시보드", layout="wide")

st.title("📈 종합 경제 대시보드 (주식·환율·뉴스)")
st.markdown("당곡고등학교 학생들을 위한 심화 대시보드입니다. 환율은 크게 확인하고, 경제 뉴스는 썸네일과 함께 컴팩트하게 읽어보세요!")

# --- 1. 사이드바 설정 ---
st.sidebar.header("⚙️ 데이터 설정")
start_date = st.sidebar.date_input("최초 시작일", date.today() - timedelta(days=365*3))
end_date = st.sidebar.date_input("최초 종료일", date.today())

stocks_dict = {
    "원/달러 환율 (USD/KRW)": "KRW=X",
    "KOSPI 지수": "^KS11",
    "삼성전자 (반도체)": "005930.KS",
    "S&P 500 지수": "^GSPC",
    "애플 (IT/기기)": "AAPL",
    "엔비디아 (반도체)": "NVDA"
}

selected_stocks = st.sidebar.multiselect(
    "분석할 항목을 선택하세요",
    options=list(stocks_dict.keys()),
    default=["원/달러 환율 (USD/KRW)", "KOSPI 지수", "삼성전자 (반도체)", "S&P 500 지수", "애플 (IT/기기)"]
)

@st.cache_data
def load_data(tickers, start, end):
    data = yf.download(tickers, start=start, end=end)["Close"]
    if isinstance(data, pd.Series):
        data = data.to_frame(name=tickers[0])
    return data

if selected_stocks:
    tickers = [stocks_dict[stock] for stock in selected_stocks]

    with st.spinner('데이터를 불러오고 있습니다...'):
        df_close = load_data(tickers, start_date, end_date)

    # 💡 [핵심 해결 포인트] 결측치 완벽 처리
    df_close.ffill(inplace=True) # 1. 앞의 데이터로 빈칸 채우기 (중간 휴장일 해결)
    df_close.bfill(inplace=True) # 2. 뒤의 데이터로 빈칸 당겨 채우기 (첫날 휴장일 해결!)
    
    rename_dict = {ticker: name for name, ticker in stocks_dict.items()}
    df_close.rename(columns=rename_dict, inplace=True)
    
    min_date = df_close.index.min().date()
    max_date = df_close.index.max().date()

    st.markdown("---")
    
    # --- 2. 조이스틱 (기간 슬라이더) ---
    selected_range = st.slider(
        "🕹️ 마우스로 양 끝을 움직여 분석할 기간을 조절하세요:",
        min_value=min_date,
        max_value=max_date,
        value=(min_date, max_date),
        format="YYYY-MM-DD"
    )

    # 선택된 기간으로 데이터 필터링
    mask = (df_close.index.date >= selected_range[0]) & (df_close.index.date <= selected_range[1])
    df_filtered = df_close.loc[mask].copy() # Warning 방지를 위해 copy() 추가

    if not df_filtered.empty:
        
        # --- 3. 최상단: 환율 크게 보여주기 ---
        fx_col = "원/달러 환율 (USD/KRW)"
        if fx_col in df_filtered.columns:
            start_fx = df_filtered[fx_col].iloc[0]
            current_fx = df_filtered[fx_col].iloc[-1]
            fx_diff = current_fx - start_fx
            
            st.metric(
                label=f"💵 선택 기간 마지막 날의 원/달러 환율 (기준: {selected_range[1]})", 
                value=f"{current_fx:,.1f} 원", 
                delta=f"{fx_diff:,.1f} 원 (선택 기간 시작일 대비)"
            )
            st.markdown("<br>", unsafe_allow_html=True)

        # --- 4. 화면 분할: 차트 / 뉴스 ---
        col_chart, col_news = st.columns([7, 3])

        with col_chart:
            # 환율 그래프
            if fx_col in df_filtered.columns:
                fig_fx = px.line(df_filtered, x=df_filtered.index, y=fx_col)
                fig_fx.update_layout(title="원/달러 환율 추이 (보조 차트)", height=200, margin=dict(t=30, b=10))
                fig_fx.update_traces(line_color='gray')
                st.plotly_chart(fig_fx, use_container_width=True)

            # 주식 수익률 그래프
            stock_cols = [col for col in df_filtered.columns if col != fx_col]
            if stock_cols:
                df_stocks = df_filtered[stock_cols]
                
                # 💡 [핵심 해결 포인트 2] 슬라이더로 자른 데이터에서도 첫날이 비어있을 수 있으므로 bfill 적용
                first_valid_prices = df_stocks.bfill().iloc[0] 
                
                # 이제 첫날 데이터가 안전하게 확보되었으므로 계산 가능!
                df_returns = (df_stocks / first_valid_prices - 1) * 100
                
                fig_stocks = px.line(df_returns, x=df_returns.index, y=df_returns.columns,
                                     labels={'value': '누적 수익률 (%)', 'Date': '날짜', 'variable': '종목명'},
                                     title="📈 주요 주식 및 지수 누적 수익률")
                fig_stocks.update_layout(height=450)
                st.plotly_chart(fig_stocks, use_container_width=True)

        with col_news:
            st.subheader("📰 최신 경제 뉴스")
            st.caption("구글 뉴스 제공")
            
            try:
                rss_url = "https://news.google.com/rss/search?q=경제&hl=ko&gl=KR&ceid=KR:ko"
                feed = feedparser.parse(rss_url)
                
                news_html = "<div style='display:flex; flex-direction:column; gap:12px;'>"
                
                for entry in feed.entries[:8]:
                    title = entry.title
                    link = entry.link
                    
                    soup = BeautifulSoup(entry.description, 'html.parser')
                    img_tag = soup.find('img')
                    img_url = img_tag['src'] if img_tag else "https://via.placeholder.com/60?text=News"
                    
                    news_html += f"""
                    <div style="display: flex; align-items: center; border-bottom: 1px solid #ddd; padding-bottom: 8px;">
                        <img src="{img_url}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 5px; margin-right: 12px; flex-shrink: 0;">
                        <a href="{link}" target="_blank" style="font-size: 14px; text-decoration: none; color: inherit; line-height: 1.3;">{title}</a>
                    </div>
                    """
                news_html += "</div>"
                
                st.markdown(news_html, unsafe_allow_html=True)
                    
            except Exception as e:
                st.error("뉴스를 불러오는 중 오류가 발생했습니다.")
else:
    st.warning("👈 왼쪽 사이드바에서 비교할 항목을 하나 이상 선택해주세요.")
