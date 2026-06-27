"""
2_Meeting_Prep.py

Negotiation prep packet generator. Procurement Manager selects an upcoming
meeting, clicks Generate, and receives a one-page AI briefing built from
emails, contracts, and commodity prices.
"""

import csv
import os
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from ui_helpers import section_label, alert_card, brief_card, prose_card

if "ANTHROPIC_API_KEY" in st.secrets:
    os.environ["ANTHROPIC_API_KEY"] = st.secrets["ANTHROPIC_API_KEY"]

from utils.metrics import record_generation, update_correction_rate

from packet_generator import get_upcoming_meetings, run_packet, load_cached_packet

# ── Session state ─────────────────────────────────────────────────────────────

if "packets" not in st.session_state:
    st.session_state.packets = {}
if "corrections" not in st.session_state:
    st.session_state.corrections = {}
if "selected_id" not in st.session_state:
    st.session_state.selected_id = None
if "doc_request" not in st.session_state:
    st.session_state.doc_request = None
if "_doc_open" not in st.session_state:
    st.session_state._doc_open = 0
if "_doc_shown" not in st.session_state:
    st.session_state._doc_shown = 0

# ── Constants ─────────────────────────────────────────────────────────────────

LOG_PATH = Path(__file__).parent.parent.parent / "data" / "correction_log.csv"
PREP_LOG_PATH = Path(__file__).parent.parent.parent / "data" / "prep_time_log.csv"
LOG_COLUMNS = ["timestamp", "meeting_id", "supplier_name", "field_key", "field_label", "flagged", "packet_generated_at"]

ISSUE_CONFIG = {
    "price_discrepancy":        ("🔴", "Price discrepancy",        "error"),
    "no_active_contract":       ("🔴", "No active contract",       "error"),
    "quality_dispute":          ("🔴", "Quality dispute",           "error"),
    "spec_change_dispute":      ("🟠", "Spec change dispute",      "warning"),
    "renewal_date_discrepancy": ("🟠", "Renewal date discrepancy", "warning"),
    "delivery_dispute":         ("🟠", "Delivery dispute",         "warning"),
    "contract_renegotiation":   ("🟡", "Contract renegotiation",   "info"),
    "unanswered_thread":        ("🟡", "Unanswered thread",        "info"),
}

