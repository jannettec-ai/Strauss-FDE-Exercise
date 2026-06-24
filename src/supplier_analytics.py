"""
supplier_analytics.py

Local analytics — relationship health metrics computed directly from email
and contract files. No Claude API calls. Used by the Home dashboard and
Supplier Directory pages so browsing is fast and free.
"""

import json
import re
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).parent.parent
EMAILS_DIR = ROOT / "data" / "emails"
CONTRACTS_DIR = ROOT / "data" / "contracts"
STRAUSS_EMAIL = "david.cohen@strauss-group.com"

SUPPLIERS = {
    "01": ("Ivoire Cacao Export",             "cocoa",     "Côte d'Ivoire"),
    "02": ("Golden Coast Cocoa Traders",      "cocoa",     "Ghana"),
    "03": ("Lowlands Dairy Co-op",            "dairy",     "Netherlands"),
    "04": ("Galil Dairy Suppliers",           "dairy",     "Israel"),
    "05": ("Cana Doce Açúcar",                "sugar",     "Brazil"),
    "06": ("Siam Sugar Partners",             "sugar",     "Thailand"),
    "07": ("Sierra Verde Coffee Cooperative", "coffee",    "Colombia"),
    "08": ("EuroPack Solutions",              "packaging", "Poland"),
}


def load_emails(supplier_num: str) -> list[dict]:
    matches = list(EMAILS_DIR.glob(f"supplier_{supplier_num}_*.json"))
    if not matches:
        return []
    with open(matches[0], encoding="utf-8") as f:
        emails = json.load(f)
    return sorted(emails, key=lambda e: e["date"])


