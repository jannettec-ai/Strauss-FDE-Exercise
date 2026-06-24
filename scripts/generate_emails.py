#!/usr/bin/env python3
"""
generate_emails.py

Generates synthetic supplier email corpora for the Strauss Procurement
prototype. Each supplier thread is produced by a separate Claude API call
using a detailed per-supplier prompt drawn from data/emails/GENERATION_SPEC.md.
Outputs JSON files to data/emails/.

Usage:
    python scripts/generate_emails.py            # regenerate all suppliers
    python scripts/generate_emails.py 03 05      # regenerate specific suppliers only

Signal requirements (see GENERATION_SPEC.md for full detail):
  - ≥2 suppliers with quantifiable late delivery patterns (extractable numbers)
  - ≥1 supplier with explicit on-time record language
  - ≥1 supplier with MOQ pushback (explicit minimum + surcharge)
  - ≥1 supplier with volume-tiered pricing (specific thresholds + %)
  - ≥1 supplier requesting letter of credit (with currency stated)
  - ≥1 supplier offering early payment discount (2.5% / 10 days)
  - ≥1 supplier requesting net 60 as negotiation ask
  - ≥3 suppliers with explicit FX denomination statement
  - ≥1 FX supplier is cocoa or dairy
  - ≥1 tension thread unresolved at end of corpus
"""

import json
import os
import sys
import time
from pathlib import Path

import anthropic

ROOT = Path(__file__).parent.parent
EMAILS_DIR = ROOT / "data" / "emails"
STRAUSS_EMAIL = "david.cohen@strauss-group.com"

# ── Per-supplier specifications ───────────────────────────────────────────────
# Each entry: (output_filename, display_name, category, domain_note, signal_prompt)

