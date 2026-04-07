import os
import pandas as pd
import streamlit as st
from datetime import datetime, date, timedelta
import plotly.graph_objects as go
from supabase import create_client, Client

# ─────────────────────────────────────────────
# 1. 페이지 설정
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Dorco Asset Pro",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────
# 2. Supabase 클라이언트
# ─────────────────────────────────────────────
@st.cache_resource
def get_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

sb = get_supabase()

# ─────────────────────────────────────────────
# 3. 세션 상태 초기화
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
# 4. Supabase CRUD 헬퍼
# ─────────────────────────────────────────────

def sb_select(table: str) -> pd.DataFrame:
    """테이블 전체 조회 → DataFrame"""
    try:
        res = sb.table(table).select("*").execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except Exception as e:
        st.error(f"[DB 조회 오류] {table}: {e}")
        return pd.DataFrame()


def sb_insert(table: str, row: dict):
    """단일 행 삽입"""
    row = {k: v for k, v in row.items() if k != "id"}
    try:
        sb.table(table).insert(row).execute()
    except Exception as e:
        st.error(f"[DB 저장 오류] {table}: {e}")


def sb_update(table: str, row_id: int, fields: dict):
    """id 기준 업데이트"""
    try:
        sb.table(table).update(fields).eq("id", row_id).execute()
    except Exception as e:
        st.error(f"[DB 수정 오류] {table}: {e}")


def sb_delete_where(table: str, col: str, val):
    """컬럼 값 기준 전체 삭제"""
    try:
        sb.table(table).delete().eq(col, val).execute()
    except Exception as e:
        st.error(f"[DB 삭제 오류] {table}: {e}")


def prep_num(df: pd.DataFrame, cols: list) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)
    return df

# ─────────────────────────────────────────────
# 5. 중복 발주 방지
# ─────────────────────────────────────────────
def is_duplicate_request(cat: str, item: str, minutes: int = 30) -> bool:
    try:
        res = (
            sb.table("order_requests")
            .select("요청일시")
            .eq("대분류", cat)
            .eq("품목", item)
            .eq("상태", "대기")
            .execute()
        )
        if not res.data:
            return False
        cutoff = datetime.now() - timedelta(minutes=minutes)
        for row in res.data:
            try:
                if datetime.strptime(row["요청일시"], "%Y-%m-%d %H:%M") >= cutoff:
                    return True
            except Exception:
                continue
        return False
    except Exception:
        return False

# ─────────────────────────────────────────────
# 6. CSS — 크림/베이지 테마
# ─────────────────────────────────────────────
IS_REQUEST_PAGE = (st.session_state.selected_menu == "ORDER_REQ")

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,300;9..144,400;9..144,500&family=DM+Sans:wght@400;500;600&family=DM+Mono:wght@400;500&display=swap');

*, *::before, *::after {{ box-sizing: border-box; }}

