import random
import numpy as np
import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh

# ---------------------------------------------------------
# 1. 페이지 및 자동 갱신 (10초 = 10,000ms) 설정
# ---------------------------------------------------------
st.set_page_config(page_title="200개 종목 서바이벌 투자 시뮬레이션", layout="wide")
st_autorefresh(interval=10000, key="stock_survival_game_refresh")

# ---------------------------------------------------------
# 2. 세션 상태 (Session State) 초기화
# ---------------------------------------------------------
NUM_STOCKS = 200
INITIAL_PRICE = 100000
INITIAL_CASH = 100000000  # 1억 원

if "initialized" not in st.session_state:
    st.session_state.cash = INITIAL_CASH
    st.session_state.event_logs = []  # 사건/사고 로그 기록용
    
    # 200개 종목 생성 (기업_001 ~ 기업_200)
    stock_names = [f"기업_{i+1:03d}" for i in range(NUM_STOCKS)]
    
    st.session_state.stocks = pd.DataFrame({
        "종목명": stock_names,
        "현재가": [float(INITIAL_PRICE)] * NUM_STOCKS,
        "초인가": [float(INITIAL_PRICE)] * NUM_STOCKS,
        "변동률(%)": [0.0] * NUM_STOCKS,
        "파산여부": [False] * NUM_STOCKS,
        "보유수량": [0] * NUM_STOCKS,
        "팀": ["무소속"] * NUM_STOCKS,
        "이전순위": [999] * NUM_STOCKS,
        "응원남은턴": [0] * NUM_STOCKS  # 응원 버프 남은 턴 수
    }).set_index("종목명")
    
    st.session_state.initialized = True

# ---------------------------------------------------------
# 3. 10초마다 실행되는 시세 및 이벤트 로직
# ---------------------------------------------------------
def update_game_state():
    stocks = st.session_state.stocks
    
    # 1. 이전 순위 계산 (상위 10위 혜택 부여용)
    rank_series = stocks["현재가"].rank(ascending=False, method="min")
    for symbol in stocks.index:
        stocks.loc[symbol, "이전순위"] = rank_series[symbol]

    # 2. 개별 주가 변동 및 파산 체크
    teams = ["🔴 Red", "🔵 Blue", "🟡 Yellow"]
    
    for symbol in stocks.index:
        if stocks.loc[symbol, "파산여부"]:
            continue
            
        is_top10 = stocks.loc[symbol, "이전순위"] <= 10
        cheer_turns = stocks.loc[symbol, "응원남은턴"]
        
        # 0.01% 확률로 갑작스러운 돌연 부도
        if np.random.rand() < 0.0001:
            stocks.loc[symbol, "현재가"] = 0
            stocks.loc[symbol, "파산여부"] = True
            stocks.loc[symbol, "변동률(%)"] = -100.0
            st.session_state.event_logs.append(f"💥 [{symbol}] 갑작스러운 자금난으로 돌연 부도 처리 (파산)")
            continue

        # 0.1% 확률로 팀 결성/가입
        if stocks.loc[symbol, "팀"] == "무소속" and np.random.rand() < 0.001:
            assigned_team = random.choice(teams)
            stocks.loc[symbol, "팀"] = assigned_team
            st.session_state.event_logs.append(f"🤝 [{symbol}] 이(가) {assigned_team} 동맹에 가입했습니다.")

        # 가격 변동 범위 설정
        # 1) 응원 버프 적용 중 (3턴 동안): -30% ~ +150%
        # 2) 상위 10위 혜택: -50% ~ +100%
        # 3) 일반: -100% ~ +100%
        if cheer_turns > 0:
            min_rate, max_rate = -0.3, 1.5
            stocks.loc[symbol, "응원남은턴"] -= 1  # 턴 차감
        elif is_top10:
            min_rate, max_rate = -0.5, 1.0
        else:
            min_rate, max_rate = -1.0, 1.0
            
        change_rate = np.random.uniform(min_rate, max_rate)
        
        current_price = stocks.loc[symbol, "현재가"]
        new_price = current_price * (1.0 + change_rate)
        
        if new_price <= 0:
            stocks.loc[symbol, "현재가"] = 0
            stocks.loc[symbol, "파산여부"] = True
            stocks.loc[symbol, "변동률(%)"] = -100.0
            st.session_state.event_logs.append(f"💸 [{symbol}] 주가 0원 도달로 파산 탈락")
        else:
            stocks.loc[symbol, "현재가"] = round(new_price)
            initial = stocks.loc[symbol, "초인가"]
            stocks.loc[symbol, "변동률(%)"] = round(((new_price - initial) / initial) * 100, 2)

    # 3. 1% 확률로 적대적 M&A 공격 이벤트 발생
    if np.random.rand() < 0.01:
        survivors = stocks[~stocks["파산여부"]]
        if len(survivors) > 1:
            attacker = survivors.sample(1).index[0]
            attacker_team = stocks.loc[attacker, "팀"]
            
            possible_targets = survivors[survivors.index != attacker]
            if attacker_team != "무소속":
                possible_targets = possible_targets[possible_targets["팀"] != attacker_team]
                
            if not possible_targets.empty:
                # 자산 상위 종목 중 대상 선정
                target = possible_targets.sort_values(by="현재가", ascending=False).iloc[0].name
                
                # 50% 확률로 M&A 성공(상대 파산)
                if np.random.rand() < 0.5:
                    stocks.loc[target, "현재가"] = 0
                    stocks.loc[target, "파산여부"] = True
                    stocks.loc[target, "변동률(%)"] = -100.0
                    st.session_state.event_logs.append(f"⚔️ [{attacker}] 이(가) [{target}] (을)를 적대적 M&A로 인수해 탈락시켰습니다.")
                else:
                    st.session_state.event_logs.append(f"🛡️ [{attacker}] 의 [{target}] 적대적 M&A 시도가 방어에 막혀 실패했습니다.")

