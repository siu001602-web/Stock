import numpy as np
import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh

# ---------------------------------------------------------
# 1. 페이지 및 자동 갱신(30초 = 30,000ms) 설정
# ---------------------------------------------------------
st.set_page_config(page_title="실시간 주식 변동 게임", layout="wide")
st_autorefresh(interval=30000, key="stock_game_refresh")

# ---------------------------------------------------------
# 2. 세션 상태 (Session State) 초기화
# ---------------------------------------------------------
NUM_STOCKS = 50
INITIAL_PRICE = 100000
INITIAL_CASH = 100000000  # 1억 원

if "initialized" not in st.session_state:
    st.session_state.cash = INITIAL_CASH
    
    # 50개 종목 이름 생성 (종목_01 ~ 종목_50)
    stock_names = [f"종목_{i+1:02d}" for i in range(NUM_STOCKS)]
    
    # 주식 데이터 프레임 초기화
    st.session_state.stocks = pd.DataFrame({
        "종목명": stock_names,
        "현재가": [float(INITIAL_PRICE)] * NUM_STOCKS,
        "초인가": [float(INITIAL_PRICE)] * NUM_STOCKS,
        "변동률(%)": [0.0] * NUM_STOCKS,
        "파산여부": [False] * NUM_STOCKS,
        "보유수량": [0] * NUM_STOCKS
    }).set_index("종목명")
    
    st.session_state.initialized = True

# ---------------------------------------------------------
# 3. 가격 변동 및 파산 로직 (30초마다 자동 수행)
# ---------------------------------------------------------
def update_stock_prices():
    stocks = st.session_state.stocks
    
    for symbol in stocks.index:
        # 이미 파산한 주식은 변동하지 않음
        if stocks.loc[symbol, "파산여부"]:
            continue
        
        # 0.01% 확률로 sudden bankruptcy (갑작스러운 파산)
        if np.random.rand() < 0.0001:
            stocks.loc[symbol, "현재가"] = 0
            stocks.loc[symbol, "파산여부"] = True
            stocks.loc[symbol, "변동률(%)"] = -100.0
            continue
        
        # -100% ~ +100% 무작위 변동율 계산
        change_rate = np.random.uniform(-1.0, 1.0)
        current_price = stocks.loc[symbol, "현재가"]
        new_price = current_price * (1.0 + change_rate)
        
        # 가격이 0 이하로 떨어지면 파산 처리
        if new_price <= 0:
            stocks.loc[symbol, "현재가"] = 0
            stocks.loc[symbol, "파산여부"] = True
            stocks.loc[symbol, "변동률(%)"] = -100.0
        else:
            stocks.loc[symbol, "현재가"] = round(new_price)
            # 시작 가격 대비 총 변동률 계산
            initial = stocks.loc[symbol, "초인가"]
            stocks.loc[symbol, "변동률(%)"] = round(((new_price - initial) / initial) * 100, 2)

# 자동 갱신 트리거 시 시세 업데이트
update_stock_prices()

# ---------------------------------------------------------
# 4. 화면 레이아웃 구성
# ---------------------------------------------------------
st.title("📈 50개 종목 실시간 주식 변동 게임")
st.caption("⏱️ 30초마다 시세가 -100% ~ +100% 사이로 무작위 변동하며, 0.01% 확률로 파산합니다.")

# 총 자산 계산 (현금 + 보유 주식 평가금액)
stocks_df = st.session_state.stocks
total_stock_val = (stocks_df["현재가"] * stocks_df["보유수량"]).sum()
total_assets = st.session_state.cash + total_stock_val

# 상단 자산 현황 요약
m1, m2, m3 = st.columns(3)
m1.metric("보유 현금", f"{int(st.session_state.cash):,} 원")
m2.metric("주식 평가금액", f"{int(total_stock_val):,} 원")
m3.metric("총 자산", f"{int(total_assets):,} 원")

st.divider()

# 메인 2컬럼 레이아웃 (좌: 주식 목록 및 거래 / 우: 랭킹 TOP 5)
left_col, right_col = st.columns([3, 1])

