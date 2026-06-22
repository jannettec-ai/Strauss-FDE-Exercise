"""
app.py

Streamlit interface for the Strauss negotiation prep packet.
Procurement Manager selects an upcoming meeting from the sidebar,
clicks Generate, and receives a one-page briefing built from emails,
contracts, and commodity prices.

Run:
    streamlit run src/app.py
"""

import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st

# Expose the API key to the Anthropic SDK before any extraction imports.
# On Streamlit Cloud the key lives in the secrets manager; locally it comes
# from the shell environment. The SDK reads os.environ, so we bridge the two.
if "ANTHROPIC_API_KEY" in st.secrets:
    os.environ["ANTHROPIC_API_KEY"] = st.secrets["ANTHROPIC_API_KEY"]

from datetime import date
from packet_generator import get_upcoming_meetings, run_packet

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Strauss Procurement — Negotiation Prep",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Session state defaults ────────────────────────────────────────────────────

if "packets" not in st.session_state:
    st.session_state.packets = {}       # {meeting_id: packet dict}
if "corrections" not in st.session_state:
    st.session_state.corrections = {}   # {meeting_id: {field_key: bool}}
if "selected_id" not in st.session_state:
    st.session_state.selected_id = None

# ── Helpers ───────────────────────────────────────────────────────────────────

ISSUE_CONFIG = {
    "price_discrepancy":       ("🔴", "Price discrepancy",        "error"),
    "no_active_contract":      ("🔴", "No active contract",       "error"),
    "quality_dispute":         ("🔴", "Quality dispute",           "error"),
    "spec_change_dispute":     ("🟠", "Spec change dispute",      "warning"),
    "renewal_date_discrepancy":("🟠", "Renewal date discrepancy", "warning"),
    "delivery_dispute":        ("🟠", "Delivery dispute",         "warning"),
    "contract_renegotiation":  ("🟡", "Contract renegotiation",   "info"),
    "unanswered_thread":       ("🟡", "Unanswered thread",        "info"),
}

# Fields tracked for KPI §5 (correction rate). Order matches display order.
TRACKABLE_FIELDS = [
    ("email_summary",          "Email summary"),
    ("latest_price_quoted",    "Latest price quoted"),
    ("contract_base_price",    "Contract base price"),
    ("renewal_date",           "Renewal date"),
    ("payment_terms",          "Payment terms"),
    ("volume_commitment",      "Volume commitment"),
    ("key_penalty",            "Key penalty clause"),
    ("heads_up",               "Heads-up"),
]


def renewal_status(days: int | None, contract_status: str) -> tuple[str, str]:
    """Return (display_text, streamlit_color) for the renewal KPI tile."""
    if contract_status in ("no_active_contract", "draft"):
        return "NO ACTIVE CONTRACT", "off"
    if contract_status == "expired":
        return "EXPIRED", "off"
    if days is None:
        return "Unknown", "off"
    if days < 0:
        return f"OVERDUE ({abs(days)}d)", "off"
    if days < 30:
        return f"{days}d — urgent", "off"
    if days < 90:
        return f"{days}d", "normal"
    return f"{days}d", "normal"


def price_delta_display(delta: dict | None, latest: dict) -> str:
    """Format the price-vs-contract delta for the KPI tile label."""
    if latest.get("display") == "ambiguous — see open issues":
        return "Ambiguous unit"
    if delta is None:
        return "No quote on file"
    sign = "+" if delta["absolute"] >= 0 else ""
    return f"{sign}{delta['pct']}%"


def flag_key(meeting_id: int, field: str) -> str:
    return f"flag_{meeting_id}_{field}"


def count_flags(meeting_id: int) -> int:
    return sum(
        1 for fk, _ in TRACKABLE_FIELDS
        if st.session_state.corrections.get(meeting_id, {}).get(fk, False)
    )

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("📋 Strauss Procurement")
    st.caption("Negotiation Prep Packets")
    st.divider()

    meetings = get_upcoming_meetings()
    if not meetings:
        st.warning("No upcoming meetings in calendar.")
        st.stop()

    st.subheader("Upcoming meetings")

    for m in meetings:
        d = m["days_until"]
        badge = "**Today**" if d == 0 else f"in {d}d"
        label = f"**{m['date']}** · {m['supplier']}  \n_{m['category']} · {badge}_"
        if st.button(label, key=f"mtg_{m['meeting_id']}", use_container_width=True):
            st.session_state.selected_id = m["meeting_id"]

    st.divider()

    if st.session_state.selected_id:
        sel = next(m for m in meetings if m["meeting_id"] == st.session_state.selected_id)
        st.markdown(f"**Selected:** {sel['supplier']}  \n{sel['date']}")

        if st.button("⚡ Generate Packet", type="primary", use_container_width=True):
            mid = st.session_state.selected_id
            with st.spinner(f"Extracting supplier data and generating packet…"):
                try:
                    packet = run_packet(mid)
                    st.session_state.packets[mid] = packet
                    if mid not in st.session_state.corrections:
                        st.session_state.corrections[mid] = {}
                except Exception as e:
                    st.error(f"Generation failed: {e}")
    else:
        st.info("Select a meeting above, then click Generate.")

