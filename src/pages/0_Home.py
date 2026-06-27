"""Home dashboard — upcoming meetings, supplier health, latest discussions."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

from packet_generator import get_upcoming_meetings
from supplier_analytics import SUPPLIERS, get_all_summaries
from utils.metrics import get_summary
from ui_helpers import section_label, kpi_card, meeting_card, health_row, discussion_card

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

st.title("Procurement Overview")
st.caption("Negotiation intelligence dashboard · All data is local — no API calls on this page")
st.divider()

# ── Stat tiles ────────────────────────────────────────────────────────────────

total_suppliers = len(summaries)
meetings_this_week = [m for m in meetings if m["days_until"] <= 7]
at_risk = [s for s in summaries if s["combined_health_label"] == "At risk"]
contract_issues = [s for s in summaries if s["contract"]["status"] in ("expired", "draft", "no_active_contract")]

s1, s2, s3, s4 = st.columns(4)
with s1:
    st.markdown(kpi_card(str(len(meetings)), "Upcoming Meetings", "From today"), unsafe_allow_html=True)
with s2:
    st.markdown(kpi_card(str(len(meetings_this_week)), "This Week", "Next 7 days"), unsafe_allow_html=True)
with s3:
    st.markdown(kpi_card(f"{len(at_risk)} of {total_suppliers}", "Suppliers at Risk", "Combined health score"), unsafe_allow_html=True)
with s4:
    st.markdown(kpi_card(f"{len(contract_issues)} of {total_suppliers}", "Contract Issues", "Expired or missing"), unsafe_allow_html=True)

st.divider()

# ── Two-column layout ─────────────────────────────────────────────────────────

left, right = st.columns([3, 2], gap="large")

with left:
    st.markdown(section_label("Upcoming Meetings", "Supplier meetings scheduled in the next 90 days, ordered by date."), unsafe_allow_html=True)
    if not meetings:
        st.info("No upcoming meetings in calendar.")
    else:
        cards_html = "".join(
            meeting_card(
                m["date"], m["supplier"], m["days_until"],
                m.get("notes", ""), m.get("geography", ""), m["category"],
            )
            for m in meetings[:8]
        )
        st.markdown(cards_html, unsafe_allow_html=True)
        if len(meetings) > 8:
            st.caption(f"…and {len(meetings) - 8} more meetings")
        st.caption("→ Use **Meeting Prep** in the sidebar to generate a packet")

with right:
    st.markdown(section_label("Supplier Health", "Combined score: relationship signals (response time, email frequency) + contract status. Green = healthy, Yellow = stable, Red = at risk."), unsafe_allow_html=True)
    rows_html = "".join(
        health_row(
            s["supplier_name"],
            s["combined_health_label"],
            s["days_since_last_contact"],
        )
        for s in summaries
    )
    st.markdown(rows_html, unsafe_allow_html=True)
    st.caption("→ Use **Suppliers** in the sidebar to view all profiles")

st.divider()

# ── Latest discussions ────────────────────────────────────────────────────────

st.markdown(section_label("Latest Discussions", "Most recent email per supplier. Shows who last made contact and when."), unsafe_allow_html=True)
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
    preview = last["body"][:200] + ("…" if len(last["body"]) > 200 else "")
    with cols[i % 2]:
        st.markdown(
            discussion_card(
                s["supplier_name"], sender, last["date"], days_ago,
                last["subject"], preview,
            ),
            unsafe_allow_html=True,
        )

# ── FDE Dashboard (password-protected, not visible to end users) ──────────────

st.divider()

if "fde_authenticated" not in st.session_state:
    st.session_state.fde_authenticated = False

with st.expander("🔒 FDE Access", expanded=False):
    if not st.session_state.fde_authenticated:
        pwd = st.text_input(
            "Password", type="password", key="fde_pwd_input",
            label_visibility="collapsed", placeholder="FDE password",
        )
        if pwd:
            correct = os.environ.get("FDE_METRICS_PASSWORD", "")
            if pwd == correct:
                st.session_state.fde_authenticated = True
                st.rerun()
            else:
                st.error("Incorrect password.")

    if st.session_state.fde_authenticated:
        st.markdown("### FDE Metrics Dashboard")
        st.caption(
            "Generation events persisted to SQLite (data/metrics.db). "
            "Resets on Streamlit Cloud redeploy — production would use a persistent event store."
        )

        summary = get_summary()
        import pandas as pd

        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric("Total Packets Generated", summary["total_packets"])
        with m2:
            avg = summary["avg_duration_sec"]
            st.metric("Avg Generation Time", f"{avg}s" if avg is not None else "—")
        with m3:
            st.metric("Unique Suppliers Queried", summary["unique_suppliers"])

        if not summary["total_packets"]:
            st.info("No generation events recorded yet. Generate a packet on the Meeting Prep page.")
        else:
            st.divider()
            st.markdown("**KPI summary across all packets generated (metrics.md §1–5)**")
            kpi = summary["kpi_summary"]
            k1, k2, k3, k4, k5 = st.columns(5)
            with k1:
                v = kpi.get("avg_response_days")
                st.metric("§1 Avg Response Time", f"{v}d" if v else "—",
                          help="Avg supplier reply time across all packets (metrics.md §1)")
            with k2:
                v = kpi.get("avg_open_issues")
                st.metric("§2 Avg Open Issues", str(v) if v is not None else "—",
                          help="Avg unresolved issues per packet (metrics.md §2)")
            with k3:
                v = kpi.get("avg_price_delta_pct")
                st.metric("§3 Avg Price Delta", f"{v:+.1f}%" if v is not None else "—",
                          help="Avg email price vs contract base across all packets (metrics.md §3)")
            with k4:
                v = kpi.get("avg_days_to_renewal")
                st.metric("§4 Avg Days to Renewal", f"{int(v)}d" if v is not None else "—",
                          help="Avg days to contract renewal date (metrics.md §4)")
            with k5:
                v = kpi.get("avg_correction_rate_pct")
                st.metric("§5 Avg Correction Rate", f"{v}%" if v is not None else "—",
                          help="Avg % of fields flagged as wrong (metrics.md §5)")

            st.divider()

            if summary["supplier_breakdown"]:
                st.markdown("**Per-supplier KPI breakdown**")
                df_sup = pd.DataFrame(summary["supplier_breakdown"])
                df_sup.columns = [
                    "Supplier", "Category", "Packets", "Avg Gen (s)",
                    "§1 Response (d)", "§2 Open Issues", "§3 Price Delta %", "§4 Renewal (d)",
                ]
                st.dataframe(df_sup, use_container_width=True, hide_index=True)

            if summary["daily_breakdown"]:
                st.markdown("**Daily generation counts**")
                df_daily = pd.DataFrame(summary["daily_breakdown"])
                df_daily.columns = ["Date", "Packets", "Avg Duration (s)", "Avg Open Issues"]
                st.dataframe(df_daily, use_container_width=True, hide_index=True)

            if summary["recent_events"]:
                st.markdown("**Last 10 generation events**")
                df_recent = pd.DataFrame(summary["recent_events"])
                df_recent["timestamp"] = df_recent["timestamp"].str.replace("T", " ")
                st.dataframe(df_recent, use_container_width=True, hide_index=True)

        if st.button("Lock", key="fde_lock"):
            st.session_state.fde_authenticated = False
            st.rerun()
