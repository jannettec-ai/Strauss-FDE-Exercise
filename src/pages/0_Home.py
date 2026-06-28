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
            "Tracks the three KPIs from the pilot proposal. "
            "Data sources: data/metrics.db (generation events), "
            "data/prep_time_log.csv (prep time), data/correction_log.csv (AI accuracy)."
        )

        summary = get_summary()
        import pandas as pd

        CORR_LOG  = ROOT / "data" / "correction_log.csv"
        PREP_LOG  = ROOT / "data" / "prep_time_log.csv"
        CACHE_DIR_FDE = ROOT / "data" / "packet_cache"
        TOTAL_MEETINGS = 14  # from data/calendar.csv

        # ── Adoption Rate (computed from cache + calendar) ──────────────────
        cached_meeting_ids = {
            p.stem.split("_")[1]
            for p in CACHE_DIR_FDE.glob("meeting_*.json")
        }
        adoption_count = len(cached_meeting_ids)
        adoption_rate  = round(adoption_count / TOTAL_MEETINGS * 100) if TOTAL_MEETINGS else 0

        # ── Prep Time Saved (from log) ──────────────────────────────────────
        PREP_BASELINE_MIN = 120
        if PREP_LOG.exists():
            df_prep = pd.read_csv(PREP_LOG)
            sessions_logged   = len(df_prep)
            avg_prep_min      = round(df_prep["prep_minutes"].mean(), 1) if sessions_logged else None
            time_saved_min    = round(PREP_BASELINE_MIN - avg_prep_min, 1) if avg_prep_min is not None else None
            pct_saved         = round(time_saved_min / PREP_BASELINE_MIN * 100) if time_saved_min is not None else None
        else:
            df_prep = pd.DataFrame()
            sessions_logged = avg_prep_min = time_saved_min = pct_saved = None

        # ── Correction Rate (from log) ──────────────────────────────────────
        if CORR_LOG.exists():
            df_corr = pd.read_csv(CORR_LOG)
            df_corr["flagged"] = df_corr["flagged"].astype(str).str.lower() == "true"
            flagged = df_corr[df_corr["flagged"]]
            corr_rate = round(len(flagged) / len(df_corr) * 100, 1) if len(df_corr) else 0
        else:
            df_corr = pd.DataFrame()
            flagged  = pd.DataFrame()
            corr_rate = None

        # ── 3 KPI headline tiles ────────────────────────────────────────────
        k1, k2, k3 = st.columns(3)
        with k1:
            st.markdown("**KPI 1 — Prep Time Saved**")
            st.caption(f"Baseline: {PREP_BASELINE_MIN} min manual prep · {sessions_logged or 0} sessions logged")
            if time_saved_min is not None:
                st.metric("Time saved per session", f"{time_saved_min} min", delta=f"{pct_saved}% reduction")
                st.caption(f"Avg with tool: {avg_prep_min} min")
            else:
                st.metric("Time saved per session", "—")
                st.caption("No sessions logged yet — click 'Ready for meeting' in Meeting Prep to record.")
        with k2:
            st.markdown("**KPI 2 — Adoption Rate**")
            st.caption(f"Packets generated / total upcoming meetings ({TOTAL_MEETINGS})")
            st.metric("Adoption rate", f"{adoption_rate}%", delta=f"{adoption_count}/{TOTAL_MEETINGS} meetings")
        with k3:
            st.markdown("**KPI 3 — AI Correction Rate**")
            st.caption("Fields flagged as incorrect by PM / total fields presented")
            if corr_rate is not None:
                st.metric("Correction rate", f"{corr_rate}%",
                          delta=f"{len(flagged)} of {len(df_corr)} fields flagged",
                          delta_color="inverse")
            else:
                st.metric("Correction rate", "—")
                st.caption("No corrections logged yet — use Field Corrections panel in Meeting Prep.")

        st.divider()

        # ── Detail sections ─────────────────────────────────────────────────
        tab_prep, tab_adopt, tab_corr_detail = st.tabs([
            "Prep Time Detail", "Adoption Detail", "Correction Detail"
        ])

        with tab_prep:
            if not df_prep.empty:
                st.markdown(f"**{sessions_logged} sessions logged**  ·  baseline {PREP_BASELINE_MIN} min")
                cols_show = [c for c in ["timestamp","supplier_name","prep_minutes","advance_hours","opened_24h_before","interactions"] if c in df_prep.columns]
                st.dataframe(
                    df_prep[cols_show].rename(columns={
                        "timestamp": "Timestamp", "supplier_name": "Supplier",
                        "prep_minutes": "Prep (min)", "advance_hours": "Hrs before meeting",
                        "opened_24h_before": "24h+ advance", "interactions": "Interactions",
                    }),
                    hide_index=True, use_container_width=True,
                )
            else:
                st.info(
                    "No prep-time sessions logged yet.  \n"
                    "Open a packet in Meeting Prep and click **✅ Ready for meeting** when done."
                )

        with tab_adopt:
            st.markdown(f"**{adoption_count} of {TOTAL_MEETINGS} meetings** have a prep packet generated.")
            summary_val = get_summary()
            if summary_val["total_packets"]:
                st.caption(f"Unique suppliers queried: {summary_val['unique_suppliers']}  ·  "
                           f"Avg generation time: {summary_val['avg_duration_sec']}s")
                if summary_val["recent_events"]:
                    df_ev = pd.DataFrame(summary_val["recent_events"])
                    df_ev["timestamp"] = df_ev["timestamp"].str.replace("T", " ")
                    st.markdown("**Last 10 generation events**")
                    st.dataframe(df_ev, hide_index=True, use_container_width=True)
            else:
                st.info("No generation events in metrics.db yet.")

        with tab_corr_detail:
            if not df_corr.empty:
                col_f, col_s = st.columns(2)
                with col_f:
                    st.markdown("**By field — which AI extractions get flagged most**")
                    if not flagged.empty:
                        fc = flagged["field_label"].value_counts().reset_index()
                        fc.columns = ["Field", "Times Flagged"]
                        st.dataframe(fc, hide_index=True, use_container_width=True)
                    else:
                        st.caption("No flags yet.")
                with col_s:
                    st.markdown("**By supplier — where extraction noise is highest**")
                    if not flagged.empty:
                        sc = flagged["supplier_name"].value_counts().reset_index()
                        sc.columns = ["Supplier", "Times Flagged"]
                        st.dataframe(sc, hide_index=True, use_container_width=True)
                    else:
                        st.caption("No flags yet.")
                if not flagged.empty:
                    st.divider()
                    st.markdown("**Full correction log**")
                    df_show = flagged[["timestamp","supplier_name","field_label","meeting_id"]].copy()
                    df_show.columns = ["Timestamp","Supplier","Field Flagged","Meeting #"]
                    st.dataframe(df_show.sort_values("Timestamp", ascending=False), hide_index=True, use_container_width=True)
            else:
                st.info(
                    "No corrections logged yet.  \n"
                    "Open a packet in Meeting Prep, flag any wrong fields in the **Field Corrections** panel, "
                    "then click **Save corrections**."
                )

        if st.button("Lock", key="fde_lock"):
            st.session_state.fde_authenticated = False
            st.rerun()