# 시세 업데이트 실행
update_game_state()

# ---------------------------------------------------------
# 4. 화면 레이아웃 구성
# ---------------------------------------------------------
st.title("📈 200개 종목 서바이벌 투자 시뮬레이션")
st.caption("⏱️ **10초마다** 시세가 변동합니다. 원하는 종목을 **응원**하면 3턴 동안 변동 폭이 **-30% ~ +150%**로 상승합니다.")

# 보유 자산 현황
stocks_df = st.session_state.stocks
total_stock_val = (stocks_df["현재가"] * stocks_df["보유수량"]).sum()
total_assets = st.session_state.cash + total_stock_val

m1, m2, m3, m4 = st.columns(4)
m1.metric("보유 현금", f"{int(st.session_state.cash):,} 원")
m2.metric("주식 평가금액", f"{int(total_stock_val):,} 원")
m3.metric("총 자산", f"{int(total_assets):,} 원")
m4.metric("생존 기업 수", f"{len(stocks_df[~stocks_df['파산여부']])} / 200")

st.divider()

left_col, right_col = st.columns([3, 1])

# ---------------------------------------------------------
# [우측 컬럼] 사건 로그 및 TOP 5
# ---------------------------------------------------------
with right_col:
    st.subheader("📜 사건/사고 로그")
    log_container = st.container(height=350)
    with log_container:
        for log in reversed(st.session_state.event_logs):
            st.text(log)
            
    st.divider()
    
    st.subheader("🔥 상승률 TOP 5")
    top_5_up = stocks_df[~stocks_df["파산여부"]].sort_values(by="변동률(%)", ascending=False).head(5)
    for idx, row in top_5_up.iterrows():
        team_tag = f"[{row['팀']}]" if row['팀'] != '무소속' else ""
        cheer_tag = "📣" if row["응원남은턴"] > 0 else ""
        st.write(f"**{idx}** {team_tag}{cheer_tag}: {int(row['현재가']):,}원 (`+{row['변동률(%)']}%`)")

