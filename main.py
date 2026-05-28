import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import feedparser
import urllib.parse
from datetime import date, timedelta

st.set_page_config(page_title="종목 상세 분석", layout="wide")
st.title("🔍 개별 자산 종합 분석 및 전망")

# 메인 페이지와 동일한 주식/자산 목록
stocks_dict = {
    "비트코인 (BTC)": "BTC-USD",
    "이더리움 (ETH)": "ETH-USD",
    "KOSPI 지수": "^KS11",
    "NASDAQ 지수": "^IXIC",
    "삼성전자 (반도체)": "005930.KS",
    "SK하이닉스 (반도체)": "000660.KS",
    "현대차 (자동차)": "005380.KS",
    "기아 (자동차)": "000270.KS",
    "NAVER (플랫폼)": "035420.KS",
    "카카오 (플랫폼)": "035720.KS",
    "셀트리온 (바이오)": "068270.KS",
    "삼성바이오로직스 (바이오)": "207940.KS",
    "LG에너지솔루션 (2차전지)": "373220.KS",
    "애플 (IT/기기)": "AAPL",
    "마이크로소프트 (SW)": "MSFT",
    "엔비디아 (AI/반도체)": "NVDA",
    "테슬라 (전기차)": "TSLA",
    "알파벳/구글 (플랫폼)": "GOOGL",
    "아마존 (이커머스)": "AMZN",
    "메타 (SNS)": "META",
    "AMD (반도체)": "AMD",
    "넷플릭스 (엔터)": "NFLX"
}

st.sidebar.header("⚙️ 분석 항목 선택")
selected_stock = st.sidebar.selectbox("상세 분석할 자산을 선택하세요", list(stocks_dict.keys()))
ticker_symbol = stocks_dict[selected_stock]

# 💡 [핵심 학습] 데이터 속성 판별기
# 선택한 자산이 암호화폐/지수인지, 일반 기업(주식)인지 코드가 스스로 판단합니다.
is_crypto = ticker_symbol.endswith("-USD")
is_index = ticker_symbol.startswith("^")
is_company = not (is_crypto or is_index)

# 통화 단위 포맷팅
if ticker_symbol.endswith(".KS") or ticker_symbol.endswith(".KQ") or ticker_symbol == "^KS11":
    curr_unit = "원 (KRW)"
    curr_symbol = "₩"
    num_format = ",.0f" 
else:
    curr_unit = "달러 (USD)"
    curr_symbol = "$"
    num_format = ",.2f"

with st.spinner(f'{selected_stock}의 종합 데이터를 분석 중입니다...'):
    ticker = yf.Ticker(ticker_symbol)
    hist_data = ticker.history(period="1y")
    info = ticker.info