# ── Main area ─────────────────────────────────────────────────────────────────

mid = st.session_state.selected_id
packet = st.session_state.packets.get(mid) if mid else None

if packet is None:
    st.markdown("## Strauss Procurement · Negotiation Prep")
    st.markdown(
        "Select an upcoming supplier meeting from the sidebar and click "
        "**Generate Packet** to produce a one-page briefing."
    )
    st.divider()
    st.markdown("**Upcoming meetings**")
    for m in meetings[:5]:
        st.markdown(f"- **{m['date']}** — {m['supplier']} _{m['category']}_")
    if len(meetings) > 5:
        st.caption(f"…and {len(meetings) - 5} more")
    st.stop()

# ── Packet is loaded — render it ─────────────────────────────────────────────

ct = packet["contract_terms"]
lp = packet["latest_price_quoted"]
bm = packet["benchmark"]
issues = packet["open_issues"]
delta = packet["price_delta"]

# ── Header ────────────────────────────────────────────────────────────────────

col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.title(f"{packet['supplier_name']}")
    st.caption(
        f"📅 {packet['meeting_date']}  ·  "
        f"📍 {packet['geography']}  ·  "
        f"🏷 {packet['category'].title()}  ·  "
        f"Meeting #{mid}"
    )
with col_h2:
    st.caption(f"Generated {packet['generated_at'][:10]}")
    days_left = packet["days_until_meeting"]
    if days_left == 0:
        st.error("Meeting is **today**")
    elif days_left <= 3:
        st.warning(f"Meeting in **{days_left} day{'s' if days_left != 1 else ''}**")
    else:
        st.info(f"Meeting in **{days_left} days**")

if packet["meeting_notes"]:
    st.caption(f"📌 {packet['meeting_notes']}")

st.divider()

# ── Heads-up alert ────────────────────────────────────────────────────────────

has_red = any(
    ISSUE_CONFIG.get(i["issue_type"], ("", "", "info"))[2] == "error"
    for i in issues
)
if has_red:
    st.error(f"⚠️ **Heads-up:** {packet['heads_up']}")
else:
    st.warning(f"⚠️ **Heads-up:** {packet['heads_up']}")

# ── KPI row ───────────────────────────────────────────────────────────────────

k1, k2, k3, k4 = st.columns(4)

with k1:
    avg_r = packet["avg_response_days"]
    st.metric(
        "Avg Response Time",
        f"{avg_r}d" if avg_r is not None else "—",
        help="Average calendar days from Strauss outbound email to first supplier reply (metrics.md §1)",
    )

with k2:
    n_issues = packet["open_issues_count"]
    st.metric(
        "Open Issues",
        str(n_issues),
        delta=None,
        help="Count of unresolved issues found by AI extraction (metrics.md §2)",
    )

with k3:
    delta_label = price_delta_display(delta, lp)
    delta_val = delta["pct"] if delta else None
    st.metric(
        "Price vs Contract",
        delta_label,
        delta=f"{delta_val:+.1f}%" if delta_val is not None else None,
        delta_color="inverse",
        help="Latest email price quote vs contract base price (metrics.md §3)",
    )

with k4:
    d_renew, _ = renewal_status(packet["days_to_renewal"], ct.get("status", ""))
    st.metric(
        "Days to Renewal",
        d_renew,
        help="Calendar days from today to contract renewal date (metrics.md §4)",
    )

st.divider()

# ── Open issues ───────────────────────────────────────────────────────────────

st.subheader(f"Open Issues ({len(issues)})")

if not issues:
    st.success("No open issues identified.")
else:
    for issue in issues:
        cfg = ISSUE_CONFIG.get(issue["issue_type"], ("⚪", issue["issue_type"], "info"))
        icon, label, level = cfg
        msg = f"{icon} **{label}** — {issue['description']}  \n_Source: {issue['source_ref']}_"
        if level == "error":
            st.error(msg)
        elif level == "warning":
            st.warning(msg)
        else:
            st.info(msg)

st.divider()

# ── Two-column body: left = email + contract, right = pricing + benchmark ─────

left, right = st.columns([3, 2], gap="large")