SUPPLIER_SPECS = {

    "01": {
        "filename": "supplier_01_ivoire_cacao.json",
        "name": "Ivoire Cacao Export",
        "category": "cocoa / Côte d'Ivoire",
        "contacts": {
            "strauss": STRAUSS_EMAIL,
            "supplier": [
                "amara.koffi@ivoirecacao.com (Sales, Amara Koffi — slow responder, 2-5 day gaps)",
                "jb.ouattara@ivoirecacao.com (Ops/logistics, Jean-Baptiste Ouattara — terse, occasionally contradicts Amara)",
            ],
        },
        "signals": """
REQUIRED SIGNALS — embed all of these naturally:

1. LATE DELIVERY (quantifiable numbers required):
   - Early email: Amara confirms standard lead time explicitly:
     "our standard dispatch-to-arrival window is 14 business days from
     order confirmation date."
   - Mid-thread: JB sends delay notice using the same unit:
     "writing to advise revised ETA — currently tracking 26 business days
     from order confirmation due to vessel delay and port congestion at
     Abidjan. Apologies for the inconvenience."
   - Later: JB reports partial shipment (short by ~1.5 MT, quality check
     failure on two pallets before loading). Will credit the shortfall.
   - Gap must be extractable: 14bd committed → 26bd actual = +12bd delay.

2. FX DENOMINATION (satisfies the ≥1 cocoa/dairy FX requirement):
   Include this exact language in a formal quote or pro-forma email from Amara:
   "Please note that all pricing from Ivoire Cacao Export is denominated
   in USD. The exchange rate applied to your invoice is the prevailing
   Banque Centrale de Côte d'Ivoire reference rate on the date of invoice
   issuance, not the date of order."

3. TENSION (unresolved at end):
   Amara sends a Q2 price increase notice ($3,050/ton, up from ~$2,850)
   while the Q1 shipment has not yet arrived. David pushes back in writing,
   citing the contract's quarterly review mechanism (price adjustments
   require written confirmation from both parties). Amara says she doesn't
   have the contract and will ask JB. No formal amendment is received by
   the end of the thread. Last email from David still waiting.

TONE: Amara is friendly but vague, avoids hard commitments. JB is terse,
factual, few words. They do not copy each other consistently. David gets
more formal as frustration builds.
""",
    },

    "02": {
        "filename": "supplier_02_golden_coast.json",
        "name": "Golden Coast Cocoa Traders",
        "category": "cocoa / Ghana",
        "contacts": {
            "strauss": STRAUSS_EMAIL,
            "supplier": [
                "kwame.asante@goldencoastcocoa.com (Sales director, Kwame Asante — professional, firm)",
                "efua.mensah@goldencoastcocoa.com (Logistics, Efua Mensah — responsive, detail-oriented)",
            ],
        },
        "signals": """
REQUIRED SIGNALS — embed all of these naturally:

1. LATE DELIVERY (quantifiable numbers required):
   - Opening logistics email from Efua states explicitly:
     "our standard CIF lead time from Tema port to Ashdod is 12 business
     days from vessel loading date."
   - Mid-thread: vessel diversion (mechanical issue at sea, diverted to
     Las Palmas). Efua advises:
     "we are now estimating 22 business days from the original loading
     date. The shipping line is managing the situation."
   - Gap: 12bd committed → 22bd actual = +10bd delay.
   - Shipment arrives, but QC fails (moisture content 8.2% vs spec max
     7.5%). David notifies Golden Coast.

2. TENSION / OPEN DISPUTE (must NOT resolve by end of thread):
   - Kwame pushes back on quality finding. He references their
     pre-shipment moisture certificate from SGS Ghana (6.8% at loading,
     within spec). Argues the moisture increase happened in transit during
     the Las Palmas diversion, not their fault.
   - David: "our contract says risk passes at destination, not at origin."
   - Thread ends with both parties having defensible positions, an
     independent test proposed but not yet agreed. No settlement. No credit
     note issued.

TONE: Kwame is formal, professional, and firm — he does not concede easily.
Efua is practical and helpful with logistics detail. David becomes more
pointed as the dispute drags on.
""",
    },

    "03": {
        "filename": "supplier_03_lowlands_dairy.json",
        "name": "Lowlands Dairy Co-op",
        "category": "dairy / Netherlands",
        "contacts": {
            "strauss": STRAUSS_EMAIL,
            "supplier": [
                "pieter.vandenberg@lowlandsdairy.nl (Commercial, Pieter van den Berg — measured, co-op-oriented)",
                "anja.dekker@lowlandsdairy.nl (Volume planning, Anja Dekker — practical, logistics-focused)",
            ],
        },
        "signals": """
REQUIRED SIGNALS — embed all of these naturally:

1. FX DENOMINATION — EUR (satisfies ≥1 cocoa/dairy FX requirement):
   In a commercial summary or renewal framework email from Pieter:
   "Please note that all Lowlands Dairy pricing is denominated in EUR.
   Strauss is responsible for any currency conversion costs; the applicable
   rate is that of the payment date, not the order date."

2. LETTER OF CREDIT:
   Pieter raises this in the renewal negotiation:
   "For the renewed contract volumes, our finance committee requires
   payment by irrevocable Letter of Credit denominated in EUR, issued
   by a correspondent bank acceptable to our co-op, no later than 30
   days before each shipment date. We can discuss whether this applies
   to all shipments or only those above a threshold volume."

3. NET 60 REQUEST (framed as a negotiation ask, not a stated fact):
   "One commercial point we'd like to raise for the renewal: we would
   prefer to move to net 60 payment terms. Current net 30 is difficult
   for our co-op cash flow given the 4-6 week cross-border SEPA transfer
   timelines we're working with on the Israel route."

4. ONGOING RENEGOTIATION (no active signed contract):
   Contract expired December 31 2025. Thread covers the renewal
   negotiation from January through June 2026 — still not signed by
   the end. The draft proposes a volume floor (25 MT/quarter) that
   conflicts with what David wants (20 MT/quarter). Operating informally
   on old terms in the meantime. Anja is processing orders against the
   expired contract without comment.

TONE: Pieter is measured, represents the co-op's collective position,
refers decisions back to "the board" or "our members." Anja is practical
and does not engage in the commercial debate.
""",
    },

    "04": {
        "filename": "supplier_04_galil_dairy.json",
        "name": "Galil Dairy Suppliers",
        "category": "dairy / Israel",
        "contacts": {
            "strauss": STRAUSS_EMAIL,
            "supplier": [
                "yael.shapira@galildairy.co.il (Sales/commercial, Yael Shapira — friendly, relationship-focused)",
                "oren.levi@galildairy.co.il (Logistics, Oren Levi — terse, operational)",
            ],
        },
        "signals": """
REQUIRED SIGNALS — embed all of these naturally:

1. ON-TIME RECORD (explicit language required):
   Oren must use language like this in at least one shipment confirmation:
   "As with our previous two deliveries, this shipment departed within the
   5 business days from order confirmation that we quoted. Truck IL-4102,
   ETA [date]."
   And Yael, in a separate email: "Glad everything is running smoothly —
   we pride ourselves on consistently meeting the windows we commit to."

2. EARLY PAYMENT DISCOUNT (exact rate and window required):
   In a commercial email or invoice cover note from Yael:
   "As a reminder — Galil offers a 2.5% discount on invoices settled
   within 10 days of issue date. Standard terms are net 30. Just flag
   to your finance team if they want to take advantage on this next
   invoice."

3. PRICE CONTRADICTION — planted inconsistency (do NOT make it obvious):
   One email from Yael, partway through the thread, must casually mention:
   "Given where the dairy market is right now, we'll need to move to
   ₪15.50/kg from Q2. I know it's a step up but input costs have really
   moved."
   — NO reference to a written amendment, NO mention of contract Section
   4.2, NO indication Yael knows this requires formal approval. It should
   read like a routine update. The contract caps the price at ₪14.20/kg
   with no increase valid without a signed written amendment. The
   extraction logic catches this, not the email text itself.

TONE: Yael is warm, slightly chatty, uses Hebrew phrases occasionally
(Shana tova, todah). Oren is minimal — just logistics facts. David is
friendly but gets businesslike when the pricing issue comes up.
""",
    },

    "05": {
        "filename": "supplier_05_cana_doce.json",
        "name": "Cana Doce Açúcar",
        "category": "sugar / Brazil",
        "contacts": {
            "strauss": STRAUSS_EMAIL,
            "supplier": [
                "fernando.almeida@canadoce.com.br (Sales Director, Fernando Almeida — formal, precise)",
                "isabela.souza@canadoce.com.br (Logistics Coordinator, Isabela Souza — professional, detail-oriented)",
            ],
        },
        "signals": """
REQUIRED SIGNALS — embed all of these naturally:

1. FX DENOMINATION — USD:
   In Fernando's first substantive commercial email:
   "Please note that all Cana Doce Açúcar pricing is quoted in USD.
   Pursuant to our contract terms, the applicable exchange rate is that
   of the invoice issue date. Any currency conversion costs are borne
   by the buyer."

2. VOLUME-TIERED PRICING (specific thresholds and percentages required):
   In a renewal discussion or commercial proposal from Fernando:
   "For the renewal period, we are able to offer the following tiered
   pricing structure:
   - 50–74 MT/quarter: base contract rate (no discount)
   - 75–99 MT/quarter: 2.0% below base rate
   - 100 MT/quarter and above: 4.5% below base rate
   We note your current run-rate of approximately 60 MT/quarter. An
   increase to 75 MT would qualify you for the first tier discount,
   which at current base pricing would be worth approximately $[amount]
   per quarter."

3. RENEWAL DATE DISCREPANCY (planted inconsistency):
   Fernando mentions the renewal date as "October 15, 2027" in one email.
   The current active contract (STR-SUGAR-2025-018) has a renewal date
   of September 30, 2027. Strauss notices the discrepancy in a late-thread
   email and asks Fernando to confirm. Fernando's response should be
   slightly evasive — he says he'll check with his team but doesn't
   correct it definitively before the end of the thread.

4. STRONG ON-TIME RECORD:
   Isabela's shipment confirmations should reference consistent delivery:
   "Vessel departed Santos on schedule — same lead time as Q1, within
   our quoted 21-day CIF window to Ashdod."

TONE: Fernando is formal and polished throughout — full sentences, proper
greetings, no shortcuts. Isabela is equally professional but more
operational. This is the highest-formality supplier in the corpus.
""",
    },

    "06": {
        "filename": "supplier_06_siam_sugar.json",
        "name": "Siam Sugar Partners",
        "category": "sugar / Thailand",
        "contacts": {
            "strauss": STRAUSS_EMAIL,
            "supplier": [
                "wichai.tanaka@siamsugar.co.th (Operations, Wichai Tanaka — ESL, helpful)",
                "nareenart.prasit@siamsugar.co.th (Commercial, Nareenart Prasit — ESL, more assertive)",
            ],
        },
        "signals": """
REQUIRED SIGNALS — embed all of these naturally:

1. MOQ PUSHBACK (explicit minimum and surcharge required):
   In a reply to a smaller order inquiry, or proactively in a commercial
   update from Wichai or Nareenart:
   "We would like to advise our minimum order quantity for ICUMSA 150
   refined sugar is 40 metric tons per shipment. For order below this
   threshold, a handling surcharge of USD 18 per MT will apply. This
   is our company policy and cannot be waive."

2. PRICE UNIT AMBIGUITY:
   Nareenart quotes a new price: "for Q2 we propose price of $420 per
   unit" — deliberately unclear whether this is per MT or per something
   else. David follows up asking for clarification. Nareenart confirms
   it is per MT, but not before Strauss has flagged the ambiguity.

3. PRICE DISPUTE (unresolved at end):
   Ongoing negotiation: Siam proposes $420/MT (up from $398/MT contract
   rate, citing ICE benchmark movement). David counters at $408/MT. Siam
   comes back at $415/MT. Thread ends without a signed amendment. Q2
   order processed at old contract rate pending resolution. Nareenart
   follows up at the end asking for status.

4. ESL PHRASING THROUGHOUT: Both contacts use grammatically imperfect
   but understandable English — dropped articles, verb tense inconsistency,
   occasional awkward phrasing. Keep it natural, not mocking.

TONE: Wichai is operational and polite. Nareenart is commercial and more
direct despite the ESL phrasing. David is methodical, cites contract terms
explicitly when pushing back on price.
""",
    },

    "07": {
        "filename": "supplier_07_sierra_verde.json",
        "name": "Sierra Verde Coffee Cooperative",
        "category": "coffee / Colombia",
        "contacts": {
            "strauss": STRAUSS_EMAIL,
            "supplier": [
                "alejandro.reyes@sierraverdecoop.co (Co-op director, Alejandro Reyes — warm, personal, community-focused)",
                "sofia.gutierrez@sierraverdecoop.co (Logistics, Sofia Gutierrez — professional, handles export docs)",
            ],
        },
        "signals": """
REQUIRED SIGNALS — embed all of these naturally:

1. FX DENOMINATION — USD (personal, informal register):
   Alejandro raises it naturally in a relationship-oriented email:
   "One thing I should mention — all our invoices are in USD, as you know.
   I just want to flag in case the ILS/USD rate ever becomes an issue for
   your team — if timing of payment ever creates a problem for you, just
   tell me and we can talk about it. We are flexible with people we trust."
   (This should NOT feel like a legal notice — it should feel like
   Alejandro raising it as a friend.)

2. RELATIONSHIP TONE (at least one email where personal content exceeds
   business content):
   Alejandro writes a long email about the harvest, mentions Diego the
   field worker by name, asks about David's family, reminisces about a
   past visit to the farm. The actual business content (ship date, volume
   confirmation) is almost a postscript.

3. QUALITY SIGNALS: Cup scores referenced (85+ SCA), specific micro-lot
   names (La Esperanza plot, San Augustín lot), harvest updates, flavor
   notes — all of which make structured fact extraction harder because
   the signal is buried in narrative.

4. MINOR DELAY (within tolerance, not a "late delivery" signal):
   One shipment is 3-4 days behind the originally quoted ship date due
   to a harvest processing delay or equipment issue at the dry mill.
   Still arrives within the agreed delivery window. Alejandro mentions
   it casually mid-email between personal notes. No dispute.

TONE: Alejandro's emails read like letters from a friend who happens to
be in business with you. Sofia's emails are shorter, operational, and
professional. David is warmer with Alejandro than with any other supplier.
""",
    },

    "08": {
        "filename": "supplier_08_europack.json",
        "name": "EuroPack Solutions",
        "category": "packaging / Poland",
        "contacts": {
            "strauss": STRAUSS_EMAIL,
            "supplier": [
                "marek.wojcik@europack.pl (Account manager, Marek Wójcik — commercial lead)",
                "agnieszka.kowalska@europack.pl (Production coordinator, Agnieszka Kowalska — operational)",
                "piotr.nowak@europack.pl (Technical lead, Piotr Nowak — engineering detail)",
                "katarzyna.wisniewska@europack.pl (Account management, Katarzyna Wiśniewska — invoicing/admin)",
            ],
        },
        "signals": """
REQUIRED SIGNALS — embed all of these naturally:

1. SPEC CHANGE DISPUTE (central conflict of this thread):
   Marek proposes mid-thread: upgrade from ESP-CHOC-350 (350gsm board,
   PLN 1.85/unit) to ESP-CHOC-380 (380gsm, PLN 1.93/unit, +4.3%).
   Reason: structural complaints from two other clients in hot-weather
   transit. David asks for the datasheet, Piotr sends it.
   Agnieszka then assumes approval and schedules the 380gsm run without
   explicit sign-off. David spots this when Katarzyna's invoice preview
   shows "ESP-CHOC-380 @ PLN 1.93" and sends a firm email: the spec
   change has NOT been agreed, revert to original.
   Marek acknowledges and puts the run on hold, but notes the delay will
   push delivery by 2-3 weeks. David says proceed at original spec.
   Thread ends with Q2 running on original spec but Q3 discussion on the
   380gsm upgrade still open.

2. MULTI-PERSON CC GAP: Piotr sends the technical datasheet but doesn't
   CC Agnieszka. She continues assuming the change is approved. Marek
   doesn't catch this until David escalates. This is the coordination
   failure — document it naturally across the email chain.

3. PLN PRICING: All pricing in PLN throughout. No FX denomination
   statement needed (PLN used matter-of-factly).

4. MOQ INCIDENTAL MENTION:
   In a thread about a potential new smaller packaging run for a seasonal
   product, Katarzyna mentions: "Please note that custom print runs below
   50,000 units are subject to a setup surcharge of PLN 2,800, covering
   press setup and colour registration for the shorter run."

TONE: Marek is businesslike and commercial. Agnieszka is operational and
a bit brusque. Piotr is technical and precise. Katarzyna is administrative.
The tone contrast between the four contacts is part of what makes the CC
chain confusing. David is professional but firm when the spec mix-up
surfaces.
""",
    },
}

