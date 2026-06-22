"""
packet_generator.py

Assembles the negotiation prep packet for a single upcoming supplier meeting.

Flow:
  1. Load the negotiation calendar (data/calendar.csv)
  2. Look up the meeting by ID
  3. Resolve supplier number from supplier name
  4. Call extraction.run_extraction() to get Claude-extracted facts + KPIs
  5. Load and enrich the commodity benchmark (data/prices/)
  6. Return a single packet dict that app.py renders directly

The packet dict is the contract between this module and app.py.
All display formatting happens in app.py; this module returns raw values.
"""

import csv
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

from extraction import SUPPLIERS, run_extraction

# ── Paths ────────────────────────────────────────────────────────────────────

ROOT = Path(__file__).parent.parent
CALENDAR_PATH = ROOT / "data" / "calendar.csv"
PRICES_DIR = ROOT / "data" / "prices"

# ── Supplier name → number reverse lookup ────────────────────────────────────

NAME_TO_NUM: dict[str, str] = {name: num for num, (name, _) in SUPPLIERS.items()}

# ── Benchmark metadata ────────────────────────────────────────────────────────

# Units match the Yahoo Finance tickers used in pull_prices.py:
#   CC=F  → USD per metric ton
#   SB=F  → US cents per pound
#   DC=F  → USD per hundredweight (cwt)
BENCHMARK_META = {
    "cocoa": {
        "unit": "USD/MT",
        "unit_label": "USD per metric ton",
        "source": "ICE Cocoa Futures (CC=F) via Yahoo Finance",
    },
    "sugar": {
        "unit": "¢/lb",
        "unit_label": "US cents per pound (ICE No.11)",
        "source": "ICE Sugar No.11 Futures (SB=F) via Yahoo Finance",
    },
    "dairy": {
        "unit": "USD/cwt",
        "unit_label": "USD per hundredweight (CME Class III Milk)",
        "source": "CME Class III Milk Futures (DC=F) via Yahoo Finance",
        "note": (
            "CME dairy futures are thinly traded and the series may be "
            "incomplete. Treat as directional indicator only, not a "
            "precise benchmark for direct negotiation use."
        ),
    },
}

# ── Calendar loading ──────────────────────────────────────────────────────────

