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
# 2. 세션 상태 (Session State) 초기화 및 200개 리얼 기업명 생성
# ---------------------------------------------------------
NUM_STOCKS = 200
INITIAL_PRICE = 100000
INITIAL_CASH = 100000000  # 1억 원

if "initialized" not in st.session_state:
    st.session_state.cash = INITIAL_CASH
    st.session_state.event_logs = []  # 직전 턴 사건/사고 로그
    st.session_state.bankruptcy_tickets = 0  # 플레이어 보유 부도권 개수
    
    st.session_state.team_bankruptcy_counts = {
        "🔴 Red": 0,
        "🔵 Blue": 0,
        "🟡 Yellow": 0,
        "플레이어": 0
    }
    
    # 200개의 다양한 한글 기업명 자동 조합 생성
    prefixes = ["미래", "글로벌", "대한", "넥스트", "유니온", "에이펙스", "한성", "태양", "한국", "하이퍼", "코리아", "스마트", "비전", "누리", "대성"]
    suffixes = ["전자", "바이오", "케미칼", "테크", "홀딩스", "에너지", "솔루션", "시스템", "디지털", "소프트", "인베스트", "물산", "통신", "제약", "로보틱스"]
    
    stock_names = []
    for p in prefixes:
        for s in suffixes:
            stock_names.append(f"{p}{s}")
            
    stock_names = stock_names[:NUM_STOCKS]
    if len(stock_names) < NUM_STOCKS:
        for i in range(len(stock_names), NUM_STOCKS):
            stock_names.append(f"한국기업_{i+1:03d}")
            
    random.shuffle(stock_names)
    
    st.session_state.stocks = pd.DataFrame({
        "종목명": stock_names,
        "현재가": [float(INITIAL_PRICE)] * NUM_STOCKS,
        "초인가": [float(INITIAL_PRICE)] * NUM_STOCKS,
        "변동률(%)": [0.0] * NUM_STOCKS,
        "파산여부": [False] * NUM_STOCKS,
        "보유수량": [0] * NUM_STOCKS,
        "팀": ["무소속"] * NUM_STOCKS,
        "이전순위": [999] * NUM_STOCKS,
        "응원남은턴": [0] * NUM_STOCKS,      
        "팀버프남은턴": [0] * NUM_STOCKS,
        "공매도남은턴": [0] * NUM_STOCKS     
    }).set_index("종목명")
    
    st.session_state.initialized = True

# ---------------------------------------------------------
# 3. 부도 처리 함수 (물귀신 전략 공통 적용)
# ---------------------------------------------------------
def bankruptcy_company(symbol, reason_msg, current_logs):
    stocks = st.session_state.stocks
    if stocks.loc[symbol, "파산여부"]:
        return
        
    current_rank = int(stocks.loc[symbol, "이전순위"])
    stocks.loc[symbol, "현재가"] = 0
    stocks.loc[symbol, "파산여부"] = True
    stocks.loc[symbol, "변동률(%)"] = -100.0
    current_logs.append(f"💥 [종합 {current_rank}위] [{symbol}] {reason_msg}")

    # 물귀신 전략: 10% 확률로 다른 생존 기업 1개를 랜덤하게 같이 부도시킴
    survivors = stocks[~stocks["파산여부"]]
    if len(survivors) > 0 and np.random.rand() < 0.10:
        dragged_symbol = survivors.sample(1).index[0]
        dragged_rank = int(stocks.loc[dragged_symbol, "이전순위"])
        stocks.loc[dragged_symbol, "현재가"] = 0
        stocks.loc[dragged_symbol, "파산여부"] = True
        stocks.loc[dragged_symbol, "변동률(%)"] = -100.0
        current_logs.append(f"👻 [물귀신 발동] [{symbol}]의 여파로 [종합 {dragged_rank}위] [{dragged_symbol}]이(가) 휘말려 동반 부도 처리되었습니다!")

# ---------------------------------------------------------
# 4. 사이드바: 게임 난이도 조절 및 플레이어 부도권 관리 패널
# ---------------------------------------------------------
st.sidebar.header("⚙️ 게임 난이도 및 액션")
st.sidebar.caption("실시간으로 주가 변동 폭을 조절하고 부도권을 관리하세요.")

user_min_rate = st.sidebar.slider("최대 하락률 (%)", min_value=-100, max_value=-10, value=-100, step=5) / 100.0
user_max_rate = st.sidebar.slider("최대 상승률 (%)", min_value=10, max_value=200, value=100, step=5) / 100.0

