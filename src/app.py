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

from utils.data_fetcher import fetch_reference_data

st.set_page_config(
    page_title="Strauss Procurement",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

from ui_helpers import GLOBAL_CSS
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

if "reference_data" not in st.session_state:
    with st.spinner("Fetching live market data..."):
        st.session_state.reference_data = fetch_reference_data()

_fx = st.session_state.reference_data["fx_rates"]
_as_of = _fx["as_of_date"].max() if not _fx.empty else "unavailable"
st.sidebar.caption(f"Market data as of: {_as_of}")
st.sidebar.markdown(
    f"""
    <div style="position:fixed;bottom:1.2rem;left:0;width:244px;padding:0 1rem;">
      <hr style="border-color:#334155;margin-bottom:0.6rem;">
      <p style="font-size:0.72rem;color:#94a3b8;line-height:1.5;margin:0 0 0.35rem 0;">
        🔒 Email content is processed in memory only and not retained beyond this session.
      </p>
      <p style="font-size:0.72rem;color:#94a3b8;line-height:1.5;margin:0;">
        ⚠️ Negotiation briefs and recommendations are AI-generated — please verify before acting on them.
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

pg = st.navigation([
    st.Page("pages/0_Home.py",              title="Procurement Overview", icon="🏠", default=True),
    st.Page("pages/2_Meeting_Prep.py",      title="Meeting Prep",      icon="⚡"),
    st.Page("pages/financial_decisions.py", title="Financial Analysis", icon="💡"),
    st.Page("pages/3_Pricing.py",           title="Market Intel",      icon="📈"),
    st.Page("pages/1_Suppliers.py",         title="Suppliers",         icon="🏭"),
])
pg.run()
