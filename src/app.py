"""
app.py — Home dashboard

Landing page for the Strauss Procurement Negotiation Prep tool.
Shows upcoming meetings, supplier health overview, and latest discussions.

Navigation:
  Suppliers  → browse/search all 8 suppliers, view relationship health
  Meeting Prep → generate AI briefing packet for a specific meeting

Run:
    streamlit run src/app.py
"""

import os
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st

if "ANTHROPIC_API_KEY" in st.secrets:
    os.environ["ANTHROPIC_API_KEY"] = st.secrets["ANTHROPIC_API_KEY"]

from packet_generator import get_upcoming_meetings
from supplier_analytics import SUPPLIERS, get_all_summaries

st.set_page_config(
    page_title="Strauss Procurement",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Cache ─────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def cached_summaries():
    return get_all_summaries()

@st.cache_data(ttl=300)
def cached_meetings():
    return get_upcoming_meetings()

# ── Constants ─────────────────────────────────────────────────────────────────

CONTRACT_BADGE = {
    "active":             "🟢 Active",
    "expired":            "🔴 Expired",
    "draft":              "🟠 Draft",
    "no_active_contract": "🔴 No contract",
    "unknown":            "⚪ Unknown",
}

HEALTH_BADGE = {"Healthy": "🟢", "Stable": "🟡", "At risk": "🔴"}

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("📋 Strauss Procurement")
    st.caption("Negotiation Prep")
    st.divider()
    st.caption(f"Today: {date.today().isoformat()}")
    st.caption(f"{len(SUPPLIERS)} active suppliers")

# ── Load data ─────────────────────────────────────────────────────────────────

summaries = cached_summaries()
meetings = cached_meetings()

# ── Header ────────────────────────────────────────────────────────────────────

st.title("Strauss Procurement")
st.caption("Negotiation intelligence dashboard · All data is local — no API calls on this page")
st.divider()

# ── Stat tiles ────────────────────────────────────────────────────────────────

meetings_this_week = [m for m in meetings if m["days_until"] <= 7]
at_risk = [s for s in summaries if s["health_label"] == "At risk"]
contract_issues = [s for s in summaries if s["contract"]["status"] in ("expired", "draft", "no_active_contract")]

s1, s2, s3, s4 = st.columns(4)
with s1:
    st.metric("Upcoming Meetings", str(len(meetings)), help="Total meetings in calendar from today")
with s2:
    st.metric("This Week", str(len(meetings_this_week)), help="Meetings in the next 7 days")
with s3:
    st.metric("Suppliers at Risk", str(len(at_risk)), help="Relationship health = At risk")
with s4:
    st.metric("Contract Issues", str(len(contract_issues)), help="Expired, draft, or missing contracts")

st.divider()

# ── Two-column layout ─────────────────────────────────────────────────────────

left, right = st.columns([3, 2], gap="large")

with left:

    # ── Upcoming meetings ──────────────────────────────────────────────────────

    st.subheader("Upcoming Meetings")
    if not meetings:
        st.info("No upcoming meetings in calendar.")
    else:
        for m in meetings[:8]:
            days = m["days_until"]
            if days == 0:
                badge = "🔴 **Today**"
            elif days <= 3:
                badge = f"🟠 in {days}d"
            elif days <= 7:
                badge = f"🟡 in {days}d"
            else:
                badge = f"⚪ in {days}d"

            with st.container(border=True):
                c1, c2, c3 = st.columns([2, 3, 2])
                with c1:
                    st.markdown(f"**{m['date']}**  \n{badge}")
                with c2:
                    st.markdown(f"**{m['supplier']}**  \n_{m.get('notes', '')}_ ")
                with c3:
                    st.caption(f"📍 {m.get('geography', '')}  \n🏷 {m['category']}")

        if len(meetings) > 8:
            st.caption(f"…and {len(meetings) - 8} more meetings")

        st.markdown("")
        st.caption("→ Use **Meeting Prep** in the sidebar to generate a packet")

with right:

    # ── Supplier health overview ───────────────────────────────────────────────

    st.subheader("Supplier Health")
    for s in summaries:
        contract = s["contract"]
        health_icon = HEALTH_BADGE.get(s["health_label"], "⚪")
        contract_badge = CONTRACT_BADGE.get(contract["status"], "⚪")
        days_since = s["days_since_last_contact"]

        with st.container(border=False):
            c1, c2, c3 = st.columns([3, 2, 1])
            with c1:
                st.markdown(f"**{s['supplier_name']}**  \n{contract_badge}")
            with c2:
                st.caption(
                    f"Last contact: {days_since}d ago" if days_since is not None else "No emails"
                )
            with c3:
                st.markdown(f"### {health_icon}")

        st.divider()

    st.caption("→ Use **Suppliers** in the sidebar to view all profiles")

# ── Latest discussions ────────────────────────────────────────────────────────

st.subheader("Latest Discussions")
st.caption("Most recent email per supplier, across all active relationships")

latest = sorted(
    [s for s in summaries if s["last_email"]],
    key=lambda s: s["last_email"]["date"],
    reverse=True,
)[:6]

cols = st.columns(2)
for i, s in enumerate(latest):
    last = s["last_email"]
    sender = last["from"].split("@")[0].replace(".", " ").title()
    days_ago = s["days_since_last_contact"]
    with cols[i % 2]:
        with st.container(border=True):
            st.markdown(f"**{s['supplier_name']}**  \n_{sender} · {last['date']} ({days_ago}d ago)_")
            st.caption(f"📧 {last['subject']}")
            with st.expander("Preview", expanded=False):
                preview = last["body"][:300]
                st.caption(preview + ("…" if len(last["body"]) > 300 else ""))
