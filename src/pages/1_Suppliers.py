"""
1_Suppliers.py

Searchable supplier directory. Browse all suppliers, filter by name or
category, and click through to a per-supplier profile showing contract
status, email activity, and relationship health analytics.

All analytics are computed locally from email/contract files — no API calls.
"""

import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import streamlit as st

from supplier_analytics import (
    SUPPLIERS,
    get_all_summaries,
    get_supplier_summary,
    load_emails,
)
from packet_generator import get_upcoming_meetings

st.set_page_config(
    page_title="Suppliers — Strauss Procurement",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Cache the full summary load (reads 8 email files + 10 contract files) ────

@st.cache_data(ttl=300)
def cached_all_summaries():
    return get_all_summaries()

@st.cache_data(ttl=300)
def cached_meetings():
    return get_upcoming_meetings()

# ── Helpers ───────────────────────────────────────────────────────────────────

CONTRACT_BADGE = {
    "active":            "🟢 Active",
    "expired":           "🔴 Expired",
    "draft":             "🟠 Draft",
    "no_active_contract":"🔴 No contract",
    "unknown":           "⚪ Unknown",
}

HEALTH_BADGE = {
    "Healthy":  "🟢",
    "Stable":   "🟡",
    "At risk":  "🔴",
}

DIRECTION_LABEL = {
    "faster":     "⬇ Faster (improving)",
    "slower":     "⬆ Slower (deteriorating)",
    "stable":     "➡ Stable",
    "increasing": "⬆ Increasing",
    "decreasing": "⬇ Decreasing",
}

def days_to_renewal_display(renewal_date_str):
    if not renewal_date_str:
        return "—"
    rd = datetime.strptime(renewal_date_str, "%Y-%m-%d").date()
    days = (rd - date.today()).days
    if days < 0:
        return f"Overdue ({abs(days)}d)"
    if days < 30:
        return f"⚠️ {days}d"
    if days < 90:
        return f"{days}d"
    return f"{days}d"

# ── Sidebar — search and filter ───────────────────────────────────────────────

with st.sidebar:
    st.title("🏭 Supplier Directory")
    st.divider()
    search = st.text_input("🔍 Search supplier", placeholder="Name, category, or country…")
    categories = ["All"] + sorted({s[1] for s in SUPPLIERS.values()})
    cat_filter = st.selectbox("Category", categories)
    st.divider()
    st.caption(f"{len(SUPPLIERS)} active suppliers")

# ── Load data ─────────────────────────────────────────────────────────────────

all_summaries = cached_all_summaries()
all_meetings = cached_meetings()

# ── Filter ────────────────────────────────────────────────────────────────────

filtered = all_summaries
if search:
    q = search.lower()
    filtered = [
        s for s in filtered
        if q in s["supplier_name"].lower()
        or q in s["category"].lower()
        or q in s["geography"].lower()
    ]
if cat_filter != "All":
    filtered = [s for s in filtered if s["category"] == cat_filter]

# ── Selected supplier (from session state) ────────────────────────────────────

if "selected_supplier" not in st.session_state:
    st.session_state.selected_supplier = None

# ── Directory view ────────────────────────────────────────────────────────────

if st.session_state.selected_supplier is None:

    st.title("Supplier Directory")
    st.caption(
        f"Showing {len(filtered)} of {len(all_summaries)} suppliers · "
        "Click a supplier to view profile"
    )
    st.divider()

    if not filtered:
        st.info("No suppliers match your search.")
        st.stop()

    # Render supplier cards — 2 per row
    for i in range(0, len(filtered), 2):
        row_cols = st.columns(2, gap="large")
        for col, s in zip(row_cols, filtered[i:i+2]):
            with col:
                contract = s["contract"]
                health_icon = HEALTH_BADGE.get(s["health_label"], "⚪")
                contract_badge = CONTRACT_BADGE.get(contract["status"], "⚪")

                # Next meeting for this supplier
                next_mtg = next(
                    (m for m in all_meetings if m["supplier"] == s["supplier_name"]),
                    None,
                )
                next_mtg_str = (
                    f"Next meeting: **{next_mtg['date']}** (in {next_mtg['days_until']}d)"
                    if next_mtg else "No upcoming meetings"
                )

                days_since = s["days_since_last_contact"]
                last_contact_str = f"{days_since}d ago" if days_since is not None else "—"

                with st.container(border=True):
                    c1, c2 = st.columns([4, 1])
                    with c1:
                        st.markdown(f"### {s['supplier_name']}")
                        st.caption(f"📍 {s['geography']} · 🏷 {s['category'].title()}")
                    with c2:
                        st.markdown(f"## {health_icon}")
                        st.caption(s["health_label"])

                    st.markdown(
                        f"{contract_badge} · "
                        f"**{s['email_count']}** emails · "
                        f"Last contact: {last_contact_str}"
                    )
                    if contract.get("renewal_date"):
                        st.caption(f"Renewal: {days_to_renewal_display(contract['renewal_date'])}")
                    st.caption(next_mtg_str)

                    if st.button(
                        "View profile →",
                        key=f"view_{s['supplier_num']}",
                        use_container_width=True,
                    ):
                        st.session_state.selected_supplier = s["supplier_num"]
                        st.rerun()

# ── Supplier profile view ─────────────────────────────────────────────────────

else:
    num = st.session_state.selected_supplier
    s = get_supplier_summary(num)
    contract = s["contract"]
    emails = load_emails(num)

    if st.button("← Back to directory"):
        st.session_state.selected_supplier = None
        st.rerun()

    st.divider()

    # Header
    col_h, col_badge = st.columns([4, 1])
    with col_h:
        st.title(s["supplier_name"])
        st.caption(f"📍 {s['geography']}  ·  🏷 {s['category'].title()}  ·  Supplier #{num}")
    with col_badge:
        health_icon = HEALTH_BADGE.get(s["health_label"], "⚪")
        contract_badge = CONTRACT_BADGE.get(contract["status"], "⚪")
        st.metric("Relationship", f"{health_icon} {s['health_label']}")
        st.caption(f"Contract: {contract_badge}")

    # Upcoming meetings for this supplier
    supplier_meetings = [m for m in all_meetings if m["supplier"] == s["supplier_name"]]
    if supplier_meetings:
        m = supplier_meetings[0]
        st.info(
            f"📅 Next meeting: **{m['date']}** (in {m['days_until']} days)  \n"
            f"_{m.get('notes', '')}_ · {m.get('geography', '')}"
        )
        if len(supplier_meetings) > 1:
            st.caption(
                f"Also: " + ", ".join(f"{x['date']}" for x in supplier_meetings[1:])
            )

    st.divider()

    # ── KPI tiles ──────────────────────────────────────────────────────────────

    t1, t2, t3, t4 = st.columns(4)
    with t1:
        rt = s["response_trend"]
        st.metric(
            "Avg Response Time",
            f"{rt['recent_avg']}d" if rt["recent_avg"] is not None else "—",
            delta=f"{rt['recent_avg'] - rt['early_avg']:.1f}d vs earlier"
            if rt["recent_avg"] is not None and rt["early_avg"] is not None else None,
            delta_color="inverse",
            help="Recent half of email history vs earlier half",
        )
    with t2:
        st.metric(
            "Total Emails",
            str(s["email_count"]),
            help=f"From {s['first_email_date']} to {s['last_email_date']}",
        )
    with t3:
        days_since = s["days_since_last_contact"]
        st.metric(
            "Days Since Last Contact",
            f"{days_since}d" if days_since is not None else "—",
        )
    with t4:
        renewal_disp = days_to_renewal_display(contract.get("renewal_date"))
        st.metric(
            "Days to Renewal",
            renewal_disp,
            help=f"Contract: {contract.get('contract_id', '—')}",
        )

    st.divider()

    # ── Two columns: left = analytics, right = contract + last email ──────────

    left, right = st.columns([3, 2], gap="large")

    with left:

        # Email frequency chart
        st.subheader("Email Activity")
        by_month = s["email_by_month"]
        if by_month:
            df = pd.DataFrame.from_dict(by_month, orient="index", columns=["Emails"])
            df.index.name = "Month"
            st.bar_chart(df, color="#c8102e")
        else:
            st.caption("No email data.")

        st.divider()

        # Retention / relationship health breakdown
        st.subheader("Relationship Health Analysis")

        rt = s["response_trend"]
        vt = s["volume_trend"]

        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("**Responsiveness trend**")
            if rt["early_avg"] is not None and rt["recent_avg"] is not None:
                st.markdown(
                    f"Early avg: **{rt['early_avg']}d**  \n"
                    f"Recent avg: **{rt['recent_avg']}d**"
                )
                direction_label = DIRECTION_LABEL.get(rt["direction"], rt["direction"])
                if rt["direction"] == "slower":
                    st.warning(f"Response time: {direction_label}")
                elif rt["direction"] == "faster":
                    st.success(f"Response time: {direction_label}")
                else:
                    st.info(f"Response time: {direction_label}")
            else:
                st.caption("Not enough data.")

        with col_b:
            st.markdown("**Communication volume trend**")
            st.markdown(
                f"Recent 3mo: **{vt['recent_3mo']} emails**  \n"
                f"Prior 3mo: **{vt['prior_3mo']} emails**"
            )
            direction_label = DIRECTION_LABEL.get(vt["direction"], vt["direction"])
            if vt["direction"] == "decreasing":
                st.warning(f"Volume: {direction_label}")
            elif vt["direction"] == "increasing":
                st.success(f"Volume: {direction_label}")
            else:
                st.info(f"Volume: {direction_label}")

        st.divider()

        # Retention signal interpretation
        st.subheader("Retention Signal")
        health = s["health_label"]
        health_icon = HEALTH_BADGE.get(health, "⚪")

        if health == "Healthy":
            st.success(
                f"{health_icon} **{health}** — Communication frequency and response time "
                "are stable or improving. Relationship shows no early warning signs."
            )
        elif health == "Stable":
            st.info(
                f"{health_icon} **{health}** — No strong positive or negative trend. "
                "Monitor for changes ahead of next meeting."
            )
        else:
            st.warning(
                f"{health_icon} **{health}** — One or more signals (slower responses, "
                "declining email frequency, or extended silence) suggest the relationship "
                "may be cooling. Prioritise relationship maintenance in the next meeting."
            )

    with right:

        # Contract summary
        st.subheader("Contract")
        badge = CONTRACT_BADGE.get(contract["status"], "⚪")
        st.markdown(f"**{contract.get('contract_id', '—')}** · {badge}")
        if contract.get("renewal_date"):
            st.markdown(f"**Renewal date:** {contract['renewal_date']} ({days_to_renewal_display(contract['renewal_date'])})")
        else:
            st.markdown("**Renewal date:** Not found")

        st.divider()

        # Latest discussion
        st.subheader("Latest Discussion")
        if emails:
            last = emails[-1]
            prev_emails = emails[-4:-1]  # up to 3 prior messages
            st.markdown(
                f"**{last['date']}** · {last['from'].split('@')[0].replace('.', ' ').title()}  \n"
                f"_{last['subject']}_"
            )
            with st.expander("Read message", expanded=False):
                st.markdown(last["body"])

            if prev_emails:
                st.caption("Recent thread:")
                for e in reversed(prev_emails):
                    sender = e["from"].split("@")[0].replace(".", " ").title()
                    st.caption(f"**{e['date']}** {sender}: {e['subject']}")
        else:
            st.caption("No emails on file.")

        st.divider()

        # Generate prep packet shortcut
        st.subheader("Prep Packet")
        if supplier_meetings:
            next_m = supplier_meetings[0]
            st.markdown(
                f"Next meeting: **{next_m['date']}** (Meeting #{next_m['meeting_id']})"
            )
            if st.button("⚡ Go to Meeting Prep →", use_container_width=True, type="primary"):
                st.session_state.selected_id = next_m["meeting_id"]
                st.switch_page("pages/2_Meeting_Prep.py")
        else:
            st.caption("No upcoming meetings scheduled.")
