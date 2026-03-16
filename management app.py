import os
import pandas as pd
import streamlit as st
from datetime import datetime, date
import plotly.graph_objects as go

# 1. 페이지 설정
st.set_page_config(page_title="Dorco Asset Pro", layout="wide")

# 2. 세션 상태 및 초기화
if "selected_menu" not in st.session_state:
    params = st.query_params
    if params.get("page") == "request":
        st.session_state.selected_menu = "ORDER_REQ"
        st.session_state.sidebar_open = False
    else:
        st.session_state.selected_menu = "DORCO"
        st.session_state.sidebar_open = True

if "selected_submenu" not in st.session_state:
    st.session_state.selected_submenu = "입고"

# 3. 파일 경로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

FILE_PATH = os.path.join(BASE_DIR, "inventory.csv")
INFO_FILE = os.path.join(BASE_DIR, "inventory_info.csv")
IN_FILE = os.path.join(BASE_DIR, "inventory_in.csv")
OUT_FILE = os.path.join(BASE_DIR, "inventory_out.csv")
ORDER_REQ_FILE = os.path.join(BASE_DIR, "order_requests.csv")

# 4. 공통 함수
def load_csv_safe(path, cols=None):
    if not os.path.exists(path):
        return pd.DataFrame(columns=cols) if cols else pd.DataFrame()
    encodings = ["utf-8-sig", "cp949", "utf-8"]
    for enc in encodings:
        try:
            df = pd.read_csv(path, encoding=enc, low_memory=False)
            return df
        except: continue
    return pd.DataFrame(columns=cols) if cols else pd.DataFrame()

def ensure_csv(path, cols):
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        pd.DataFrame(columns=cols).to_csv(path, index=False, encoding="utf-8-sig")

def save_issue_log(path, data_dict):
    df_log = load_csv_safe(path)
    new_row = pd.DataFrame([data_dict])
    df_log = pd.concat([df_log, new_row], ignore_index=True)
    df_log.to_csv(path, index=False, encoding="utf-8-sig")

def prep_num_cols(df, columns):
    if df is None or df.empty: return df
    for col in columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
    return df

# 파일 초기화
ensure_csv(FILE_PATH, ["대분류","품목","수량단위","현재고","안전재고","최근입고일","최근출고일"])
ensure_csv(INFO_FILE, ["대분류","품목","구매처","수량단위","안전재고","기본발주수량","비고"])
ensure_csv(IN_FILE, ["입고일자","대분류","품목","입고수량","구매금액"])
ensure_csv(OUT_FILE, ["출고일자","대분류","품목","출고수량","비고"])
ensure_csv(ORDER_REQ_FILE, ["요청일시", "대분류", "품목", "비고", "상태"])

st.markdown("""
<style>
    /* 전체 컨테이너 여백 - 기존 유지하면서 조금 더 균형감 있게 */
    .block-container {
        padding-top: 5.5rem !important;    /* 헤더 60~64px 고려 */
        padding-bottom: 3rem !important;
        padding-left: 3.5rem !important;
        padding-right: 3.5rem !important;
        max-width: 1400px !important;      /* 너무 넓지 않게 중앙 정렬감 강화 */
        margin: 0 auto;
    }

    /* Streamlit 기본 헤더 완전 제거 */
    header[data-testid="stHeader"] {
        background-color: rgba(0,0,0,0) !important;
        height: 0px !important;
        visibility: hidden !important;
    }
    div[data-testid="stDecoration"] {
        display: none !important;
    }

    /* 앱 배경 - 살짝 따뜻한 오프화이트 → 깔끔하면서도 부드러움 */
    .stApp {
        background-color: #fafcff;
        background: linear-gradient(135deg, #f8faff 0%, #f0f4ff 100%);
    }

    /* 프리미엄 헤더 - 2025~26 트렌드 gradient + blur edge */
    .premium-header {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 64px;
        background: linear-gradient(90deg, #5b21b6 0%, #3b82f6 50%, #06b6d4 100%);
        color: white;
        display: flex;
        align-items: center;
        padding-left: 80px;
        font-size: 1.5rem;               /* 24px 정도로 살짝 키움 */
        font-weight: 800;
        letter-spacing: -0.02em;
        z-index: 9999;
        box-shadow: 0 4px 20px rgba(59, 130, 246, 0.18);
        backdrop-filter: blur(8px);      /* 살짝 glass 느낌 */
        -webkit-backdrop-filter: blur(8px);
        border-bottom: 1px solid rgba(255,255,255,0.12);
    }

    /* 메트릭 카드 - glassmorphism + soft shadow */
    div[data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.75);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        padding: 28px !important;
        border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 0.25);
        box-shadow: 0 8px 32px rgba(31, 38, 135, 0.12);
        transition: all 0.3s ease;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-4px);
        box-shadow: 0 16px 48px rgba(31, 38, 135, 0.18);
    }

    /* 정보 카드 - indigo accent + glass 스타일 */
    .info-card {
        background: rgba(255, 255, 255, 0.78);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        padding: 24px;
        border-radius: 18px;
        border-left: 5px solid #6366f1;
        border: 1px solid rgba(99, 102, 241, 0.18);
        box-shadow: 0 6px 24px rgba(99, 102, 241, 0.08);
        margin-bottom: 24px;
        transition: all 0.25s ease;
    }
    .info-card:hover {
        border-left-color: #4f46e5;
        box-shadow: 0 10px 32px rgba(99, 102, 241, 0.14);
    }

    /* 사이드 메뉴 버튼 - 더 modern한 hover */
    .stButton > button {
        width: 100%;
        text-align: left;
        border-radius: 12px !important;
        border: none !important;
        height: 48px;
        background: transparent;
        transition: all 0.28s cubic-bezier(0.4, 0, 0.2, 1);
        color: #334155;
        font-weight: 600;
        font-size: 15px;
        padding-left: 16px !important;
        margin-bottom: 10px;
    }
    .stButton > button:hover {
        background: rgba(241, 245, 249, 0.92) !important;
        color: #4f46e5 !important;
        padding-left: 20px !important;
        transform: translateX(4px);
        box-shadow: 0 4px 12px rgba(79, 70, 229, 0.1);
    }
    .stButton > button:active {
        transform: scale(0.98);
    }

    /* 메뉴 구분 라벨 - 더 세련된 타이포 */
    .menu-label {
        font-size: 11.5px;
        font-weight: 700;
        color: #64748b;
        margin: 2rem 0 0.75rem 1.25rem;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        opacity: 0.9;
    }
</style>

<div class="premium-header">DORCO SMART ASSET PRO</div>
""", unsafe_allow_html=True)