if not hist_data.empty:
    st.markdown("---")
    
    current_price = hist_data['Close'].iloc[-1]
    prev_price = hist_data['Close'].iloc[-2]
    price_change = current_price - prev_price
    change_percent = (price_change / prev_price) * 100

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("현재가", f"{curr_symbol}{current_price:{num_format}}", f"{price_change:{num_format}} ({change_percent:.2f}%)")
    with col2:
        market_cap = info.get('marketCap', '정보 없음')
        if market_cap != '정보 없음':
            if curr_unit == "원 (KRW)":
                st.metric("시가총액", f"{market_cap / 1_0000_0000_0000:,.0f} 조원")
            else:
                st.metric("시가총액", f"{market_cap / 1_000_000_000:,.0f} Billion USD")
        else:
            st.metric("시가총액", "해당 없음 (지수/일부 자산)")
    with col3:
        high_52 = info.get('fiftyTwoWeekHigh', '정보 없음')
        if high_52 != '정보 없음':
            st.metric("52주 최고가", f"{curr_symbol}{high_52:{num_format}}")
        else:
            st.metric("52주 최고가", "정보 없음")
    with col4:
        low_52 = info.get('fiftyTwoWeekLow', '정보 없음')
        if low_52 != '정보 없음':
            st.metric("52주 최저가", f"{curr_symbol}{low_52:{num_format}}")
        else:
            st.metric("52주 최저가", "정보 없음")

    st.subheader("📊 기술적 분석 (차트)")
    fig = go.Figure(data=[go.Candlestick(
        x=hist_data.index,
        open=hist_data['Open'], high=hist_data['High'],
        low=hist_data['Low'], close=hist_data['Close'], name='가격'
    )])

    hist_data['MA20'] = hist_data['Close'].rolling(window=20).mean()
    hist_data['MA60'] = hist_data['Close'].rolling(window=60).mean()

    fig.add_trace(go.Scatter(x=hist_data.index, y=hist_data['MA20'], line=dict(color='orange', width=1.5), name='20일선 (단기)'))
    fig.add_trace(go.Scatter(x=hist_data.index, y=hist_data['MA60'], line=dict(color='blue', width=1.5), name='60일선 (중장기)'))
    fig.update_layout(height=500, margin=dict(t=20, b=20), xaxis_rangeslider_visible=False, yaxis_title=f"가격 ({curr_unit})")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    
    # 💡 자산 성격(기업 vs 코인/지수)에 따라 하단 내용을 다르게 표시
    if is_company:
        st.subheader("🔮 기업 전망 및 비즈니스 개요")
    else:
        st.subheader(f"🔮 {selected_stock} 시장 전망 및 전문가 견해")
    
    col_prospect, col_desc = st.columns([1, 1])
    
    with col_prospect:
        # 기술적 분석 (공통)
        st.markdown("**📉 데이터 추세 진단 (이동평균선 기준)**")
        if not pd.isna(hist_data['MA20'].iloc[-1]):
            if current_price > hist_data['MA20'].iloc[-1]:
                st.success("현재 가격이 20일 이동평균선 위에 있습니다. 단기 상승 추세(Uptrend)입니다.")
            else:
                st.warning("현재 가격이 20일 이동평균선 아래에 있습니다. 단기 하락 추세(Downtrend) 혹은 조정 기간입니다.")
        else:
            st.info("데이터가 부족하여 추세를 진단할 수 없습니다.")
            
        st.markdown("<br>", unsafe_allow_html=True)
        
        # 기업일 때만 목표 주가 표시
        if is_company:
            st.markdown(f"**📈 월가/증권사 목표 주가**")
            target_price = info.get('targetMeanPrice', '정보 없음')
            recommendation = info.get('recommendationKey', '정보 없음')
            
            if target_price != '정보 없음':
                st.write(f"- **전문가 평균 목표가:** {curr_symbol}{target_price:{num_format}}")
            else:
                st.write("- **전문가 평균 목표가:** 데이터 없음")
                
            recom_korean = {"buy": "매수 (Buy)", "strong_buy": "강력 매수 (Strong Buy)", "hold": "유지 (Hold)", "sell": "매도 (Sell)", "underperform": "시장 수익률 하회"}
            recom_display = recom_korean.get(str(recommendation).lower(), recommendation)
            st.write(f"- **종합 투자 의견:** {recom_display}")
        else:
            st.markdown(f"**💡 자산 특성 요약**")
            st.write(f"이 항목({selected_stock})은 개별 기업이 아니므로 증권사 목표 주가가 제공되지 않습니다. 대신 우측의 관련 뉴스와 전문가 견해를 참고하여 거시적인 시장 흐름을 파악하는 것이 중요합니다.")

    with col_desc:
        if is_company:
            st.markdown("**🏢 비즈니스 요약**")
            summary = info.get('longBusinessSummary', '기업 상세 정보가 제공되지 않았습니다.')
            st.markdown(f"""
                <div style="height: 200px; overflow-y: scroll; padding: 15px; background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 14px; line-height: 1.6;">
                    {summary}
                </div>
            """, unsafe_allow_html=True)
        else:
            # 💡 암호화폐나 지수일 경우, 비즈니스 요약 대신 '동적 맞춤형 뉴스 크롤러'를 가동합니다.
            st.markdown(f"**📰 {selected_stock.split(' ')[0]} 관련 최신 뉴스 및 전문가 분석**")
            try:
                # 검색어 생성 (예: "비트코인 전망 OR 분석")
                search_keyword = f"{selected_stock.split(' ')[0]} 전망 OR 분석"
                # 한글 검색어를 URL에 쓸 수 있게 인코딩
                encoded_query = urllib.parse.quote(search_keyword)
                rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=ko&gl=KR&ceid=KR:ko"
                
                feed = feedparser.parse(rss_url)
                
                news_html = "<div style='height: 200px; overflow-y: scroll; padding: 15px; background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px;'>"
                if len(feed.entries) > 0:
                    for entry in feed.entries[:5]: # 최신 뉴스 5개만 추출
                        news_html += f"<div style='margin-bottom: 10px;'><a href='{entry.link}' target='_blank' style='text-decoration: none; color: #1e3a8a; font-weight: 500; font-size: 14px;'>📌 {entry.title}</a></div>"
                else:
                    news_html += "관련 뉴스를 찾을 수 없습니다."
                news_html += "</div>"
                st.markdown(news_html, unsafe_allow_html=True)
                
            except Exception as e:
                st.error("최신 분석 정보를 불러오는 데 실패했습니다.")

else:
    st.error("데이터를 불러오는 데 실패했습니다.")
