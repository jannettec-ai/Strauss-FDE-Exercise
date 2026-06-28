"""Procurement Overview — executive dashboard with portfolio alerts, renewals, and health."""

import json
import os
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

from packet_generator import get_upcoming_meetings
from supplier_analytics import SUPPLIERS, get_all_summaries
from utils.metrics import get_summary
from ui_helpers import section_label, kpi_card, meeting_card, alert_card

ROOT = Path(__file__).parent.parent.parent
CACHE_DIR = ROOT / "data" / "packet_cache"

# ── Cache ─────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def cached_summaries():
    return get_all_summaries()

@st.cache_data(ttl=300)
def cached_meetings():
    return get_upcoming_meetings()

@st.cache_data(ttl=300)
def load_portfolio_issues() -> list[dict]:
    """Aggregate open issues from all cached packets. One entry per supplier (latest meeting)."""
    seen_suppliers = set()
    issues_out = []
    cache_files = sorted(CACHE_DIR.glob("meeting_*.json"), key=lambda p: int(p.stem.split("_")[1]))
    for fp in reversed(cache_files):
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
            supplier = data.get("supplier_name", "")
            if supplier in seen_suppliers:
                continue
            seen_suppliers.add(supplier)
            for issue in data.get("open_issues", []):
                issues_out.append({
                    "supplier": supplier,
                    "meeting_id": data.get("meeting_id"),
                    "meeting_date": data.get("meeting_date"),
                    "issue_type": issue.get("issue_type", ""),
                    "description": issue.get("description", ""),
                })
        except Exception:
            continue

    severity = {
        "no_active_contract": 0,
        "price_discrepancy": 1,
        "delivery_dispute": 2,
        "contract_renegotiation": 3,
        "unanswered_thread": 4,
    }
    issues_out.sort(key=lambda x: severity.get(x["issue_type"], 5))
    return issues_out

ISSUE_ICONS = {
    "no_active_contract":   ("🔴", "No active contract"),
    "price_discrepancy":    ("🟠", "Price discrepancy"),
    "delivery_dispute":     ("🟠", "Delivery dispute"),
    "contract_renegotiation": ("🟡", "Contract renegotiation"),
    "unanswered_thread":    ("🟡", "Unanswered thread"),
}

# ── Load data ─────────────────────────────────────────────────────────────────

summaries  = cached_summaries()
meetings   = cached_meetings()
all_issues = load_portfolio_issues()

# ── Header ────────────────────────────────────────────────────────────────────

st.title("Procurement Overview")
st.caption("Negotiation intelligence dashboard · All data is local — no API calls on this page")
st.divider()

# ── KPI tiles ─────────────────────────────────────────────────────────────────

today = date.today()
total_suppliers    = len(summaries)
meetings_this_week = [m for m in meetings if m["days_until"] <= 7]
at_risk            = [s for s in summaries if s["health_label"] == "At risk"]
contract_issues    = [s for s in summaries if s["contract"]["status"] in ("expired", "draft", "no_active_contract")]

s1, s2, s3, s4 = st.columns(4)
with s1:
    st.markdown(kpi_card(str(len(meetings)), "Upcoming Meetings", "From today"), unsafe_allow_html=True)
with s2:
    st.markdown(kpi_card(str(len(meetings_this_week)), "This Week", "Next 7 days"), unsafe_allow_html=True)
with s3:
    _val = f'{len(at_risk)}<span style="font-size:0.9rem;font-weight:400;color:#94a3b8"> /{total_suppliers}</span>'
    st.markdown(kpi_card(_val, "Suppliers at Risk", "Relationship health signals"), unsafe_allow_html=True)
with s4:
    _val = f'{len(contract_issues)}<span style="font-size:0.9rem;font-weight:400;color:#94a3b8"> /{total_suppliers}</span>'
    st.markdown(kpi_card(_val, "Contract Issues", "Expired or missing"), unsafe_allow_html=True)

st.divider()

# ── Portfolio Alerts ──────────────────────────────────────────────────────────

st.markdown(
    section_label("Portfolio Alerts", "Top open issues across all suppliers, ranked by severity. Sourced from AI-generated prep packets."),
    unsafe_allow_html=True,
)