# ✅ 상단 메뉴 토글 버튼
top_l, top_r = st.columns([1, 9])
with top_l:
    if st.button("☰", key="m_toggle"):
        st.session_state.sidebar_open = not st.session_state.sidebar_open
        st.rerun()

# ✅ 레이아웃
if st.session_state.sidebar_open:
    col_side, col_main = st.columns([1.2, 4.8], gap="large")
    with col_side:
        st.markdown('<p class="menu-label">Analytics</p>', unsafe_allow_html=True)
        if st.button("🏠 Home Overview"): st.session_state.selected_menu = "DORCO"; st.rerun()
        if st.button("📊 Insight Report"): st.session_state.selected_menu = "REPORT"; st.rerun()

        st.markdown('<p class="menu-label">Management</p>', unsafe_allow_html=True)
        if st.button("📦 Stock Board"): st.session_state.selected_menu = "STOCK"; st.rerun()
        if st.button("📥 Inbound"):
            st.session_state.selected_menu = "INOUT"
            st.session_state.selected_submenu = "입고"
            st.rerun()
        if st.button("📤 Outbound"):
            st.session_state.selected_menu = "INOUT"
            st.session_state.selected_submenu = "출고"
            st.rerun()

        st.markdown('<p class="menu-label">System</p>', unsafe_allow_html=True)
        if st.button("⚙️ Admin Settings"): st.session_state.selected_menu = "SYSTEM"; st.rerun()

        st.markdown('<p class="menu-label">External</p>', unsafe_allow_html=True)

        req_log_side = load_csv_safe(ORDER_REQ_FILE)
        pending_cnt = len(req_log_side[req_log_side["상태"] == "대기"]) if not req_log_side.empty and "상태" in req_log_side.columns else 0
        badge = f" 🔔({pending_cnt})" if pending_cnt > 0 else ""

        if st.button(f"📢 Field Request{badge}"):
            st.session_state.selected_menu = "ORDER_REQ"
            st.rerun()

else:
    col_main = st.container()