st.sidebar.divider()
st.sidebar.subheader("⚔️ 적대적 M&A 부도권")
st.sidebar.write(f"보유 부도권: **{st.session_state.bankruptcy_tickets} 개**")

if st.sidebar.button("💸 부도권 구매 (1,000,000원)"):
    if st.session_state.cash >= 1000000:
        st.session_state.cash -= 1000000
        st.session_state.bankruptcy_tickets += 1
        st.sidebar.success("부도권 1개를 획득했습니다!")
        st.rerun()
    else:
        st.sidebar.warning("현금이 부족합니다! (100만원 필요)")

# ---------------------------------------------------------
# 5. 10초마다 실행되는 시세 및 이벤트 로직
# ---------------------------------------------------------
def update_game_state():
    stocks = st.session_state.stocks
    current_turn_logs = []
    
    rank_series = stocks["현재가"].rank(ascending=False, method="first")
    for symbol in stocks.index:
        stocks.loc[symbol, "이전순위"] = int(rank_series[symbol])

    teams = ["🔴 Red", "🔵 Blue", "🟡 Yellow"]
    total_survivors_count = len(stocks[~stocks["파산여부"]])
    survivors = stocks[~stocks["파산여부"]]

    # --- [글로벌 경제 위기 (블랙 먼데이) 이벤트] ---
    # 생존 기업 수가 절반(100개) 이하일 때 5% 확률로 발생
    if total_survivors_count <= (NUM_STOCKS / 2) and np.random.rand() < 0.05:
        current_turn_logs.append("🚨 [블랙 먼데이] 글로벌 금융 위기가 터졌습니다! 모든 생존 기업의 주가가 일제히 -30폭락하고 모든 버프가 소멸합니다!")
        for symbol in survivors.index:
            old_price = stocks.loc[symbol, "현재가"]
            new_price = max(10, round(old_price * 0.7))
            stocks.loc[symbol, "현재가"] = new_price
            initial = stocks.loc[symbol, "초인가"]
            stocks.loc[symbol, "변동률(%)"] = round(((new_price - initial) / initial) * 100, 2)
            stocks.loc[symbol, "응원남은턴"] = 0
            stocks.loc[symbol, "팀버프남은턴"] = 0
            stocks.loc[symbol, "공매도남은턴"] = 0
        st.session_state.event_logs = current_turn_logs
        return

    # --- [랜덤 글로벌 이벤트 발생] ---
    if len(survivors) > 0:
        # 1. 공매도 세력의 습격 (2% 확률)
        if len(survivors) >= 5 and np.random.rand() < 0.02:
            top5_survivors = survivors.sort_values(by="현재가", ascending=False).head(5)
            victim = top5_survivors.sample(1).index[0]
            if stocks.loc[victim, "공매도남은턴"] == 0:
                victim_rank = int(stocks.loc[victim, "이전순위"])
                stocks.loc[victim, "공매도남은턴"] = 3
                current_turn_logs.append(f"📉 [공매도 습격] [종합 {victim_rank}위] [{victim}]이(가) 공매도의 집중 공격을 받아 3턴간 하락 압력(-60%~-20%)을 받습니다!")

        # 2. 대형 회계 감사 스캔들 (1% 확률)
        if np.random.rand() < 0.01:
            scandal_victim = survivors.sample(1).index[0]
            victim_rank = int(stocks.loc[scandal_victim, "이전순위"])
            old_price = stocks.loc[scandal_victim, "현재가"]
            new_price = round(old_price * 0.5)
            stocks.loc[scandal_victim, "현재가"] = new_price
            stocks.loc[scandal_victim, "팀"] = "무소속"
            initial = stocks.loc[scandal_victim, "초인가"]
            stocks.loc[scandal_victim, "변동률(%)"] = round(((new_price - initial) / initial) * 100, 2)
            current_turn_logs.append(f"🚨 [회계 스캔들] [종합 {victim_rank}위] [{scandal_victim}] 분식 회계 적발! 주가 반토막(-50%) 및 팀 강제 퇴출(무소속) 처분되었습니다.")

        # 3. 국민연금 긴급 투입 (1% 확률)
        low_survivors = survivors[survivors["이전순위"] >= (NUM_STOCKS - 9)]
        if not low_survivors.empty and np.random.rand() < 0.01:
            pension_saved = low_survivors.sample(1).index[0]
            saved_rank = int(stocks.loc[pension_saved, "이전순위"])
            old_price = stocks.loc[pension_saved, "현재가"]
            new_price = round(old_price * 2.0)
            stocks.loc[pension_saved, "현재가"] = new_price
            initial = stocks.loc[pension_saved, "초인가"]
            stocks.loc[pension_saved, "변동률(%)"] = round(((new_price - initial) / initial) * 100, 2)
            current_turn_logs.append(f"💰 [국민연금 긴급투입] 바닥을 기던 [종합 {saved_rank}위] [{pension_saved}]에 자금이 수혈되어 주가가 2배(+100%) 폭등했습니다!")

        # 4. 블록딜 폭탄 (2% 확률)
        if len(survivors) >= 3 and np.random.rand() < 0.02:
            bomb_target = survivors.sample(1).index[0]
            bomb_rank = int(stocks.loc[bomb_target, "이전순위"])
            old_price = stocks.loc[bomb_target, "현재가"]
            new_price = max(10, round(old_price * 0.6))
            stocks.loc[bomb_target, "현재가"] = new_price
            initial = stocks.loc[bomb_target, "초인가"]
            stocks.loc[bomb_target, "변동률(%)"] = round(((new_price - initial) / initial) * 100, 2)
            current_turn_logs.append(f"💣 [블록딜 폭탄] 대규모 블록딜 물량이 출하되어 [종합 {bomb_rank}위] [{bomb_target}]의 주가가 40% 폭락했습니다!")

    # --- [각 기업별 턴 진행] ---
    for symbol in stocks.index:
        if stocks.loc[symbol, "파산여부"]:
            continue
            
        current_rank = int(stocks.loc[symbol, "이전순위"])
        is_top10 = (current_rank <= 10) and (total_survivors_count > 20)
        is_low10 = current_rank >= (NUM_STOCKS - 9)
        cheer_turns = stocks.loc[symbol, "응원남은턴"]
        team_buff_turns = stocks.loc[symbol, "팀버프남은턴"]
        short_turns = stocks.loc[symbol, "공매도남은턴"]
        
        # 0.01% 확률로 갑작스러운 돌연 부도
        if np.random.rand() < 0.0001:
            bankruptcy_company(symbol, "갑작스러운 자금난으로 돌연 부도 처리되었습니다.", current_turn_logs)
            continue

        # 팀 가입 (확률 0.5%)
        if stocks.loc[symbol, "팀"] == "무소속" and np.random.rand() < 0.005:
            assigned_team = random.choice(teams)
            stocks.loc[symbol, "팀"] = assigned_team
            current_turn_logs.append(f"🤝 [{symbol}] 이(가) {assigned_team} 동맹에 가입했습니다.")

        # 가격 변동 범위 설정
        if short_turns > 0:
            min_rate, max_rate = -0.6, -0.2
            stocks.loc[symbol, "공매도남은턴"] -= 1
        elif team_buff_turns > 0:
            min_rate, max_rate = 0.01, 1.0
            stocks.loc[symbol, "팀버프남은턴"] -= 1
        elif cheer_turns > 0:
            min_rate, max_rate = -0.3, 1.5
            stocks.loc[symbol, "응원남은턴"] -= 1
        elif is_top10:
            min_rate, max_rate = max(user_min_rate, -0.5), user_max_rate
        elif is_low10:
            min_rate, max_rate = -0.5, 1.0
        else:
            min_rate, max_rate = user_min_rate, user_max_rate
            
        change_rate = np.random.uniform(min_rate, max_rate)
        
        current_price = stocks.loc[symbol, "현재가"]
        new_price = current_price * (1.0 + change_rate)
        
        if new_price <= 0:
            bankruptcy_company(symbol, "자본금 전액 소진으로 부도 처리되었습니다.", current_turn_logs)
        else:
            stocks.loc[symbol, "현재가"] = round(new_price)
            initial = stocks.loc[symbol, "초인가"]
            stocks.loc[symbol, "변동률(%)"] = round(((new_price - initial) / initial) * 100, 2)

    # --- [동시다발적 M&A 공격 및 백기사 방어 시스템] ---
    survivors = stocks[~stocks["파산여부"]]
    for attacker in survivors.index:
        if stocks.loc[attacker, "파산여부"]:
            continue
            
        attacker_team = stocks.loc[attacker, "팀"]
        team_member_count = 0
        if attacker_team != "무소속":
            team_member_count = len(survivors[survivors["팀"] == attacker_team])
            
        attack_prob = 0.01 + (team_member_count * 0.01)
        
        if np.random.rand() < attack_prob:
            possible_targets = survivors[survivors.index != attacker]
            if attacker_team != "무소속":
                possible_targets = possible_targets[possible_targets["팀"] != attacker_team]
                
            if not possible_targets.empty:
                target = possible_targets.sort_values(by="현재가", ascending=False).iloc[0].name
                target_rank = int(stocks.loc[target, "이전순위"])
                
                if stocks.loc[target, "보유수량"] > 0:
                    current_turn_logs.append(f"🛡️ [백기사 발동] 플레이어가 보유 중인 [{target}](종합 {target_rank}위)을(를) 보호하여 [{attacker}]의 적대적 M&A 공격을 완벽히 막아냈습니다!")
                else:
                    if np.random.rand() < 0.5:
                        team_name_str = attacker_team if attacker_team != '무소속' else attacker
                        bankruptcy_company(target, f"[{team_name_str}] 그룹의 공격을 받고 부도 되었습니다.", current_turn_logs)
                        
                        if attacker_team in st.session_state.team_bankruptcy_counts:
                            st.session_state.team_bankruptcy_counts[attacker_team] += 1
                        
                        if attacker_team != "무소속":
                            team_members = stocks[(stocks["팀"] == attacker_team) & (~stocks["파산여부"])].index
                            stocks.loc[team_members, "팀버프남은턴"] = 3
                            current_turn_logs.append(f"🎉 [{attacker_team}] 팀이 부도 공격에 성공하여 3턴간 팀원 전원 상승 버프(+1%~+100%)를 받습니다!")
                        else:
                            stocks.loc[attacker, "팀버프남은턴"] = 3
                            current_turn_logs.append(f"🎉 [{attacker}] 기업이 부도 공격에 성공하여 3턴간 상승 버프(+1%~+100%)를 받습니다!")
                    else:
                        current_turn_logs.append(f"🛡️ [{attacker}] 의 [{target}] 대상 부도 공격이 방어벽에 막혀 실패했습니다.")

    st.session_state.event_logs = current_turn_logs