TRACKABLE_FIELDS = [
    ("email_summary",       "Email summary"),
    ("latest_price_quoted", "Latest price quoted"),
    ("contract_base_price", "Contract base price"),
    ("renewal_date",        "Renewal date"),
    ("payment_terms",       "Payment terms"),
    ("volume_commitment",   "Volume commitment"),
    ("key_penalty",         "Key penalty clause"),
    ("heads_up",            "Heads-up"),
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def renewal_status(days, contract_status):
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
    return f"{days}d", "normal"


def price_delta_display(delta, latest):
    if latest.get("display") == "ambiguous — see open issues":
        return "Ambiguous unit"
    if delta is None:
        return "No quote on file"
    sign = "+" if delta["absolute"] >= 0 else ""
    return f"{sign}{delta['pct']}%"


def flag_key(meeting_id, field):
    return f"flag_{meeting_id}_{field}"


def count_flags(meeting_id):
    return sum(
        1 for fk, _ in TRACKABLE_FIELDS
        if st.session_state.corrections.get(meeting_id, {}).get(fk, False)
    )


@st.dialog("Source Document", width="large")
def _doc_dialog():
    """Popup document viewer. Called at top level before any columns."""
    from extraction import load_emails as _le, load_contracts as _lc
    req = st.session_state.doc_request or {}
    supplier_num  = req.get("supplier_num", "")
    supplier_name = req.get("supplier_name", "")
    doc_type      = req.get("type", "")
    highlight     = req.get("highlight")

    if not supplier_num or not doc_type:
        st.warning("No document selected.")
        return

    if doc_type == "emails":
        try:
            emails = _le(supplier_num)
        except Exception as e:
            st.error(f"Could not load emails: {e}")
            return
        st.caption(f"**{supplier_name}** · {len(emails)} emails · most recent first")
        st.divider()
        for email in reversed(emails):
            is_strauss = "strauss-group.com" in email.get("from", "")
            is_hl = bool(highlight) and email.get("date", "") == highlight
            direction = "→ Strauss out" if is_strauss else "← Supplier in"
            with st.container(border=True):
                st.caption(
                    f"**{email.get('date','')}** · {direction} · "
                    f"_{email.get('subject','')}_"
                )
                if is_hl:
                    st.caption(f"From: {email.get('from','')}")
                    st.markdown(email.get("body", ""))
                else:
                    with st.expander("Read email"):
                        st.caption(f"From: {email.get('from','')}")
                        st.markdown(email.get("body", ""))

    elif doc_type == "contract":
        try:
            contracts = _lc(supplier_num)
        except Exception as e:
            st.error(f"Could not load contract: {e}")
            return
        if highlight:
            st.info(f"📌 Referenced: {highlight}")
        for fname, content in contracts.items():
            st.caption(f"📄 {fname}")
            st.markdown(content)


def src_expander(key, packet, doc_type, source_text, highlight=None):
    """📎 Source expander — collapsed by default, 'Open document' inside triggers popup."""
    _mid = st.session_state.get("selected_id")
    with st.expander("📎 Source", expanded=False):
        st.caption(source_text)
        if st.button("Open source document ↗", key=key):
            if _mid is not None:
                st.session_state[f"interactions_{_mid}"] = st.session_state.get(f"interactions_{_mid}", 0) + 1
            st.session_state.doc_request = {
                "type": doc_type,
                "highlight": highlight,
                "supplier_num": packet.get("supplier_num", ""),
                "supplier_name": packet.get("supplier_name", ""),
            }
            st.session_state._doc_open += 1
            st.rerun()


def save_correction_log(meeting_id, supplier_name, corrections, generated_at):
    write_header = not LOG_PATH.exists()
    with open(LOG_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=LOG_COLUMNS)
        if write_header:
            writer.writeheader()
        ts = datetime.utcnow().isoformat() + "Z"
        for fk, label in TRACKABLE_FIELDS:
            writer.writerow({
                "timestamp": ts,
                "meeting_id": meeting_id,
                "supplier_name": supplier_name,
                "field_key": fk,
                "field_label": label,
                "flagged": corrections.get(fk, False),
                "packet_generated_at": generated_at,
            })

def log_prep_time(meeting_id: int, supplier_name: str, elapsed_sec: int,
                   advance_hours=None, interactions: int = 0):
    """Append one prep-time entry to data/prep_time_log.csv."""
    PREP_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    write_header = not PREP_LOG_PATH.exists()
    with open(PREP_LOG_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow([
                "timestamp", "meeting_id", "supplier_name",
                "prep_seconds", "prep_minutes",
                "advance_hours", "opened_24h_before", "interactions"
            ])
        writer.writerow([
            datetime.utcnow().isoformat(),
            meeting_id,
            supplier_name,
            elapsed_sec,
            round(elapsed_sec / 60, 1),
            advance_hours,
            (advance_hours is not None and advance_hours >= 24),
            interactions
        ])


_FALLBACK_CURRENCY = {
    "Ivoire Cacao Export": "USD", "Golden Coast Cocoa Traders": "USD",
    "Lowlands Dairy Co-op": "EUR", "Galil Dairy Suppliers": "ILS",
    "Cana Doce Açúcar": "USD", "Siam Sugar Partners": "USD",
    "Sierra Verde Coffee Cooperative": "USD", "EuroPack Solutions": "PLN",
}


def _apply_financial_context(packet: dict, mid: int) -> None:
    """Set st.session_state.financial_context from a packet (works for cache or fresh)."""
    _sig = packet.get("financial_signals", {})
    _currency = _sig.get("contract_currency") or _FALLBACK_CURRENCY.get(packet["supplier_name"], "USD")
    st.session_state.financial_context = {
        "supplier_name": packet["supplier_name"],
        "supplier_num": packet["supplier_num"],
        "meeting_date": packet["meeting_date"],
        "contract_currency": _currency,
        "contract_value_foreign": None,
        "early_payment_discount_rate": _sig.get("early_payment_discount_rate"),
        "early_payment_discount_days": _sig.get("early_payment_discount_days"),
        "net_payment_days": _sig.get("net_payment_days"),
        "delivery_reliability_score": _sig.get("delivery_reliability_score"),
        "flags": {
            "fx_exposure": _currency != "ILS",
            "early_payment_discount": _sig.get("early_payment_discount_rate") is not None,
            "net_60_request": (_sig.get("net_payment_days") or 0) >= 60,
        },
    }
    if mid not in st.session_state.corrections:
        st.session_state.corrections[mid] = {}


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("⚡ Meeting Prep")
    st.caption("Generate a one-page briefing")
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
            st.rerun()

    if not st.session_state.selected_id:
        st.info("Select a meeting above.")

# ── Main area ─────────────────────────────────────────────────────────────────

mid = st.session_state.selected_id
packet = st.session_state.packets.get(mid) if mid else None

_force_regen = st.session_state.pop(f"force_{mid}", False) if mid else False

if packet is None and mid is not None:
    # Skip disk cache if user explicitly requested a refresh
    _cached = None if _force_regen else load_cached_packet(mid)
    if _cached:
        st.session_state.packets[mid] = _cached
        _apply_financial_context(_cached, mid)
        packet = _cached
    else:
        sel = next(m for m in meetings if m["meeting_id"] == mid)
        with st.status(f"Preparing packet for {sel['supplier']}…", expanded=True) as _status:
            _token_el = st.empty()
            _tick = [0]

            def _on_token(n: int) -> None:
                if n - _tick[0] >= 100:
                    _token_el.caption(f"🤖 Analysing… {n:,} chars")
                    _tick[0] = n

            try:
                t_start = time.time()
                packet = run_packet(mid, on_token=_on_token)
                duration = time.time() - t_start
                _token_el.empty()
                _status.update(label=f"✅ Ready in {duration:.1f}s", state="complete", expanded=False)
                st.session_state.packets[mid] = packet
                _apply_financial_context(packet, mid)
                st.rerun()
                price_delta = packet.get("price_delta")
                record_generation(
                    supplier_name=packet["supplier_name"],
                    duration_seconds=duration,
                    packet_length_chars=len(str(packet)),
                    meeting_id=mid,
                    category=packet.get("category"),
                    kpi_response_days=packet.get("avg_response_days"),
                    kpi_open_issues=packet.get("open_issues_count"),
                    kpi_price_delta_pct=price_delta["pct"] if price_delta else None,
                    kpi_days_to_renewal=packet.get("days_to_renewal"),
                )
            except Exception as e:
                _status.update(label="❌ Generation failed", state="error")
                st.error(f"Generation failed: {e}")
                st.stop()

if packet is None:
    st.markdown("## ⚡ Meeting Prep")
    st.markdown("Select an upcoming supplier meeting from the sidebar.")
    st.divider()
    for m in meetings[:5]:
        st.markdown(f"- **{m['date']}** — {m['supplier']} _{m['category']}_")
    if len(meetings) > 5:
        st.caption(f"…and {len(meetings) - 5} more")
    st.stop()

# ── Render packet ─────────────────────────────────────────────────────────────

# Start prep timer when the packet is first displayed
if f"prep_start_{mid}" not in st.session_state:
    st.session_state[f"prep_start_{mid}"] = time.time()
    st.session_state[f"interactions_{mid}"] = 0

    # Calculate advance hours: how far before the meeting is this packet being opened
    meeting_dt = None
    for m in meetings:  # meetings list should be in scope
        if m.get("meeting_id") == mid:
            dt_str = m.get("date") or m.get("meeting_date") or m.get("datetime")
            if dt_str:
                try:
                    meeting_dt = datetime.fromisoformat(str(dt_str))
                except Exception:
                    pass
            break

    if meeting_dt:
        now = datetime.utcnow()
        advance_hours = round((meeting_dt - now).total_seconds() / 3600, 1)
        st.session_state[f"advance_hours_{mid}"] = advance_hours
    else:
        st.session_state[f"advance_hours_{mid}"] = None

# Cache banner — shown when packet was served from disk cache
if packet.get("_from_cache"):
    _age_h = packet.get("_cache_age_hours", 0)
    _age_str = "just now" if _age_h < 0.1 else f"{_age_h:.0f}h ago"
    _cb1, _cb2 = st.columns([5, 1])
    with _cb1:
        st.info(f"📦 Loaded from cache — generated {_age_str}. Reflects data as of that time.")
    with _cb2:
        if st.button("🔄 Refresh", key=f"regen_{mid}"):
            from packet_generator import CACHE_DIR
            _cf = CACHE_DIR / f"meeting_{mid}.json"
            if _cf.exists():
                _cf.unlink()
            st.session_state[f"force_{mid}"] = True
            del st.session_state.packets[mid]
            st.rerun()

# Fire dialog at the TOP LEVEL (before any columns) so it always works.
# Uses a counter so it fires once per button click and stays closed after dismiss.
if st.session_state._doc_open > st.session_state._doc_shown:
    st.session_state._doc_shown = st.session_state._doc_open
    _doc_dialog()

ct = packet["contract_terms"]
lp = packet["latest_price_quoted"]
bm = packet["benchmark"]
issues = packet["open_issues"]
delta = packet["price_delta"]
fs = packet.get("field_sources", {})

# Header
col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.title(packet["supplier_name"])
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
        st.markdown(alert_card("Meeting is today", level="error"), unsafe_allow_html=True)
    elif days_left <= 3:
        st.markdown(alert_card(f"Meeting in {days_left} day{'s' if days_left != 1 else ''}", level="warning"), unsafe_allow_html=True)
    else:
        st.markdown(alert_card(f"Meeting in {days_left} days", level="info"), unsafe_allow_html=True)

if packet["meeting_notes"]:
    st.caption(f"📌 {packet['meeting_notes']}")

st.divider()

# ── KPI row ───────────────────────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)
with k1:
    avg_r = packet["avg_response_days"]
    st.metric("Avg Response Time", f"{avg_r}d" if avg_r is not None else "—",
              help="Average days from Strauss email to first supplier reply (metrics.md §1)")
with k2:
    st.metric("Open Issues", str(packet["open_issues_count"]),
              help="Unresolved issues found by AI extraction (metrics.md §2)")
with k3:
    delta_label = price_delta_display(delta, lp)
    delta_val = delta["pct"] if delta else None
    st.metric("Price vs Contract", delta_label,
              delta=f"{delta_val:+.1f}%" if delta_val is not None else None,
              delta_color="inverse",
              help="Latest email price vs contract base price (metrics.md §3)")
with k4:
    d_renew, _ = renewal_status(packet["days_to_renewal"], ct.get("status", ""))
    st.metric("Days to Renewal", d_renew,
              help="Days from today to contract renewal date (metrics.md §4)")

st.divider()

# ── Negotiation Brief ─────────────────────────────────────────────────────────
nb = packet.get("negotiation_brief", "")
if nb:
    st.markdown(brief_card(nb), unsafe_allow_html=True)
else:
    st.markdown(brief_card("Negotiation brief not available — click 🔄 Refresh to regenerate with AI insights."), unsafe_allow_html=True)
st.divider()

# ── Watch for Today ───────────────────────────────────────────────────────────
_wl, _wr = st.columns([3, 2], gap="large")
with _wl:
    n_issues = len(issues)
    issue_label = f"Watch for Today — {n_issues} open issue{'s' if n_issues != 1 else ''}" if n_issues else "Watch for Today"
    st.markdown(section_label(issue_label), unsafe_allow_html=True)

    has_red = any(
        ISSUE_CONFIG.get(i["issue_type"], ("", "", "info"))[2] == "error"
        for i in issues
    )
    hu_level = "error" if has_red else "warning"
    st.markdown(alert_card(packet["heads_up"], level=hu_level, title="Priority alert"), unsafe_allow_html=True)
    if fs.get("heads_up"):
        doc_type = "contract" if "contract" in fs["heads_up"].lower() else "emails"
        src_expander("src_headsup", packet, doc_type, fs["heads_up"])

    if not issues:
        st.markdown(alert_card("No open issues identified.", level="success"), unsafe_allow_html=True)
    else:
        for i, issue in enumerate(issues):
            cfg = ISSUE_CONFIG.get(issue["issue_type"], ("⚪", issue["issue_type"], "info"))
            icon, label, level = cfg
            src_ref = issue.get("source_ref", "")
            doc_type = "contract" if any(w in src_ref.lower() for w in ("contract", "section", "clause")) else "email"
            st.markdown(alert_card(issue["description"], level=level, title=f"{icon} {label}"), unsafe_allow_html=True)
            if src_ref:
                src_expander(f"src_issue_{i}", packet, doc_type, src_ref)

st.divider()

# ── Reference detail ──────────────────────────────────────────────────────────
left, right = st.columns([3, 2], gap="large")

with left:
    _email_cap = (
        f"Based on {packet['email_count']} emails · Avg supplier response: {packet['avg_response_days']}d"
        if packet["avg_response_days"] is not None
        else f"Based on {packet['email_count']} emails"
    )
    st.markdown(prose_card("Email History", packet["email_summary"], caption=_email_cap), unsafe_allow_html=True)
    if fs.get("email_summary"):
        src_expander("src_email_summary", packet, "emails", fs["email_summary"])

    st.divider()
    st.markdown(section_label("Contract at a Glance"), unsafe_allow_html=True)
    status = ct.get("status", "unknown")
    status_badge = {
        "active": "🟢 Active",
        "expired": "🔴 Expired",
        "draft": "🟠 Draft — not signed",
        "no_active_contract": "🔴 No active contract",
    }.get(status, status)
    st.markdown(f"**{ct.get('contract_id', '—')}** · {status_badge}")

    contract_rows = [
        ("Payment terms", ct.get("payment_terms", "—")),
        ("Volume min",    ct.get("volume_min", "—")),
        ("Volume max",    ct.get("volume_max", "—")),
        ("Base price",    ct.get("contract_base_price", "—")),
        ("Key penalty",   ct.get("key_penalty", "—")),
    ]
    renewal_str = ct.get("renewal_date")
    if renewal_str:
        auto = ct.get("auto_renewal", False)
        notice = ct.get("notice_period_days")
        renewal_display = renewal_str
        if auto and notice:
            rd = datetime.strptime(renewal_str, "%Y-%m-%d").date()
            notice_by = rd - timedelta(days=notice)
            renewal_display += f" (auto-renews; notice by {notice_by})"
        contract_rows.insert(0, ("Renewal date", renewal_display))
    elif status in ("no_active_contract", "draft"):
        contract_rows.insert(0, ("Renewal date", "No active signed contract"))

    for field_label, field_value in contract_rows:
        st.markdown(f"**{field_label}:** {field_value}")

    contract_source_fields = [
        ("renewal_date",        "Renewal date"),
        ("contract_base_price", "Base price"),
        ("payment_terms",       "Payment terms"),
        ("volume_commitment",   "Volume"),
        ("key_penalty",         "Penalty clause"),
    ]
    source_lines = [f"- **{lbl}:** {fs[fk]}" for fk, lbl in contract_source_fields if fs.get(fk)]
    if source_lines:
        with st.expander("📎 Source", expanded=False):
            st.markdown("\n".join(source_lines))
            if st.button("Open contract ↗", key="src_contract"):
                first_src = next((fs[fk] for fk, _ in contract_source_fields if fs.get(fk)), None)
                st.session_state.doc_request = {
                    "type": "contract",
                    "highlight": first_src,
                    "supplier_num": packet.get("supplier_num", ""),
                    "supplier_name": packet.get("supplier_name", ""),
                }
                st.session_state._doc_open += 1
                st.rerun()

with right:
    st.markdown(section_label("Pricing"), unsafe_allow_html=True)
    st.markdown(f"**Contract base price:** {ct.get('contract_base_price', '—')}")

    if lp.get("display"):
        st.markdown(
            f"**Latest quote:** {lp['display']}  \n"
            f"_{lp.get('quoted_by', 'Unknown')} · {lp.get('date', '—')}_"
        )
        if fs.get("latest_price_quoted"):
            src_expander("src_price", packet, "emails", fs["latest_price_quoted"],
                         highlight=lp.get("date"))
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
    st.markdown(section_label("Commodity Benchmark"), unsafe_allow_html=True)
    if bm:
        chg = bm.get("six_month_change_pct")
        chg_str = f"{chg:+.1f}%" if chg is not None else "n/a"
        bm_dir = "▲" if chg and chg > 0 else ("▼" if chg and chg < 0 else "")
        st.markdown(
            f"**{bm['current_price']} {bm['unit']}** as of {bm['current_date']}  \n"
            f"6-month change: {bm_dir} {chg_str} "
            f"(from {bm['six_month_ago_price']} on {bm['six_month_ago_date']})"
        )
        st.caption(f"Source: {bm['source']}")
        if "note" in bm:
            st.info(f"ℹ️ {bm['note']}")
        st.caption(packet.get("commodity_benchmark", ""))
    else:
        st.caption(packet.get("commodity_benchmark", "No benchmark in scope for this category."))

    # ── Live Market Signals ───────────────────────────────────────────────────

    _SUPPLIER_CURRENCY = {
        "Ivoire Cacao Export":             "USD",
        "Golden Coast Cocoa Traders":      "USD",
        "Lowlands Dairy Co-op":            "EUR",
        "Galil Dairy Suppliers":           "ILS",
        "Cana Doce Açúcar":               "USD",
        "Siam Sugar Partners":             "USD",
        "Sierra Verde Coffee Cooperative": "USD",
        "EuroPack Solutions":              "PLN",
    }
    _CATEGORY_TO_LIVE = {
        "cocoa": "Cocoa",
        "sugar": "Sugar (No. 11)",
        "dairy": "Dairy (Class III Milk)",
    }

    rd = st.session_state.get("reference_data", {})
    _fx  = rd.get("fx_rates",             pd.DataFrame())
    _bm  = rd.get("commodity_benchmarks", pd.DataFrame())
    _lr  = rd.get("lending_rates",        pd.DataFrame())

    st.divider()
    st.markdown(section_label("Live Market Signals"), unsafe_allow_html=True)

    signals_shown = 0

    # 1. Live commodity spot vs static benchmark
    live_commodity = _CATEGORY_TO_LIVE.get(packet.get("category", ""))
    if live_commodity and not _bm.empty:
        bm_row = _bm[_bm["commodity"] == live_commodity]
        if not bm_row.empty:
            live_price = bm_row.iloc[0]["price_usd"]
            live_unit  = bm_row.iloc[0]["unit"]
            live_date  = bm_row.iloc[0]["as_of_date"]
            st.markdown(f"**Live {live_commodity} spot**")
            st.markdown(
                f"{live_price:,.2f} {live_unit} · as of {live_date}"
            )
            # Show drift vs static benchmark (last CSV row)
            if bm and bm.get("current_price"):
                static_price = bm["current_price"]
                drift_pct = round((live_price - static_price) / static_price * 100, 1) if static_price else None
                if drift_pct is not None and abs(drift_pct) >= 0.5:
                    arrow = "▲" if drift_pct > 0 else "▼"
                    color = "#c8102e" if drift_pct > 0 else "#16a34a"
                    st.markdown(
                        f"<span style='color:{color};font-size:0.82rem;font-weight:600'>"
                        f"{arrow} {abs(drift_pct)}% vs last benchmark snapshot</span>",
                        unsafe_allow_html=True,
                    )
                    if drift_pct > 5:
                        st.caption("Market has moved up materially since benchmark was last pulled — supplier may reference spot in negotiation.")
                    elif drift_pct < -5:
                        st.caption("Market has softened since benchmark was last pulled — use this in negotiation if discussing pricing.")
            signals_shown += 1

    # 2. FX rate for this supplier's invoice currency
    supplier_currency = _SUPPLIER_CURRENCY.get(packet.get("supplier_name", ""), "USD")
    if not _fx.empty:
        if supplier_currency == "ILS":
            st.markdown("**FX Exposure:** None — supplier invoices in ILS")
        else:
            pair = f"{supplier_currency}/ILS"
            fx_row = _fx[_fx["currency_pair"] == pair]
            if not fx_row.empty:
                rate   = fx_row.iloc[0]["rate"]
                as_of  = fx_row.iloc[0]["as_of_date"]
                st.markdown(f"**{pair}:** {rate:.4f}  ·  as of {as_of}")
                st.caption(f"Supplier invoices in {supplier_currency}. Each 1% move in this rate shifts your ILS cost by 1%.")
        signals_shown += 1

    # 3. Cost of capital (always relevant for payment term discussions)
    if not _lr.empty:
        boi_row = _lr[_lr["rate_type"] == "Prime Rate"]
        if not boi_row.empty:
            boi_rate = float(boi_row.iloc[0]["rate_pct"])
            boi_src  = boi_row.iloc[0]["source"]
            src_ok   = "fallback" not in boi_src
            src_label = "BOI API" if src_ok else "fallback estimate"
            st.markdown(f"**BOI Prime Rate:** {boi_rate:.2f}%  ·  {src_label}")
            st.caption(
                "Your ILS cost of capital. An early payment discount is financially "
                f"rational if its implied APR exceeds {boi_rate:.2f}%. "
                "See Market Intel → Cost of Money for full analysis."
            )
            signals_shown += 1

    if signals_shown == 0:
        st.caption("Live market data unavailable — check network or reload.")

# ── Financial implications button ────────────────────────────────────────────

_fc = st.session_state.get("financial_context", {})
if _fc.get("flags") and any(_fc["flags"].values()):
    st.divider()
    _active_flags = [k for k, v in _fc["flags"].items() if v]
    _flag_labels = {
        "fx_exposure": "FX exposure",
        "early_payment_discount": "early payment discount",
        "net_60_request": "net 60 request",
    }
    _flag_str = " · ".join(_flag_labels[f] for f in _active_flags)
    st.caption(f"Financial flags detected: {_flag_str}")
    col_fin, _ = st.columns([2, 3])
    with col_fin:
        if st.button("💡 Explore financial implications", type="primary", use_container_width=True):
            st.switch_page("pages/financial_decisions.py")

# ── Correction tracking ───────────────────────────────────────────────────────

st.divider()
with st.expander("🔍 Field Corrections (internal quality tracking)", expanded=False):
    st.caption(
        "Flag any field the AI got wrong. Tracks extraction accuracy over time. "
        "Not shown to suppliers. (metrics.md §5)"
    )
    if mid not in st.session_state.corrections:
        st.session_state.corrections[mid] = {}
    corr = st.session_state.corrections[mid]
    cols = st.columns(2)
    for i, (fk, label) in enumerate(TRACKABLE_FIELDS):
        with cols[i % 2]:
            val = corr.get(fk, False)
            corr[fk] = st.checkbox(f"🚩 {label}", value=val, key=flag_key(mid, fk))

    n_flagged = count_flags(mid)
    total = len(TRACKABLE_FIELDS)
    rate = round(n_flagged / total * 100, 1) if total else 0.0
    st.metric("Correction rate this packet", f"{rate}%",
              help=f"{n_flagged} of {total} fields flagged as incorrect")

    if st.button("💾 Save corrections to log", key=f"save_log_{mid}"):
        save_correction_log(mid, packet["supplier_name"], corr, packet["generated_at"])
        update_correction_rate(mid, rate)  # metrics.md §5 — write to metrics.db
        st.session_state[f"interactions_{mid}"] = st.session_state.get(f"interactions_{mid}", 0) + 1
        st.success(f"Saved — {n_flagged} field(s) flagged ({rate}% correction rate recorded).")

# ── Prep time timer ───────────────────────────────────────────────────────────

elapsed_sec = int(time.time() - st.session_state[f"prep_start_{mid}"])
elapsed_min = elapsed_sec // 60
elapsed_s = elapsed_sec % 60

if not st.session_state.get(f"prep_logged_{mid}", False):
    st.divider()
    col_timer, col_btn = st.columns([3, 1])
    with col_timer:
        advance_h = st.session_state.get(f"advance_hours_{mid}")
        if advance_h is not None and advance_h > 0:
            advance_label = f" · {advance_h:.0f}h before meeting"
        elif advance_h is not None:
            advance_label = " · meeting is now or past"
        else:
            advance_label = ""
        st.caption(f"⏱ Prep time so far: {elapsed_min}m {elapsed_s:02d}s{advance_label}")
    with col_btn:
        if st.button("✅ Ready for meeting", key=f"ready_{mid}", type="primary"):
            st.session_state[f"interactions_{mid}"] = st.session_state.get(f"interactions_{mid}", 0) + 1
            st.session_state[f"prep_elapsed_{mid}"] = elapsed_sec
            log_prep_time(
                mid,
                packet.get("supplier_name", ""),
                elapsed_sec,
                advance_hours=st.session_state.get(f"advance_hours_{mid}"),
                interactions=st.session_state.get(f"interactions_{mid}", 0)
            )
            st.session_state[f"prep_logged_{mid}"] = True
            st.rerun()
else:
    elapsed_logged = st.session_state.get(f"prep_elapsed_{mid}", 0)
    st.success(f"✅ Prep time logged: {elapsed_logged // 60}m {elapsed_logged % 60:02d}s")