with col_main:
   
    df = load_csv_safe(FILE_PATH)
    info_df = load_csv_safe(INFO_FILE)
    req_log = load_csv_safe(ORDER_REQ_FILE)
    df = prep_num_cols(df, ["현재고", "안전재고"])
    
    current = st.session_state.selected_menu

    # --- 🏠 [DORCO] 대시보드 ---
    if current == "DORCO":

        req_log = load_csv_safe(ORDER_REQ_FILE)   # ← 파일 경로 확인 필요

        # pending_df 정의 (이 5~7줄이 핵심!)
        if not req_log.empty and "상태" in req_log.columns:
            pending_df = req_log[req_log["상태"] == "대기"].copy()
        else:
            pending_df = pd.DataFrame()
        df = prep_num_cols(df, ["현재고", "안전재고"])

        # 입고/구매 데이터 로드
        df_in_dash = load_csv_safe(IN_FILE, cols=["입고일자", "대분류", "품목", "입고수량", "구매금액"])

        if not df_in_dash.empty:
            df_in_dash["구매금액"] = pd.to_numeric(df_in_dash["구매금액"], errors="coerce").fillna(0)
            df_in_dash["입고일자"] = pd.to_datetime(df_in_dash["입고일자"], errors="coerce")
            df_in_dash = df_in_dash.dropna(subset=["입고일자"])

            this_year = datetime.now().year
            year_df = df_in_dash[df_in_dash["입고일자"].dt.year == this_year].copy()
            annual_spent = int(year_df["구매금액"].sum()) if not year_df.empty else 0
        else:
            year_df = pd.DataFrame()
            annual_spent = 0

        current_month = datetime.now().month

        if not year_df.empty:
            month_df = year_df[year_df["입고일자"].dt.month == current_month].copy()
        else:
            month_df = pd.DataFrame()

        monthly_spent = int(month_df["구매금액"].sum()) if not month_df.empty else 0

        # -----------------------------
        # 📢 발주 요청 알림 → expander로 깔끔하게 접기
        # -----------------------------
        with st.expander("🔔 발주 대기 요청", expanded=not pending_df.empty):
            if pending_df.empty:
                st.success("현재 대기 중인 발주 요청이 없습니다.", icon="✅")
            else:
                st.metric("미처리 요청 건수", len(pending_df), delta_color="inverse")
                
                # 상세 목록
                with st.container():
                    show_cols = ["요청일시", "대분류", "품목", "요청수량", "비고"]
                    st.dataframe(
                        pending_df.sort_values("요청일시", ascending=False)[show_cols].head(8),
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "요청일시": st.column_config.DatetimeColumn(format="D HH:mm")
                        }
                    )
                
                # 처리 버튼 (건수가 적을 때만 노출)
                if pending_df.shape[0] <= 5:
                    st.markdown("#### 대기 요청 처리")
                    cols = st.columns(min(3, len(pending_df)))
                    for (idx, row), col in zip(pending_df.iterrows(), cols):
                        with col:
                            req_item = row["품목"]
                            if st.button(f"✓ {req_item}", key=f"req_{idx}", use_container_width=True):
                                    req_log.at[idx, "상태"] = "처리완료"
                                    req_log.to_csv(ORDER_REQ_FILE, index=False, encoding="utf-8-sig")
                                    st.success(f"{req_item} 처리 완료", icon="✅")
                                    st.rerun()
                                       
        # -----------------------------
        # 핵심 KPI
        # -----------------------------
        st.markdown("### Dashboard Overview")
        k1, k2 = st.columns(2)
        k1.metric("이번 달 사용 금액", f"{monthly_spent:,} 원", delta=None)
        k2.metric("연간 누적 사용 금액", f"{annual_spent:,} 원", delta=None)

        st.divider()

        # -----------------------------
        # 차트 + 테이블 영역
        # -----------------------------
        left, right = st.columns([6, 4], gap="medium")

        with left:
            st.markdown("#### 이번 달 사용금액 현황")
            if not month_df.empty:
                # ── 여기서부터 차트 생성 시작 ──
                month_cat = (
                    month_df.groupby("대분류", as_index=False)["구매금액"]
                    .sum()
                    .sort_values("구매금액", ascending=False)
                )

                fig_month_donut = go.Figure(
                    go.Pie(
                        labels=month_cat["대분류"],
                        values=month_cat["구매금액"],
                        hole=0.55,
                        textinfo="label+percent",
                        hovertemplate="<b>%{label}</b><br>사용금액: %{value:,.0f}원<extra></extra>"
                    )
                )

                fig_month_donut.update_layout(
                    height=340,
                    margin=dict(t=10, b=10, l=0, r=0),
                    showlegend=True,
                    legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5)
                )

                # annotations (센터 금액 표시) 추가하려면 아래 주석 해제
                # fig_month_donut.update_layout(
                #     annotations=[
                #         dict(
                #             text=f"{current_month}월<br><b>{monthly_spent:,}원</b>",
                #             x=0.5, y=0.5,
                #             showarrow=False,
                #             font=dict(size=18)
                #         )
                #     ]
                # )

                st.plotly_chart(fig_month_donut, use_container_width=True, config={'displayModeBar': False})
            else:
                st.info("이번 달 데이터 없음", icon="ℹ️")

        with right:
            st.markdown("#### 분류별 금액")
            if not month_df.empty:
                month_summary = (
                    month_df.groupby("대분류", as_index=False)["구매금액"]
                    .sum()
                    .sort_values("구매금액", ascending=False)
                )
                st.dataframe(
                    month_summary.style.format({"구매금액": "{:,.0f} 원"}),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("데이터 없음", icon="ℹ️")    # --------------------------------------------------
    # 📦 2. 재고 보드 (현황 조회 및 상시 수정)
    # --------------------------------------------------
    elif current == "STOCK":
        st.markdown('<div class="main-title">Inventory Stock Board</div>', unsafe_allow_html=True)
        
        # 상단: 현황 조회 및 검색
        search_name = st.text_input("🔍 품목 검색", placeholder="검색할 품목명을 입력하세요...")
        
        df_display = df.copy()
        df_display = prep_num_cols(df_display, ["현재고", "안전재고"])

        if search_name:
            df_display = df_display[df_display["품목"].str.contains(search_name, na=False)]

        # 상태 계산 및 테이블 출력
        if not df_display.empty:
            st.markdown('<div class="sub-title">📦 현재고 실시간 현황</div>', unsafe_allow_html=True)
            st.dataframe(
                df_display[["대분류", "품목", "수량단위", "현재고", "안전재고", "최근입고일"]], 
                use_container_width=True, 
                hide_index=True
            )
        else:
            st.info("💡 등록된 비품 데이터가 없습니다.")

        st.divider()

        # 하단: 상시 재고 수정 섹션 (Quick Adjustment)
        st.markdown('<div class="sub-title">⚙️ 실시간 재고 수정</div>', unsafe_allow_html=True)
        st.caption("현장에서 실사 후 수량이 다를 경우 여기서 즉시 수정하세요.")

        # 1. [실시간 연동] 대분류 선택 (폼 외부)
        if not info_df.empty:
            all_cats = sorted(info_df["대분류"].unique().tolist())
            adj_cat = st.selectbox("📂 수정할 대분류 선택", all_cats, key="adj_cat_select")
            relevant_items = sorted(info_df[info_df["대분류"] == adj_cat]["품목"].tolist())
        else:
            adj_cat = None
            relevant_items = []

        # 2. 재고 수정 폼
        with st.form("quick_adj_form", clear_on_submit=True):
            c1, c2, c3 = st.columns([1.5, 1.5, 1])
            
            with c1:
                adj_date = st.date_input("기록 일자", date.today())
                adj_item = st.selectbox("📦 품목 선택", relevant_items if relevant_items else ["품목 없음"])
            
            with c2:
                # 현재고 불러오기 (도움말용)
                target_row = df[df["품목"] == adj_item]
                current_val = int(target_row["현재고"].values[0]) if not target_row.empty else 0
                
                new_qty = st.number_input(f"최종 현재고 입력 (기존: {current_val})", min_value=0, step=1)
            
            with c3:
                st.markdown("<br>", unsafe_allow_html=True)
                submit_adj = st.form_submit_button("💾 재고 동기화")

            if submit_adj:
                if not relevant_items or adj_item == "품목 없음":
                    st.error("품목을 선택해주세요.")
                else:
                    # 1. 메인 재고 파일(inventory.csv) 업데이트
                    idx = df[df["품목"] == adj_item].index
                    if not idx.empty:
                        old_qty = int(df.at[idx[0], "현재고"])
                        df.at[idx[0], "현재고"] = new_qty
                        df.at[idx[0], "최근출고일" if new_qty < old_qty else "최근입고일"] = adj_date.strftime("%Y-%m-%d")
                        df.at[idx[0], "비고"] = f"{adj_date} 실사 후 조정"
                        df.to_csv(FILE_PATH, index=False, encoding="utf-8-sig")
                        
                        # 2. 로그 기록 (조정 내역을 출고/입고 로그 중 한 곳에 남길 수도 있으나, 여기서는 별도 기록 없이 재고만 반영)
                        st.success(f"✅ {adj_item} 재고가 {new_qty}개로 수정되었습니다.")
                        st.rerun()

    # --- 🔄 [INOUT] 입출고 관리 ---
    elif current == "INOUT":
        st.markdown(f'<div class="main-title">{st.session_state.selected_submenu} 관리</div>', unsafe_allow_html=True)
        mode = st.session_state.selected_submenu
        
        # 1. 대분류 선택 (폼 외부로 배치하여 즉시 반영되도록 함)
        if not info_df.empty:
            all_cats = sorted(info_df["대분류"].unique().tolist())
            sel_cat = st.selectbox("📂 먼저 대분류를 선택하세요", all_cats, key="io_cat_selector")
            # 선택된 대분류에 맞는 품목 리스트 필터링
            relevant_items = sorted(info_df[info_df["대분류"] == sel_cat]["품목"].tolist())
        else:
            sel_cat = st.text_input("대분류 직접 입력")
            relevant_items = []

        # 2. 입출고 상세 입력 폼
        with st.form("inout_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                io_date = st.date_input("날짜", date.today())
                # 위에서 선택한 품목 리스트를 사용
                io_item = st.selectbox("품목 선택", relevant_items if relevant_items else ["품목 없음"])
            with col2:
                io_qty = st.number_input("수량 입력", min_value=1, step=1)
                io_note = st.text_input("비고 (필요 시)")

            # ✅ 입고일 때만 구매금액 입력
            if mode == "입고":
                io_amount = st.number_input("구매금액 입력", min_value=0, step=1000, value=0)
            else:
                io_amount = 0

            # 제출 버튼
            if st.form_submit_button(f"{mode} 확정"):
                if not relevant_items or io_item == "품목 없음":
                    st.error("품목을 선택해주세요.")
                else:
                    # 재고 업데이트 로직
                    idx = df[df["품목"] == io_item].index
                    if not idx.empty:
                        i = idx[0]
                        # 숫자형 변환 확인
                        curr_stock = int(pd.to_numeric(df.at[i, "현재고"], errors='coerce') or 0)
                        
                        if mode == "입고":
                            df.at[i, "현재고"] = curr_stock + io_qty
                            df.at[i, "최근입고일"] = io_date.strftime("%Y-%m-%d")
                            save_issue_log(IN_FILE, {"입고일자": io_date, "대분류": sel_cat, "품목": io_item, "입고수량": io_qty, "구매금액": io_amount})
                        else:
                            # 출고 시 재고 부족 체크
                            if curr_stock < io_qty:
                                st.error(f"재고가 부족합니다. (현재고: {curr_stock})")
                                st.stop()
                            df.at[i, "현재고"] = curr_stock - io_qty
                            df.at[i, "최근출고일"] = io_date.strftime("%Y-%m-%d")
                            save_issue_log(OUT_FILE, {"출고일자": io_date, "대분류": sel_cat, "품목": io_item, "출고수량": io_qty, "비고": io_note})
                        
                        # 파일 저장 및 새로고침
                        df.to_csv(FILE_PATH, index=False, encoding="utf-8-sig")
                        st.success(f"{io_item} {io_qty}개 {mode} 처리가 완료되었습니다.")
                        st.rerun()

    # --------------------------------------------------
    # 📊 5. 통계 리포트
    # --------------------------------------------------
    elif current == "REPORT":
        st.markdown('<div class="main-title">📈 재고 분석 및 통계 리포트</div>', unsafe_allow_html=True)
        
        # 1. 입고 데이터 로드 및 전처리
        df_in_stat = load_csv_safe(IN_FILE, cols=["입고일자","대분류","품목","입고수량","구매금액"])
        
        if df_in_stat.empty:
            st.info("📌 등록된 입고 내역이 없습니다. 입고 관리를 통해 데이터를 먼저 등록해 주세요.")
        else:
            # 데이터 숫자형 변환 및 날짜 처리
            df_in_stat["입고수량"] = pd.to_numeric(df_in_stat["입고수량"], errors="coerce").fillna(0)
            df_in_stat["구매금액"] = pd.to_numeric(df_in_stat["구매금액"], errors="coerce").fillna(0)
            df_in_stat["입고일자"] = pd.to_datetime(df_in_stat["입고일자"], errors="coerce")
            
            # 유효하지 않은 날짜 제거 및 월별 그룹화를 위한 컬럼 생성
            df_in_stat = df_in_stat.dropna(subset=["입고일자"])
            df_in_stat["년월"] = df_in_stat["입고일자"].dt.to_period("M").astype(str)

            # --- [1] 핵심 KPI 지표 (상단 카드) ---
            today = pd.Timestamp.today()
            current_month_str = today.to_period("M").strftime("%Y-%m")
            prev_month_str = (today.to_period("M") - 1).strftime("%Y-%m")

            current_month_spent = df_in_stat.loc[
                df_in_stat["년월"] == current_month_str, "구매금액"
            ].sum()

            prev_month_spent = df_in_stat.loc[
                df_in_stat["년월"] == prev_month_str, "구매금액"
            ].sum()

            month_diff = current_month_spent - prev_month_spent

            m1, m2, m3 = st.columns(3)

            m1.metric(
                "💰 당월 집행 금액",
                f"{int(current_month_spent):,} 원"
            )

            m2.metric(
                "💳 전월 집행 금액",
                f"{int(prev_month_spent):,} 원"
            )

            m3.metric(
                "📊 전월 대비 증감",
                f"{int(month_diff):,} 원",
                delta=f"{int(month_diff):,} 원"
            )

            st.markdown("---")

            # --- [2] 시각화 분석 (도넛 차트) ---
            st.markdown('<div class="sub-title">🍩 카테고리별 사용 금액 비중</div>', unsafe_allow_html=True)

            summary_cat = (
                df_in_stat.groupby("대분류")["구매금액"]
                .sum()
                .reset_index()
                .sort_values("구매금액", ascending=False)
            )

            fig_donut = go.Figure(
                go.Pie(
                    labels=summary_cat["대분류"],
                    values=summary_cat["구매금액"],
                    hole=0.55,
                    textinfo="label+percent",
                    hovertemplate="<b>%{label}</b><br>사용금액: %{value:,.0f}원<extra></extra>"
                )
            )

            fig_donut.update_layout(
                height=360,
                margin=dict(t=10, b=10, l=10, r=10),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                showlegend=True
            )

            st.plotly_chart(fig_donut, use_container_width=True)

            st.markdown("---")            # --- [3] 하단 상세 로그 및 필터 ---
            st.markdown('<div class="sub-title">📄 상세 입고 기록</div>', unsafe_allow_html=True)
            
            # 필터 컨트롤러
            c_f1, c_f2 = st.columns([2, 1])
            with c_f1:
                month_list = ["전체"] + sorted(df_in_stat["년월"].unique().tolist(), reverse=True)
                sel_month = st.selectbox("📅 조회 월 필터", month_list)
            
            with c_f2:
                st.markdown("<br>", unsafe_allow_html=True)
                csv = df_in_stat.to_csv(index=False, encoding="utf-8-sig")
                st.download_button(
                    label="📥 전체 데이터 다운로드(CSV)",
                    data=csv,
                    file_name=f"inventory_report_{date.today()}.csv",
                    mime="text/csv",
                    use_container_width=True
                )

            # 데이터 필터링 적용
            display_df = df_in_stat.copy()
            if sel_month != "전체":
                display_df = display_df[display_df["년월"] == sel_month]
            
            # 날짜 형식 정리 및 테이블 출력
            display_df["입고일자"] = display_df["입고일자"].dt.strftime("%Y-%m-%d")
            st.dataframe(
                display_df[["입고일자", "대분류", "품목", "입고수량", "구매금액"]].sort_values("입고일자", ascending=False),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "구매금액": st.column_config.NumberColumn("구매금액", format="%d 원"),
                    "입고수량": st.column_config.NumberColumn("수량", format="%d")
                }
            )

    # --------------------------------------------------
    # ⚙️ 6. 시스템 관리
    # --------------------------------------------------
    elif current == "SYSTEM":
        st.markdown('<div class="main-title">⚙️ 비품관리 시스템 설정</div>', unsafe_allow_html=True)
    
        # 🔔 관리자 화면 진입 시 1회 알림(toast)
        if "admin_toast_shown" not in st.session_state:
            st.session_state.admin_toast_shown = False

        req_log_admin = load_csv_safe(ORDER_REQ_FILE)
        pending_cnt = len(req_log_admin[req_log_admin["상태"] == "대기"]) if not req_log_admin.empty and "상태" in req_log_admin.columns else 0

        if pending_cnt > 0 and st.session_state.admin_toast_shown is False:
            st.toast(f"📦 발주 요청 {pending_cnt}건 대기 중입니다.", icon="🔔")
            st.session_state.admin_toast_shown = True
    
        tab1, tab2, tab3 = st.tabs(["🆕 신규 품목 등록", "🗑️ 품목/분류 삭제", "🚨 데이터 초기화"])


       # --- TAB 1: 신규 품목 등록 ---
        with tab1:
            st.markdown('<div class="sub-title">새로운 비품 마스터 등록</div>', unsafe_allow_html=True)
            
            # 1. 기존 카테고리 불러오기 (마스터 파일 기준)
            existing_cats = sorted(info_df["대분류"].unique().tolist()) if not info_df.empty else ["식음료류", "미화용품", "상비약", "기타"]
            
            with st.form("new_item_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                
                with col1:
                    selected_cat = st.selectbox("📂 대분류 선택", existing_cats + ["+ 직접 입력"])
                    # '직접 입력' 선택 시에만 입력창 표시
                    new_cat_input = ""
                    if selected_cat == "+ 직접 입력":
                        new_cat_input = st.text_input("📝 신규 분류명 입력", placeholder="예: 미화용품")
                    
                    item_name = st.text_input("📦 품목명 (필수)", placeholder="예: A4 용지(75g)")
                    vendor = st.text_input("🏪 주요 구매처", placeholder="예: 쿠팡, 대형문구")

                with col2:
                    unit = st.text_input("📏 수량 단위", value="EA", placeholder="예: EA, Box, 묶음")
                    safety_stock = st.number_input("⚠️ 안전재고 설정", min_value=0, value=5, help="재고가 이 수치 미만으로 떨어지면 경고가 표시됩니다.")
                    
                note = st.text_area("🗒️ 품목 상세 설명 및 비고")
                
                # 폼 제출 버튼
                submit_btn = st.form_submit_button("📥 시스템에 신규 등록")
                
                if submit_btn:
                    # 최종 분류명 결정
                    final_cat = new_cat_input if selected_cat == "+ 직접 입력" else selected_cat
                    
                    # 유효성 검사
                    if not item_name:
                        st.error("❌ 품목명은 비워둘 수 없습니다.")
                    elif not final_cat:
                        st.error("❌ 분류명을 입력하거나 선택해주세요.")
                    elif not df.empty and item_name in df["품목"].values:
                        st.error(f"❌ '{item_name}'은(는) 이미 등록된 품목입니다.")
                    else:
                        # 1. 마스터 정보용 데이터 (inventory_info.csv)
                        new_entry_info = {
                            "대분류": final_cat, "품목": item_name, "구매처": vendor,
                            "수량단위": unit, "안전재고": safety_stock, "비고": note
                        }
                        
                        # 2. 실시간 재고 관리용 데이터 (inventory.csv)
                        new_entry_inv = {
                            "대분류": final_cat, "품목": item_name, "수량단위": unit, "구매금액": 0,
                            "현재고": 0, "안전재고": safety_stock, "비고": note,
                            "누적입고": 0, "누적출고": 0, "최근입고일": "", "최근출고일": ""
                        }
                        
                        # 파일 저장 (기존 유틸리티 함수 활용)
                        save_issue_log(INFO_FILE, new_entry_info)
                        save_issue_log(FILE_PATH, new_entry_inv)
                        
                        st.success(f"✅ '{item_name}' 품목이 시스템에 성공적으로 등록되었습니다!")
                        st.balloons()
                        st.rerun()

        with tab2:
            st.markdown('<div class="sub-title">품목 / 대분류 삭제</div>', unsafe_allow_html=True)
            st.warning("삭제 후 복구가 어렵습니다. 신중히 진행하세요.")

            del_mode = st.radio(
                "삭제 유형 선택",
                ["품목 삭제", "대분류 삭제"],
                horizontal=True
            )

            if del_mode == "품목 삭제":
                if not info_df.empty:
                    del_cat = st.selectbox(
                        "삭제할 품목의 대분류 선택",
                        sorted(info_df["대분류"].dropna().unique().tolist()),
                        key="del_item_cat"
                    )

                    del_items = sorted(
                        info_df[info_df["대분류"] == del_cat]["품목"].dropna().unique().tolist()
                    )

                    del_item = st.selectbox(
                        "삭제할 품목 선택",
                        del_items,
                        key="del_item_name"
                    )

                    confirm_item = st.checkbox(f"'{del_item}' 품목을 삭제하겠습니다.", key="confirm_del_item")

                    if st.button("🗑️ 품목 삭제"):
                        if confirm_item:
                            info_df_new = info_df[info_df["품목"] != del_item].copy()
                            df_new = df[df["품목"] != del_item].copy()

                            info_df_new.to_csv(INFO_FILE, index=False, encoding="utf-8-sig")
                            df_new.to_csv(FILE_PATH, index=False, encoding="utf-8-sig")

                            st.success(f"✅ '{del_item}' 품목이 삭제되었습니다.")
                            st.rerun()
                        else:
                            st.error("삭제 확인 체크를 먼저 해주세요.")
                else:
                    st.info("삭제할 품목 데이터가 없습니다.")

            elif del_mode == "대분류 삭제":
                if not info_df.empty:
                    del_cat_group = st.selectbox(
                        "삭제할 대분류 선택",
                        sorted(info_df["대분류"].dropna().unique().tolist()),
                        key="del_group_name"
                    )

                    target_count = len(info_df[info_df["대분류"] == del_cat_group])

                    st.warning(f"'{del_cat_group}' 대분류를 삭제하면 해당 품목 {target_count}개도 함께 삭제됩니다.")

                    confirm_cat = st.checkbox(
                        f"'{del_cat_group}' 대분류 전체를 삭제하겠습니다.",
                        key="confirm_del_cat"
                    )

                    if st.button("🗑️ 대분류 삭제"):
                        if confirm_cat:
                            info_df_new = info_df[info_df["대분류"] != del_cat_group].copy()
                            df_new = df[df["대분류"] != del_cat_group].copy()

                            info_df_new.to_csv(INFO_FILE, index=False, encoding="utf-8-sig")
                            df_new.to_csv(FILE_PATH, index=False, encoding="utf-8-sig")

                            st.success(f"✅ '{del_cat_group}' 대분류 및 관련 품목이 삭제되었습니다.")
                            st.rerun()
                        else:
                            st.error("삭제 확인 체크를 먼저 해주세요.")
                else:
                    st.info("삭제할 대분류 데이터가 없습니다.")

        # --- TAB 3: 데이터 초기화 ---
        with tab3:
            st.markdown('<div class="sub-title">데이터 초기화 및 로그 삭제</div>', unsafe_allow_html=True)
            st.warning("⚠️ **주의**: 아래 버튼을 클릭하면 모든 재고 현황, 입/출고 내역, 품목 마스터가 삭제되며 복구가 불가능합니다.")
            
            # 관리자 확인 절차
            confirm_pw = st.text_input("초기화를 위해 관리자 비밀번호를 입력하세요.", type="password", key="reset_pw_check")
            
            if st.button("🚨 시스템 데이터 영구 삭제"):
                if confirm_pw == "0422":
                    # 각 파일별 헤더 초기화
                    ensure_csv(INFO_FILE, ["대분류","품목","구매처","수량단위","안전재고","기본발주수량","비고"])
                    ensure_csv(FILE_PATH, ["대분류","품목","수량단위","현재고","안전재고","최근입고일","최근출고일"])
                    ensure_csv(IN_FILE, ["입고일자","대분류","품목","입고수량","구매금액"])
                    ensure_csv(OUT_FILE, ["출고일자","대분류","품목","출고수량","비고"])
                    ensure_csv(ORDER_REQ_FILE, ["요청일시", "대분류", "품목", "비고", "상태"])
                    
                    st.success("모든 데이터가 초기화되었습니다. 깨끗한 상태로 다시 시작합니다.")
                    st.rerun()
                else:
                    st.error("비밀번호가 일치하지 않습니다.")

    # --- 📢 [ORDER_REQ] 여사님용 발주 요청 (간편 요청형) ---
    elif current == "ORDER_REQ":
        st.markdown('<div class="main-title">📢 비품 발주 요청</div>', unsafe_allow_html=True)

        if info_df.empty:
            st.warning("등록된 품목이 없습니다. (inventory_info.csv 확인 필요)")
        else:
            st.caption("대분류를 선택하면 해당 품목만 자동으로 표시됩니다.")

            # ✅ 대분류 선택은 form 밖
            cat_list = sorted(
                info_df["대분류"]
                .dropna()
                .astype(str)
                .unique()
                .tolist()
            )

            sel_cat = st.selectbox(
                "대분류 선택",
                cat_list,
                key="req_cat_select"
            )

            # ✅ 선택한 대분류에 맞는 품목만 필터링
            items_in_cat = sorted(
                info_df.loc[
                    info_df["대분류"] == sel_cat,
                    "품목"
                ]
                .dropna()
                .astype(str)
                .unique()
                .tolist()
            )

            with st.form("request_form", clear_on_submit=True):
                sel_item = st.selectbox(
                    "품목 선택",
                    items_in_cat,
                    key="req_item_select"
                )

                # 선택 품목의 마스터 정보 조회
                item_info = info_df[
                    (info_df["대분류"] == sel_cat) &
                    (info_df["품목"] == sel_item)
                ]

                unit_val = (
                    item_info["수량단위"].values[0]
                    if not item_info.empty and "수량단위" in item_info.columns
                    else ""
                )

                default_order_qty = (
                    int(pd.to_numeric(item_info["기본발주수량"].values[0], errors="coerce"))
                    if (
                        not item_info.empty and
                        "기본발주수량" in item_info.columns and
                        pd.notna(item_info["기본발주수량"].values[0])
                    )
                    else 1
                )

                c1 = st.columns(1)[0]

                with c1:
                    st.metric("기본 발주수량", f"{default_order_qty} {unit_val}")

                st.info(
                    f"선택한 품목은 **{default_order_qty} {unit_val}** 기준으로 요청됩니다."
                )

                btn = st.form_submit_button(
                    "🚀 요청하기",
                    use_container_width=True
                )

                if btn:
                    save_issue_log(
                        ORDER_REQ_FILE,
                        {
                            "요청일시": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "대분류": sel_cat,
                            "품목": sel_item,
                            "요청수량": default_order_qty,
                            "비고": "",
                            "상태": "대기"
                        }
                    )

                    st.success(
                        f"✅ [{sel_cat} > {sel_item}] {default_order_qty} {unit_val} 발주 요청이 접수되었습니다."
                    )
                    st.toast("📦 발주 요청이 관리자에게 전송되었습니다.", icon="🔔")
                    st.rerun()
대분류,품목,수량단위,현재고,안전재고,위치,최근입고일,최근출고일,구매금액,비고,누적입고,누적출고
식음료류,스타블렌드(원두),박스,20,0,,2026-03-16,,,,,
식음료류,허니블렌드(원두),박스,0,0,,,,,,,
식음료류,디카페인(원두),박스,0,0,,,,,,,
식음료류,돈시몬 주스(오렌지),박스,3,0,,2026-03-16,,,,,
식음료류,돈시몬 주스(자몽),박스,0,0,,,,,,,
식음료류,음료(1.5L),개,0,0,,,,,,,
식음료류,설탕스틱,박스,0,0,,,,,,,
식음료류,커피시럽,개,0,0,,,,,,,
식음료류,커피스틱(맥심),박스,0,0,,,,,,,
식음료류,티백(둥글레차),박스,0,0,,,,,,,
식음료류,티백(녹차),박스,0,0,,,,,,,
미화용품,펌핑치약,개,0,0,,,,,,,
미화용품,석류시초(참그린),개,0,0,,,,,,,
미화용품,수세미,개,0,0,,,,,,,
미화용품,핸드워시,개,0,0,,,,,,,
미화용품,롤화장지,박스,0,0,,,,,,,
미화용품,핸드티슈,박스,0,0,,,,,,,
기타,스틱빨대,박스,0,0,,,,,,,
기타,머신세정제,개,2,0,,2026-03-11,,,,,
기타,머신세척솔,개,0,0,,,,,,,
미화용품,종이컵(10온즈),박스,12,1,,2026-03-16,,0.0,,0.0,0.0

입고일자,대분류,품목,입고수량,구매금액
2026-03-11,기타,머신세정제,2,57000
2026-03-16,미화용품,종이컵(10온즈),12,149950
2026-03-16,식음료류,돈시몬 주스(오렌지),3,193560
2026-03-16,식음료류,스타블렌드(원두),20,590000

대분류,품목,구매처,수량단위,안전재고,기본발주수량,위치,비고
식음료류,스타블렌드(원두),콩지커피,박스,7,15.0,,
식음료류,허니블렌드(원두),콩지커피,박스,5,10.0,,
식음료류,디카페인(원두),디카커피랩,박스,5,10.0,,
식음료류,돈시몬 주스(오렌지),메가커피,박스,1,6.0,,
식음료류,돈시몬 주스(자몽),메가커피,박스,1,6.0,,
식음료류,음료(1.5L),워커스하이,개,50,72.0,,
식음료류,설탕스틱,쿠팡,박스,1,2.0,,
식음료류,커피시럽,네이버,개,2,4.0,,
식음료류,커피스틱(맥심),네이버,박스,1,2.0,,
식음료류,티백(둥글레차),네이버,박스,2,2.0,,
식음료류,티백(녹차),네이버,박스,2,2.0,,
미화용품,펌핑치약,네이버,개,12,5.0,,
미화용품,석류시초(참그린),네이버,개,12,5.0,,
미화용품,수세미,네이버,개,12,5.0,,
미화용품,핸드워시,네이버,개,12,5.0,,
미화용품,롤화장지,동방제지,박스,1,12.0,,
미화용품,핸드티슈,동방제지,박스,1,12.0,,
기타,스틱빨대,쿠팡,박스,1,3.0,,
기타,머신세정제,네이버,개,"def ensure_csv(path, cols):",2.0,,
기타,머신세척솔,네이버,개,    if not os.path.exists(path) or os.path.getsize(path) == 0:,2.0,,
미화용품,종이컵(10온즈),네이버,박스,1,,,

출고일자,대분류,품목,출고수량,비고

요청일시,대분류,품목,비고,상태,요청수량
2026-03-11 16:19,기타,머신세정제,,처리완료,2.0
2026-03-11 16:59,미화용품,롤화장지,,처리완료,12.0

streamlit
pandas
openpyxl