if not all_issues:
    st.info("No issues on file — generate prep packets on the Meeting Prep page to populate this view.")
else:
    shown = all_issues[:8]
    col_a, col_b = st.columns(2, gap="large")
    for i, issue in enumerate(shown):
        icon, label = ISSUE_ICONS.get(issue["issue_type"], ("⚪", issue["issue_type"].replace("_", " ").title()))
        desc = issue["description"]
        desc_short = desc[:160] + "…" if len(desc) > 160 else desc
        card_html = (
            f'<div style="background:white;border:1px solid #e2e8f0;border-radius:10px;'
            f'padding:0.85rem 1rem;margin-bottom:0.6rem;'
            f'border-left:3px solid {"#c8102e" if icon == "🔴" else "#f59e0b" if icon == "🟠" else "#94a3b8"};">'
            f'<div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.3rem;">'
            f'<span style="font-size:0.75rem;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:0.05em;">'
            f'{icon} {issue["supplier"]} · {label}</span></div>'
            f'<div style="font-size:0.92rem;color:#1e293b;line-height:1.5;">{desc_short}</div>'
            f'</div>'
        )
        with col_a if i % 2 == 0 else col_b:
            st.markdown(card_html, unsafe_allow_html=True)

    if len(all_issues) > 8:
        st.caption(f"…and {len(all_issues) - 8} more issues across the portfolio. Open Meeting Prep for full detail.")

st.divider()

# ── Meetings + Renewals ───────────────────────────────────────────────────────

left, right = st.columns([3, 2], gap="large")

with left:
    st.markdown(
        section_label("Upcoming Meetings", "Supplier meetings scheduled in the next 90 days, ordered by date."),
        unsafe_allow_html=True,
    )
    if not meetings:
        st.info("No upcoming meetings in calendar.")
    else:
        cards_html = "".join(
            meeting_card(
                m["date"], m["supplier"], m["days_until"],
                m.get("notes", ""), m.get("geography", ""), m["category"],
            )
            for m in meetings[:6]
        )
        st.markdown(cards_html, unsafe_allow_html=True)
        if len(meetings) > 6:
            st.caption(f"…and {len(meetings) - 6} more · use Meeting Prep to generate a packet")