# ── System prompt (shared across all supplier calls) ──────────────────────────

SYSTEM_PROMPT = """You are generating synthetic supplier email correspondence for a
procurement prototype. The output must be a valid JSON array of email objects.

Each email object must have exactly these fields:
  "date"    — ISO format YYYY-MM-DD
  "from"    — email address string
  "to"      — email address string
  "cc"      — array of email address strings (can be empty [])
  "subject" — subject line string
  "body"    — full email body string (use \\n for line breaks)

Rules:
- Output ONLY the raw JSON array. No markdown, no code fences, no explanation.
- Dates must span January–June 2026, chronologically ordered.
- Distribution must be bursty — not evenly spaced. Real correspondence
  clusters around events (order placed → logistics flurry → then quiet).
- All required signals listed in the prompt MUST appear in the output.
- Signals must be embedded naturally in business correspondence — not as
  structured data in prose, not as obvious flags. Write them as a
  procurement professional would actually write them.
- Never resolve all open issues cleanly. At least one thread per supplier
  should remain open as of the last email.
- Vary sentence length, formality level, and sign-off style according to
  the character voice described.
- The Strauss-side sender is always david.cohen@strauss-group.com.
"""


def build_prompt(num: str, spec: dict) -> str:
    contacts_str = "\n".join(
        f"  - {c}" for c in spec["contacts"]["supplier"]
    )
    return f"""Generate a realistic email thread for this supplier.

SUPPLIER: {spec['name']} (Supplier {num})
CATEGORY: {spec['category']}
STRAUSS CONTACT: {spec['contacts']['strauss']}
SUPPLIER CONTACTS:
{contacts_str}

{spec['signals']}

Generate 12-16 emails spanning January through June 2026.
Distribution must be bursty — cluster emails around key events
(order placed, shipment update, dispute emerges, follow-up chase).
Output only the JSON array.
"""


