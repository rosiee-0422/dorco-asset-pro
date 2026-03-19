import os
import pandas as pd
import streamlit as st
from datetime import datetime, date, timedelta
import plotly.graph_objects as go

# ─────────────────────────────────────────────
# 1. 페이지 설정
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Dorco Asset Pro",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────
# 2. 세션 상태 초기화
# ─────────────────────────────────────────────
params = st.query_params
if "selected_menu" not in st.session_state:
    if params.get("page") == "request":
        st.session_state.selected_menu = "ORDER_REQ"
        st.session_state.sidebar_open = False
    else:
        st.session_state.selected_menu = "DORCO"
        st.session_state.sidebar_open = True

if "selected_submenu" not in st.session_state:
    st.session_state.selected_submenu = "입고"

if "admin_toast_shown" not in st.session_state:
    st.session_state.admin_toast_shown = False

# ─────────────────────────────────────────────
# 3. 파일 경로
# ─────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_PATH      = os.path.join(BASE_DIR, "inventory.csv")
INFO_FILE      = os.path.join(BASE_DIR, "inventory_info.csv")
IN_FILE        = os.path.join(BASE_DIR, "inventory_in.csv")
OUT_FILE       = os.path.join(BASE_DIR, "inventory_out.csv")
ORDER_REQ_FILE = os.path.join(BASE_DIR, "order_requests.csv")

# ─────────────────────────────────────────────
# 4. 공통 유틸
# ─────────────────────────────────────────────
def load_csv_safe(path, cols=None):
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return pd.DataFrame(columns=cols) if cols else pd.DataFrame()
    for enc in ["utf-8-sig", "cp949", "utf-8"]:
        try:
            return pd.read_csv(path, encoding=enc, low_memory=False)
        except Exception:
            continue
    return pd.DataFrame(columns=cols) if cols else pd.DataFrame()

def ensure_csv(path, cols):
    """파일이 없거나 헤더조차 없을 때만 초기화"""
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        pd.DataFrame(columns=cols).to_csv(path, index=False, encoding="utf-8-sig")

def save_log(path, data_dict):
    df = load_csv_safe(path)
    df = pd.concat([df, pd.DataFrame([data_dict])], ignore_index=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")

def prep_num(df, cols):
    if df is None or df.empty:
        return df
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)
    return df

# CSV 초기화 (없을 때만)
ensure_csv(FILE_PATH,      ["대분류","품목","수량단위","현재고","안전재고","최근입고일","최근출고일"])
ensure_csv(INFO_FILE,      ["대분류","품목","구매처","수량단위","안전재고","기본발주수량","비고"])
ensure_csv(IN_FILE,        ["입고일자","대분류","품목","입고수량","구매금액"])
ensure_csv(OUT_FILE,       ["출고일자","대분류","품목","출고수량","비고"])
ensure_csv(ORDER_REQ_FILE, ["요청일시","대분류","품목","요청수량","비고","상태"])

# ─────────────────────────────────────────────
# 5. 중복 발주 방지 헬퍼
# ─────────────────────────────────────────────
def is_duplicate_request(req_log: pd.DataFrame, cat: str, item: str, minutes: int = 30) -> bool:
    """같은 품목이 최근 N분 내 '대기' 상태로 이미 접수됐으면 True"""
    if req_log.empty or "상태" not in req_log.columns:
        return False
    pending = req_log[
        (req_log["상태"] == "대기") &
        (req_log["대분류"] == cat) &
        (req_log["품목"] == item)
    ]
    if pending.empty:
        return False
    try:
        pending = pending.copy()
        pending["요청일시"] = pd.to_datetime(pending["요청일시"], errors="coerce")
        cutoff = datetime.now() - timedelta(minutes=minutes)
        return bool((pending["요청일시"] >= cutoff).any())
    except Exception:
        return False

# ─────────────────────────────────────────────
# 6. 전체 CSS — 2025 트렌드 디자인
# ─────────────────────────────────────────────
IS_REQUEST_PAGE = (st.session_state.selected_menu == "ORDER_REQ")

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,300;9..144,400;9..144,500&family=DM+Sans:wght@400;500;600&family=DM+Mono:wght@400;500&display=swap');

/*
  팔레트
  배경     #f5f0e8  (따뜻한 크림)
  서피스   #fdfaf4  (밝은 크림화이트)
  카드     #fff9ef  (아이보리)
  테두리   #e8e0d0  (샌드)
  텍스트   #2c2416  (딥 브라운)
  서브텍스  #8a7d6b  (웜 모카)
  힌트     #b8ad9e  (라이트 탄)
  포인트   #c07c3a  (번트 앰버)  ← 메인 액센트
  포인트2  #5c7a5c  (세이지 그린) ← 보조 액센트
*/

*, *::before, *::after {{ box-sizing: border-box; }}

html, body, [data-testid="stApp"], .stApp {{
    font-family: 'DM Sans', sans-serif !important;
    background: #f5f0e8 !important;
    color: #2c2416 !important;
}}

header[data-testid="stHeader"],
div[data-testid="stDecoration"],
div[data-testid="stToolbar"] {{
    display: none !important;
    height: 0 !important;
}}

.block-container {{
    padding-top: {"4rem" if IS_REQUEST_PAGE else "5.5rem"} !important;
    padding-bottom: 3rem !important;
    padding-left: 2.5rem !important;
    padding-right: 2.5rem !important;
    max-width: 1360px !important;
    margin: 0 auto;
}}

