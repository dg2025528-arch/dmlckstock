import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import date, timedelta

st.set_page_config(page_title="종목 상세 분석", layout="wide")
st.title("🔍 개별 종목 종합 분석 및 전망")

# 메인 페이지와 동일하게 확장된 주식 목록
stocks_dict = {
    "비트코인 (BTC)": "BTC-USD",
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

st.sidebar.header("⚙️ 분석 종목 선택")
selected_stock = st.sidebar.selectbox("상세 분석할 단일 종목을 선택하세요", list(stocks_dict.keys()))
ticker_symbol = stocks_dict[selected_stock]

# 💡 [핵심 로직] 티커 심볼을 보고 한국 주식인지 미국/코인인지 판별하여 단위(원/달러) 지정
if ticker_symbol.endswith(".KS") or ticker_symbol.endswith(".KQ"):
    curr_unit = "원 (KRW)"
    curr_symbol = "₩"
    num_format = ",.0f" # 원화는 소수점 생략
else:
    curr_unit = "달러 (USD)"
    curr_symbol = "$"
    num_format = ",.2f" # 달러는 소수점 2자리까지 표기

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
        # 단위를 명확하게 추가
        st.metric("현재가", f"{curr_symbol}{current_price:{num_format}}", f"{price_change:{num_format}} ({change_percent:.2f}%)")
    with col2:
        market_cap = info.get('marketCap', '정보 없음')
        if market_cap != '정보 없음':
            # 달러와 원화 시총 단위 다르게 표기
            if curr_unit == "원 (KRW)":
                st.metric("시가총액", f"{market_cap / 1_0000_0000_0000:,.0f} 조원")
            else:
                st.metric("시가총액", f"{market_cap / 1_000_000_000:,.0f} Billion USD")
        else:
            st.metric("시가총액", "정보 없음")
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
        low=hist_data['Low'], close=hist_data['Close'], name='주가'
    )])

    hist_data['MA20'] = hist_data['Close'].rolling(window=20).mean()
    hist_data['MA60'] = hist_data['Close'].rolling(window=60).mean()

    fig.add_trace(go.Scatter(x=hist_data.index, y=hist_data['MA20'], line=dict(color='orange', width=1.5), name='20일선 (단기)'))
    fig.add_trace(go.Scatter(x=hist_data.index, y=hist_data['MA60'], line=dict(color='blue', width=1.5), name='60일선 (중장기)'))
    fig.update_layout(height=500, margin=dict(t=20, b=20), xaxis_rangeslider_visible=False, yaxis_title=f"주가 ({curr_unit})")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.subheader("🔮 앞으로의 전망 및 기업 개요")
    
    col_prospect, col_desc = st.columns([1, 1])
    with col_prospect:
        st.markdown(f"**💡 {selected_stock} 월가/증권사 전망**")
        target_price = info.get('targetMeanPrice', '정보 없음')
        recommendation = info.get('recommendationKey', '정보 없음')
        
        if target_price != '정보 없음':
            st.write(f"- **전문가 평균 목표 주가:** {curr_symbol}{target_price:{num_format}}")
        else:
            st.write("- **전문가 평균 목표 주가:** 데이터 없음")
            
        recom_korean = {"buy": "매수 (Buy)", "strong_buy": "강력 매수 (Strong Buy)", "hold": "유지 (Hold)", "sell": "매도 (Sell)", "underperform": "시장 수익률 하회"}
        recom_display = recom_korean.get(str(recommendation).lower(), recommendation)
        st.write(f"- **종합 투자 의견:** {recom_display}")
        
        st.write("- **데이터 추세 진단 (이동평균선 기준):**")
        if not pd.isna(hist_data['MA20'].iloc[-1]):
            if current_price > hist_data['MA20'].iloc[-1]:
                st.success("현재 주가가 20일 이동평균선 위에 있습니다. 단기 상승 추세(Uptrend)입니다.")
            else:
                st.warning("현재 주가가 20일 이동평균선 아래에 있습니다. 단기 하락 추세(Downtrend) 혹은 조정 기간입니다.")
        else:
            st.info("데이터가 부족하여 추세를 진단할 수 없습니다.")

    with col_desc:
        st.markdown("**🏢 비즈니스 요약**")
        summary = info.get('longBusinessSummary', '기업 상세 정보가 제공되지 않았습니다.')
        st.markdown(f"""
            <div style="height: 200px; overflow-y: scroll; padding: 10px; background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 14px; line-height: 1.6;">
                {summary}
            </div>
        """, unsafe_allow_html=True)
else:
    st.error("데이터를 불러오는 데 실패했습니다.")
