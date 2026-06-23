"""Home dashboard — upcoming meetings, supplier health, latest discussions."""

import os
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

from packet_generator import get_upcoming_meetings
from supplier_analytics import SUPPLIERS, get_all_summaries
from utils.metrics import get_summary

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
                    st.markdown(f"**{m['supplier']}**  \n_{m.get('notes', '')}_")
                with c3:
                    st.caption(f"📍 {m.get('geography', '')}  \n🏷 {m['category']}")

        if len(meetings) > 8:
            st.caption(f"…and {len(meetings) - 8} more meetings")

        st.caption("→ Use **Meeting Prep** in the sidebar to generate a packet")

with right:
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

# ── FDE Dashboard (password-protected, not visible to end users) ──────────────

st.divider()

if "fde_authenticated" not in st.session_state:
    st.session_state.fde_authenticated = False

with st.expander("🔒 FDE Access", expanded=False):
    if not st.session_state.fde_authenticated:
        pwd = st.text_input("Password", type="password", key="fde_pwd_input", label_visibility="collapsed", placeholder="FDE password")
        if pwd:
            correct = os.environ.get("FDE_METRICS_PASSWORD", "")
            if pwd == correct:
                st.session_state.fde_authenticated = True
                st.rerun()
            else:
                st.error("Incorrect password.")

    if st.session_state.fde_authenticated:
        st.markdown("### FDE Metrics Dashboard")
        st.caption("Generation events persisted to SQLite (data/metrics.db). Resets on Streamlit Cloud redeploy — production would use a persistent event store.")

        summary = get_summary()

        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric("Total Packets Generated", summary["total_packets"])
        with m2:
            avg = summary["avg_duration_sec"]
            st.metric("Avg Generation Time", f"{avg}s" if avg is not None else "—")
        with m3:
            st.metric("Unique Suppliers Queried", summary["unique_suppliers"])

        st.divider()

        if summary["daily_breakdown"]:
            st.markdown("**Daily generation counts**")
            import pandas as pd
            df_daily = pd.DataFrame(summary["daily_breakdown"])
            df_daily.columns = ["Date", "Packets", "Avg Duration (s)"]
            st.dataframe(df_daily, use_container_width=True, hide_index=True)
        else:
            st.info("No generation events recorded yet. Generate a packet on the Meeting Prep page.")

        if summary["supplier_breakdown"]:
            st.markdown("**By supplier**")
            df_sup = pd.DataFrame(summary["supplier_breakdown"])
            df_sup.columns = ["Supplier", "Packets", "Avg Duration (s)", "Avg Open Issues"]
            st.dataframe(df_sup, use_container_width=True, hide_index=True)

        if summary["recent_events"]:
            st.markdown("**Last 10 events**")
            df_recent = pd.DataFrame(summary["recent_events"])
            df_recent["timestamp"] = df_recent["timestamp"].str[:19].str.replace("T", " ")
            st.dataframe(df_recent, use_container_width=True, hide_index=True)

        if st.button("Lock", key="fde_lock"):
            st.session_state.fde_authenticated = False
            st.rerun()