/* ── 헤더 ── */
.site-header {{
    position: fixed;
    top: 0; left: 0;
    width: 100%;
    height: 56px;
    background: #fdfaf4;
    border-bottom: 1px solid #e8e0d0;
    display: flex;
    align-items: center;
    padding: 0 2.5rem;
    gap: 14px;
    z-index: 9999;
}}
.site-header .logo-mark {{
    width: 28px; height: 28px;
    background: #2c2416;
    border-radius: 8px;
    flex-shrink: 0;
    position: relative;
}}
.site-header .logo-mark::after {{
    content: '';
    position: absolute;
    top: 6px; left: 6px;
    width: 10px; height: 10px;
    background: #c07c3a;
    border-radius: 3px;
}}
.site-header .logo-text {{
    font-family: 'Fraunces', serif;
    font-size: 16px;
    font-weight: 400;
    letter-spacing: 0.01em;
    color: #2c2416;
}}
.site-header .header-badge {{
    margin-left: auto;
    font-size: 10px;
    font-weight: 600;
    color: #c07c3a;
    background: rgba(192, 124, 58, 0.1);
    border: 1px solid rgba(192, 124, 58, 0.25);
    padding: 3px 10px;
    border-radius: 20px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}}

/* ── 메뉴 버튼 ── */
.stButton > button {{
    width: 100% !important;
    text-align: left !important;
    background: transparent !important;
    border: none !important;
    border-radius: 8px !important;
    height: 40px !important;
    color: #8a7d6b !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 13.5px !important;
    font-weight: 500 !important;
    padding: 0 12px !important;
    margin-bottom: 2px !important;
    transition: all 0.18s ease !important;
}}
.stButton > button:hover {{
    background: rgba(192, 124, 58, 0.08) !important;
    color: #c07c3a !important;
}}
.stButton > button:active {{
    transform: scale(0.98) !important;
}}

.menu-section {{
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #b8ad9e;
    padding: 20px 12px 6px;
}}

/* ── 페이지 타이틀 ── */
.page-title {{
    font-family: 'Fraunces', serif;
    font-size: 28px;
    font-weight: 300;
    color: #2c2416;
    letter-spacing: -0.01em;
    margin-bottom: 4px;
    line-height: 1.2;
}}
.page-sub {{
    font-size: 13px;
    color: #8a7d6b;
    margin-bottom: 28px;
    font-weight: 400;
}}

/* ── 메트릭 카드 ── */
div[data-testid="stMetric"] {{
    background: #fff9ef !important;
    border: 1px solid #e8e0d0 !important;
    border-radius: 14px !important;
    padding: 22px 24px !important;
    transition: all 0.2s ease !important;
}}
div[data-testid="stMetric"]:hover {{
    border-color: #c07c3a !important;
    box-shadow: 0 4px 20px rgba(192, 124, 58, 0.1) !important;
}}
div[data-testid="stMetric"] label {{
    font-size: 11px !important;
    font-weight: 600 !important;
    color: #b8ad9e !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
}}
div[data-testid="stMetric"] [data-testid="stMetricValue"] {{
    font-family: 'DM Mono', monospace !important;
    font-size: 24px !important;
    font-weight: 500 !important;
    color: #2c2416 !important;
    letter-spacing: -0.02em !important;
}}

/* ── 섹션 헤딩 ── */
.section-heading {{
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #b8ad9e;
    margin-bottom: 14px;
    margin-top: 32px;
}}

/* ── 구분선 ── */
hr, [data-testid="stDivider"] {{
    border-color: #e8e0d0 !important;
    margin: 24px 0 !important;
}}

/* ── 데이터프레임 ── */
[data-testid="stDataFrame"] {{
    border: 1px solid #e8e0d0 !important;
    border-radius: 12px !important;
    overflow: hidden !important;
    background: #fff9ef !important;
}}
[data-testid="stDataFrame"] table {{
    background: #fff9ef !important;
}}
[data-testid="stDataFrame"] th {{
    background: #fdfaf4 !important;
    color: #b8ad9e !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    border-bottom: 1px solid #e8e0d0 !important;
}}
[data-testid="stDataFrame"] td {{
    color: #2c2416 !important;
    font-size: 13px !important;
    border-bottom: 1px solid #f0e8dc !important;
}}

/* ── 폼 인풋 ── */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
[data-testid="stDateInput"] input,
[data-testid="stTextArea"] textarea {{
    background: #fdfaf4 !important;
    border: 1px solid #e8e0d0 !important;
    border-radius: 10px !important;
    color: #2c2416 !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 14px !important;
    transition: border-color 0.2s ease !important;
}}
[data-testid="stTextInput"] input:focus,
[data-testid="stNumberInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {{
    border-color: #c07c3a !important;
    box-shadow: 0 0 0 3px rgba(192, 124, 58, 0.12) !important;
    outline: none !important;
}}
[data-testid="stSelectbox"] div[data-baseweb="select"] > div:hover {{
    border-color: #c07c3a !important;
}}

/* 인풋 라벨 */
[data-testid="stTextInput"] label,
[data-testid="stNumberInput"] label,
[data-testid="stSelectbox"] label,
[data-testid="stDateInput"] label,
[data-testid="stTextArea"] label {{
    color: #8a7d6b !important;
    font-size: 13px !important;
    font-weight: 500 !important;
}}

/* ── 폼 제출 버튼 ── */
[data-testid="stFormSubmitButton"] button {{
    background: #2c2416 !important;
    border: none !important;
    border-radius: 10px !important;
    color: #f5f0e8 !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    height: 44px !important;
    letter-spacing: 0.02em !important;
    transition: all 0.2s ease !important;
}}
[data-testid="stFormSubmitButton"] button:hover {{
    background: #c07c3a !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 8px 24px rgba(192, 124, 58, 0.25) !important;
}}
[data-testid="stFormSubmitButton"] button:active {{
    transform: scale(0.98) translateY(0) !important;
}}

