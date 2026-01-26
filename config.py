import os
import streamlit as st

# -------------------------------------------------
# Base directory (absolute path to project folder)
# -------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# -------------------------------------------------
# CSV files (absolute paths)
# -------------------------------------------------
DB_FILE = os.path.join(BASE_DIR, "asx_portfolio_master.csv")
BRAIN_FILE = os.path.join(BASE_DIR, "asx_model_brain.csv")

# -------------------------------------------------
# Defaults
# -------------------------------------------------
DEFAULT_BUY_FEE = 3.0
DEFAULT_SELL_FEE = 3.0

# -------------------------------------------------
# Theme / UI
# -------------------------------------------------
def apply_theme():
    st.markdown(
        """
        <style>
        .main { background:#0d1117; color:#c9d1d9; }
        .card { background:#161b22; border:1px solid #30363d;
                border-radius:14px; padding:16px; }
        .kpi { text-align:center; }
        .good { color:#3fb950; font-weight:700; }
        .bad { color:#f85149; font-weight:700; }
        .muted { color:#8b949e; }
        .big { font-size:26px; font-weight:800; }
        div[data-testid="stDataFrame"] {
            border: 1px solid #30363d;
            border-radius: 12px;
            overflow: hidden;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
