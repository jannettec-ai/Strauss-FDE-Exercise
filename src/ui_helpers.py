"""
ui_helpers.py

Design system for Strauss Procurement UI.
Returns HTML strings rendered via st.markdown(html, unsafe_allow_html=True).
No Streamlit imports — pure string helpers only.
"""

from typing import Optional

# ── Global CSS (injected once from app.py) ────────────────────────────────────

GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
  font-family: 'Inter', sans-serif !important;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
  background: #0f172a !important;
  border-right: 1px solid #1e293b !important;
}
[data-testid="stSidebar"] * {
  color: #cbd5e1 !important;
}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] strong {
  color: #f1f5f9 !important;
}
[data-testid="stSidebar"] .stTextInput input {
  background: #1e293b !important;
  border: 1px solid #334155 !important;
  color: #e2e8f0 !important;
  border-radius: 8px !important;
}
[data-testid="stSidebar"] [data-testid="stSelectbox"] > div > div {
  background: #1e293b !important;
  border: 1px solid #334155 !important;
  color: #e2e8f0 !important;
  border-radius: 8px !important;
}
[data-testid="stSidebar"] [data-testid="stButton"] button {
  background: #1e293b !important;
  border: 1px solid #334155 !important;
  color: #cbd5e1 !important;
  border-radius: 8px !important;
  font-size: 0.82rem !important;
  text-align: left !important;
  transition: all 0.2s ease !important;
}
[data-testid="stSidebar"] [data-testid="stButton"] button:hover {
  background: #c8102e !important;
  border-color: #c8102e !important;
  color: white !important;
  transform: translateX(3px) !important;
}
[data-testid="stSidebar"] hr {
  border-color: #334155 !important;
}
[data-testid="stSidebar"] [data-baseweb="notification"] {
  background: #1e293b !important;
  border-color: #334155 !important;
}

/* ── Main area ── */
.main .block-container {
  padding-top: 2rem !important;
  padding-bottom: 3rem !important;
}