/* ── 알림 박스 ── */
[data-testid="stSuccess"] {{
    background: rgba(92, 122, 92, 0.08) !important;
    border: 1px solid rgba(92, 122, 92, 0.25) !important;
    border-radius: 10px !important;
    color: #3a5c3a !important;
}}
[data-testid="stError"] {{
    background: rgba(180, 60, 60, 0.07) !important;
    border: 1px solid rgba(180, 60, 60, 0.2) !important;
    border-radius: 10px !important;
    color: #8c3030 !important;
}}
[data-testid="stWarning"] {{
    background: rgba(192, 124, 58, 0.08) !important;
    border: 1px solid rgba(192, 124, 58, 0.25) !important;
    border-radius: 10px !important;
    color: #8a5520 !important;
}}
[data-testid="stInfo"] {{
    background: rgba(80, 110, 140, 0.07) !important;
    border: 1px solid rgba(80, 110, 140, 0.2) !important;
    border-radius: 10px !important;
    color: #3a5a78 !important;
}}

/* ── 탭 ── */
[data-testid="stTabs"] [role="tab"] {{
    font-family: 'DM Sans', sans-serif !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    color: #b8ad9e !important;
    border-bottom: 2px solid transparent !important;
    padding: 8px 16px !important;
    transition: all 0.2s !important;
    background: transparent !important;
}}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {{
    color: #2c2416 !important;
    border-bottom-color: #c07c3a !important;
}}
[data-testid="stTabs"] [role="tablist"] {{
    border-bottom: 1px solid #e8e0d0 !important;
    background: transparent !important;
}}

/* ── Expander ── */
[data-testid="stExpander"] {{
    border: 1px solid #e8e0d0 !important;
    border-radius: 12px !important;
    background: #fff9ef !important;
    overflow: hidden !important;
}}
[data-testid="stExpander"] summary {{
    font-size: 14px !important;
    font-weight: 500 !important;
    color: #2c2416 !important;
    padding: 14px 18px !important;
    background: #fff9ef !important;
}}

/* ── ORDER_REQ 히어로 ── */
.request-hero {{
    text-align: center;
    padding: 40px 20px 30px;
}}
.request-hero .r-logo {{
    width: 56px; height: 56px;
    background: #2c2416;
    border-radius: 18px;
    margin: 0 auto 18px;
    position: relative;
}}
.request-hero .r-logo::after {{
    content: '';
    position: absolute;
    top: 14px; left: 14px;
    width: 16px; height: 16px;
    background: #c07c3a;
    border-radius: 5px;
}}
.request-hero h1 {{
    font-family: 'Fraunces', serif;
    font-size: 26px;
    font-weight: 300;
    color: #2c2416;
    letter-spacing: -0.01em;
    margin: 0 0 8px;
}}
.request-hero p {{
    font-size: 13px;
    color: #8a7d6b;
    margin: 0;
}}

/* ── 체크박스 / 라디오 ── */
[data-testid="stCheckbox"] label,
[data-testid="stRadio"] label {{
    color: #8a7d6b !important;
    font-size: 13px !important;
}}

/* ── 다운로드 버튼 ── */
[data-testid="stDownloadButton"] button {{
    background: #fff9ef !important;
    border: 1px solid #e8e0d0 !important;
    border-radius: 10px !important;
    color: #8a7d6b !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 13px !important;
    height: 40px !important;
    transition: all 0.2s !important;
}}
[data-testid="stDownloadButton"] button:hover {{
    border-color: #c07c3a !important;
    color: #c07c3a !important;
    background: rgba(192, 124, 58, 0.05) !important;
}}

/* ── Plotly ── */
.js-plotly-plot .plotly {{
    background: transparent !important;
}}