html, body, [data-testid="stApp"], .stApp {{
    font-family: 'DM Sans', sans-serif !important;
    background: #f5f0e8 !important;
    color: #2c2416 !important;
}}
header[data-testid="stHeader"],
div[data-testid="stDecoration"],
div[data-testid="stToolbar"] {{
    display: none !important; height: 0 !important;
}}
.block-container {{
    padding-top: {"4rem" if IS_REQUEST_PAGE else "5.5rem"} !important;
    padding-bottom: 3rem !important;
    padding-left: 2.5rem !important;
    padding-right: 2.5rem !important;
    max-width: 1360px !important;
    margin: 0 auto;
}}
.site-header {{
    position: fixed; top: 0; left: 0;
    width: 100%; height: 56px;
    background: #fdfaf4; border-bottom: 1px solid #e8e0d0;
    display: flex; align-items: center;
    padding: 0 2.5rem; gap: 14px; z-index: 9999;
}}
.site-header .logo-mark {{
    width: 28px; height: 28px; background: #2c2416;
    border-radius: 8px; flex-shrink: 0; position: relative;
}}
.site-header .logo-mark::after {{
    content: ''; position: absolute;
    top: 6px; left: 6px; width: 10px; height: 10px;
    background: #c07c3a; border-radius: 3px;
}}
.site-header .logo-text {{
    font-family: 'Fraunces', serif; font-size: 16px;
    font-weight: 400; letter-spacing: 0.01em; color: #2c2416;
}}
.site-header .header-badge {{
    margin-left: auto; font-size: 10px; font-weight: 600;
    color: #c07c3a; background: rgba(192,124,58,0.1);
    border: 1px solid rgba(192,124,58,0.25);
    padding: 3px 10px; border-radius: 20px;
    letter-spacing: 0.08em; text-transform: uppercase;
}}
.stButton > button {{
    width: 100% !important; text-align: left !important;
    background: transparent !important; border: none !important;
    border-radius: 8px !important; height: 40px !important;
    color: #8a7d6b !important; font-family: 'DM Sans', sans-serif !important;
    font-size: 13.5px !important; font-weight: 500 !important;
    padding: 0 12px !important; margin-bottom: 2px !important;
    transition: all 0.18s ease !important;
}}
.stButton > button:hover {{
    background: rgba(192,124,58,0.08) !important; color: #c07c3a !important;
}}
.stButton > button:active {{ transform: scale(0.98) !important; }}
.menu-section {{
    font-size: 10px; font-weight: 600; letter-spacing: 0.14em;
    text-transform: uppercase; color: #b8ad9e; padding: 20px 12px 6px;
}}
.page-title {{
    font-family: 'Fraunces', serif; font-size: 28px; font-weight: 300;
    color: #2c2416; letter-spacing: -0.01em; margin-bottom: 4px; line-height: 1.2;
}}
.page-sub {{
    font-size: 13px; color: #8a7d6b; margin-bottom: 28px; font-weight: 400;
}}
div[data-testid="stMetric"] {{
    background: #fff9ef !important; border: 1px solid #e8e0d0 !important;
    border-radius: 14px !important; padding: 22px 24px !important;
    transition: all 0.2s ease !important;
}}
div[data-testid="stMetric"]:hover {{
    border-color: #c07c3a !important;
    box-shadow: 0 4px 20px rgba(192,124,58,0.1) !important;
}}
div[data-testid="stMetric"] label {{
    font-size: 11px !important; font-weight: 600 !important;
    color: #b8ad9e !important; letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
}}
div[data-testid="stMetric"] [data-testid="stMetricValue"] {{
    font-family: 'DM Mono', monospace !important; font-size: 24px !important;
    font-weight: 500 !important; color: #2c2416 !important; letter-spacing: -0.02em !important;
}}
.section-heading {{
    font-size: 11px; font-weight: 600; letter-spacing: 0.1em;
    text-transform: uppercase; color: #b8ad9e;
    margin-bottom: 14px; margin-top: 32px;
}}
hr, [data-testid="stDivider"] {{
    border-color: #e8e0d0 !important; margin: 24px 0 !important;
}}
[data-testid="stDataFrame"] {{
    border: 1px solid #e8e0d0 !important; border-radius: 12px !important;
    overflow: hidden !important; background: #fff9ef !important;
}}
[data-testid="stDataFrame"] th {{
    background: #fdfaf4 !important; color: #b8ad9e !important;
    font-size: 11px !important; font-weight: 600 !important;
    letter-spacing: 0.08em !important; text-transform: uppercase !important;
    border-bottom: 1px solid #e8e0d0 !important;
}}
[data-testid="stDataFrame"] td {{
    color: #2c2416 !important; font-size: 13px !important;
    border-bottom: 1px solid #f0e8dc !important;
}}
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
[data-testid="stDateInput"] input,
[data-testid="stTextArea"] textarea {{
    background: #fdfaf4 !important; border: 1px solid #e8e0d0 !important;
    border-radius: 10px !important; color: #2c2416 !important;
    font-family: 'DM Sans', sans-serif !important; font-size: 14px !important;
    transition: border-color 0.2s ease !important;
}}
[data-testid="stTextInput"] input:focus,
[data-testid="stNumberInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {{
    border-color: #c07c3a !important;
    box-shadow: 0 0 0 3px rgba(192,124,58,0.12) !important; outline: none !important;
}}
[data-testid="stTextInput"] label,
[data-testid="stNumberInput"] label,
[data-testid="stSelectbox"] label,
[data-testid="stDateInput"] label,
[data-testid="stTextArea"] label {{
    color: #8a7d6b !important; font-size: 13px !important; font-weight: 500 !important;
}}
[data-testid="stFormSubmitButton"] button {{
    background: #2c2416 !important; border: none !important;
    border-radius: 10px !important; color: #f5f0e8 !important;
    font-family: 'DM Sans', sans-serif !important; font-weight: 600 !important;
    font-size: 14px !important; height: 44px !important;
    letter-spacing: 0.02em !important; transition: all 0.2s ease !important;
}}
[data-testid="stFormSubmitButton"] button:hover {{
    background: #c07c3a !important; transform: translateY(-1px) !important;
    box-shadow: 0 8px 24px rgba(192,124,58,0.25) !important;
}}
[data-testid="stSuccess"] {{
    background: rgba(92,122,92,0.08) !important;
    border: 1px solid rgba(92,122,92,0.25) !important;
    border-radius: 10px !important; color: #3a5c3a !important;
}}
[data-testid="stError"] {{
    background: rgba(180,60,60,0.07) !important;
    border: 1px solid rgba(180,60,60,0.2) !important;
    border-radius: 10px !important; color: #8c3030 !important;
}}
[data-testid="stWarning"] {{
    background: rgba(192,124,58,0.08) !important;
    border: 1px solid rgba(192,124,58,0.25) !important;
    border-radius: 10px !important; color: #8a5520 !important;
}}
[data-testid="stInfo"] {{
    background: rgba(80,110,140,0.07) !important;
    border: 1px solid rgba(80,110,140,0.2) !important;
    border-radius: 10px !important; color: #3a5a78 !important;
}}
[data-testid="stTabs"] [role="tab"] {{
    font-family: 'DM Sans', sans-serif !important; font-size: 13px !important;
    font-weight: 500 !important; color: #b8ad9e !important;
    border-bottom: 2px solid transparent !important; padding: 8px 16px !important;
    transition: all 0.2s !important; background: transparent !important;
}}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {{
    color: #2c2416 !important; border-bottom-color: #c07c3a !important;
}}
[data-testid="stTabs"] [role="tablist"] {{
    border-bottom: 1px solid #e8e0d0 !important; background: transparent !important;
}}
[data-testid="stExpander"] {{
    border: 1px solid #e8e0d0 !important; border-radius: 12px !important;
    background: #fff9ef !important; overflow: hidden !important;
}}
[data-testid="stExpander"] summary {{
    font-size: 14px !important; font-weight: 500 !important;
    color: #2c2416 !important; padding: 14px 18px !important;
    background: #fff9ef !important;
}}
.request-hero {{ text-align: center; padding: 40px 20px 30px; }}
.request-hero .r-logo {{
    width: 56px; height: 56px; background: #2c2416;
    border-radius: 18px; margin: 0 auto 18px; position: relative;
}}
.request-hero .r-logo::after {{
    content: ''; position: absolute;
    top: 14px; left: 14px; width: 16px; height: 16px;
    background: #c07c3a; border-radius: 5px;
}}
.request-hero h1 {{
    font-family: 'Fraunces', serif; font-size: 26px; font-weight: 300;
    color: #2c2416; letter-spacing: -0.01em; margin: 0 0 8px;
}}
.request-hero p {{ font-size: 13px; color: #8a7d6b; margin: 0; }}
[data-testid="stCheckbox"] label,
[data-testid="stRadio"] label {{
    color: #8a7d6b !important; font-size: 13px !important;
}}
[data-testid="stDownloadButton"] button {{
    background: #fff9ef !important; border: 1px solid #e8e0d0 !important;
    border-radius: 10px !important; color: #8a7d6b !important;
    font-family: 'DM Sans', sans-serif !important; font-size: 13px !important;
    height: 40px !important; transition: all 0.2s !important;
}}
[data-testid="stDownloadButton"] button:hover {{
    border-color: #c07c3a !important; color: #c07c3a !important;
    background: rgba(192,124,58,0.05) !important;
}}
.js-plotly-plot .plotly {{ background: transparent !important; }}
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
# 7. 레이아웃
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

if st.session_state.sidebar_open:
    with col_side:
        _req_df  = sb_select("order_requests")
        _pending = len(_req_df[_req_df["상태"] == "대기"]) if not _req_df.empty and "상태" in _req_df.columns else 0
        _badge   = f" 🔔 {_pending}" if _pending > 0 else ""

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
    df      = prep_num(sb_select("inventory"), ["현재고", "안전재고"])
    info_df = sb_select("inventory_info")
    req_log = sb_select("order_requests")
    current = st.session_state.selected_menu

    # ══════════════════════════════════════════
    # 🏠 HOME DASHBOARD
    # ══════════════════════════════════════════
    if current == "DORCO":
        st.markdown('<p class="page-title">Home Overview</p>', unsafe_allow_html=True)
        st.markdown('<p class="page-sub">비품 자산 현황 요약</p>', unsafe_allow_html=True)

        pending_df = (
            req_log[req_log["상태"] == "대기"].copy()
            if not req_log.empty and "상태" in req_log.columns
            else pd.DataFrame()
        )

        with st.expander(
            f"🔔 발주 대기 요청{'  ─  ' + str(len(pending_df)) + '건' if not pending_df.empty else ''}",
            expanded=not pending_df.empty
        ):
            if pending_df.empty:
                st.success("처리 대기 중인 발주 요청이 없습니다.")
            else:
                show_cols = [c for c in ["요청일시","대분류","품목","요청수량","비고"] if c in pending_df.columns]
                st.dataframe(
                    pending_df.sort_values("요청일시", ascending=False)[show_cols].head(10),
                    use_container_width=True, hide_index=True,
                )
                if pending_df.shape[0] <= 6:
                    st.markdown("**빠른 처리**")
                    cols_btn = st.columns(min(3, len(pending_df)))
                    for (_, row), col in zip(pending_df.iterrows(), cols_btn):
                        with col:
                            if st.button(f"✓ {row['품목']}", key=f"req_{row['id']}", use_container_width=True):
                                sb_update("order_requests", int(row["id"]), {"상태": "처리완료"})
                                st.success(f"{row['품목']} 처리 완료")
                                st.rerun()

        st.divider()

        df_in = sb_select("inventory_in")
        today = datetime.now()

        if not df_in.empty:
            df_in["구매금액"] = pd.to_numeric(df_in["구매금액"], errors="coerce").fillna(0)
            df_in["입고일자"] = pd.to_datetime(df_in["입고일자"], errors="coerce")
            df_in     = df_in.dropna(subset=["입고일자"])
            year_df   = df_in[df_in["입고일자"].dt.year  == today.year]
            month_df  = year_df[year_df["입고일자"].dt.month == today.month]
        else:
            year_df = month_df = pd.DataFrame()

        annual_spent  = int(year_df["구매금액"].sum())  if not year_df.empty  else 0
        monthly_spent = int(month_df["구매금액"].sum()) if not month_df.empty else 0
        low_stock_cnt = int((df["현재고"] < df["안전재고"]).sum()) if not df.empty and "현재고" in df.columns else 0

        k1, k2, k3 = st.columns(3)
        k1.metric("이번 달 사용 금액",   f"{monthly_spent:,} 원")
        k2.metric("연간 누적 사용 금액", f"{annual_spent:,} 원")
        k3.metric("안전재고 미달 품목",  f"{low_stock_cnt} 개",
                  delta="주의 필요" if low_stock_cnt > 0 else None,
                  delta_color="inverse")

        st.divider()

        left, right = st.columns([6, 4], gap="medium")
        with left:
            st.markdown('<p class="section-heading">이번 달 카테고리별 사용금액</p>', unsafe_allow_html=True)
            if not month_df.empty:
                cat_sum = month_df.groupby("대분류", as_index=False)["구매금액"].sum().sort_values("구매금액", ascending=False)
                fig = go.Figure(go.Pie(
                    labels=cat_sum["대분류"], values=cat_sum["구매금액"],
                    hole=0.6, textinfo="label+percent",
                    hovertemplate="<b>%{label}</b><br>%{value:,.0f} 원<extra></extra>",
                    marker=dict(colors=["#c07c3a","#5c7a5c","#a0704a","#8a9e6c","#c4a882","#6b8f71"])
                ))
                fig.update_layout(
                    height=320, margin=dict(t=10,b=10,l=0,r=0),
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#8a7d6b", family="DM Sans"), showlegend=True,
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
                st.dataframe(summary.style.format({"구매금액": "{:,.0f} 원"}),
                             use_container_width=True, hide_index=True)
            else:
                st.info("데이터 없음")

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

        stock_df = prep_num(sb_select("inventory"), ["현재고", "안전재고"])

        sf1, sf2 = st.columns([1, 2])
        with sf1:
            stock_cats    = ["전체"] + sorted(stock_df["대분류"].dropna().astype(str).unique().tolist()) if not stock_df.empty else ["전체"]
            stock_cat_sel = st.selectbox("대분류 필터", stock_cats, key="stock_cat_filter")
        with sf2:
            search = st.text_input("🔍 품목 검색", placeholder="품목명을 입력하세요...")

        disp = stock_df.copy()
        if stock_cat_sel != "전체":
            disp = disp[disp["대분류"] == stock_cat_sel]
        if search:
            disp = disp[disp["품목"].astype(str).str.contains(search, na=False)]

        if not disp.empty:
            show_cols = [c for c in ["대분류","품목","수량단위","현재고","안전재고","최근입고일"] if c in disp.columns]
            st.dataframe(disp[show_cols], use_container_width=True, hide_index=True)
        else:
            st.info("등록된 비품 데이터가 없습니다.")

        st.divider()
        st.markdown('<p class="section-heading">실시간 재고 수정</p>', unsafe_allow_html=True)
        st.caption("실사 후 수량이 다를 경우 즉시 수정하세요.")

        if not info_df.empty:
            all_cats  = sorted(info_df["대분류"].dropna().astype(str).unique().tolist())
            adj_cat   = st.selectbox("대분류 선택", all_cats, key="adj_cat")
            adj_items = sorted(info_df[info_df["대분류"] == adj_cat]["품목"].dropna().astype(str).unique().tolist())
        else:
            adj_cat, adj_items = None, []

        adj_item   = st.selectbox("품목 선택", adj_items if adj_items else ["품목 없음"], key="adj_item")
        target_row = stock_df[(stock_df["대분류"] == adj_cat) & (stock_df["품목"] == adj_item)] if not stock_df.empty else pd.DataFrame()
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
                elif not target_row.empty:
                    row_id   = int(target_row["id"].values[0])
                    date_str = adj_date.strftime("%Y-%m-%d")
                    fields   = {"현재고": int(new_qty)}
                    fields["최근출고일" if int(new_qty) < current_val else "최근입고일"] = date_str
                    sb_update("inventory", row_id, fields)
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
            all_cats  = sorted(info_df["대분류"].dropna().unique().tolist())
            sel_cat   = st.selectbox("대분류 선택", all_cats, key="io_cat")
            rel_items = sorted(info_df[info_df["대분류"] == sel_cat]["품목"].dropna().tolist())
        else:
            sel_cat, rel_items = st.text_input("대분류 직접 입력"), []

        with st.form("inout_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                io_date = st.date_input("날짜", date.today())
                io_item = st.selectbox("품목 선택", rel_items if rel_items else ["품목 없음"])
            with c2:
                io_qty  = st.number_input("수량", min_value=1, step=1)
                io_note = st.text_input("비고")
            io_amount = 0
            if mode == "입고":
                io_amount = st.number_input("구매금액 (원)", min_value=0, step=100, value=0)

            submitted = st.form_submit_button(f"{icon} {mode} 확정", use_container_width=True)
            if submitted:
                if not rel_items or io_item == "품목 없음":
                    st.error("품목을 선택해주세요.")
                else:
                    inv_row = df[(df["대분류"] == sel_cat) & (df["품목"] == io_item)]
                    if inv_row.empty:
                        st.error("재고 마스터에 해당 품목이 없습니다.")
                    else:
                        row_id     = int(inv_row["id"].values[0])
                        curr_stock = int(inv_row["현재고"].values[0])
                        if mode == "입고":
                            sb_update("inventory", row_id, {
                                "현재고": curr_stock + io_qty,
                                "최근입고일": io_date.strftime("%Y-%m-%d")
                            })
                            sb_insert("inventory_in", {
                                "입고일자": io_date.strftime("%Y-%m-%d"),
                                "대분류": sel_cat, "품목": io_item,
                                "입고수량": io_qty, "구매금액": io_amount
                            })
                        else:
                            if curr_stock < io_qty:
                                st.error(f"재고 부족 — 현재고: {curr_stock}개")
                                st.stop()
                            sb_update("inventory", row_id, {
                                "현재고": curr_stock - io_qty,
                                "최근출고일": io_date.strftime("%Y-%m-%d")
                            })
                            sb_insert("inventory_out", {
                                "출고일자": io_date.strftime("%Y-%m-%d"),
                                "대분류": sel_cat, "품목": io_item,
                                "출고수량": io_qty, "비고": io_note
                            })
                        st.success(f"✅ {io_item} {io_qty}개 {mode} 처리 완료")
                        st.rerun()

    # ══════════════════════════════════════════
    # 📊 INSIGHT REPORT
    # ══════════════════════════════════════════
    elif current == "REPORT":
        st.markdown('<p class="page-title">Insight Report</p>', unsafe_allow_html=True)
        st.markdown('<p class="page-sub">입고 내역 기반 비용 분석</p>', unsafe_allow_html=True)

        df_in_stat = sb_select("inventory_in")

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

            # ── KPI 카드 + 당월 도넛 차트 나란히 ──
            kpi_col, donut_col = st.columns([1, 1.4], gap="large")

            with kpi_col:
                st.metric("당월 집행 금액", f"{int(cur_spent):,} 원")
                st.markdown("<br>", unsafe_allow_html=True)
                st.metric("전월 대비 증감", f"{int(diff):,} 원",
                          delta=f"{int(diff):,} 원",
                          delta_color="inverse" if diff > 0 else "normal")

            with donut_col:
                cur_month_df = df_in_stat[df_in_stat["년월"] == cur_m_str]
                st.markdown('<p class="section-heading">당월 카테고리별 비중</p>', unsafe_allow_html=True)
                if not cur_month_df.empty:
                    cur_cat = cur_month_df.groupby("대분류")["구매금액"].sum().reset_index().sort_values("구매금액", ascending=False)
                    fig_cur = go.Figure(go.Pie(
                        labels=cur_cat["대분류"], values=cur_cat["구매금액"],
                        hole=0.6, textinfo="label+percent",
                        hovertemplate="<b>%{label}</b><br>%{value:,.0f} 원<extra></extra>",
                        marker=dict(colors=["#c07c3a","#5c7a5c","#a0704a","#8a9e6c","#c4a882","#6b8f71"])
                    ))
                    fig_cur.update_layout(
                        height=260, margin=dict(t=10, b=0, l=0, r=0),
                        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(color="#8a7d6b", family="DM Sans"),
                        showlegend=True,
                        legend=dict(orientation="h", y=-0.08, x=0.5, xanchor="center",
                                    font=dict(size=11, color="#8a7d6b"))
                    )
                    st.plotly_chart(fig_cur, use_container_width=True, config={"displayModeBar": False})
                else:
                    st.info("당월 데이터 없음")

            st.divider()

            # ── 상세 입고 기록 + 필터 + CSV ──
            st.markdown('<p class="section-heading">상세 입고 기록</p>', unsafe_allow_html=True)

            ff1, ff2, ff3 = st.columns([1.2, 1.2, 1])
            with ff1:
                month_list = ["전체"] + sorted(df_in_stat["년월"].unique().tolist(), reverse=True)
                sel_month  = st.selectbox("월 필터", month_list, key="report_month")
            with ff2:
                cat_list_r = ["전체"] + sorted(df_in_stat["대분류"].dropna().unique().tolist())
                sel_cat_r  = st.selectbox("대분류 필터", cat_list_r, key="report_cat")
            with ff3:
                st.markdown("<br>", unsafe_allow_html=True)
                # 필터 적용 후 다운로드
                disp_df = df_in_stat.copy()
                if sel_month != "전체":
                    disp_df = disp_df[disp_df["년월"] == sel_month]
                if sel_cat_r != "전체":
                    disp_df = disp_df[disp_df["대분류"] == sel_cat_r]

                fname_parts = []
                if sel_month != "전체": fname_parts.append(sel_month)
                if sel_cat_r != "전체": fname_parts.append(sel_cat_r)
                fname = "입고기록_" + ("_".join(fname_parts) if fname_parts else "전체") + f"_{date.today()}.csv"

                csv_data = disp_df[["입고일자","대분류","품목","입고수량","구매금액"]].sort_values("입고일자", ascending=False)
                csv_data = csv_data.copy()
                csv_data["입고일자"] = pd.to_datetime(csv_data["입고일자"], errors="coerce").dt.strftime("%Y-%m-%d")
                st.download_button(
                    "📥 CSV 다운로드",
                    data=csv_data.to_csv(index=False, encoding="utf-8-sig"),
                    file_name=fname, mime="text/csv",
                    use_container_width=True
                )

            # 테이블
            disp_df2 = disp_df.copy()
            disp_df2["입고일자"] = pd.to_datetime(disp_df2["입고일자"], errors="coerce").dt.strftime("%Y-%m-%d")
            st.dataframe(
                disp_df2[["입고일자","대분류","품목","입고수량","구매금액"]].sort_values("입고일자", ascending=False),
                use_container_width=True, hide_index=True,
                column_config={
                    "구매금액": st.column_config.NumberColumn("구매금액", format="%d 원"),
                    "입고수량": st.column_config.NumberColumn("수량",     format="%d"),
                }
            )

    # ══════════════════════════════════════════
    # ⚙️ ADMIN SETTINGS
    # ══════════════════════════════════════════
    elif current == "SYSTEM":
        st.markdown('<p class="page-title">Admin Settings</p>', unsafe_allow_html=True)
        st.markdown('<p class="page-sub">품목 마스터 관리 및 시스템 설정</p>', unsafe_allow_html=True)

        _req_admin  = sb_select("order_requests")
        _pend_admin = len(_req_admin[_req_admin["상태"] == "대기"]) if not _req_admin.empty and "상태" in _req_admin.columns else 0
        if _pend_admin > 0 and not st.session_state.admin_toast_shown:
            st.toast(f"📦 발주 요청 {_pend_admin}건 대기 중", icon="🔔")
            st.session_state.admin_toast_shown = True

        tab1, tab_edit, tab2, tab3 = st.tabs(["🆕 신규 품목 등록", "✏️ 품목 수정", "🗑️ 품목 / 분류 삭제", "🚨 데이터 초기화"])

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
                    unit      = st.text_input("수량 단위",     value="EA")
                with c2:
                    safety_stock      = st.number_input("안전재고",     min_value=0, value=5)
                    default_order_qty = st.number_input("기본 발주수량", min_value=1, value=1)
                    note = st.text_area("비고")

                if st.form_submit_button("📥 등록", use_container_width=True):
                    final_cat = new_cat_input if selected_cat == "+ 직접 입력" else selected_cat
                    if not item_name:
                        st.error("품목명은 필수입니다.")
                    elif not final_cat:
                        st.error("분류명을 입력하거나 선택하세요.")
                    elif not df.empty and ((df["대분류"] == final_cat) & (df["품목"] == item_name)).any():
                        st.error(f"'{item_name}'은 이미 등록된 품목입니다.")
                    else:
                        sb_insert("inventory_info", {
                            "대분류": final_cat, "품목": item_name, "구매처": vendor,
                            "수량단위": unit, "안전재고": safety_stock,
                            "기본발주수량": default_order_qty, "비고": note
                        })
                        sb_insert("inventory", {
                            "대분류": final_cat, "품목": item_name, "수량단위": unit,
                            "현재고": 0, "안전재고": safety_stock,
                            "최근입고일": "", "최근출고일": ""
                        })
                        st.success(f"✅ '{item_name}' 등록 완료!")
                        st.balloons()
                        st.rerun()

        # ── 품목 수정 탭 ──
        with tab_edit:
            st.markdown('<p class="section-heading">등록된 품목 정보 수정</p>', unsafe_allow_html=True)

            if info_df.empty:
                st.info("등록된 품목이 없습니다.")
            else:
                # 대분류 → 품목 선택
                edit_cats  = sorted(info_df["대분류"].dropna().unique().tolist())
                edit_cat   = st.selectbox("대분류 선택", edit_cats, key="edit_cat")
                edit_items = sorted(info_df[info_df["대분류"] == edit_cat]["품목"].dropna().unique().tolist())
                edit_item  = st.selectbox("수정할 품목 선택", edit_items, key="edit_item")

                # 선택 품목의 현재 값 조회
                cur_info = info_df[
                    (info_df["대분류"] == edit_cat) & (info_df["품목"] == edit_item)
                ]
                cur_inv = df[
                    (df["대분류"] == edit_cat) & (df["품목"] == edit_item)
                ]

                if not cur_info.empty:
                    ci = cur_info.iloc[0]
                    info_id = int(ci["id"])
                    inv_id  = int(cur_inv["id"].values[0]) if not cur_inv.empty else None

                    st.caption("현재 값을 불러왔습니다. 수정 후 저장하세요.")

                    with st.form("edit_item_form", clear_on_submit=False):
                        c1, c2 = st.columns(2)
                        with c1:
                            new_vendor = st.text_input(
                                "구매처",
                                value=str(ci.get("구매처", "") or ""),
                            )
                            new_unit = st.text_input(
                                "수량 단위",
                                value=str(ci.get("수량단위", "EA") or "EA"),
                            )
                            new_note = st.text_area(
                                "비고",
                                value=str(ci.get("비고", "") or ""),
                            )
                        with c2:
                            new_safety = st.number_input(
                                "안전재고",
                                min_value=0,
                                value=int(pd.to_numeric(ci.get("안전재고", 0), errors="coerce") or 0),
                            )
                            new_order_qty = st.number_input(
                                "기본 발주수량",
                                min_value=1,
                                value=int(pd.to_numeric(ci.get("기본발주수량", 1), errors="coerce") or 1),
                            )

                        if st.form_submit_button("💾 수정 저장", use_container_width=True):
                            # inventory_info 업데이트
                            sb_update("inventory_info", info_id, {
                                "구매처":     new_vendor,
                                "수량단위":   new_unit,
                                "안전재고":   new_safety,
                                "기본발주수량": new_order_qty,
                                "비고":       new_note,
                            })
                            # inventory 테이블도 단위·안전재고 동기화
                            if inv_id:
                                sb_update("inventory", inv_id, {
                                    "수량단위": new_unit,
                                    "안전재고": new_safety,
                                })
                            st.success(f"✅ '{edit_item}' 정보가 수정되었습니다.")
                            st.rerun()

        with tab2:
            st.markdown('<p class="section-heading">품목 / 대분류 삭제</p>', unsafe_allow_html=True)
            st.warning("삭제 후 복구가 불가능합니다. 신중히 진행하세요.")
            del_mode = st.radio("삭제 유형", ["품목 삭제", "대분류 삭제"], horizontal=True)

            if del_mode == "품목 삭제":
                if not info_df.empty:
                    del_cat   = st.selectbox("대분류 선택", sorted(info_df["대분류"].dropna().unique().tolist()), key="del_item_cat")
                    del_items = sorted(info_df[info_df["대분류"] == del_cat]["품목"].dropna().unique().tolist())
                    del_item  = st.selectbox("삭제할 품목", del_items, key="del_item_name")
                    confirm   = st.checkbox(f"'{del_item}' 을(를) 삭제하겠습니다.")
                    if st.button("🗑️ 품목 삭제"):
                        if confirm:
                            sb_delete_where("inventory_info", "품목", del_item)
                            sb_delete_where("inventory",      "품목", del_item)
                            st.success(f"'{del_item}' 삭제 완료")
                            st.rerun()
                        else:
                            st.error("삭제 확인 체크박스를 먼저 선택하세요.")
                else:
                    st.info("삭제할 품목이 없습니다.")
            else:
                if not info_df.empty:
                    del_cat_g = st.selectbox("삭제할 대분류", sorted(info_df["대분류"].dropna().unique().tolist()), key="del_grp")
                    cnt       = len(info_df[info_df["대분류"] == del_cat_g])
                    st.warning(f"'{del_cat_g}' 대분류 삭제 시 품목 {cnt}개도 함께 삭제됩니다.")
                    confirm_g = st.checkbox(f"'{del_cat_g}' 대분류 전체를 삭제하겠습니다.")
                    if st.button("🗑️ 대분류 삭제"):
                        if confirm_g:
                            sb_delete_where("inventory_info", "대분류", del_cat_g)
                            sb_delete_where("inventory",      "대분류", del_cat_g)
                            st.success(f"'{del_cat_g}' 삭제 완료")
                            st.rerun()
                        else:
                            st.error("삭제 확인 체크박스를 먼저 선택하세요.")
                else:
                    st.info("삭제할 대분류가 없습니다.")

        with tab3:
            st.markdown('<p class="section-heading">시스템 데이터 초기화</p>', unsafe_allow_html=True)
            st.error("⚠️ 아래 실행 시 모든 재고 현황, 입/출고 내역, 품목 마스터가 영구 삭제됩니다.")
            confirm_pw = st.text_input("관리자 비밀번호 입력", type="password", key="reset_pw")
            if st.button("🚨 전체 데이터 초기화"):
                if confirm_pw == "0422":
                    for tbl in ["inventory","inventory_info","inventory_in","inventory_out","order_requests"]:
                        try:
                            sb.table(tbl).delete().gt("id", 0).execute()
                        except Exception as e:
                            st.error(f"{tbl} 초기화 실패: {e}")
                    st.success("초기화 완료.")
                    st.rerun()
                else:
                    st.error("비밀번호가 일치하지 않습니다.")

    # ══════════════════════════════════════════
    # 📢 ORDER REQUEST — QR 랜딩
    # ══════════════════════════════════════════
    elif current == "ORDER_REQ":
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
            cat_list     = sorted(info_df["대분류"].dropna().astype(str).unique().tolist())
            sel_cat      = st.selectbox("카테고리", cat_list, key="req_cat")
            items_in_cat = sorted(info_df[info_df["대분류"] == sel_cat]["품목"].dropna().astype(str).unique().tolist())

            with st.form("request_form", clear_on_submit=True):
                sel_item  = st.selectbox("품목 선택", items_in_cat, key="req_item")
                item_info = info_df[(info_df["대분류"] == sel_cat) & (info_df["품목"] == sel_item)]
                unit_val  = item_info["수량단위"].values[0] if not item_info.empty and "수량단위" in item_info.columns else ""
                def_qty   = (
                    int(pd.to_numeric(item_info["기본발주수량"].values[0], errors="coerce"))
                    if not item_info.empty and "기본발주수량" in item_info.columns
                    and pd.notna(item_info["기본발주수량"].values[0]) else 1
                )

                req_qty  = st.number_input(f"요청 수량 ({unit_val})", min_value=1, value=def_qty, step=1)
                req_note = st.text_input("전달 사항 (선택)", placeholder="예: 빨리 필요해요")

                if st.form_submit_button("🚀 발주 요청하기", use_container_width=True):
                    if is_duplicate_request(sel_cat, sel_item, minutes=30):
                        st.warning(
                            f"⚠️ **{sel_item}** 은(는) 최근 30분 내 이미 요청되었습니다.\n\n"
                            "처리 완료 후 다시 요청해주세요."
                        )
                    else:
                        sb_insert("order_requests", {
                            "요청일시": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "대분류": sel_cat, "품목": sel_item,
                            "요청수량": req_qty, "비고": req_note, "상태": "대기"
                        })
                        st.success(
                            f"✅ [{sel_cat}] **{sel_item}** {req_qty} {unit_val} "
                            "요청이 접수되었습니다!\n\n관리자에게 알림이 전송됩니다."
                        )
                        st.toast("📦 발주 요청 접수 완료", icon="✅")
