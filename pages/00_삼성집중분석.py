import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import date, timedelta

# 페이지 기본 설정
st.set_page_config(page_title="종목 상세 분석", layout="wide")

st.title("🔍 개별 종목 종합 분석 및 전망")
st.markdown("특정 기업의 현재 상태, 재무 지표, 그리고 애널리스트들의 미래 전망을 종합적으로 분석합니다.")

# 분석할 종목 리스트 (필요한 종목을 자유롭게 더 추가하세요)
stocks_dict = {
    "삼성전자": "005930.KS",
    "SK하이닉스": "000660.KS",
    "현대차": "005380.KS",
    "NAVER": "035420.KS",
    "애플 (Apple)": "AAPL",
    "마이크로소프트 (MSFT)": "MSFT",
    "엔비디아 (NVIDIA)": "NVDA",
    "테슬라 (Tesla)": "TSLA"
}

# 1. 사이드바: 1개의 종목만 선택하도록 selectbox 사용
st.sidebar.header("⚙️ 분석 종목 선택")
selected_stock = st.sidebar.selectbox("상세 분석할 종목을 선택하세요", list(stocks_dict.keys()))
ticker_symbol = stocks_dict[selected_stock]

# 데이터 불러오기
with st.spinner(f'{selected_stock}의 종합 데이터를 분석 중입니다...'):
    # yfinance의 Ticker 객체 생성
    ticker = yf.Ticker(ticker_symbol)
    
    # 최근 1년치 주가 데이터 가져오기
    hist_data = ticker.history(period="1y")
    
    # 기업 종합 정보 가져오기 (시간이 조금 걸릴 수 있음)
    info = ticker.info

if not hist_data.empty:
    st.markdown("---")
    
    # --- 2. 기업 핵심 요약 (상단 메트릭) ---
    current_price = hist_data['Close'].iloc[-1]
    prev_price = hist_data['Close'].iloc[-2]
    price_change = current_price - prev_price
    change_percent = (price_change / prev_price) * 100

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("현재가", f"{current_price:,.0f}", f"{price_change:,.0f} ({change_percent:.2f}%)")
    with col2:
        # get() 함수를 써서 정보가 없을 때(한국 주식 등)의 에러를 방지합니다.
        market_cap = info.get('marketCap', '정보 없음')
        if market_cap != '정보 없음':
            # 보기 쉽게 조 단위로 변환 (대략적)
            st.metric("시가총액", f"{market_cap / 1_0000_0000_0000:,.0f} 조원")
        else:
            st.metric("시가총액", "정보 없음")
    with col3:
        st.metric("52주 최고가", f"{info.get('fiftyTwoWeekHigh', '정보 없음'):,.0f}")
    with col4:
        st.metric("52주 최저가", f"{info.get('fiftyTwoWeekLow', '정보 없음'):,.0f}")

    # --- 3. 캔들스틱 및 이동평균선 차트 (기술적 분석) ---
    st.subheader("📊 기술적 분석 (차트)")
    
    # plotly.graph_objects를 이용한 캔들스틱 차트 생성
    fig = go.Figure(data=[go.Candlestick(
        x=hist_data.index,
        open=hist_data['Open'],
        high=hist_data['High'],
        low=hist_data['Low'],
        close=hist_data['Close'],
        name='주가'
    )])

    # 추세를 보기 위한 이동평균선(Moving Average) 추가
    hist_data['MA20'] = hist_data['Close'].rolling(window=20).mean()
    hist_data['MA60'] = hist_data['Close'].rolling(window=60).mean()

    fig.add_trace(go.Scatter(x=hist_data.index, y=hist_data['MA20'], line=dict(color='orange', width=1.5), name='20일 이동평균선 (단기 추세)'))
    fig.add_trace(go.Scatter(x=hist_data.index, y=hist_data['MA60'], line=dict(color='blue', width=1.5), name='60일 이동평균선 (중장기 추세)'))

    fig.update_layout(height=500, margin=dict(t=20, b=20), xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

    # --- 4. 앞으로의 전망 및 기업 정보 ---
    st.markdown("---")
    st.subheader("🔮 앞으로의 전망 및 기업 개요")
    
    col_prospect, col_desc = st.columns([1, 1])
    
    with col_prospect:
        st.markdown(f"**💡 {selected_stock} 월가/증권사 전망**")
        
        # 애널리스트들의 목표 주가
        target_price = info.get('targetMeanPrice', '정보 없음')
        recommendation = info.get('recommendationKey', '정보 없음')
        
        st.write(f"- **전문가 평균 목표 주가:** {target_price}")
        
        # 투자 의견 한글화 로직
        recom_korean = {"buy": "매수 (Buy)", "strong_buy": "강력 매수 (Strong Buy)", "hold": "유지 (Hold)", "sell": "매도 (Sell)", "underperform": "시장 수익률 하회", "정보 없음": "데이터 없음"}
        recom_display = recom_korean.get(str(recommendation).lower(), recommendation)
        
        st.write(f"- **종합 투자 의견:** {recom_display}")
        
        # 이동평균선을 활용한 데이터 기반 단순 추세 진단
        st.write("- **데이터 추세 진단 (이동평균선 기준):**")
        if not pd.isna(hist_data['MA20'].iloc[-1]):
            if current_price > hist_data['MA20'].iloc[-1]:
                st.success("현재 주가가 20일 이동평균선 위에 있습니다. 단기적으로 상승 추세(Uptrend)에 있다고 해석할 수 있습니다.")
            else:
                st.warning("현재 주가가 20일 이동평균선 아래에 있습니다. 단기적으로 하락 추세(Downtrend)이거나 조정 기간일 수 있습니다.")
        else:
            st.info("데이터가 부족하여 추세를 진단할 수 없습니다.")

    with col_desc:
        st.markdown("**🏢 비즈니스 요약**")
        summary = info.get('longBusinessSummary', '기업 상세 정보가 제공되지 않았습니다.')
        
        # 내용이 너무 길면 스크롤 박스에 담아 깔끔하게 보여주기 (HTML/CSS 활용)
        st.markdown(f"""
            <div style="height: 200px; overflow-y: scroll; padding: 10px; background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 14px; line-height: 1.6;">
                {summary}
            </div>
            <br>
            <span style="font-size:12px; color:gray;">※ yfinance API 특성상 미국 주식의 비즈니스 요약은 영어로, 한국 주식은 비어있는 경우가 많습니다.</span>
        """, unsafe_allow_html=True)

else:
    st.error("데이터를 불러오는 데 실패했습니다. 종목 기호를 확인하거나 잠시 후 다시 시도해주세요.")