/* ── 스크롤바 ── */
::-webkit-scrollbar {{ width: 6px; height: 6px; }}
::-webkit-scrollbar-track {{ background: #f5f0e8; }}
::-webkit-scrollbar-thumb {{ background: #d4c9b8; border-radius: 10px; }}
::-webkit-scrollbar-thumb:hover {{ background: #c07c3a; }}

</style>

<div class="site-header">
    <div class="logo-mark"></div>
    <span class="logo-text">Dorco Smart Asset</span>
    <span class="header-badge">Pro</span>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 7. 레이아웃 — 사이드바 토글
# ─────────────────────────────────────────────
top_l, _ = st.columns([1, 9])
with top_l:
    if st.button("☰", key="m_toggle"):
        st.session_state.sidebar_open = not st.session_state.sidebar_open
        st.rerun()

if st.session_state.sidebar_open:
    col_side, col_main = st.columns([1.15, 4.85], gap="large")
else:
    col_main = st.container()

# ── 사이드바 메뉴 ──
if st.session_state.sidebar_open:
    with col_side:
        # 알림 배지용 미리 로드
        _req = load_csv_safe(ORDER_REQ_FILE)
        _pending = len(_req[_req["상태"] == "대기"]) if not _req.empty and "상태" in _req.columns else 0
        _badge = f" 🔔 {_pending}" if _pending > 0 else ""

        st.markdown('<p class="menu-section">Analytics</p>', unsafe_allow_html=True)
        if st.button("  🏠  Home Overview"):
            st.session_state.selected_menu = "DORCO"; st.rerun()
        if st.button("  📊  Insight Report"):
            st.session_state.selected_menu = "REPORT"; st.rerun()

        st.markdown('<p class="menu-section">Management</p>', unsafe_allow_html=True)
        if st.button("  📦  Stock Board"):
            st.session_state.selected_menu = "STOCK"; st.rerun()
        if st.button("  📥  Inbound"):
            st.session_state.selected_menu = "INOUT"
            st.session_state.selected_submenu = "입고"; st.rerun()
        if st.button("  📤  Outbound"):
            st.session_state.selected_menu = "INOUT"
            st.session_state.selected_submenu = "출고"; st.rerun()

        st.markdown('<p class="menu-section">System</p>', unsafe_allow_html=True)
        if st.button("  ⚙️  Admin Settings"):
            st.session_state.selected_menu = "SYSTEM"; st.rerun()

        st.markdown('<p class="menu-section">External</p>', unsafe_allow_html=True)
        if st.button(f"  📢  Field Request{_badge}"):
            st.session_state.selected_menu = "ORDER_REQ"; st.rerun()

# ─────────────────────────────────────────────
# 8. 메인 콘텐츠
# ─────────────────────────────────────────────
with col_main:
    df       = prep_num(load_csv_safe(FILE_PATH), ["현재고", "안전재고"])
    info_df  = load_csv_safe(INFO_FILE)
    req_log  = load_csv_safe(ORDER_REQ_FILE)
    current  = st.session_state.selected_menu

    # ══════════════════════════════════════════
    # 🏠 HOME DASHBOARD
    # ══════════════════════════════════════════
    if current == "DORCO":
        st.markdown('<p class="page-title">Home Overview</p>', unsafe_allow_html=True)
        st.markdown('<p class="page-sub">비품 자산 현황 요약</p>', unsafe_allow_html=True)

        # 발주 대기 알림
        pending_df = req_log[req_log["상태"] == "대기"].copy() if not req_log.empty and "상태" in req_log.columns else pd.DataFrame()

        with st.expander(
            f"🔔 발주 대기 요청{'  ─  ' + str(len(pending_df)) + '건' if not pending_df.empty else ''}",
            expanded=not pending_df.empty
        ):
            if pending_df.empty:
                st.success("처리 대기 중인 발주 요청이 없습니다.")
            else:
                show_cols = ["요청일시","대분류","품목","요청수량","비고"]
                st.dataframe(
                    pending_df.sort_values("요청일시", ascending=False)[show_cols].head(10),
                    use_container_width=True,
                    hide_index=True,
                    column_config={"요청일시": st.column_config.DatetimeColumn(format="MM/DD HH:mm")}
                )
                if pending_df.shape[0] <= 6:
                    st.markdown("**빠른 처리**")
                    cols_btn = st.columns(min(3, len(pending_df)))
                    for (idx, row), col in zip(pending_df.iterrows(), cols_btn):
                        with col:
                            if st.button(f"✓ {row['품목']}", key=f"req_{idx}", use_container_width=True):
                                req_log.at[idx, "상태"] = "처리완료"
                                req_log.to_csv(ORDER_REQ_FILE, index=False, encoding="utf-8-sig")
                                st.success(f"{row['품목']} 처리 완료")
                                st.rerun()

        st.divider()

        # KPI 카드
        df_in = load_csv_safe(IN_FILE, cols=["입고일자","대분류","품목","입고수량","구매금액"])
        today = datetime.now()

        if not df_in.empty:
            df_in["구매금액"] = pd.to_numeric(df_in["구매금액"], errors="coerce").fillna(0)
            df_in["입고일자"] = pd.to_datetime(df_in["입고일자"], errors="coerce")
            df_in = df_in.dropna(subset=["입고일자"])
            year_df  = df_in[df_in["입고일자"].dt.year  == today.year]
            month_df = year_df[year_df["입고일자"].dt.month == today.month]
        else:
            year_df = month_df = pd.DataFrame()

        annual_spent  = int(year_df["구매금액"].sum())  if not year_df.empty  else 0
        monthly_spent = int(month_df["구매금액"].sum()) if not month_df.empty else 0

        # 안전재고 미달 품목 수
        low_stock_cnt = 0
        if not df.empty and "현재고" in df.columns and "안전재고" in df.columns:
            low_stock_cnt = int((df["현재고"] < df["안전재고"]).sum())

        k1, k2, k3 = st.columns(3)
        k1.metric("이번 달 사용 금액",   f"{monthly_spent:,} 원")
        k2.metric("연간 누적 사용 금액", f"{annual_spent:,} 원")
        k3.metric("안전재고 미달 품목",  f"{low_stock_cnt} 개",
                  delta="주의 필요" if low_stock_cnt > 0 else None,
                  delta_color="inverse")

        st.divider()

        # 차트 영역
        left, right = st.columns([6, 4], gap="medium")
        with left:
            st.markdown('<p class="section-heading">이번 달 카테고리별 사용금액</p>', unsafe_allow_html=True)
            if not month_df.empty:
                cat_sum = month_df.groupby("대분류", as_index=False)["구매금액"].sum().sort_values("구매금액", ascending=False)
                fig = go.Figure(go.Pie(
                    labels=cat_sum["대분류"],
                    values=cat_sum["구매금액"],
                    hole=0.6,
                    textinfo="label+percent",
                    hovertemplate="<b>%{label}</b><br>%{value:,.0f} 원<extra></extra>",
                    marker=dict(colors=["#c07c3a","#5c7a5c","#a0704a","#8a9e6c","#c4a882","#6b8f71"])
                ))
                fig.update_layout(
                    height=320, margin=dict(t=10,b=10,l=0,r=0),
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#8a7d6b", family="DM Sans"),
                    showlegend=True,
                    legend=dict(orientation="h", y=-0.05, x=0.5, xanchor="center",
                                font=dict(size=12, color="#8a7d6b"))
                )
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            else:
                st.info("이번 달 입고 데이터가 없습니다.")

        with right:
            st.markdown('<p class="section-heading">분류별 금액 합계</p>', unsafe_allow_html=True)
            if not month_df.empty:
                summary = month_df.groupby("대분류", as_index=False)["구매금액"].sum().sort_values("구매금액", ascending=False)
                st.dataframe(
                    summary.style.format({"구매금액": "{:,.0f} 원"}),
                    use_container_width=True, hide_index=True
                )
            else:
                st.info("데이터 없음")

        # 안전재고 미달 목록
        if not df.empty and low_stock_cnt > 0:
            st.divider()
            st.markdown('<p class="section-heading">⚠️ 안전재고 미달 품목</p>', unsafe_allow_html=True)
            low_df = df[df["현재고"] < df["안전재고"]][["대분류","품목","현재고","안전재고"]].copy()
            low_df["부족수량"] = low_df["안전재고"] - low_df["현재고"]
            st.dataframe(low_df, use_container_width=True, hide_index=True)

    # ══════════════════════════════════════════
    # 📦 STOCK BOARD
    # ══════════════════════════════════════════
    elif current == "STOCK":
        st.markdown('<p class="page-title">Stock Board</p>', unsafe_allow_html=True)
        st.markdown('<p class="page-sub">현재고 실시간 조회 및 수정</p>', unsafe_allow_html=True)

        stock_df = prep_num(load_csv_safe(FILE_PATH), ["현재고", "안전재고"])

        search = st.text_input("🔍 품목 검색", placeholder="품목명을 입력하세요...")
        disp = stock_df.copy()
        if search:
            disp = disp[disp["품목"].astype(str).str.contains(search, na=False)]

        if not disp.empty:
            # 안전재고 미달 강조
            def highlight_low(row):
                color = "color: #ff6b6b; font-weight:600" if row["현재고"] < row["안전재고"] else ""
                return [color] * len(row)
            st.dataframe(
                disp[["대분류","품목","수량단위","현재고","안전재고","최근입고일"]],
                use_container_width=True, hide_index=True
            )
        else:
            st.info("등록된 비품 데이터가 없습니다.")

        st.divider()
        st.markdown('<p class="section-heading">실시간 재고 수정</p>', unsafe_allow_html=True)
        st.caption("실사 후 수량이 다를 경우 즉시 수정하세요.")

        if not info_df.empty:
            all_cats = sorted(info_df["대분류"].dropna().astype(str).unique().tolist())
            adj_cat  = st.selectbox("대분류 선택", all_cats, key="adj_cat")
            adj_items = sorted(info_df[info_df["대분류"] == adj_cat]["품목"].dropna().astype(str).unique().tolist())
        else:
            adj_cat, adj_items = None, []

        adj_item = st.selectbox("품목 선택", adj_items if adj_items else ["품목 없음"], key="adj_item")

        target_row  = stock_df[(stock_df["대분류"] == adj_cat) & (stock_df["품목"] == adj_item)]
        current_val = int(target_row["현재고"].values[0]) if not target_row.empty else 0
        st.info(f"현재 선택 품목의 현재고: **{current_val}개**")

        with st.form("quick_adj_form", clear_on_submit=True):
            c1, c2, c3 = st.columns([1.2, 1.5, 1])
            with c1:
                adj_date = st.date_input("기록 일자", date.today())
            with c2:
                new_qty = st.number_input(f"최종 현재고 입력 (기존: {current_val})", min_value=0, step=1, value=current_val)
            with c3:
                st.markdown("<br>", unsafe_allow_html=True)
                submit_adj = st.form_submit_button("💾 재고 동기화", use_container_width=True)

            if submit_adj:
                if not adj_items or adj_item == "품목 없음":
                    st.error("품목을 선택해주세요.")
                else:
                    idx = stock_df[(stock_df["대분류"] == adj_cat) & (stock_df["품목"] == adj_item)].index
                    if not idx.empty:
                        old_qty = int(pd.to_numeric(stock_df.at[idx[0], "현재고"], errors="coerce") or 0)
                        stock_df.at[idx[0], "현재고"] = int(new_qty)
                        date_str = adj_date.strftime("%Y-%m-%d")
                        if int(new_qty) < old_qty:
                            stock_df.at[idx[0], "최근출고일"] = date_str
                        else:
                            stock_df.at[idx[0], "최근입고일"] = date_str
                        stock_df.to_csv(FILE_PATH, index=False, encoding="utf-8-sig")
                        st.success(f"✅ {adj_item} 재고가 {new_qty}개로 수정되었습니다.")
                        st.rerun()

    # ══════════════════════════════════════════
    # 📥📤 INBOUND / OUTBOUND
    # ══════════════════════════════════════════
    elif current == "INOUT":
        mode = st.session_state.selected_submenu
        icon = "📥" if mode == "입고" else "📤"
        st.markdown(f'<p class="page-title">{icon} {mode} 관리</p>', unsafe_allow_html=True)
        st.markdown(f'<p class="page-sub">{mode} 처리 및 재고 자동 반영</p>', unsafe_allow_html=True)

        if not info_df.empty:
            all_cats = sorted(info_df["대분류"].dropna().unique().tolist())
            sel_cat  = st.selectbox("대분류 선택", all_cats, key="io_cat")
            rel_items = sorted(info_df[info_df["대분류"] == sel_cat]["품목"].dropna().tolist())
        else:
            sel_cat   = st.text_input("대분류 직접 입력")
            rel_items = []

        with st.form("inout_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                io_date = st.date_input("날짜", date.today())
                io_item = st.selectbox("품목 선택", rel_items if rel_items else ["품목 없음"])
            with c2:
                io_qty    = st.number_input("수량", min_value=1, step=1)
                io_note   = st.text_input("비고")
            io_amount = 0
            if mode == "입고":
                io_amount = st.number_input("구매금액 (원)", min_value=0, step=100, value=0)

            submitted = st.form_submit_button(f"{icon} {mode} 확정", use_container_width=True)
            if submitted:
                if not rel_items or io_item == "품목 없음":
                    st.error("품목을 선택해주세요.")
                else:
                    idx = df[(df["대분류"] == sel_cat) & (df["품목"] == io_item)].index
                    if idx.empty:
                        st.error("재고 마스터에 해당 품목이 없습니다. Stock Board에서 확인하세요.")
                    else:
                        i = idx[0]
                        curr_stock = int(pd.to_numeric(df.at[i, "현재고"], errors="coerce") or 0)
                        if mode == "입고":
                            df.at[i, "현재고"]    = curr_stock + io_qty
                            df.at[i, "최근입고일"] = io_date.strftime("%Y-%m-%d")
                            save_log(IN_FILE, {"입고일자": io_date, "대분류": sel_cat,
                                               "품목": io_item, "입고수량": io_qty, "구매금액": io_amount})
                        else:
                            if curr_stock < io_qty:
                                st.error(f"재고 부족 — 현재고: {curr_stock}개")
                                st.stop()
                            df.at[i, "현재고"]    = curr_stock - io_qty
                            df.at[i, "최근출고일"] = io_date.strftime("%Y-%m-%d")
                            save_log(OUT_FILE, {"출고일자": io_date, "대분류": sel_cat,
                                                "품목": io_item, "출고수량": io_qty, "비고": io_note})
                        df.to_csv(FILE_PATH, index=False, encoding="utf-8-sig")
                        st.success(f"✅ {io_item} {io_qty}개 {mode} 처리 완료")
                        st.rerun()

    # ══════════════════════════════════════════
    # 📊 INSIGHT REPORT
    # ══════════════════════════════════════════
    elif current == "REPORT":
        st.markdown('<p class="page-title">Insight Report</p>', unsafe_allow_html=True)
        st.markdown('<p class="page-sub">입고 내역 기반 비용 분석</p>', unsafe_allow_html=True)

        df_in_stat = load_csv_safe(IN_FILE, cols=["입고일자","대분류","품목","입고수량","구매금액"])

        if df_in_stat.empty:
            st.info("입고 내역이 없습니다. 입고 관리에서 데이터를 먼저 등록하세요.")
        else:
            df_in_stat["입고수량"] = pd.to_numeric(df_in_stat["입고수량"], errors="coerce").fillna(0)
            df_in_stat["구매금액"] = pd.to_numeric(df_in_stat["구매금액"], errors="coerce").fillna(0)
            df_in_stat["입고일자"] = pd.to_datetime(df_in_stat["입고일자"], errors="coerce")
            df_in_stat = df_in_stat.dropna(subset=["입고일자"])
            df_in_stat["년월"] = df_in_stat["입고일자"].dt.to_period("M").astype(str)

            today_ts  = pd.Timestamp.today()
            cur_m_str = today_ts.to_period("M").strftime("%Y-%m")
            prv_m_str = (today_ts.to_period("M") - 1).strftime("%Y-%m")
            cur_spent = df_in_stat[df_in_stat["년월"] == cur_m_str]["구매금액"].sum()
            prv_spent = df_in_stat[df_in_stat["년월"] == prv_m_str]["구매금액"].sum()
            diff      = cur_spent - prv_spent

            m1, m2, m3 = st.columns(3)
            m1.metric("당월 집행 금액", f"{int(cur_spent):,} 원")
            m2.metric("전월 집행 금액", f"{int(prv_spent):,} 원")
            m3.metric("전월 대비 증감", f"{int(diff):,} 원",
                      delta=f"{int(diff):,} 원",
                      delta_color="inverse" if diff > 0 else "normal")

            st.divider()

            # 도넛 차트
            st.markdown('<p class="section-heading">카테고리별 사용금액 비중 (전체)</p>', unsafe_allow_html=True)
            cat_sum = df_in_stat.groupby("대분류")["구매금액"].sum().reset_index().sort_values("구매금액", ascending=False)
            fig_donut = go.Figure(go.Pie(
                labels=cat_sum["대분류"], values=cat_sum["구매금액"], hole=0.6,
                textinfo="label+percent",
                hovertemplate="<b>%{label}</b><br>%{value:,.0f} 원<extra></extra>",
                marker=dict(colors=["#c07c3a","#5c7a5c","#a0704a","#8a9e6c","#c4a882","#6b8f71"])
            ))
            fig_donut.update_layout(
                height=320, margin=dict(t=10,b=10,l=10,r=10),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#8a7d6b", family="DM Sans"),
                legend=dict(orientation="h", y=-0.05, x=0.5, xanchor="center",
                            font=dict(size=12, color="#8a7d6b"))
            )
            st.plotly_chart(fig_donut, use_container_width=True, config={"displayModeBar": False})

            st.divider()

            # 상세 로그
            st.markdown('<p class="section-heading">상세 입고 기록</p>', unsafe_allow_html=True)
            cf1, cf2 = st.columns([2,1])
            with cf1:
                month_list = ["전체"] + sorted(df_in_stat["년월"].unique().tolist(), reverse=True)
                sel_month  = st.selectbox("조회 월", month_list)
            with cf2:
                st.markdown("<br>", unsafe_allow_html=True)
                csv_data = df_in_stat.to_csv(index=False, encoding="utf-8-sig")
                st.download_button("📥 CSV 다운로드", data=csv_data,
                                   file_name=f"report_{date.today()}.csv", mime="text/csv",
                                   use_container_width=True)
            disp_df = df_in_stat.copy()
            if sel_month != "전체":
                disp_df = disp_df[disp_df["년월"] == sel_month]
            disp_df["입고일자"] = disp_df["입고일자"].dt.strftime("%Y-%m-%d")
            st.dataframe(
                disp_df[["입고일자","대분류","품목","입고수량","구매금액"]].sort_values("입고일자", ascending=False),
                use_container_width=True, hide_index=True,
                column_config={
                    "구매금액": st.column_config.NumberColumn("구매금액", format="%d 원"),
                    "입고수량": st.column_config.NumberColumn("수량", format="%d"),
                }
            )

    # ══════════════════════════════════════════
    # ⚙️ ADMIN SETTINGS
    # ══════════════════════════════════════════
    elif current == "SYSTEM":
        st.markdown('<p class="page-title">Admin Settings</p>', unsafe_allow_html=True)
        st.markdown('<p class="page-sub">품목 마스터 관리 및 시스템 설정</p>', unsafe_allow_html=True)

        _req_admin  = load_csv_safe(ORDER_REQ_FILE)
        _pend_admin = len(_req_admin[_req_admin["상태"] == "대기"]) if not _req_admin.empty and "상태" in _req_admin.columns else 0
        if _pend_admin > 0 and not st.session_state.admin_toast_shown:
            st.toast(f"📦 발주 요청 {_pend_admin}건 대기 중", icon="🔔")
            st.session_state.admin_toast_shown = True

        tab1, tab2, tab3 = st.tabs(["🆕 신규 품목 등록", "🗑️ 품목 / 분류 삭제", "🚨 데이터 초기화"])

        # ── TAB 1: 신규 등록 ──
        with tab1:
            st.markdown('<p class="section-heading">새 비품 마스터 등록</p>', unsafe_allow_html=True)
            existing_cats = sorted(info_df["대분류"].dropna().unique().tolist()) if not info_df.empty else ["식음료류","미화용품","상비약","기타"]

            selected_cat  = st.selectbox("대분류 선택", existing_cats + ["+ 직접 입력"], key="new_cat")
            new_cat_input = ""
            if selected_cat == "+ 직접 입력":
                new_cat_input = st.text_input("신규 분류명 입력", placeholder="예: 미화용품")

            with st.form("new_item_form", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1:
                    item_name = st.text_input("품목명 (필수)", placeholder="예: A4 용지(75g)")
                    vendor    = st.text_input("구매처",        placeholder="예: 쿠팡")
                    unit      = st.text_input("수량 단위",     value="EA", placeholder="EA / Box / 묶음")
                with c2:
                    safety_stock      = st.number_input("안전재고", min_value=0, value=5)
                    default_order_qty = st.number_input("기본 발주수량", min_value=1, value=1)
                    note = st.text_area("비고")

                submit_btn = st.form_submit_button("📥 등록", use_container_width=True)
                if submit_btn:
                    final_cat = new_cat_input if selected_cat == "+ 직접 입력" else selected_cat
                    if not item_name:
                        st.error("품목명은 필수입니다.")
                    elif not final_cat:
                        st.error("분류명을 입력하거나 선택하세요.")
                    elif not df.empty and ((df["대분류"] == final_cat) & (df["품목"] == item_name)).any():
                        st.error(f"'{item_name}'은 이미 등록된 품목입니다.")
                    else:
                        save_log(INFO_FILE, {"대분류": final_cat, "품목": item_name, "구매처": vendor,
                                             "수량단위": unit, "안전재고": safety_stock,
                                             "기본발주수량": default_order_qty, "비고": note})
                        save_log(FILE_PATH, {"대분류": final_cat, "품목": item_name, "수량단위": unit,
                                             "현재고": 0, "안전재고": safety_stock,
                                             "최근입고일": "", "최근출고일": ""})
                        st.success(f"✅ '{item_name}' 등록 완료!")
                        st.balloons()
                        st.rerun()

        # ── TAB 2: 삭제 ──
        with tab2:
            st.markdown('<p class="section-heading">품목 / 대분류 삭제</p>', unsafe_allow_html=True)
            st.warning("삭제 후 복구가 불가능합니다. 신중히 진행하세요.")

            del_mode = st.radio("삭제 유형", ["품목 삭제", "대분류 삭제"], horizontal=True)

            if del_mode == "품목 삭제":
                if not info_df.empty:
                    del_cat = st.selectbox("대분류 선택", sorted(info_df["대분류"].dropna().unique().tolist()), key="del_item_cat")
                    del_items = sorted(info_df[info_df["대분류"] == del_cat]["품목"].dropna().unique().tolist())
                    del_item  = st.selectbox("삭제할 품목", del_items, key="del_item_name")
                    confirm   = st.checkbox(f"'{del_item}' 을(를) 삭제하겠습니다.")
                    if st.button("🗑️ 품목 삭제"):
                        if confirm:
                            info_df_new = info_df[info_df["품목"] != del_item]
                            df_new      = df[df["품목"] != del_item]
                            info_df_new.to_csv(INFO_FILE, index=False, encoding="utf-8-sig")
                            df_new.to_csv(FILE_PATH, index=False, encoding="utf-8-sig")
                            st.success(f"'{del_item}' 삭제 완료")
                            st.rerun()
                        else:
                            st.error("삭제 확인 체크박스를 먼저 선택하세요.")
                else:
                    st.info("삭제할 품목이 없습니다.")

            else:
                if not info_df.empty:
                    del_cat_g = st.selectbox("삭제할 대분류", sorted(info_df["대분류"].dropna().unique().tolist()), key="del_grp")
                    cnt = len(info_df[info_df["대분류"] == del_cat_g])
                    st.warning(f"'{del_cat_g}' 대분류 삭제 시 품목 {cnt}개도 함께 삭제됩니다.")
                    confirm_g = st.checkbox(f"'{del_cat_g}' 대분류 전체를 삭제하겠습니다.")
                    if st.button("🗑️ 대분류 삭제"):
                        if confirm_g:
                            info_df_new = info_df[info_df["대분류"] != del_cat_g]
                            df_new      = df[df["대분류"] != del_cat_g]
                            info_df_new.to_csv(INFO_FILE, index=False, encoding="utf-8-sig")
                            df_new.to_csv(FILE_PATH, index=False, encoding="utf-8-sig")
                            st.success(f"'{del_cat_g}' 삭제 완료")
                            st.rerun()
                        else:
                            st.error("삭제 확인 체크박스를 먼저 선택하세요.")
                else:
                    st.info("삭제할 대분류가 없습니다.")

        # ── TAB 3: 초기화 ──
        with tab3:
            st.markdown('<p class="section-heading">시스템 데이터 초기화</p>', unsafe_allow_html=True)
            st.error("⚠️ 아래 실행 시 모든 재고 현황, 입/출고 내역, 품목 마스터가 영구 삭제됩니다.")
            confirm_pw = st.text_input("관리자 비밀번호 입력", type="password", key="reset_pw")
            if st.button("🚨 전체 데이터 초기화"):
                if confirm_pw == "0422":
                    for path, cols in [
                        (INFO_FILE,      ["대분류","품목","구매처","수량단위","안전재고","기본발주수량","비고"]),
                        (FILE_PATH,      ["대분류","품목","수량단위","현재고","안전재고","최근입고일","최근출고일"]),
                        (IN_FILE,        ["입고일자","대분류","품목","입고수량","구매금액"]),
                        (OUT_FILE,       ["출고일자","대분류","품목","출고수량","비고"]),
                        (ORDER_REQ_FILE, ["요청일시","대분류","품목","요청수량","비고","상태"]),
                    ]:
                        pd.DataFrame(columns=cols).to_csv(path, index=False, encoding="utf-8-sig")
                    st.success("초기화 완료.")
                    st.rerun()
                else:
                    st.error("비밀번호가 일치하지 않습니다.")

    # ══════════════════════════════════════════
    # 📢 ORDER REQUEST — 현장 여사님용 (QR 랜딩)
    # ══════════════════════════════════════════
    elif current == "ORDER_REQ":
        # 모바일 최적화 히어로 섹션
        st.markdown("""
        <div class="request-hero">
            <div class="r-logo"></div>
            <h1>비품 발주 요청</h1>
            <p>필요한 비품을 선택하고 요청 버튼을 누르세요</p>
        </div>
        """, unsafe_allow_html=True)

        if info_df.empty:
            st.warning("등록된 품목이 없습니다. 관리자에게 문의하세요.")
        else:
            cat_list = sorted(info_df["대분류"].dropna().astype(str).unique().tolist())
            sel_cat  = st.selectbox("카테고리", cat_list, key="req_cat")

            items_in_cat = sorted(
                info_df[info_df["대분류"] == sel_cat]["품목"].dropna().astype(str).unique().tolist()
            )

            with st.form("request_form", clear_on_submit=True):
                sel_item = st.selectbox("품목 선택", items_in_cat, key="req_item")

                item_info = info_df[(info_df["대분류"] == sel_cat) & (info_df["품목"] == sel_item)]
                unit_val  = item_info["수량단위"].values[0] if not item_info.empty and "수량단위" in item_info.columns else ""
                def_qty   = (int(pd.to_numeric(item_info["기본발주수량"].values[0], errors="coerce"))
                             if not item_info.empty and "기본발주수량" in item_info.columns
                             and pd.notna(item_info["기본발주수량"].values[0]) else 1)

                # 수량 직접 조정 가능
                req_qty = st.number_input(
                    f"요청 수량 ({unit_val})", min_value=1, value=def_qty, step=1,
                    help=f"기본 발주수량은 {def_qty} {unit_val}입니다."
                )
                req_note = st.text_input("전달 사항 (선택)", placeholder="예: 빨리 필요해요")

                btn = st.form_submit_button("🚀 발주 요청하기", use_container_width=True)

                if btn:
                    # ── 중복 발주 방지 (30분 내 동일 품목 대기 요청 차단) ──
                    fresh_log = load_csv_safe(ORDER_REQ_FILE)
                    if is_duplicate_request(fresh_log, sel_cat, sel_item, minutes=30):
                        st.warning(
                            f"⚠️ **{sel_item}** 은(는) 최근 30분 내 이미 요청되었습니다.\n\n"
                            "처리 완료 후 다시 요청해주세요.",
                            icon="🔔"
                        )
                    else:
                        save_log(
                            ORDER_REQ_FILE,
                            {
                                "요청일시": datetime.now().strftime("%Y-%m-%d %H:%M"),
                                "대분류": sel_cat,
                                "품목": sel_item,
                                "요청수량": req_qty,
                                "비고": req_note,
                                "상태": "대기",
                            }
                        )
                        st.success(
                            f"✅ [{sel_cat}] **{sel_item}** {req_qty} {unit_val} 요청이 접수되었습니다!\n\n"
                            "관리자에게 알림이 전송됩니다."
                        )
                        st.toast("📦 발주 요청 접수 완료", icon="✅")