# ---------------------------------------------------------
# [좌측 컬럼] 주식 랭킹 순 표출 및 응원 / 매매 시스템
# ---------------------------------------------------------
with left_col:
    st.subheader("📊 전체 종목 순위 (현재가 높은 순)")
    
    sorted_stocks = stocks_df.sort_values(by="현재가", ascending=False)
    
    # 일괄 거래 버튼
    b1, b2, _ = st.columns([1, 1, 2])
    with b1:
        if st.button("🚀 생존 종목 1주씩 일괄 매수"):
            for symbol in sorted_stocks.index:
                if not stocks_df.loc[symbol, "파산여부"]:
                    price = stocks_df.loc[symbol, "현재가"]
                    if st.session_state.cash >= price:
                        st.session_state.cash -= price
                        st.session_state.stocks.loc[symbol, "보유수량"] += 1
            st.rerun()
            
    with b2:
        if st.button("💰 보유 주식 전량 일괄 매도"):
            for symbol in sorted_stocks.index:
                qty = stocks_df.loc[symbol, "보유수량"]
                if qty > 0:
                    price = stocks_df.loc[symbol, "현재가"]
                    st.session_state.cash += price * qty
                    st.session_state.stocks.loc[symbol, "보유수량"] = 0
            st.rerun()

    st.write("")

    search_term = st.text_input("🔍 종목 검색", placeholder="예: 기업_001")
    
    display_df = sorted_stocks
    if search_term:
        display_df = sorted_stocks[sorted_stocks.index.str.contains(search_term)]
        
    for rank, (symbol, row) in enumerate(display_df.iterrows(), 1):
        with st.container():
            c_info, c_cheer, c_qty, c_buy, c_sell = st.columns([3, 1, 1, 1, 1])
            
            # 태그 및 혜택 표시
            team_badge = f"`{row['팀']}`" if row["팀"] != "무소속" else ""
            top10_badge = "🌟[TOP 10]" if row["이전순위"] <= 10 and not row["파산여부"] else ""
            cheer_badge = f"📣[응원중: {row['응원남은턴']}턴]" if row["응원남은턴"] > 0 else ""
            
            if row["파산여부"]:
                info_text = f"~~{rank}위. {symbol}~~ | 💥 **파산** | 보유: {row['보유수량']}주"
            else:
                info_text = f"**{rank}위. {symbol}** {team_badge} {top10_badge} {cheer_badge} | **{int(row['현재가']):,}원** (`{row['변동률(%)']}%`) | 보유: {row['보유수량']}주"
                
            c_info.markdown(info_text)
            
            if not row["파산여부"]:
                # 응원하기 버튼
                if c_cheer.button("📣 응원", key=f"cheer_{symbol}"):
                    st.session_state.stocks.loc[symbol, "응원남은턴"] = 3
                    st.session_state.event_logs.append(f"🙌 [{symbol}] 이(가) 응원을 받아 3턴 동안 버프(-30%~+150%)가 적용됩니다!")
                    st.rerun()

                qty = c_qty.number_input("수량", min_value=1, value=1, key=f"q_{symbol}", label_visibility="collapsed")
                
                if c_buy.button("매수", key=f"b_{symbol}"):
                    cost = row["현재가"] * qty
                    if st.session_state.cash >= cost:
                        st.session_state.cash -= cost
                        st.session_state.stocks.loc[symbol, "보유수량"] += qty
                        st.rerun()
                    else:
                        st.warning("현금 부족")
                        
                if c_sell.button("매도", key=f"s_{symbol}"):
                    if row["보유수량"] >= qty:
                        st.session_state.cash += row["현재가"] * qty
                        st.session_state.stocks.loc[symbol, "보유수량"] -= qty
                        st.rerun()
                    else:
                        st.warning("수량 부족")
            else:
                c_cheer.write("-")
                c_qty.write("-")
                c_buy.write("-")
                c_sell.write("-")