update_game_state()

# ---------------------------------------------------------
# 6. 화면 레이아웃 구성
# ---------------------------------------------------------
st.title("📈 200개 종목 서바이벌 투자 시뮬레이션")
st.caption("⏱️ **10초마다** 시세 변동! (블랙 먼데이, 백기사 방어, 리얼 기업명 등 하드코어 시스템 활성화)")

stocks_df = st.session_state.stocks
total_survivors = len(stocks_df[~stocks_df['파산여부']])
total_stock_val = (stocks_df["현재가"] * stocks_df["보유수량"]).sum()
total_assets = st.session_state.cash + total_stock_val

m1, m2, m3, m4 = st.columns(4)
m1.metric("보유 현금", f"{int(st.session_state.cash):,} 원")
m2.metric("주식 평가금액", f"{int(total_stock_val):,} 원")
m3.metric("총 자산", f"{int(total_assets):,} 원")
m4.metric("생존 기업 수", f"{total_survivors} / 200")

st.divider()

left_col, right_col = st.columns([3, 1])

# ---------------------------------------------------------
# [우측 컬럼] 팀 현황, 부도 전과 랭킹, TOP 5, 사건 로그
# ---------------------------------------------------------
with right_col:
    st.subheader("🛡️ 팀별 생존 현황")
    teams_list = ["🔴 Red", "🔵 Blue", "🟡 Yellow"]
    for team in teams_list:
        team_stocks = stocks_df[(stocks_df["팀"] == team) & (~stocks_df["파산여부"])]
        st.markdown(f"**{team}** (생존: {len(team_stocks)}개)")
        if not team_stocks.empty:
            st.caption(", ".join(team_stocks.index.tolist()))
        else:
            st.caption("생존 기업 없음")
            
    st.divider()

    st.subheader("🏆 팀별 M&A 부도 전과")
    for team, count in st.session_state.team_bankruptcy_counts.items():
        st.write(f"- **{team}**: 파산시킨 기업 **{count}개**")

    st.divider()

    st.subheader("🔥 상승률 TOP 5")
    top_5_up = stocks_df[~stocks_df["파산여부"]].sort_values(by="변동률(%)", ascending=False).head(5)
    for idx, row in top_5_up.iterrows():
        team_tag = f"[{row['팀']}]" if row['팀'] != '무소속' else ""
        cheer_tag = "📣" if row["응원남은턴"] > 0 else ""
        tbuff_tag = "⚡" if row["팀버프남은턴"] > 0 else ""
        short_tag = "📉" if row["공매도남은턴"] > 0 else ""
        st.write(f"**{idx}** {team_tag}{cheer_tag}{tbuff_tag}{short_tag}: {int(row['현재가']):,}원 (`+{row['변동률(%)']}%`)")
        
    st.divider()

    st.subheader("📜 이번 턴 사건/사고 로그")
    log_container = st.container(height=250)
    with log_container:
        if st.session_state.event_logs:
            for log in st.session_state.event_logs:
                st.text(log)
        else:
            st.text("이번 턴에 발생한 특이 사건/사고가 없습니다.")