with left:

    # Email summary
    st.subheader("Email Thread Summary")
    st.markdown(packet["email_summary"])
    st.caption(
        f"Based on {packet['email_count']} emails · "
        f"Avg supplier response: "
        f"{packet['avg_response_days']}d"
        if packet["avg_response_days"] is not None
        else f"Based on {packet['email_count']} emails"
    )

    st.divider()

    # Contract at a glance
    st.subheader("Contract at a Glance")

    status = ct.get("status", "unknown")
    status_badge = {
        "active": "🟢 Active",
        "expired": "🔴 Expired",
        "draft": "🟠 Draft — not signed",
        "no_active_contract": "🔴 No active contract",
    }.get(status, status)

    st.markdown(f"**{ct.get('contract_id', '—')}** · {status_badge}")

    contract_rows = [
        ("Payment terms",    ct.get("payment_terms", "—")),
        ("Volume min",       ct.get("volume_min", "—")),
        ("Volume max",       ct.get("volume_max", "—")),
        ("Base price",       ct.get("contract_base_price", "—")),
        ("Key penalty",      ct.get("key_penalty", "—")),
    ]

    renewal_str = ct.get("renewal_date")
    if renewal_str:
        auto = ct.get("auto_renewal", False)
        notice = ct.get("notice_period_days")
        renewal_display = renewal_str
        if auto and notice:
            from datetime import datetime, timedelta
            rd = datetime.strptime(renewal_str, "%Y-%m-%d").date()
            notice_by = rd - timedelta(days=notice)
            renewal_display += f" (auto-renews; notice by {notice_by})"
        contract_rows.insert(0, ("Renewal date", renewal_display))
    elif status in ("no_active_contract", "draft"):
        contract_rows.insert(0, ("Renewal date", "No active signed contract"))

    for field_label, field_value in contract_rows:
        st.markdown(f"**{field_label}:** {field_value}")

with right:

    # Pricing
    st.subheader("Pricing")

    base_display = ct.get("contract_base_price", "—")
    st.markdown(f"**Contract base price:** {base_display}")

    if lp.get("display"):
        st.markdown(
            f"**Latest quote:** {lp['display']}  \n"
            f"_{lp.get('quoted_by', 'Unknown')} · {lp.get('date', '—')}_"
        )
    else:
        st.markdown("**Latest quote:** No price quoted in email thread")

    if delta:
        sign = "+" if delta["absolute"] >= 0 else ""
        direction = "above" if delta["absolute"] > 0 else "below"
        st.markdown(
            f"**Delta:** {sign}{delta['absolute']:.2f} {lp.get('unit', '')} "
            f"({sign}{delta['pct']}%) — quote is {direction} contract price"
        )
        if delta["absolute"] > 0:
            st.error("Quote exceeds contract price. Verify written amendment exists before agreeing.")
        elif delta["absolute"] == 0:
            st.success("In line with contract price.")
    elif lp.get("display") == "ambiguous — see open issues":
        st.warning("Price unit in email is ambiguous. See open issues.")
    elif lp.get("display") is None:
        st.caption("No email price quote to compare.")

    st.divider()

    # Commodity benchmark
    st.subheader("Commodity Benchmark")

    if bm:
        chg = bm.get("six_month_change_pct")
        chg_str = f"{chg:+.1f}%" if chg is not None else "n/a"
        direction = "▲" if chg and chg > 0 else ("▼" if chg and chg < 0 else "")

        st.markdown(
            f"**{bm['current_price']} {bm['unit']}** as of {bm['current_date']}  \n"
            f"6-month change: {direction} {chg_str} "
            f"(from {bm['six_month_ago_price']} on {bm['six_month_ago_date']})"
        )
        st.caption(f"Source: {bm['source']}")

        if "note" in bm:
            st.info(f"ℹ️ {bm['note']}")

        st.caption(packet.get("commodity_benchmark", ""))
    else:
        st.caption(
            packet.get("commodity_benchmark", "No benchmark in scope for this category.")
        )

# ── Correction tracking (KPI §5, internal monitoring) ────────────────────────

st.divider()

with st.expander("🔍 Field Corrections (internal quality tracking)", expanded=False):
    st.caption(
        "Flag any field the AI got wrong. This tracks extraction accuracy "
        "over time — not shown to suppliers. (metrics.md §5)"
    )

    if mid not in st.session_state.corrections:
        st.session_state.corrections[mid] = {}

    corr = st.session_state.corrections[mid]
    cols = st.columns(2)
    for i, (fk, label) in enumerate(TRACKABLE_FIELDS):
        with cols[i % 2]:
            val = corr.get(fk, False)
            checked = st.checkbox(f"🚩 {label}", value=val, key=flag_key(mid, fk))
            corr[fk] = checked

    n_flagged = count_flags(mid)
    total = len(TRACKABLE_FIELDS)
    rate = round(n_flagged / total * 100, 1) if total else 0.0
    st.metric(
        "Correction rate this packet",
        f"{rate}%",
        help=f"{n_flagged} of {total} fields flagged as incorrect",
    )
