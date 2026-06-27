"""
extraction.py

Single-supplier extraction pass. Given a supplier number, loads that
supplier's emails, contract(s), and commodity price data (if in scope),
runs one Claude API call to extract structured facts, then computes the
local KPIs (response time, price delta, days to renewal) per metrics.md.

Returns a dict ready for packet_generator.py to consume.
"""

import json
import re
from datetime import date, datetime
from pathlib import Path

import anthropic

# ── Paths ────────────────────────────────────────────────────────────────────

ROOT = Path(__file__).parent.parent
EMAILS_DIR = ROOT / "data" / "emails"
CONTRACTS_DIR = ROOT / "data" / "contracts"
PRICES_DIR = ROOT / "data" / "prices"

# ── Supplier metadata ────────────────────────────────────────────────────────

# Maps supplier number → (display name, commodity category for price lookup)
# Category is None for coffee and packaging — no benchmark in scope per CLAUDE.md
SUPPLIERS = {
    "01": ("Ivoire Cacao Export",           "cocoa"),
    "02": ("Golden Coast Cocoa Traders",    "cocoa"),
    "03": ("Lowlands Dairy Co-op",          "dairy"),
    "04": ("Galil Dairy Suppliers",         "dairy"),
    "05": ("Cana Doce Açúcar",              "sugar"),
    "06": ("Siam Sugar Partners",           "sugar"),
    "07": ("Sierra Verde Coffee Cooperative", None),
    "08": ("EuroPack Solutions",            None),
}

STRAUSS_EMAIL = "david.cohen@strauss-group.com"

# ── Data loaders ─────────────────────────────────────────────────────────────

def load_emails(supplier_num: str) -> list[dict]:
    matches = list(EMAILS_DIR.glob(f"supplier_{supplier_num}_*.json"))
    if not matches:
        raise FileNotFoundError(f"No email file for supplier {supplier_num}")
    with open(matches[0], encoding="utf-8") as f:
        emails = json.load(f)
    return sorted(emails, key=lambda e: e["date"])


def load_contracts(supplier_num: str) -> dict[str, str]:
    """Returns {filename: content} for all contract files for this supplier."""
    matches = sorted(CONTRACTS_DIR.glob(f"supplier_{supplier_num}_*.md"))
    if not matches:
        raise FileNotFoundError(f"No contract file for supplier {supplier_num}")
    return {fp.name: fp.read_text(encoding="utf-8") for fp in matches}


def load_price_data(category: str | None) -> str | None:
    """Returns last 13 rows of the price CSV (header + 12 months), or None."""
    if category is None:
        return None
    fp = PRICES_DIR / f"{category}_24mo.csv"
    if not fp.exists():
        return None
    lines = fp.read_text(encoding="utf-8").strip().splitlines()
    # header + most recent 12 data rows
    recent = [lines[0]] + lines[-12:]
    return "\n".join(recent)


# ── KPI: Supplier Response Time (metrics.md §1) ───────────────────────────

def compute_response_time(emails: list[dict]) -> float | None:
    """
    Average calendar days between each Strauss outbound email and the first
    supplier reply. Unanswered outbounds are excluded from the mean.
    Matches the formula in .claude/rules/metrics.md §1 exactly.
    """
    gaps = []
    pending_outbound: datetime | None = None

    for email in emails:  # already sorted by date
        sent = datetime.strptime(email["date"], "%Y-%m-%d")
        if email["from"] == STRAUSS_EMAIL:
            pending_outbound = sent
        elif pending_outbound is not None:
            # first inbound after an outbound
            gaps.append((sent - pending_outbound).days)
            pending_outbound = None  # reset; only first reply counts

    if not gaps:
        return None
    return round(sum(gaps) / len(gaps), 1)


# ── KPI: Price vs. Contract Delta (metrics.md §3) ────────────────────────

def compute_price_delta(
    latest_price_quoted: dict, contract_terms: dict
) -> dict | None:
    """
    Computes absolute and percentage delta between latest email quote and
    contract base price. Returns None if either value is missing or ambiguous.
    Matches metrics.md §3 formula exactly.
    """
    raw_quote = latest_price_quoted.get("value")
    raw_contract = contract_terms.get("contract_base_price_numeric")

    if raw_quote is None or raw_contract is None:
        return None

    delta_abs = round(raw_quote - raw_contract, 2)
    delta_pct = round((delta_abs / raw_contract) * 100, 1)
    return {"absolute": delta_abs, "pct": delta_pct}


# ── KPI: Days to Renewal (metrics.md §4) ─────────────────────────────────

def compute_days_to_renewal(renewal_date_str: str | None) -> int | None:
    """Days from today to contract renewal date. Negative means overdue."""
    if not renewal_date_str:
        return None
    try:
        renewal = datetime.strptime(renewal_date_str, "%Y-%m-%d").date()
        return (renewal - date.today()).days
    except ValueError:
        return None