# ---------------------------------------------------------
# [좌측 컬럼] 주식 랭킹 순 표출 및 응원 / 매매 / 부도권 공격 시스템
# ---------------------------------------------------------
with left_col:
    st.subheader("📊 전체 종목 순위 (현재가 높은 순)")
    
    sorted_stocks = stocks_df.sort_values(by="현재가", ascending=False)
    
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

    search_term = st.text_input("🔍 종목 검색", placeholder="예: 미래전자")
    
    display_df = sorted_stocks
    if search_term:
        display_df = sorted_stocks[sorted_stocks.index.str.contains(search_term)]
        
    for rank, (symbol, row) in enumerate(display_df.iterrows(), 1):
        with st.container():
            c_info, c_cheer, c_attack, c_qty, c_buy, c_sell = st.columns([2.5, 0.8, 0.9, 0.8, 0.8, 0.8])
            
            current_rank = int(row["이전순위"])
            team_badge = f"`{row['팀']}`" if row["팀"] != "무소속" else ""
            top10_badge = "🌟[TOP 10]" if (current_rank <= 10 and total_survivors > 20 and not row["파산여부"]) else ""
            low10_badge = "🔻[LOW]" if current_rank >= (NUM_STOCKS - 9) and not row["파산여부"] else ""
            cheer_badge = f"📣[응원: {row['응원남은턴']}턴]" if row["응원남은턴"] > 0 else ""
            tbuff_badge = f"⚡[팀버프: {row['팀버프남은턴']}턴]" if row["팀버프남은턴"] > 0 else ""
            short_badge = f"📉[공매도: {row['공매도남은턴']}턴]" if row["공매도남은턴"] > 0 else ""
            
            if row["파산여부"]:
                info_text = f"~~{rank}위. {symbol}~~ | 💥 **부도 완료** | 보유: {row['보유수량']}주"
            else:
                info_text = f"**{rank}위. {symbol}** {team_badge} {top10_badge} {low10_badge} {cheer_badge} {tbuff_badge} {short_badge} | **{int(row['현재가']):,}원** (`{row['변동률(%)']}%`) | 보유: {row['보유수량']}주"
                
            c_info.markdown(info_text)
            
            if not row["파산여부"]:
                if c_cheer.button("📣 응원", key=f"cheer_{symbol}"):
                    st.session_state.stocks.loc[symbol, "응원남은턴"] = 3
                    st.session_state.event_logs = [f"🙌 [{symbol}] 이(가) 응원을 받아 3턴 동안 버프(-30%~+150%)가 적용됩니다!"]
                    st.rerun()

                if c_attack.button("⚔️ 부도권", key=f"attack_{symbol}"):
                    if st.session_state.bankruptcy_tickets > 0:
                        st.session_state.bankruptcy_tickets -= 1
                        if np.random.rand() < 0.5:
                            st.session_state.event_logs = []
                            bankruptcy_company(symbol, "플레이어의 적대적 M&A 부도권 공격을 받아 부도 처리되었습니다.", st.session_state.event_logs)
                            st.session_state.team_bankruptcy_counts["플레이어"] += 1
                        else:
                            st.session_state.event_logs = [f"🛡️ [플레이어]의 [{symbol}] 대상 적대적 M&A 공격이 방어벽에 막혀 실패했습니다."]
                        st.rerun()
                    else:
                        st.warning("부도권이 부족합니다! (사이드바에서 구매 가능)")

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
                        st.warning("보유 수량 부족")
            else:
                c_cheer.write("-")
                c_attack.write("-")
                c_qty.write("-")
                c_buy.write("-")
                c_sell.write("-")