/* ── Headings ── */
h1 { font-size: 1.9rem !important; font-weight: 700 !important; color: #0f172a !important; letter-spacing: -0.02em !important; }
h2 { font-size: 1.35rem !important; font-weight: 600 !important; color: #0f172a !important; }
h3 { font-size: 1.1rem !important; font-weight: 600 !important; color: #1e293b !important; }

/* ── Primary buttons ── */
[data-testid="stBaseButton-primary"] button,
[data-testid="stButton"] button[kind="primary"] {
  background: linear-gradient(135deg, #c8102e 0%, #e8293e 100%) !important;
  border: none !important;
  color: white !important;
  border-radius: 10px !important;
  font-weight: 600 !important;
  box-shadow: 0 2px 8px rgba(200,16,46,0.35) !important;
  transition: all 0.2s ease !important;
}
[data-testid="stBaseButton-primary"] button:hover,
[data-testid="stButton"] button[kind="primary"]:hover {
  box-shadow: 0 4px 16px rgba(200,16,46,0.45) !important;
  transform: translateY(-1px) !important;
}

/* ── Secondary / default buttons ── */
[data-testid="stBaseButton-secondary"] button,
[data-testid="stButton"] button:not([kind="primary"]) {
  border-radius: 10px !important;
  font-weight: 500 !important;
  transition: all 0.2s ease !important;
  border-color: #e2e8f0 !important;
  color: #475569 !important;
}
[data-testid="stBaseButton-secondary"] button:hover,
[data-testid="stButton"] button:not([kind="primary"]):hover {
  border-color: #c8102e !important;
  color: #c8102e !important;
}

/* ── Metric tiles ── */
[data-testid="stMetric"] {
  background: white !important;
  border-radius: 12px !important;
  padding: 1rem 1.25rem !important;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04) !important;
  border: 1px solid #e2e8f0 !important;
}
[data-testid="stMetric"] label {
  font-size: 0.72rem !important;
  font-weight: 600 !important;
  text-transform: uppercase !important;
  letter-spacing: 0.06em !important;
  color: #64748b !important;
}
[data-testid="stMetricValue"] {
  font-size: 1.8rem !important;
  font-weight: 700 !important;
  color: #0f172a !important;
}

/* ── Containers with border ── */
[data-testid="stVerticalBlockBorderWrapper"] {
  border-radius: 12px !important;
  border: 1px solid #e2e8f0 !important;
  background: white !important;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04) !important;
  transition: box-shadow 0.2s ease !important;
}
[data-testid="stVerticalBlockBorderWrapper"]:hover {
  box-shadow: 0 4px 16px rgba(0,0,0,0.08) !important;
}

/* ── Alerts ── */
[data-testid="stAlert"] {
  border-radius: 10px !important;
}

/* ── Expanders ── */
[data-testid="stExpander"] {
  border-radius: 10px !important;
  border: 1px solid #e2e8f0 !important;
  background: white !important;
}
[data-testid="stExpander"] summary {
  font-weight: 500 !important;
  color: #475569 !important;
}

/* ── Dividers ── */
hr { border-color: #e2e8f0 !important; margin: 1rem 0 !important; }

/* ── Tabs ── */
[data-testid="stTabs"] [data-baseweb="tab"] {
  border-radius: 8px 8px 0 0 !important;
  font-weight: 500 !important;
}

/* ── Bar chart ── */
[data-testid="stArrowVegaLiteChart"] {
  border-radius: 12px !important;
  overflow: hidden !important;
}

/* ── Dataframes ── */
[data-testid="stDataFrame"] {
  border-radius: 10px !important;
  overflow: hidden !important;
}

/* ── Custom card components ── */
.s-kpi-card {
  background: white;
  border-radius: 14px;
  padding: 1.25rem 1.5rem;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
  border: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  height: 100%;
}
.s-kpi-card .s-label {
  font-size: 0.68rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: #64748b;
}
.s-kpi-card .s-value {
  font-size: 2.2rem;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.1;
}
.s-kpi-card .s-sub {
  font-size: 0.75rem;
  color: #94a3b8;
  margin-top: 0.1rem;
}

.s-meeting-card {
  background: white;
  border-radius: 12px;
  padding: 0.85rem 1.1rem;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  border: 1px solid #e2e8f0;
  margin-bottom: 0.6rem;
  display: flex;
  align-items: flex-start;
  gap: 1rem;
  transition: box-shadow 0.2s ease, border-color 0.2s ease;
}
.s-meeting-card:hover {
  box-shadow: 0 4px 14px rgba(0,0,0,0.09);
  border-color: #cbd5e1;
}
.s-meeting-card .s-date-col {
  min-width: 76px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding-top: 2px;
}
.s-meeting-card .s-date {
  font-size: 0.8rem;
  font-weight: 700;
  color: #0f172a;
  white-space: nowrap;
}
.s-meeting-card .s-meta { flex: 1; min-width: 0; }
.s-meeting-card .s-supplier {
  font-weight: 600;
  color: #0f172a;
  font-size: 0.92rem;
}
.s-meeting-card .s-notes {
  font-size: 0.78rem;
  color: #64748b;
  font-style: italic;
  margin-top: 1px;
}
.s-meeting-card .s-tag {
  font-size: 0.73rem;
  color: #94a3b8;
  margin-top: 3px;
}

.s-badge {
  display: inline-block;
  border-radius: 99px;
  padding: 0.18em 0.65em;
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  white-space: nowrap;
}
.s-badge-red    { background: #fee2e2; color: #c8102e; }
.s-badge-amber  { background: #fef3c7; color: #92400e; }
.s-badge-green  { background: #dcfce7; color: #166534; }
.s-badge-blue   { background: #dbeafe; color: #1d4ed8; }
.s-badge-gray   { background: #f1f5f9; color: #64748b; }
.s-badge-today  { background: #c8102e; color: white; }

.s-health-row {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.55rem 0;
  border-bottom: 1px solid #f1f5f9;
}
.s-health-row:last-child { border-bottom: none; }
.s-health-row .s-name { font-weight: 600; color: #0f172a; font-size: 0.87rem; }
.s-health-row .s-contract { font-size: 0.72rem; color: #64748b; margin-top: 1px; }
.s-health-row .s-info { flex: 1; min-width: 0; }
.s-health-row .s-since { font-size: 0.72rem; color: #94a3b8; text-align: right; white-space: nowrap; }
.s-dot { width: 9px; height: 9px; border-radius: 50%; flex-shrink: 0; }
.s-dot-green  { background: #16a34a; }
.s-dot-amber  { background: #ca8a04; }
.s-dot-red    { background: #c8102e; }
.s-dot-gray   { background: #94a3b8; }

.s-disc-card {
  background: white;
  border-radius: 12px;
  padding: 1rem 1.1rem;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  border: 1px solid #e2e8f0;
  margin-bottom: 0.6rem;
  transition: box-shadow 0.2s ease;
}
.s-disc-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.08); }
.s-disc-card .s-supplier { font-weight: 700; color: #0f172a; font-size: 0.88rem; }
.s-disc-card .s-sender { font-size: 0.75rem; color: #64748b; margin-top: 1px; }
.s-disc-card .s-subject {
  font-size: 0.8rem; color: #334155; margin-top: 0.4rem;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.s-disc-card .s-preview {
  font-size: 0.75rem; color: #94a3b8; margin-top: 0.35rem;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
  overflow: hidden;
}

.s-section-label {
  font-size: 0.68rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.09em;
  color: #94a3b8;
  margin: 0 0 0.6rem 0;
  padding: 0;
}

/* ── Markdown content containers: prevent heading bleed and overflow ── */
[data-testid="stMarkdownContainer"] {
  overflow-wrap: break-word !important;
  word-break: break-word !important;
  overflow: hidden !important;
}
[data-testid="stMarkdownContainer"] h1 {
  font-size: 1.05rem !important;
  font-weight: 700 !important;
  letter-spacing: 0 !important;
  text-transform: none !important;
  margin: 0.6rem 0 0.3rem !important;
}
[data-testid="stMarkdownContainer"] h2 {
  font-size: 0.92rem !important;
  font-weight: 700 !important;
  letter-spacing: 0 !important;
  text-transform: none !important;
  margin: 0.5rem 0 0.25rem !important;
}
[data-testid="stMarkdownContainer"] h3,
[data-testid="stMarkdownContainer"] h4 {
  font-size: 0.85rem !important;
  font-weight: 600 !important;
  letter-spacing: 0 !important;
  text-transform: none !important;
  margin: 0.4rem 0 0.2rem !important;
}
[data-testid="stMarkdownContainer"] p {
  font-size: 0.88rem !important;
  line-height: 1.6 !important;
  margin: 0.2rem 0 !important;
}
[data-testid="stMarkdownContainer"] ul,
[data-testid="stMarkdownContainer"] ol {
  font-size: 0.88rem !important;
  padding-left: 1.2rem !important;
  margin: 0.2rem 0 !important;
}
[data-testid="stMarkdownContainer"] li {
  margin-bottom: 0.15rem !important;
  line-height: 1.5 !important;
}

.s-dir-card {
  background: white;
  border-radius: 14px;
  padding: 1.1rem 1.25rem 0.85rem;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
  border: 1px solid #e2e8f0;
  transition: box-shadow 0.2s ease, border-color 0.2s ease;
  margin-bottom: 0.5rem;
}
.s-dir-card:hover {
  box-shadow: 0 6px 20px rgba(0,0,0,0.1);
  border-color: #cbd5e1;
}
.s-dir-card .s-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 0.6rem;
}
.s-dir-card .s-name { font-weight: 700; color: #0f172a; font-size: 0.97rem; }
.s-dir-card .s-geo { font-size: 0.75rem; color: #64748b; margin-top: 2px; }
.s-dir-card .s-row {
  font-size: 0.77rem; color: #475569;
  margin-top: 0.3rem;
  display: flex; align-items: center; gap: 0.3rem;
}
</style>
"""

# ── Component builders ─────────────────────────────────────────────────────────


def badge(text: str, variant: str = "gray") -> str:
    return f'<span class="s-badge s-badge-{variant}">{text}</span>'


def section_label(text: str) -> str:
    return f'<p class="s-section-label">{text}</p>'


def kpi_card(value: str, label: str, sub: str = "") -> str:
    sub_html = f'<div class="s-sub">{sub}</div>' if sub else ""
    return (
        f'<div class="s-kpi-card">'
        f'<div class="s-label">{label}</div>'
        f'<div class="s-value">{value}</div>'
        f'{sub_html}'
        f'</div>'
    )


def meeting_card(
    date_str: str,
    supplier: str,
    days_until: int,
    notes: str,
    geography: str,
    category: str,
) -> str:
    if days_until == 0:
        b = badge("Today", "today")
    elif days_until <= 3:
        b = badge(f"In {days_until}d", "red")
    elif days_until <= 7:
        b = badge(f"In {days_until}d", "amber")
    else:
        b = badge(f"In {days_until}d", "gray")

    notes_html = f'<div class="s-notes">{notes}</div>' if notes else ""
    return (
        f'<div class="s-meeting-card">'
        f'  <div class="s-date-col"><div class="s-date">{date_str}</div>{b}</div>'
        f'  <div class="s-meta">'
        f'    <div class="s-supplier">{supplier}</div>'
        f'    {notes_html}'
        f'    <div class="s-tag">📍 {geography} &nbsp;·&nbsp; {category.title()}</div>'
        f'  </div>'
        f'</div>'
    )


def health_row(
    name: str,
    health_label: str,
    days_since: Optional[int],
) -> str:
    dot_cls = {
        "Healthy": "s-dot-green",
        "Stable": "s-dot-amber",
        "At risk": "s-dot-red",
    }.get(health_label, "s-dot-gray")
    since_str = f"{days_since}d ago" if days_since is not None else "No emails"
    return (
        f'<div class="s-health-row">'
        f'  <div class="s-dot {dot_cls}"></div>'
        f'  <div class="s-info">'
        f'    <div class="s-name">{name}</div>'
        f'  </div>'
        f'  <div class="s-since">{since_str}</div>'
        f'</div>'
    )


def discussion_card(
    supplier: str,
    sender: str,
    date_str: str,
    days_ago: Optional[int],
    subject: str,
    preview: str,
) -> str:
    days_str = f"· {days_ago}d ago" if days_ago is not None else ""
    # Escape angle brackets in preview to avoid HTML injection
    safe_preview = preview.replace("<", "&lt;").replace(">", "&gt;")
    safe_subject = subject.replace("<", "&lt;").replace(">", "&gt;")
    return (
        f'<div class="s-disc-card">'
        f'  <div class="s-supplier">{supplier}</div>'
        f'  <div class="s-sender">{sender} &nbsp;·&nbsp; {date_str} {days_str}</div>'
        f'  <div class="s-subject">📧 {safe_subject}</div>'
        f'  <div class="s-preview">{safe_preview}</div>'
        f'</div>'
    )


def supplier_dir_card_html(
    name: str,
    geography: str,
    category: str,
    contract_badge_str: str,
    health_label: str,
    email_count: int,
    last_contact: str,
    renewal: str,
    next_meeting: str,
) -> str:
    dot_cls = {
        "Healthy": "s-dot-green",
        "Stable": "s-dot-amber",
        "At risk": "s-dot-red",
    }.get(health_label, "s-dot-gray")
    health_b = {
        "Healthy": badge(health_label, "green"),
        "Stable": badge(health_label, "amber"),
        "At risk": badge(health_label, "red"),
    }.get(health_label, badge(health_label, "gray"))

    renewal_row = (
        f'<div class="s-row">🔄 {renewal}</div>' if renewal else ""
    )
    return (
        f'<div class="s-dir-card">'
        f'  <div class="s-top">'
        f'    <div>'
        f'      <div class="s-name">{name}</div>'
        f'      <div class="s-geo">📍 {geography} &nbsp;·&nbsp; {category.title()}</div>'
        f'    </div>'
        f'    <div style="display:flex;flex-direction:column;align-items:flex-end;gap:5px">'
        f'      <div class="s-dot {dot_cls}" style="width:11px;height:11px"></div>'
        f'      {health_b}'
        f'    </div>'
        f'  </div>'
        f'  <div class="s-row">{contract_badge_str} &nbsp;·&nbsp; {email_count} emails &nbsp;·&nbsp; Last: {last_contact}</div>'
        f'  {renewal_row}'
        f'  <div class="s-row">📅 {next_meeting}</div>'
        f'</div>'
    )
