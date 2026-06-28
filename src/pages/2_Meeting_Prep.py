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
from ui_helpers import section_label, alert_card, brief_card, prose_card, packet_title_html

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

        # Pin the referenced email at the top when a specific date is highlighted
        if highlight:
            hl_email = next((e for e in emails if e.get("date", "") == highlight), None)
            if hl_email:
                is_strauss_hl = "strauss-group.com" in hl_email.get("from", "")
                direction_hl = "→ Strauss out" if is_strauss_hl else "← Supplier in"
                st.markdown("**📌 Referenced email**")
                with st.container(border=True):
                    st.caption(
                        f"**{hl_email.get('date','')}** · {direction_hl} · "
                        f"_{hl_email.get('subject','')}_  \n"
                        f"From: {hl_email.get('from','')}"
                    )
                    st.markdown(hl_email.get("body", ""))
                st.divider()

        st.caption(f"**{supplier_name}** · {len(emails)} emails · full thread, most recent first")
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
                label = "Read email (referenced above ↑)" if is_hl else "Read email"
                with st.expander(label):
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
    _sig = packet.get("financial_signals") or {}
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


# ── Load meetings ─────────────────────────────────────────────────────────────

meetings = get_upcoming_meetings()

with st.sidebar:
    st.title("⚡ Meeting Prep")
    st.caption("Generate a one-page briefing")
    if st.session_state.selected_id:
        st.divider()
        if st.button("← All meetings", use_container_width=True):
            st.session_state.selected_id = None
            st.rerun()

# ── Main area ─────────────────────────────────────────────────────────────────

mid = st.session_state.selected_id
packet = st.session_state.packets.get(mid) if mid else None

_force_regen = st.session_state.pop(f"force_{mid}", False) if mid else False

# ── Meeting selector (shown when no meeting selected) ─────────────────────────