def email_frequency_by_month(emails: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for e in emails:
        counts[e["date"][:7]] += 1
    return dict(sorted(counts.items()))


def compute_response_trend(emails: list[dict]) -> dict:
    """Avg response time in first half of email history vs second half."""
    pairs: list[tuple[int, datetime]] = []
    pending: Optional[datetime] = None
    for e in emails:
        sent = datetime.strptime(e["date"], "%Y-%m-%d")
        if e["from"] == STRAUSS_EMAIL:
            pending = sent
        elif pending is not None:
            pairs.append(((sent - pending).days, sent))
            pending = None

    if len(pairs) < 2:
        return {"early_avg": None, "recent_avg": None, "direction": "stable"}

    mid = len(pairs) // 2
    early = [d for d, _ in pairs[:mid]]
    recent = [d for d, _ in pairs[mid:]]
    early_avg = round(sum(early) / len(early), 1)
    recent_avg = round(sum(recent) / len(recent), 1)

    if early_avg == 0:
        direction = "stable"
    elif recent_avg > early_avg * 1.25:
        direction = "slower"
    elif recent_avg < early_avg * 0.75:
        direction = "faster"
    else:
        direction = "stable"

    return {"early_avg": early_avg, "recent_avg": recent_avg, "direction": direction}


def compute_volume_trend(emails: list[dict]) -> dict:
    """Compare email volume: recent 3 months vs prior 3 months."""
    today = date.today()
    recent_floor = today - timedelta(days=91)
    prior_floor = today - timedelta(days=182)

    recent_count = sum(
        1 for e in emails
        if datetime.strptime(e["date"], "%Y-%m-%d").date() >= recent_floor
    )
    prior_count = sum(
        1 for e in emails
        if prior_floor <= datetime.strptime(e["date"], "%Y-%m-%d").date() < recent_floor
    )

    if prior_count == 0:
        direction = "stable"
    elif recent_count > prior_count * 1.2:
        direction = "increasing"
    elif recent_count < prior_count * 0.8:
        direction = "decreasing"
    else:
        direction = "stable"

    return {"recent_3mo": recent_count, "prior_3mo": prior_count, "direction": direction}


def days_since_last_contact(emails: list[dict]) -> Optional[int]:
    if not emails:
        return None
    last = datetime.strptime(emails[-1]["date"], "%Y-%m-%d").date()
    return (date.today() - last).days


def parse_contract_quick(supplier_num: str) -> dict:
    """Parse contract markdown files locally — no API. Returns status, ID, renewal date."""
    contracts = sorted(
        c for c in CONTRACTS_DIR.glob(f"supplier_{supplier_num}_*.md")
        if "GENERATION_SPEC" not in c.name
    )
    if not contracts:
        return {"status": "unknown", "contract_id": "—", "renewal_date": None}

    upper_names = [c.name.upper() for c in contracts]
    has_renewed = any("RENEWED" in n for n in upper_names)
    has_draft   = any("DRAFT"   in n for n in upper_names)
    has_old     = any("OLD"     in n for n in upper_names)
    has_plain   = any(
        "DRAFT" not in n and "OLD" not in n and "RENEWED" not in n
        for n in upper_names
    )

    if has_renewed:
        status = "active"
        use_file = next(c for c in contracts if "RENEWED" in c.name.upper())
    elif has_plain:
        status = "active"
        use_file = next(
            c for c in contracts
            if "DRAFT" not in c.name.upper()
            and "OLD" not in c.name.upper()
        )
    elif has_draft:
        status = "draft"
        use_file = next(c for c in contracts if "DRAFT" in c.name.upper())
    else:
        status = "expired"
        use_file = contracts[-1]

    content = use_file.read_text(encoding="utf-8")

    m = re.search(r"\*\*Contract ID:\*\*\s*(.+)", content)
    contract_id = m.group(1).strip() if m else "—"

    m = re.search(r"\*\*Renewal Date:\*\*\s*(\d{4}-\d{2}-\d{2})", content)
    renewal_date = m.group(1) if m else None

    if renewal_date and status == "active":
        if datetime.strptime(renewal_date, "%Y-%m-%d").date() < date.today():
            status = "expired"

    return {"status": status, "contract_id": contract_id, "renewal_date": renewal_date}


_CONTRACT_SCORE = {
    "active": 2,
    "draft": 1,
    "expired": 0,
    "no_active_contract": 0,
    "unknown": 1,
}

_RELATIONSHIP_SCORE = {"Healthy": 2, "Stable": 1, "At risk": 0}


def combined_health(relationship_label: str, contract_status: str) -> tuple[str, str]:
    """Average relationship and contract scores into a single signal."""
    avg = (_RELATIONSHIP_SCORE.get(relationship_label, 1) + _CONTRACT_SCORE.get(contract_status, 1)) / 2
    if avg >= 1.5:
        return "Healthy", "green"
    elif avg >= 0.75:
        return "Stable", "orange"
    else:
        return "At risk", "red"


def relationship_health(
    resp_trend: dict,
    vol_trend: dict,
    days_since: Optional[int],
) -> tuple[str, str]:
    """
    Composite health label from response speed trend, volume trend, and
    recency of contact. Returns (label, css_color_name).
    """
    score = 0
    if resp_trend["direction"] == "faster":
        score += 1
    elif resp_trend["direction"] == "slower":
        score -= 1
    if vol_trend["direction"] == "increasing":
        score += 1
    elif vol_trend["direction"] == "decreasing":
        score -= 1
    if days_since is not None and days_since > 60:
        score -= 1

    if score >= 1:
        return "Healthy", "green"
    elif score == 0:
        return "Stable", "orange"
    else:
        return "At risk", "red"


def get_supplier_summary(supplier_num: str) -> dict:
    name, category, geography = SUPPLIERS[supplier_num]
    emails = load_emails(supplier_num)
    contract = parse_contract_quick(supplier_num)
    resp_trend = compute_response_trend(emails)
    vol_trend = compute_volume_trend(emails)
    days_since = days_since_last_contact(emails)
    health_label, health_color = relationship_health(resp_trend, vol_trend, days_since)
    combined_label, combined_color = combined_health(health_label, contract["status"])

    return {
        "supplier_num": supplier_num,
        "supplier_name": name,
        "category": category,
        "geography": geography,
        "email_count": len(emails),
        "contract": contract,
        "response_trend": resp_trend,
        "volume_trend": vol_trend,
        "email_by_month": email_frequency_by_month(emails),
        "days_since_last_contact": days_since,
        "health_label": health_label,
        "health_color": health_color,
        "combined_health_label": combined_label,
        "combined_health_color": combined_color,
        "last_email": emails[-1] if emails else None,
        "first_email_date": emails[0]["date"] if emails else None,
        "last_email_date": emails[-1]["date"] if emails else None,
    }


def get_all_summaries() -> list[dict]:
    return [get_supplier_summary(num) for num in sorted(SUPPLIERS.keys())]
