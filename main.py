import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import feedparser
from bs4 import BeautifulSoup
from datetime import date

# 1. 페이지 기본 설정 (가장 먼저 와야 함)
st.set_page_config(page_title="한/미 경제 및 뉴스 대시보드", layout="wide", initial_sidebar_state="expanded")

# 2. 커스텀 CSS 주입 (디자인을 세련되게 만들기)
st.markdown("""
<style>
    /* 전체 배경 및 폰트 느낌 조정 */
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    h1, h2, h3 { color: #1f2937; font-weight: 700; }
    
    /* 환율 메트릭(숫자) 박스 디자인 개선 */
    [data-testid="stMetric"] {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    
    /* 사이드바 디자인 */
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #f1f5f9;
    }
    
    /* 뉴스 링크 호버(마우스 올렸을 때) 효과 */
    .news-link:hover { color: #2563eb !important; text-decoration: underline !important; }
</style>
""", unsafe_allow_html=True)

st.title("📊 글로벌 마켓 & 경제 대시보드")
st.markdown("당곡고 학생들을 위한 프리미엄 경제 분석 툴입니다. 더 많은 종목과 더 넓은 기간을 분석해 보세요.")

# --- 3. 사이드바 설정 (기간 및 종목 대폭 확장) ---
st.sidebar.header("⚙️ 데이터 설정")
st.sidebar.caption("분석을 시작할 기준일을 선택하세요.")
# 기본 시작일을 2010년 1월 1일로 설정 (더 오래전부터)
start_date = st.sidebar.date_input("최초 시작일", date(2010, 1, 1))
end_date = st.sidebar.date_input("최초 종료일", date.today())

# 종목 리스트 대폭 확장 (분야별)
stocks_dict = {
    "원/달러 환율": "KRW=X",
    "비트코인 (BTC)": "BTC-USD",
    "KOSPI 지수": "^KS11",
    "KOSDAQ 지수": "^KQ11",
    "삼성전자 (반도체)": "005930.KS",
    "SK하이닉스 (반도체)": "000660.KS",
    "현대차 (자동차)": "005380.KS",
    "NAVER (플랫폼)": "035420.KS",
    "카카오 (플랫폼)": "035720.KS",
    "S&P 500 지수": "^GSPC",
    "NASDAQ 지수": "^IXIC",
    "애플 (IT/기기)": "AAPL",
    "마이크로소프트 (SW)": "MSFT",
    "엔비디아 (AI/반도체)": "NVDA",
    "테슬라 (전기차)": "TSLA",
    "알파벳/구글 (플랫폼)": "GOOGL",
    "아마존 (이커머스)": "AMZN",
}

selected_stocks = st.sidebar.multiselect(
    "분석할 항목을 선택하세요 (여러 개 선택 가능)",
    options=list(stocks_dict.keys()),
    default=["원/달러 환율", "KOSPI 지수", "삼성전자 (반도체)", "S&P 500 지수", "애플 (IT/기기)"]
)

