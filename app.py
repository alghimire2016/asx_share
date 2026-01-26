import streamlit as st

from streamlit_autorefresh import st_autorefresh
from asx_calendar import get_asx_status
from config import DB_FILE, BRAIN_FILE, DEFAULT_BUY_FEE, DEFAULT_SELL_FEE, apply_theme
from storage import load_csv, normalise_portfolio, normalise_brain
from sanity import run_sanity_panel, guarded

from ui.dashboard import render_dashboard
from ui.scanner import render_scanner
from ui.brain import render_brain
from ui.pnl import render_pnl
from ui.manage import render_manage

# ---------------------------------------------------------
# Page setup
# ---------------------------------------------------------
st.set_page_config(page_title="ASX Master Intelligence", layout="wide", page_icon="🛡️")
apply_theme()

# ---------- Market status + auto-refresh ----------
status = get_asx_status()
st.caption(f"ASX: **{status.label}** | Sydney time: {status.now.strftime('%Y-%m-%d %H:%M')}")

# Auto-refresh ONLY when market is open
if status.is_open:
    st_autorefresh(interval=60_000, key="asx_refresh_1m")  # refresh every 60s
else:
    if status.next_open:
        st.caption(f"Next open: **{status.next_open.strftime('%Y-%m-%d %H:%M')} Sydney**")

# ---------------------------------------------------------
# Sidebar: Model parameters
# ---------------------------------------------------------
st.sidebar.markdown("## ⚙️ Model Parameters")

target_atr_mult = st.sidebar.slider("Target ATR multiple", 1.0, 6.0, 3.0, 0.1)
stop_atr_mult = st.sidebar.slider("Stop ATR multiple", 0.5, 3.0, 1.5, 0.1)

horizons = st.sidebar.multiselect(
    "Allowed horizons (days)",
    [5, 10, 15, 20, 30, 40, 60],
    default=[10, 20, 40]
)
if not horizons:
    horizons = [20]

top_n = st.sidebar.slider("Top picks", 3, 10, 5)
default_buy_fee = st.sidebar.number_input("Default buy fee ($)", min_value=0.0, value=float(DEFAULT_BUY_FEE), step=0.5)
default_sell_fee = st.sidebar.number_input("Default sell fee ($)", min_value=0.0, value=float(DEFAULT_SELL_FEE), step=0.5)

st.sidebar.divider()
run_sanity_panel(DB_FILE, BRAIN_FILE)

# ---------------------------------------------------------
# Load data
# ---------------------------------------------------------
portfolio = normalise_portfolio(load_csv(DB_FILE))
brain = normalise_brain(load_csv(BRAIN_FILE))

# ---------------------------------------------------------
# Header
# ---------------------------------------------------------
st.markdown(
    """
<div class="hero">
  <div class="hero-left">
    <div class="hero-badge">🛡️ ASX Master Intelligence</div>
    <div class="hero-title">Portfolio + Scanner + Brain</div>
    <div class="hero-sub">Fast signals • Clean journaling • Auto-evaluated predictions</div>
  </div>
  <div class="hero-right">
    <div class="pulse-dot"></div>
    <div class="hero-status">LIVE</div>
  </div>
</div>
""",
    unsafe_allow_html=True
)

# ---------------------------------------------------------
# Tabs
# ---------------------------------------------------------
tab_dash, tab_scan, tab_brain, tab_pnl, tab_manage = st.tabs(
    ["💎 DASHBOARD", "🔍 SCANNER", "🧠 BRAIN", "📒 P&L", "⚙️ MANAGE"]
)

with tab_dash:
    guarded("Dashboard", lambda: render_dashboard(
        portfolio, horizons, target_atr_mult, stop_atr_mult, default_buy_fee, default_sell_fee
    ))

with tab_scan:
    guarded("Scanner", lambda: render_scanner(
        BRAIN_FILE, horizons, target_atr_mult, stop_atr_mult, top_n
    ))

with tab_brain:
    guarded("Brain", lambda: render_brain(BRAIN_FILE))

with tab_pnl:
    guarded("P&L", lambda: render_pnl(DB_FILE, default_buy_fee, default_sell_fee))

with tab_manage:
    guarded("Manage", lambda: render_manage(DB_FILE, BRAIN_FILE, default_buy_fee, default_sell_fee))