def generate_supplier_emails(num: str, spec: dict, client: anthropic.Anthropic) -> list[dict]:
    print(f"  Generating supplier {num} ({spec['name']})…", flush=True)
    prompt = build_prompt(num, spec)

    response = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=8192,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()

    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        raw = raw.rsplit("```", 1)[0]

    emails = json.loads(raw)
    print(f"    → {len(emails)} emails generated", flush=True)
    return emails


def validate_emails(emails: list[dict], num: str) -> list[str]:
    """Basic validation. Returns list of warning strings."""
    warnings = []
    required_keys = {"date", "from", "to", "cc", "subject", "body"}
    for i, e in enumerate(emails):
        missing = required_keys - set(e.keys())
        if missing:
            warnings.append(f"Email {i}: missing fields {missing}")
        if not isinstance(e.get("cc"), list):
            warnings.append(f"Email {i}: 'cc' is not a list")
    dates = [e.get("date", "") for e in emails]
    if dates != sorted(dates):
        warnings.append("Emails are not in chronological order")
    strauss_count = sum(1 for e in emails if e.get("from") == "david.cohen@strauss-group.com")
    if strauss_count == 0:
        warnings.append("No Strauss outbound emails found")
    return warnings


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set.", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    # Determine which suppliers to regenerate
    if len(sys.argv) > 1:
        targets = sys.argv[1:]
        targets = [t.zfill(2) for t in targets]
        unknown = [t for t in targets if t not in SUPPLIER_SPECS]
        if unknown:
            print(f"ERROR: unknown supplier numbers: {unknown}", file=sys.stderr)
            sys.exit(1)
    else:
        targets = list(SUPPLIER_SPECS.keys())

    print(f"Generating emails for suppliers: {', '.join(targets)}\n")

    for num in targets:
        spec = SUPPLIER_SPECS[num]
        out_path = EMAILS_DIR / spec["filename"]

        try:
            emails = generate_supplier_emails(num, spec, client)
        except json.JSONDecodeError as e:
            print(f"  ERROR: JSON parse failed for supplier {num}: {e}")
            continue
        except Exception as e:
            print(f"  ERROR: API call failed for supplier {num}: {e}")
            continue

        warnings = validate_emails(emails, num)
        if warnings:
            print(f"  WARNINGS for supplier {num}:")
            for w in warnings:
                print(f"    ⚠ {w}")

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(emails, f, indent=2, ensure_ascii=False)
        print(f"  ✓ Written to {out_path.name}\n")

        # Small pause between API calls to avoid rate limits
        if num != targets[-1]:
            time.sleep(2)

    print("Done.")


if __name__ == "__main__":
    main()