# ── Claude extraction call ────────────────────────────────────────────────

def _build_prompt(
    supplier_num: str,
    supplier_name: str,
    emails: list[dict],
    contracts: dict[str, str],
    price_data: str | None,
) -> str:
    email_block = "\n\n".join(
        f"[{e['date']}] FROM: {e['from']}  TO: {e['to']}\n"
        f"SUBJECT: {e['subject']}\n{e['body']}"
        for e in emails
    )

    contract_block = "\n\n---\n\n".join(
        f"FILE: {name}\n\n{content}" for name, content in contracts.items()
    )

    price_block = (
        f"\n\n## COMMODITY PRICE DATA (last 12 months)\n{price_data}"
        if price_data
        else ""
    )

    return f"""You are a procurement analyst assistant extracting structured facts from supplier data.

Supplier: {supplier_num} — {supplier_name}

## EMAILS (chronological)
{email_block}

## CONTRACT FILE(S)
{contract_block}{price_block}

---

Return a single JSON object with exactly these fields. No markdown fences.

{{
  "email_summary": "<2-4 sentences: what was ordered, what happened, what is unresolved>",

  "latest_price_quoted": {{
    "value": <number, the numeric price value, or null if none quoted or unit is ambiguous>,
    "unit": "<e.g. '$/ton' or '₪/kg' or 'PLN/unit', or null>",
    "display": "<human-readable string e.g. '$3,050/ton', or 'ambiguous — see open issues', or null>",
    "date": "<YYYY-MM-DD of most recent price quote email, or null>",
    "quoted_by": "<full name of person who quoted it, or null>"
  }},

  "contract_terms": {{
    "contract_id": "<string, use most recent active contract ID>",
    "status": "<one of: active | expired | draft | no_active_contract>",
    "renewal_date": "<YYYY-MM-DD, or null>",
    "auto_renewal": <true | false>,
    "notice_period_days": <integer days or null>,
    "payment_terms": "<string>",
    "volume_min": "<string e.g. '35 tons/quarter'>",
    "volume_max": "<string>",
    "contract_base_price": "<display string e.g. '$2,650/ton'>",
    "contract_base_price_numeric": <numeric value only, e.g. 2650, or null if not a simple number>,
    "key_penalty": "<single most important penalty clause, one sentence>"
  }},

  "open_issues": [
    {{
      "issue_type": "<one of: price_discrepancy | delivery_dispute | quality_dispute | contract_renegotiation | renewal_date_discrepancy | spec_change_dispute | no_active_contract | unanswered_thread>",
      "description": "<plain English, 1-2 sentences, specific to this supplier>",
      "source_ref": "<e.g. 'email 2026-03-07 from Yael Shapira' or 'contract Section 4.2'>",
      "status": "open"
    }}
  ],

  "commodity_benchmark": "<one sentence on where the commodity price sits relative to the contract price, or 'No benchmark in scope for this category' if coffee/packaging>",

  "heads_up": "<1-2 sentences: the single most important thing to know before the next meeting with this supplier. Be specific, name the clause or email if relevant.>",

  "negotiation_brief": "<2-3 sentences synthesising Strauss's negotiation position for this meeting. Cover: (1) relationship and contract health — is the supplier responsive, is the contract active and in good standing; (2) price position — is the supplier quoting above or below the contract base price, and if commodity benchmark data is present in the prompt, does the market trend (up or down over 6 months) give Strauss leverage or signal cost pressure; (3) the single most important thing to know walking in. Be specific: name the price gap, the benchmark move, the renewal window, or the clause that matters. Do not describe what the packet contains — describe what Strauss's negotiation position actually is. Written for a procurement manager who has 2 minutes before the meeting starts.>",

  "field_sources": {{
    "email_summary": "<e.g. 'Based on 13 emails, 2026-01-07 to 2026-05-08'>",
    "latest_price_quoted": "<e.g. 'Email 2026-03-03 from Yael Shapira, subject: Q2 Pricing Proposal'>",
    "contract_base_price": "<e.g. 'Contract STR-DAIRY-2025-014, Section 4.2 Pricing'>",
    "renewal_date": "<e.g. 'Contract STR-DAIRY-2025-014, Section 7.1 Renewal Terms'>",
    "payment_terms": "<e.g. 'Contract STR-DAIRY-2025-014, Section 5 Payment'>",
    "volume_commitment": "<e.g. 'Contract STR-DAIRY-2025-014, Section 3.2 Volume'>",
    "key_penalty": "<e.g. 'Contract STR-DAIRY-2025-014, Section 9.3 Penalties'>",
    "heads_up": "<e.g. 'Synthesized from email 2026-03-03 (price proposal) and contract Section 4.2 (amendment requirement)'>"
  }},

  "financial_signals": {{
    "contract_currency": "<primary currency code for this supplier's invoices and contract pricing: 'ILS' if ₪, 'USD' if $, 'EUR' if €, 'PLN' if PLN. Use the currency that appears in contract pricing clauses and email invoices.>",
    "early_payment_discount_rate": <decimal rate if any email mentions early payment discount e.g. 0.025 for '2.5% discount', or null>,
    "early_payment_discount_days": <integer days within which payment earns the discount e.g. 10 for 'paid within 10 days', or null>,
    "net_payment_days": <standard payment window as integer e.g. 30 for 'net 30' or 60 for 'net 60', or null if not clearly stated in contract or emails>,
    "delivery_reliability_score": "<one-line plain-English assessment based on delivery history found in emails: 'Good — all shipments on time', 'Mixed — minor delays, within tolerance', or 'Poor — repeated delays or unresolved delivery issue'. Use null if emails contain no delivery history.>"
  }}
}}

Rules:
- open_issues must include EVERY unresolved issue. Do not omit any.
- Price quoted in email that differs from contract base price without a written amendment = price_discrepancy issue.
- Expired contract with no active signed replacement = no_active_contract issue.
- DRAFT contract not yet signed = no_active_contract issue.
- Renewal date in email that differs from contract = renewal_date_discrepancy issue.
- Spec change proposed in email but no signed change order = spec_change_dispute issue.
- If price unit in email is ambiguous, set latest_price_quoted.value to null and add it as a price_discrepancy issue.
- contract_base_price_numeric: extract only if the contract has a single unambiguous numeric base price in a consistent unit. Otherwise null.
- financial_signals.contract_currency: derive from the currency symbol in contract pricing (₪→ILS, $→USD, €→EUR, PLN→PLN). If multiple currencies appear, use the one in the contract's base price clause.
- financial_signals.early_payment_discount_rate/days: look for phrases like "2.5% discount if paid within 10 days", "2%/10 net 30", or similar. Set both or neither.
- financial_signals.net_payment_days: extract from "net 30", "net 60", "payment within 30 days" etc. If emails show a supplier requesting different terms than the contract, use the contracted terms.
- financial_signals.delivery_reliability_score: base only on explicit shipment events in emails (dispatch dates, arrival dates, delay mentions). Do not infer from tone.
- Return only valid JSON."""


