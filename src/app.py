"""
app.py — router

Entry point. Defines navigation and delegates to page files.
All per-page content lives in src/pages/.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st

if "ANTHROPIC_API_KEY" in st.secrets:
    os.environ["ANTHROPIC_API_KEY"] = st.secrets["ANTHROPIC_API_KEY"]

if "FDE_METRICS_PASSWORD" in st.secrets:
    os.environ["FDE_METRICS_PASSWORD"] = st.secrets["FDE_METRICS_PASSWORD"]

from utils.metrics import init_db
init_db()

st.set_page_config(
    page_title="Strauss Procurement",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

pg = st.navigation([
    st.Page("pages/0_Home.py",        title="Home",         icon="🏠", default=True),
    st.Page("pages/1_Suppliers.py",   title="Suppliers",    icon="🏭"),
    st.Page("pages/2_Meeting_Prep.py",title="Meeting Prep", icon="⚡"),
])
pg.run()