# 데이터 불러오기 함수 (캐싱)
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

    # 결측치 완벽 처리 (앞뒤로 빈칸 메우기)
    df_close.ffill(inplace=True)
    df_close.bfill(inplace=True)
    
    rename_dict = {ticker: name for name, ticker in stocks_dict.items()}
    df_close.rename(columns=rename_dict, inplace=True)
    
    min_date = df_close.index.min().date()
    max_date = df_close.index.max().date()

    st.markdown("---")
    
    # --- 4. 조이스틱 (기간 슬라이더) ---
    selected_range = st.slider(
        "🕹️ 마우스로 양 끝을 움직여 분석할 정확한 기간을 조절하세요:",
        min_value=min_date,
        max_value=max_date,
        value=(min_date, max_date),
        format="YYYY-MM-DD"
    )

    mask = (df_close.index.date >= selected_range[0]) & (df_close.index.date <= selected_range[1])
    df_filtered = df_close.loc[mask].copy()

    if not df_filtered.empty:
        
        # --- 5. 환율 메트릭 크게 보여주기 ---
        fx_col = "원/달러 환율"
        if fx_col in df_filtered.columns:
            start_fx = df_filtered[fx_col].iloc[0]
            current_fx = df_filtered[fx_col].iloc[-1]
            fx_diff = current_fx - start_fx
            
            st.metric(
                label=f"💵 원/달러 환율 (기준일: {selected_range[1]})", 
                value=f"{current_fx:,.1f} 원", 
                delta=f"{fx_diff:,.1f} 원 (선택 기간 첫날 대비)"
            )
            st.markdown("<br>", unsafe_allow_html=True)

        # --- 6. 화면 분할: 차트(70%) / 뉴스(30%) ---
        col_chart, col_news = st.columns([7, 3])

        with col_chart:
            # 환율이 선택되었을 때만 보조 차트 출력
            if fx_col in df_filtered.columns:
                fig_fx = px.line(df_filtered, x=df_filtered.index, y=fx_col)
                fig_fx.update_layout(
                    title="원/달러 환율 추이", 
                    height=200, 
                    margin=dict(t=30, b=10, l=0, r=0),
                    plot_bgcolor="white"
                )
                fig_fx.update_traces(line_color='#94a3b8') # 세련된 회색
                fig_fx.update_xaxes(showgrid=False)
                fig_fx.update_yaxes(showgrid=True, gridcolor='#f1f5f9')
                st.plotly_chart(fig_fx, use_container_width=True)

            # 주식 수익률 메인 차트
            stock_cols = [col for col in df_filtered.columns if col != fx_col]
            if stock_cols:
                df_stocks = df_filtered[stock_cols]
                first_valid_prices = df_stocks.bfill().iloc[0] 
                
                df_returns = (df_stocks / first_valid_prices - 1) * 100
                
                fig_stocks = px.line(df_returns, x=df_returns.index, y=df_returns.columns,
                                     labels={'value': '누적 수익률 (%)', 'Date': '날짜', 'variable': '종목명'},
                                     title="📈 주요 종목 누적 수익률 비교")
                fig_stocks.update_layout(
                    height=500,
                    plot_bgcolor="white",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                fig_stocks.update_xaxes(showgrid=False)
                fig_stocks.update_yaxes(showgrid=True, gridcolor='#f1f5f9')
                st.plotly_chart(fig_stocks, use_container_width=True)

        with col_news:
            st.subheader("📰 실시간 경제 뉴스")
            st.caption("구글 비즈니스 뉴스 제공")
            
            # 💡 [핵심 해결 포인트] 뉴스 파싱 에러 방지를 위한 튼튼한 코드
            try:
                # 구글 뉴스 경제(비즈니스) 섹션 공식 RSS 피드 사용
                rss_url = "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=ko&gl=KR&ceid=KR:ko"
                feed = feedparser.parse(rss_url)
                
                news_html = "<div style='display:flex; flex-direction:column; gap:16px; margin-top:10px;'>"
                
                for entry in feed.entries[:8]:
                    title = entry.title
                    link = entry.link
                    
                    # 이미지가 없거나 파싱에 실패할 경우를 대비해 안전한 기본 이미지(플레이스홀더) 지정
                    img_url = "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=100&q=80" 
                    
                    try:
                        soup = BeautifulSoup(entry.description, 'html.parser')
                        img_tag = soup.find('img')
                        if img_tag and 'src' in img_tag.attrs:
                            img_url = img_tag['src']
                    except:
                        pass # 이미지 추출 중 에러가 나면 기본 이미지 유지
                    
                    # 세련된 뉴스 리스트 디자인 적용
                    news_html += f"""
                    <div style="display: flex; align-items: flex-start; background: #f8fafc; padding: 12px; border-radius: 8px; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
                        <img src="{img_url}" style="width: 60px; height: 60px; object-fit: cover; border-radius: 6px; margin-right: 12px; flex-shrink: 0; border: 1px solid #e2e8f0;">
                        <a href="{link}" target="_blank" class="news-link" style="font-size: 14px; text-decoration: none; color: #334155; line-height: 1.4; font-weight: 500;">{title}</a>
                    </div>
                    """
                news_html += "</div>"
                
                st.markdown(news_html, unsafe_allow_html=True)
                    
            except Exception as e:
                st.error("현재 뉴스 서버와 연결이 원활하지 않습니다. 잠시 후 다시 시도해주세요.")
else:
    st.info("👈 왼쪽 사이드바에서 분석을 원하는 항목을 선택해주세요.")