if not mid:
    from ui_helpers import meeting_card, section_label as _sl
    st.markdown(
        '<div style="font-size:0.78rem;font-weight:700;text-transform:uppercase;'
        'letter-spacing:0.12em;color:#c8102e;margin-bottom:0.25rem;">Meeting Prep</div>',
        unsafe_allow_html=True,
    )
    st.title("Upcoming Meetings")
    st.caption("Select a meeting to generate your negotiation prep packet.")
    st.divider()

    if not meetings:
        st.info("No upcoming meetings in calendar.")
        st.stop()

    for i in range(0, len(meetings), 2):
        cols = st.columns(2, gap="large")
        for col, m in zip(cols, meetings[i:i+2]):
            with col:
                st.markdown(
                    meeting_card(
                        m["date"], m["supplier"], m["days_until"],
                        m.get("notes", ""), m.get("geography", ""), m["category"],
                    ),
                    unsafe_allow_html=True,
                )
                if st.button(
                    "Generate prep packet →",
                    key=f"sel_{m['meeting_id']}",
                    use_container_width=True,
                ):
                    st.session_state.selected_id = m["meeting_id"]
                    st.rerun()
    st.stop()

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
st.markdown(
    '<div style="font-size:0.78rem;font-weight:700;text-transform:uppercase;'
    'letter-spacing:0.12em;color:#c8102e;margin-bottom:0.25rem;">Meeting Prep</div>',
    unsafe_allow_html=True,
)
col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.markdown(
        packet_title_html(
            packet["supplier_name"],
            caption=(
                f"📅 {packet['meeting_date']}  ·  "
                f"📍 {packet['geography']}  ·  "
                f"🏷 {packet['category'].title()}  ·  "
                f"Meeting #{mid}"
            ),
        ),
        unsafe_allow_html=True,
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

# ── Other meetings for this supplier ─────────────────────────────────────────
_other_meetings = [
    m for m in meetings
    if m["supplier"] == packet["supplier_name"] and m["meeting_id"] != mid
]
for _om in _other_meetings:
    st.info(
        f"📅 This supplier also has a meeting on **{_om['date']}** "
        f"(in {_om['days_until']}d) — _{_om.get('notes', 'No agenda noted')}_"
    )
    with st.expander(f"See context for {_om['date']} meeting →", expanded=False):
        _om_packet = load_cached_packet(_om["meeting_id"])
        if _om_packet:
            _om_issues = _om_packet.get("open_issues", [])
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown(f"**Agenda:** {_om.get('notes', '—')}")
                st.markdown(f"**Geography:** {_om.get('geography', '—')}")
                _om_brief = _om_packet.get("negotiation_brief", "")
                if _om_brief:
                    st.caption((_om_brief[:280] + "…") if len(_om_brief) > 280 else _om_brief)
            with col_b:
                st.markdown(f"**Open issues ({len(_om_issues)})**")
                for _oi in _om_issues:
                    _cfg = ISSUE_CONFIG.get(_oi["issue_type"], ("⚪", _oi["issue_type"], "info"))
                    _icon, _label, _ = _cfg
                    _desc = _oi["description"]
                    st.caption(f"{_icon} **{_label}** — {(_desc[:110] + '…') if len(_desc) > 110 else _desc}")
        else:
            st.caption("No packet generated for this meeting yet.")
        if st.button(
            f"Open Meeting #{_om['meeting_id']} prep packet →",
            key=f"go_other_{_om['meeting_id']}",
        ):
            st.session_state.selected_id = _om["meeting_id"]
            st.rerun()

if _other_meetings:
    st.divider()

# ── Row 1: Relationship KPIs ──────────────────────────────────────────────────
k1, k2, k3 = st.columns(3)
with k1:
    avg_r = packet["avg_response_days"]
    st.metric("Avg Response Time", f"{avg_r}d" if avg_r is not None else "—",
              help="Average days from Strauss email to first supplier reply (metrics.md §1)")
with k2:
    st.metric("Open Issues", str(packet["open_issues_count"]),
              help="Unresolved issues found by AI extraction (metrics.md §2)")
with k3:
    d_renew, _ = renewal_status(packet["days_to_renewal"], ct.get("status", ""))
    st.metric("Days to Renewal", d_renew,
              help="Days from today to contract renewal date (metrics.md §4)")

st.markdown("<div style='margin-top:0.75rem'></div>", unsafe_allow_html=True)

# ── Row 2: Financial KPIs ─────────────────────────────────────────────────────
f1, f2, f3, f4 = st.columns(4)
with f1:
    base = ct.get("contract_base_price", "—")
    st.metric("Contract Base Price", base,
              help="Agreed base price from the signed contract")
with f2:
    st.metric("Latest Quoted Price", lp.get("display", "—") if lp.get("display") else "—",
              help="Most recent price quoted by supplier in email thread")
with f3:
    delta_label = price_delta_display(delta, lp)
    st.metric("Price vs Contract", delta_label,
              help="Latest email price vs contract base price (metrics.md §3)")
with f4:
    if bm:
        chg = bm.get("six_month_change_pct")
        arrow = "▲" if chg and chg > 0 else ("▼" if chg and chg < 0 else "")
        chg_str = f"{chg:+.1f}%" if chg is not None else ""
        bm_val = f"{bm['current_price']} {bm.get('unit','')}"
        st.metric("Market Benchmark", bm_val,
                  delta=f"{arrow} {chg_str} (6 months)" if chg_str else None,
                  delta_color="inverse",
                  help="Live commodity benchmark price and 6-month trend direction")
    else:
        st.metric("Market Benchmark", "—", help="No benchmark data for this category")

st.divider()

# ── Negotiation Brief + Recommendations ───────────────────────────────────────
nb = packet.get("negotiation_brief", "")
if nb:
    st.markdown(brief_card(nb), unsafe_allow_html=True)
else:
    st.markdown(brief_card("Negotiation brief not available — click 🔄 Refresh to regenerate with AI insights."), unsafe_allow_html=True)

# ── Key Actions (derived from structured data, no API call) ───────────────────
_sig_rec = packet.get("financial_signals") or {}
_epd_rate_rec = _sig_rec.get("early_payment_discount_rate")
_epd_days_rec = _sig_rec.get("early_payment_discount_days")
_net_days_rec  = _sig_rec.get("net_payment_days")

_recommendations = []

# Contract expired or missing
if ct.get("status") in ("expired", "no_active_contract"):
    _recommendations.append(("🔴", "Execute contract renewal before placing the next order — you are currently operating without a signed agreement."))

# Price above contract without amendment
if delta and delta["absolute"] > 0:
    _recommendations.append(("🟠", f"Request a formal written price amendment — the quoted {lp.get('display','price')} exceeds the contract base without documentation."))

# Early payment discount worth taking
if _epd_rate_rec and _epd_days_rec and _net_days_rec:
    _diff_rec = _net_days_rec - _epd_days_rec
    _apr_rec = round((_epd_rate_rec / (1 - _epd_rate_rec)) * (365 / _diff_rec) * 100, 1) if _diff_rec > 0 else None
    _rd_rec = st.session_state.get("reference_data", {})
    _lr_rec = _rd_rec.get("lending_rates", pd.DataFrame())
    _boi_rec = None
    if not _lr_rec.empty:
        _boi_row_r = _lr_rec[_lr_rec["rate_type"] == "Prime Rate"]
        if not _boi_row_r.empty:
            _boi_rec = float(_boi_row_r.iloc[0]["rate_pct"])
    if _apr_rec and _boi_rec and (_apr_rec - _boi_rec) > 0:
        _recommendations.append(("✅", f"Take the early payment discount — {_epd_rate_rec*100:.1f}% within {_epd_days_rec} days yields {_apr_rec:.1f}% APR vs your {_boi_rec:.1f}% cost of capital."))

# Delivery disputes
_delivery = [i for i in issues if i["issue_type"] == "delivery_dispute"]
if _delivery:
    _recommendations.append(("🟠", f"Confirm resolution of {len(_delivery)} open delivery dispute{'s' if len(_delivery) > 1 else ''} — verify any credits or penalties have been applied to invoices."))

# Unanswered threads
_unanswered = [i for i in issues if i["issue_type"] == "unanswered_thread"]
if _unanswered:
    _recommendations.append(("🟡", f"Follow up on {len(_unanswered)} unanswered thread{'s' if len(_unanswered) > 1 else ''} — get written confirmation before closing the meeting."))

if _recommendations:
    st.markdown(
        '<div style="margin-top:0.85rem;padding:1rem 1.1rem;background:#f8fafc;'
        'border-radius:10px;border:1px solid #e2e8f0;">'
        '<div style="font-size:0.75rem;font-weight:700;text-transform:uppercase;'
        'letter-spacing:0.08em;color:#64748b;margin-bottom:0.6rem;">Key Actions</div>'
        + "".join(
            f'<div style="display:flex;gap:0.6rem;margin-bottom:0.45rem;align-items:flex-start;">'
            f'<span style="font-size:1rem;flex-shrink:0;margin-top:0.05rem;">{icon}</span>'
            f'<span style="font-size:0.95rem;color:#1e293b;line-height:1.5;">{text}</span>'
            f'</div>'
            for icon, text in _recommendations
        )
        + '</div>',
        unsafe_allow_html=True,
    )

st.divider()

# ── Watch for Today ───────────────────────────────────────────────────────────
n_issues = len(issues)
issue_label = f"Watch for Today — {n_issues} open issue{'s' if n_issues != 1 else ''}" if n_issues else "Watch for Today"
st.markdown(section_label(issue_label), unsafe_allow_html=True)

has_red = any(
    ISSUE_CONFIG.get(i["issue_type"], ("", "", "info"))[2] == "error"
    for i in issues
)
hu_level = "error" if has_red else "warning"

_wl, _wr = st.columns([1, 1], gap="large")

# Priority alert always in left; issues split evenly across both columns
import math
import re as _re

_left_issues  = issues[:math.ceil(len(issues) / 2)]
_right_issues = issues[math.ceil(len(issues) / 2):]


def _resolve_source(src_ref: str) -> tuple[str, str | None]:
    """
    Return (doc_type, highlight_date).
    If the source_ref contains an email date, open the email viewer at that date.
    Only open the contract viewer when there is NO email date in the reference.
    """
    date_match = _re.search(r'\b(\d{4}-\d{2}-\d{2})\b', src_ref)
    if date_match and "email" in src_ref.lower():
        return "emails", date_match.group(1)
    if any(w in src_ref.lower() for w in ("contract", "section", "clause")):
        return "contract", None
    return "emails", None


with _wl:
    st.markdown(alert_card(packet["heads_up"], level=hu_level, title="Priority alert"), unsafe_allow_html=True)
    if fs.get("heads_up"):
        _hu_type, _hu_hl = _resolve_source(fs["heads_up"])
        src_expander("src_headsup", packet, _hu_type, fs["heads_up"], highlight=_hu_hl)
    if not issues:
        st.markdown(alert_card("No open issues identified.", level="success"), unsafe_allow_html=True)
    for i, issue in enumerate(_left_issues):
        cfg = ISSUE_CONFIG.get(issue["issue_type"], ("⚪", issue["issue_type"], "info"))
        icon, label, level = cfg
        src_ref = issue.get("source_ref", "")
        st.markdown(alert_card(issue["description"], level=level, title=f"{icon} {label}"), unsafe_allow_html=True)
        if src_ref:
            _dt, _hl = _resolve_source(src_ref)
            src_expander(f"src_issue_l{i}", packet, _dt, src_ref, highlight=_hl)

with _wr:
    for i, issue in enumerate(_right_issues):
        cfg = ISSUE_CONFIG.get(issue["issue_type"], ("⚪", issue["issue_type"], "info"))
        icon, label, level = cfg
        src_ref = issue.get("source_ref", "")
        st.markdown(alert_card(issue["description"], level=level, title=f"{icon} {label}"), unsafe_allow_html=True)
        if src_ref:
            _dt, _hl = _resolve_source(src_ref)
            src_expander(f"src_issue_r{i}", packet, _dt, src_ref, highlight=_hl)

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
    st.markdown(section_label("Contract at a Glance", "Key terms extracted from the signed contract on file: status, renewal date, payment terms, and volume commitments."), unsafe_allow_html=True)
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

    with st.expander("📎 Source", expanded=False):
        st.caption(f"Contract on file: {ct.get('contract_id', 'see contract document')}")
        if st.button("Open contract ↗", key="src_contract"):
            st.session_state.doc_request = {
                "type": "contract",
                "highlight": None,
                "supplier_num": packet.get("supplier_num", ""),
                "supplier_name": packet.get("supplier_name", ""),
            }
            st.session_state._doc_open += 1
            st.rerun()

with right:
    st.markdown(section_label("Pricing", "Contract base price vs. the most recent price quoted in supplier emails. Delta flags any informal increase not backed by a written amendment."), unsafe_allow_html=True)

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

    if delta and delta["absolute"] > 0:
        st.error("Quote exceeds contract price. Verify written amendment exists before agreeing.")
    elif delta and delta["absolute"] == 0:
        st.success("In line with contract price.")
    elif lp.get("display") == "ambiguous — see open issues":
        st.warning("Price unit in email is ambiguous. See open issues.")

    # Early payment discount — rendered if extracted from emails/contract
    _sig = packet.get("financial_signals") or {}
    _epd_rate = _sig.get("early_payment_discount_rate")
    _epd_days = _sig.get("early_payment_discount_days")
    _net_days = _sig.get("net_payment_days")
    if _epd_rate and _epd_days and _net_days:
        # Implied APR of taking the discount
        _diff_days = (_net_days or 30) - _epd_days
        _apr = round((_epd_rate / (1 - _epd_rate)) * (365 / _diff_days) * 100, 1) if _diff_days > 0 else None

        # BOI prime rate from live data (for verdict)
        _rd_epd = st.session_state.get("reference_data", {})
        _lr_epd = _rd_epd.get("lending_rates", pd.DataFrame())
        _boi_epd = None
        if not _lr_epd.empty:
            _boi_row = _lr_epd[_lr_epd["rate_type"] == "Prime Rate"]
            if not _boi_row.empty:
                _boi_epd = float(_boi_row.iloc[0]["rate_pct"])

        if _apr is not None:
            if _boi_epd is not None:
                _spread = _apr - _boi_epd
                if _spread > 10:
                    _verdict = f"✅ Take the discount — implied APR {_apr:.1f}% is {_spread:.1f}pp above your {_boi_epd:.1f}% cost of capital."
                    _level = "success"
                elif _spread > 0:
                    _verdict = f"⚠️ Worth considering — implied APR {_apr:.1f}% modestly exceeds your {_boi_epd:.1f}% cost of capital."
                    _level = "info"
                else:
                    _verdict = f"❌ Not financially rational — implied APR {_apr:.1f}% is below your {_boi_epd:.1f}% cost of capital."
                    _level = "warning"
            else:
                _verdict = f"Implied APR: **{_apr:.1f}%**. Compare against your cost of capital to decide."
                _level = "info"
        else:
            _verdict = "Insufficient payment term data to calculate APR."
            _level = "info"

        st.markdown(
            alert_card(
                f"**{_epd_rate * 100:.1f}%** discount if paid within {_epd_days} days "
                f"(vs. standard net {_net_days} days).  \n{_verdict}",
                level=_level,
                title="💳 Early payment discount",
            ),
            unsafe_allow_html=True,
        )

    st.divider()
    st.markdown(section_label("Commodity Benchmark", "Live market price for this supplier's commodity category. Shows where the market sits relative to your contracted and quoted price."), unsafe_allow_html=True)
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
    st.markdown(section_label("Live Market Signals", "Real-time FX rates, commodity prices, and cost of capital — pulled at session start. Relevant to this supplier's currency and category."), unsafe_allow_html=True)

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
                f"Your ILS cost of capital — used above to evaluate any early payment discount offer."
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