def load_calendar() -> list[dict]:
    """Return all rows from calendar.csv as a list of dicts."""
    with open(CALENDAR_PATH, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def get_upcoming_meetings(reference_date: Optional[date] = None) -> list[dict]:
    """
    Return meetings on or after reference_date (defaults to today),
    sorted chronologically. Each entry has days_until added.
    """
    ref = reference_date or date.today()
    upcoming = []
    for row in load_calendar():
        meeting_date = datetime.strptime(row["date"], "%Y-%m-%d").date()
        if meeting_date >= ref:
            upcoming.append({
                **row,
                "meeting_id": int(row["meeting_id"]),
                "meeting_date": meeting_date,
                "days_until": (meeting_date - ref).days,
            })
    return sorted(upcoming, key=lambda r: r["meeting_date"])


def get_meeting_by_id(meeting_id: int) -> dict:
    """Look up a single meeting by ID. Raises ValueError if not found."""
    for row in load_calendar():
        if int(row["meeting_id"]) == meeting_id:
            meeting_date = datetime.strptime(row["date"], "%Y-%m-%d").date()
            return {
                **row,
                "meeting_id": meeting_id,
                "meeting_date": meeting_date,
                "days_until": (meeting_date - date.today()).days,
            }
    raise ValueError(f"No meeting found with ID {meeting_id}")


# ── Commodity benchmark ───────────────────────────────────────────────────────

def load_benchmark(category: str) -> Optional[dict]:
    """
    Load the price CSV for a commodity category and compute:
      - current price (most recent row)
      - price 26 weeks ago (~6 months)
      - 6-month percentage change

    Returns None for categories with no price data (coffee, packaging).
    """
    if category not in BENCHMARK_META:
        return None

    fp = PRICES_DIR / f"{category}_24mo.csv"
    if not fp.exists():
        return None

    rows = []
    with open(fp, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            try:
                rows.append({
                    "date": datetime.strptime(row["date"], "%Y-%m-%d").date(),
                    "price": float(row["price"]),
                })
            except (ValueError, KeyError):
                continue

    if not rows:
        return None

    rows.sort(key=lambda r: r["date"])
    current = rows[-1]

    # Find the row closest to 26 weeks (182 days) ago
    target_past = current["date"] - timedelta(weeks=26)
    past_row = min(rows, key=lambda r: abs((r["date"] - target_past).days))

    six_month_change_pct = None
    if past_row["price"] and past_row["date"] != current["date"]:
        six_month_change_pct = round(
            (current["price"] - past_row["price"]) / past_row["price"] * 100, 1
        )

    meta = BENCHMARK_META[category]
    result = {
        "current_price": round(current["price"], 2),
        "current_date": current["date"].isoformat(),
        "six_month_ago_price": round(past_row["price"], 2),
        "six_month_ago_date": past_row["date"].isoformat(),
        "six_month_change_pct": six_month_change_pct,
        "unit": meta["unit"],
        "unit_label": meta["unit_label"],
        "source": meta["source"],
    }
    if "note" in meta:
        result["note"] = meta["note"]
    return result


# ── Packet assembly ───────────────────────────────────────────────────────────

def run_packet(meeting_id: int) -> dict:
    """
    Generate the full negotiation prep packet for a given meeting ID.

    Calls extraction.run_extraction() which makes one Claude API call,
    then enriches with benchmark data and meeting context.

    Args:
        meeting_id: Integer ID from calendar.csv.

    Returns:
        Packet dict consumed directly by app.py. All values are plain
        Python types (str, int, float, list, dict, None) — no objects.
    """
    meeting = get_meeting_by_id(meeting_id)
    supplier_name = meeting["supplier"]

    supplier_num = NAME_TO_NUM.get(supplier_name)
    if supplier_num is None:
        raise ValueError(
            f"Supplier '{supplier_name}' from calendar not found in SUPPLIERS map. "
            f"Known suppliers: {list(NAME_TO_NUM.keys())}"
        )

    # Run Claude extraction (the heavy step)
    extraction = run_extraction(supplier_num)

    # Benchmark enrichment
    category = extraction.get("category", "other")
    benchmark = load_benchmark(category)

    return {
        # ── Meeting context ──────────────────────────────────────────────
        "meeting_id": meeting_id,
        "meeting_date": meeting["date"],           # string YYYY-MM-DD
        "days_until_meeting": meeting["days_until"],
        "meeting_notes": meeting.get("notes", ""),
        "geography": meeting.get("geography", ""),

        # ── Supplier identity ────────────────────────────────────────────
        "supplier_num": supplier_num,
        "supplier_name": supplier_name,
        "category": category,
        "email_count": extraction["email_count"],

        # ── KPIs (metrics.md §1–4) ───────────────────────────────────────
        "avg_response_days": extraction.get("avg_response_days"),
        "open_issues_count": extraction.get("open_issues_count", 0),
        "price_delta": extraction.get("price_delta"),
        "days_to_renewal": extraction.get("days_to_renewal"),

        # ── Claude-extracted content ─────────────────────────────────────
        "email_summary": extraction.get("email_summary", ""),
        "latest_price_quoted": extraction.get("latest_price_quoted", {}),
        "contract_terms": extraction.get("contract_terms", {}),
        "open_issues": extraction.get("open_issues", []),
        "commodity_benchmark": extraction.get("commodity_benchmark", ""),
        "heads_up": extraction.get("heads_up", ""),

        # ── Benchmark (from CSV) ─────────────────────────────────────────
        "benchmark": benchmark,

        # ── Meta ─────────────────────────────────────────────────────────
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }


# ── CLI smoke-test ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) > 1:
        mid = int(sys.argv[1])
    else:
        # Default: next upcoming meeting
        upcoming = get_upcoming_meetings()
        if not upcoming:
            print("No upcoming meetings in calendar.")
            sys.exit(0)
        mid = upcoming[0]["meeting_id"]
        print(f"No meeting ID given — using next upcoming: meeting {mid} "
              f"({upcoming[0]['supplier']}, {upcoming[0]['date']})")

    print(f"\nGenerating packet for meeting {mid}…\n")
    packet = run_packet(mid)
    print(json.dumps(packet, indent=2, ensure_ascii=False, default=str))