# ---------------------------------------------------------
# [오른쪽 컬럼] 급상승 & 급하락 TOP 5
# ---------------------------------------------------------
with right_col:
    st.subheader("🔥 상승률 TOP 5")
    top_5_up = stocks_df.sort_values(by="변동률(%)", ascending=False).head(5)
    for idx, row in top_5_up.iterrows():
        st.write(f"**{idx}**: {int(row['현재가']):,}원 (`+{row['변동률(%)']}%`)")
        
    st.divider()
    
    st.subheader("📉 하락률 TOP 5")
    top_5_down = stocks_df.sort_values(by="변동률(%)", ascending=True).head(5)
    for idx, row in top_5_down.iterrows():
        status = "💥파산" if row["파산여부"] else f"`{row['변동률(%)']}%`"
        st.write(f"**{idx}**: {int(row['현재가']):,}원 ({status})")

# ---------------------------------------------------------
# [왼쪽 컬럼] 가격 랭킹순 목록 & 개별/일괄 매매
# ---------------------------------------------------------
with left_col:
    st.subheader("📊 주식 종목 (현재가 높은 순)")
    
    # 현재가 기준 내림차순 정렬
    sorted_stocks = stocks_df.sort_values(by="현재가", ascending=False)
    
    # 일괄 거래 버튼 구역
    c1, c2, _ = st.columns([1, 1, 2])
    with c1:
        if st.button("🚀 파산 안 한 주식 전종목 1주씩 일괄 매수"):
            for symbol in sorted_stocks.index:
                if not stocks_df.loc[symbol, "파산여부"]:
                    price = stocks_df.loc[symbol, "현재가"]
                    if st.session_state.cash >= price:
                        st.session_state.cash -= price
                        st.session_state.stocks.loc[symbol, "보유수량"] += 1
            st.rerun()

    with c2:
        if st.button("💰 보유 주식 전량 일괄 매도"):
            for symbol in sorted_stocks.index:
                qty = stocks_df.loc[symbol, "보유수량"]
                if qty > 0:
                    price = stocks_df.loc[symbol, "현재가"]
                    st.session_state.cash += price * qty
                    st.session_state.stocks.loc[symbol, "보유수량"] = 0
            st.rerun()

    st.write("")

    # 종목별 테이블 표출 및 개별 거래
    for rank, (symbol, row) in enumerate(sorted_stocks.iterrows(), 1):
        with st.container():
            col_info, col_qty, col_buy, col_sell = st.columns([3, 1, 1, 1])
            
            # 정보 출력
            if row["파산여부"]:
                info_text = f"**{rank}위. {symbol}** | 💥 **파산됨 (거래 불가)** | 보유: {row['보유수량']}주"
            else:
                color = "red" if row["변동률(%)"] > 0 else "blue"
                info_text = f"**{rank}위. {symbol}** | 현재가: **{int(row['현재가']):,}원** (`{row['변동률(%)']}%`) | 보유: {row['보유수량']}주"
            
            col_info.markdown(info_text)
            
            # 파산 종목은 거래 조작 불가
            if not row["파산여부"]:
                trade_qty = col_qty.number_input("수량", min_value=1, value=1, key=f"qty_{symbol}", label_visibility="collapsed")
                
                if col_buy.button("매수", key=f"buy_{symbol}"):
                    cost = row["현재가"] * trade_qty
                    if st.session_state.cash >= cost:
                        st.session_state.cash -= cost
                        st.session_state.stocks.loc[symbol, "보유수량"] += trade_qty
                        st.rerun()
                    else:
                        st.warning("현금이 부족합니다.")
                        
                if col_sell.button("매도", key=f"sell_{symbol}"):
                    if row["보유수량"] >= trade_qty:
                        st.session_state.cash += row["현재가"] * trade_qty
                        st.session_state.stocks.loc[symbol, "보유수량"] -= trade_qty
                        st.rerun()
                    else:
                        st.warning("보유 수량이 부족합니다.")
            else:
                col_qty.write("-")
                col_buy.write("-")
                col_sell.write("-")