with right:
    # ── Contract Renewals (next 60 days only) ────────────────────────────────
    st.markdown(
        section_label("Contract Renewals — Next 60 Days", "Suppliers with contracts expired or renewing within 60 days."),
        unsafe_allow_html=True,
    )

    expired, urgent, approaching = [], [], []
    for s in summaries:
        c = s["contract"]
        rd = c.get("renewal_date")
        name = s["supplier_name"]
        status = c.get("status", "unknown")

        if status == "no_active_contract" or (rd is None and status == "expired"):
            expired.append((name, "No active contract"))
            continue
        if status == "draft":
            expired.append((name, "Unsigned draft"))
            continue
        if rd:
            try:
                renewal = datetime.strptime(rd, "%Y-%m-%d").date()
                days = (renewal - today).days
                if days < 0:
                    expired.append((name, f"Expired {abs(days)}d ago"))
                elif days <= 30:
                    urgent.append((name, f"{days}d to renewal"))
                elif days <= 60:
                    approaching.append((name, f"{days}d to renewal"))
                # > 60 days: excluded
            except Exception:
                pass

    def renewal_row(name, note, color):
        dot_colors = {"red": "#c8102e", "amber": "#f59e0b"}
        return (
            f'<div style="display:flex;align-items:center;justify-content:space-between;'
            f'padding:0.5rem 0;border-bottom:1px solid #f1f5f9;">'
            f'<span style="font-size:0.95rem;font-weight:600;color:#0f172a;">{name}</span>'
            f'<span style="font-size:0.82rem;color:{dot_colors[color]};font-weight:600;">{note}</span>'
            f'</div>'
        )

    rows_html = ""
    for name, note in expired:
        rows_html += renewal_row(name, note, "red")
    for name, note in urgent:
        rows_html += renewal_row(name, note, "amber")
    for name, note in approaching:
        rows_html += renewal_row(name, note, "amber")

    if rows_html:
        st.markdown(f'<div>{rows_html}</div>', unsafe_allow_html=True)
    else:
        st.caption("No contracts expiring within 60 days.")

    st.markdown("<div style='margin-top:1.5rem'></div>", unsafe_allow_html=True)

    # ── Supplier Health ───────────────────────────────────────────────────────
    st.markdown(
        section_label("Supplier Health", "Combined score: relationship signals + contract status."),
        unsafe_allow_html=True,
    )

    HEALTH_COLOR = {"Healthy": "#16a34a", "Stable": "#ca8a04", "At risk": "#c8102e"}
    CONTRACT_LABEL = {
        "active": "Active contract",
        "expired": "Expired contract",
        "draft": "Unsigned draft",
        "no_active_contract": "No active contract",
        "unknown": "Contract status unknown",
    }

    _health_order = {"At risk": 0, "Stable": 1, "Healthy": 2}
    for s in sorted(summaries, key=lambda x: _health_order.get(x["combined_health_label"], 3)):
        label   = s["combined_health_label"]
        color   = HEALTH_COLOR.get(label, "#94a3b8")
        days    = s["days_since_last_contact"]
        contact = f"{days}d since contact" if days is not None else "no email on file"
        contract_ctx = CONTRACT_LABEL.get(s["contract"].get("status", "unknown"), "")
        trend   = s.get("response_trend", {})
        trend_note = ""
        if trend.get("direction") == "slower":
            trend_note = " · slowing"
        elif trend.get("direction") == "faster":
            trend_note = " · improving"

        row_html = (
            f'<div style="display:flex;align-items:flex-start;gap:0.65rem;'
            f'padding:0.55rem 0;border-bottom:1px solid #f1f5f9;">'
            f'<div style="width:9px;height:9px;border-radius:50%;background:{color};'
            f'margin-top:0.4rem;flex-shrink:0;"></div>'
            f'<div>'
            f'<div style="font-size:0.95rem;font-weight:600;color:#0f172a;">{s["supplier_name"]}</div>'
            f'<div style="font-size:0.82rem;color:#64748b;margin-top:0.1rem;">'
            f'{contract_ctx} · {contact}{trend_note}</div>'
            f'</div>'
            f'</div>'
        )
        st.markdown(row_html, unsafe_allow_html=True)

st.divider()

# ── FDE Dashboard (password-protected) ───────────────────────────────────────

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
            st.markdown("**KPI summary across all packets generated**")
            kpi = summary["kpi_summary"]
            k1, k2, k3, k4, k5 = st.columns(5)
            with k1:
                v = kpi.get("avg_response_days")
                st.metric("Avg Response Time", f"{v}d" if v else "—")
            with k2:
                v = kpi.get("avg_open_issues")
                st.metric("Avg Open Issues", str(v) if v is not None else "—")
            with k3:
                v = kpi.get("avg_price_delta_pct")
                st.metric("Avg Price Delta", f"{v:+.1f}%" if v is not None else "—")
            with k4:
                v = kpi.get("avg_days_to_renewal")
                st.metric("Avg Days to Renewal", f"{int(v)}d" if v is not None else "—")
            with k5:
                v = kpi.get("avg_correction_rate_pct")
                st.metric("Avg Correction Rate", f"{v}%" if v is not None else "—")

            st.divider()
            if summary["supplier_breakdown"]:
                st.markdown("**Per-supplier breakdown**")
                df_sup = pd.DataFrame(summary["supplier_breakdown"])
                df_sup.columns = [
                    "Supplier", "Category", "Packets", "Avg Gen (s)",
                    "§1 Response (d)", "§2 Open Issues", "§3 Price Delta %", "§4 Renewal (d)",
                ]
                st.dataframe(df_sup, use_container_width=True, hide_index=True)

            if summary["recent_events"]:
                st.markdown("**Last 10 generation events**")
                df_recent = pd.DataFrame(summary["recent_events"])
                df_recent["timestamp"] = df_recent["timestamp"].str.replace("T", " ")
                st.dataframe(df_recent, use_container_width=True, hide_index=True)

        if st.button("Lock", key="fde_lock"):
            st.session_state.fde_authenticated = False
            st.rerun()