def _call_claude(prompt: str, client: anthropic.Anthropic, on_token=None) -> dict:
    chunks = []
    n_chars = 0
    with client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for text in stream.text_stream:
            chunks.append(text)
            n_chars += len(text)
            if on_token:
                on_token(n_chars)
        final_msg = stream.get_final_message()

    raw = "".join(chunks).strip()
    raw = re.sub(r"^```[a-z]*\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Claude response is not valid JSON (stop_reason={final_msg.stop_reason!r}). "
            f"JSON error: {e}. "
            f"Last 200 chars: {raw[-200:]!r}"
        ) from e


# ── Public entry point ────────────────────────────────────────────────────

def run_extraction(supplier_num: str, on_token=None) -> dict:
    """
    Full extraction pass for one supplier.

    Loads emails, contracts, and price data; calls Claude once to extract
    structured facts; then computes local KPIs per metrics.md.

    Args:
        supplier_num: Two-digit string, e.g. "01", "04".

    Returns:
        Dict with all extracted fields and computed KPIs. Ready for
        packet_generator.run_packet().
    """
    if supplier_num not in SUPPLIERS:
        raise ValueError(f"Unknown supplier number: {supplier_num!r}")

    supplier_name, category = SUPPLIERS[supplier_num]
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from environment

    emails = load_emails(supplier_num)
    contracts = load_contracts(supplier_num)
    price_data = load_price_data(category)

    # Local KPI: response time (no API needed)
    avg_response_days = compute_response_time(emails)

    # Claude extraction
    prompt = _build_prompt(supplier_num, supplier_name, emails, contracts, price_data)
    extracted = _call_claude(prompt, client, on_token=on_token)

    # Local KPI: days to renewal
    renewal_date_str = extracted.get("contract_terms", {}).get("renewal_date")
    days_to_renewal = compute_days_to_renewal(renewal_date_str)

    # Local KPI: price delta
    price_delta = compute_price_delta(
        extracted.get("latest_price_quoted", {}),
        extracted.get("contract_terms", {}),
    )

    return {
        "supplier_num": supplier_num,
        "supplier_name": supplier_name,
        "category": category or "other",
        "email_count": len(emails),
        # KPIs
        "avg_response_days": avg_response_days,
        "days_to_renewal": days_to_renewal,
        "open_issues_count": len(extracted.get("open_issues", [])),
        "price_delta": price_delta,
        # Claude-extracted fields
        **extracted,
    }


# ── CLI smoke-test ────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    num = sys.argv[1] if len(sys.argv) > 1 else "04"
    print(f"Running extraction for supplier {num}…")
    result = run_extraction(num)
    print(json.dumps(result, indent=2, ensure_ascii=False))
