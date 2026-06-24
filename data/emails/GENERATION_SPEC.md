# Email Generation Spec — Suppliers 1-8

Reference: `data/suppliers-roster.md` for supplier names, categories, and
messiness profiles. Reference: `data/emails/supplier_01_ivoire_cacao.json`
as the exact quality bar and JSON format to match.

## Instructions for Claude Code

For each supplier, generate a JSON file at
`data/emails/supplier_0N_<short_name>.json` containing an array of email
objects with fields: `date`, `from`, `to`, `cc`, `subject`, `body`.

**Match the format and realism of supplier_01 exactly**: real-sounding
email addresses (firstname.lastname@<supplierdomain>.com), dates spanning
the 6-month window January-June 2026, bursty (not evenly spaced) timing,
natural sign-offs, occasional typos or informal phrasing where the
messiness profile calls for it, and at least one genuine inconsistency or
unresolved thread per supplier (a contradiction, a discrepancy, a dropped
ball), not just neutral correspondence.

**Per-supplier count**: 10-16 emails each (bursty distribution, do not
space them evenly across the 6 months).

## Sender consistency

Use `david.cohen@strauss-group.com` as the Strauss-side procurement
contact across all suppliers for consistency.

---

## Corpus-level signal requirements

These signals must be distributed across the 8-supplier corpus. They are
not present uniformly — see the per-supplier assignments below. Each signal
must appear as natural business correspondence, not as structured data in
prose form. The AI extraction layer (not the reader) is the one that
surfaces them.

### Delivery performance signals

**At least 2 suppliers must show a quantifiable late delivery pattern.**
The delay gap must be extractable as a number from the email text. The
pattern must span at least 2-3 emails:
- Email 1: supplier states their standard delivery window explicitly
  (e.g. "our standard dispatch-to-arrival window is 14 business days")
- Email 2: delay notification referencing the same unit
  (e.g. "we are now tracking approximately 26 business days from order
  date due to port congestion / vessel issue / inspection delay")
- Email 3: partial resolution or update (short shipment, late arrival)

**At least 1 supplier must show a consistent on-time record**, referenced
naturally across multiple shipments:
  "as with previous orders, the shipment departed within our quoted 10-day
  window" or "confirming dispatch — same schedule as Q1, within the 8
  business days we committed."

### MOQ and volume signals

**At least 1 supplier must push back on order size** with explicit MOQ
language and a surcharge:
  "Please note our minimum order quantity for this product line is [X
  units/MT]. Orders below this threshold are subject to a handling
  surcharge of [amount or %]."

**At least 1 supplier must offer volume-tiered pricing** with specific
thresholds and percentages stated in the email body:
  e.g. "For orders of 50–99 MT we offer 2% off the contract base rate;
  orders of 100 MT and above qualify for 4.5% off."

### Payment terms and financing signals

**At least 1 supplier must request a letter of credit** for international
orders, with the transaction currency stated explicitly:
  "For shipments of this size we require payment by irrevocable Letter of
  Credit, denominated in EUR, issued by a correspondent bank acceptable to
  our co-op's finance committee."

**At least 1 supplier must offer an early payment discount** with a
specific rate and window stated in the email:
  "A 2.5% discount is available on invoices settled within 10 days of
  issue date. Payment within 30 days is standard net terms."

**At least 1 supplier must request net 60 terms** framed as a negotiation
ask, not a stated fact:
  "One item we'd like to raise for renewal discussions: our preference
  would be to move to net 60 on payment, given the cross-border transfer
  timelines we're working with."

### Currency and FX exposure signals

**At least 3 suppliers must quote prices in a foreign currency (EUR or
USD) with an explicit FX denomination statement** in at least one email:
  "Please note all pricing is denominated in EUR and is subject to the
  exchange rate at date of invoice, not date of order."
  or: "All our quotations are in USD. Strauss bears the exchange rate
  risk for ILS/USD movements between order date and settlement."

**At least 1 of these FX suppliers must be a cocoa or dairy supplier**
(suppliers 01, 02, 03, or 04), as those categories are directly relevant
to Strauss's core commodity exposure.

### Realism requirements

- Vary tone across suppliers: some formal, some relationship-oriented,
  some terse. See messiness profiles below.
- Include at least one thread where there is genuine tension — a complaint,
  a dispute, or a price increase notice that the procurement manager has
  not yet responded to. This makes extraction interesting.
- Do not resolve every thread cleanly. Some issues should remain open
  as of the last email (June 2026), as these become "open issues" surfaced
  in the negotiation prep packet.

---

## Per-supplier signal assignments

### Supplier 01 — Ivoire Cacao Export (cocoa, Côte d'Ivoire)

**Messiness profile**: Slow responder (2-5 day email gaps), two contacts
(sales rep + ops manager) who don't coordinate and occasionally contradict
each other.

**Required signals for this supplier**:
- LATE DELIVERY (quantified): Sales rep confirms a standard lead time
  explicitly ("our standard dispatch window is 14 business days from
  order confirmation"). Ops manager later sends a delay notification
  referencing the same unit ("currently tracking 26 business days from
  order date due to port congestion at Abidjan"). Short shipment partial
  resolution in a third email.
- FX DENOMINATION: At least one email must include an explicit FX
  statement: "all pricing from Ivoire Cacao is denominated in USD. The
  exchange rate applied is the rate on date of invoice issuance." This
  is the cocoa FX signal that satisfies the ≥1 cocoa/dairy FX requirement.
- TENSION: A price increase notice sent by the sales rep mid-thread
  ($3,050/ton for Q2) while an order hasn't yet been fully delivered.
  Strauss pushes back citing the contract review mechanism. No resolution
  by end of thread.

### Supplier 02 — Golden Coast Cocoa Traders (cocoa, Ghana)

**Messiness profile**: Recent delivery issue and quality complaint still
unresolved. Thread must NOT reach a clean resolution by the end.

**Required signals for this supplier**:
- LATE DELIVERY (quantified): Opening email from Golden Coast confirms
  "our standard CIF lead time from Tema port is 12 business days." Later
  email from logistics contact advises "the vessel has been diverted and
  we are now estimating 22 business days from original loading date."
  Shipment eventually arrives but with quality issues.
- TENSION / OPEN DISPUTE: Quality inspection reveals moisture content
  out of spec. Supplier disputes the result citing their pre-shipment
  certificate. Thread ends without resolution — both sides have a
  defensible position, no settlement agreed.
- ON-TIME STANDARD STATED THEN BROKEN: The explicit 12-business-day
  standard makes the 22-business-day actual extractable as a number.

### Supplier 03 — Lowlands Dairy Co-op (dairy, Netherlands)

**Messiness profile**: Mid-renegotiation, contract terms and emails
partially conflict, no active signed contract.

**Required signals for this supplier**:
- FX DENOMINATION (EUR): At least one email must state: "please note that
  all Lowlands Dairy pricing is denominated in EUR. Strauss is responsible
  for any currency conversion costs at date of payment." This is the
  dairy FX signal satisfying the ≥1 cocoa/dairy FX requirement.
- LETTER OF CREDIT: Supplier requests LC for the renewal contract:
  "For the renewed contract volume, our finance committee requires payment
  by irrevocable Letter of Credit denominated in EUR, issued no later than
  30 days before each shipment date."
- NET 60 REQUEST: Framed as a negotiation ask in the renewal discussion:
  "One commercial point we want to raise: we would like to move to net 60
  payment terms for the renewal. Current net 30 is difficult for our
  co-op cash flow given the 4-6 week cross-border settlement timelines."
- ONGOING RENEGOTIATION: No active signed contract — existing contract
  expired Dec 31 2025. Draft terms partially conflict with what's
  discussed in emails (volume floor discrepancy).

### Supplier 04 — Galil Dairy Suppliers (dairy, Israel)

**Messiness profile**: One email mentions a price increase that
contradicts the contract's price cap clause — planted inconsistency.

**Required signals for this supplier**:
- ON-TIME RECORD (explicit): Multiple shipments delivered on time.
  The logistics contact must explicitly say "as with our previous two
  deliveries, this shipment departed within the 5 business days quoted
  at order confirmation" in at least one email.
- EARLY PAYMENT DISCOUNT: In a commercial update or invoice note, the
  supplier must explicitly offer: "As a reminder, Galil offers a 2.5%
  discount on invoices settled within 10 days of issue date. Standard
  terms are net 30."
- PRICE CONTRADICTION (planted inconsistency — do NOT make it obvious):
  One email must casually mention a new price of ₪15.50/kg "given where
  the market is" without referencing any written amendment or Strauss
  approval. The contract caps the price at ₪14.20/kg with no increase
  valid without a signed written amendment (Section 4.2). The email
  should feel like a routine update, not a flagged issue.

### Supplier 05 — Cana Doce Açúcar (sugar, Brazil)

**Messiness profile**: Very formal, polished correspondence. Conflict
lives in a renewal date discrepancy between email and contract (a few
weeks off), not in tone.

**Required signals for this supplier**:
- FX DENOMINATION (USD): At least one email must state explicitly:
  "Please note that all Cana Doce pricing is quoted in USD. Pursuant to
  our contract terms, the applicable exchange rate is that of the invoice
  date, and any currency conversion costs are borne by the buyer."
- VOLUME-TIERED PRICING: In a commercial proposal or renewal discussion,
  the supplier must offer specific volume tiers with percentages:
  "For your reference, our tiered pricing structure for the renewal period
  is as follows: 50–74 MT/quarter: base rate; 75–99 MT/quarter: 2.0%
  discount off base; 100 MT/quarter and above: 4.5% discount off base.
  We note your current run-rate of 60 MT/quarter would qualify for the
  first tier discount if you could commit to 75 MT."
- RENEWAL DATE DISCREPANCY: One email references the contract renewal date
  as "October 15" while the contract document states September 30. The
  discrepancy should be planted naturally (e.g., Strauss notices and
  questions it in a late-thread email).
- FORMAL TONE: Fernando Almeida communicates formally throughout. Isabela
  Souza handles logistics professionally. Contrast with Siam/Sierra Verde.

### Supplier 06 — Siam Sugar Partners (sugar, Thailand)

**Messiness profile**: English-as-second-language, price unit ambiguity.

**Required signals for this supplier**:
- MOQ PUSHBACK: In one email (in response to a smaller order inquiry or
  as a general commercial note), the supplier must state: "We would like
  to advise that our minimum order quantity for ICUMSA 150 refined sugar
  is 40 metric tons per shipment. For orders below this threshold, a
  handling surcharge of USD 18 per MT will apply." The ESL phrasing
  should be natural to this supplier's voice.
- PRICE UNIT AMBIGUITY: At least one email must quote a price without
  a clear unit (e.g., "new price $420 per unit" where it is unclear if
  this means per MT or per something else). Strauss should follow up
  asking for clarification. Supplier clarifies but not before the
  ambiguity has been logged in the thread.
- PRICE DISPUTE: Ongoing negotiation about a price increase from the
  contracted rate. Thread should not resolve cleanly.
- ESL PHRASING: Grammatically imperfect but understandable throughout.
  Wichai and Nareenart have distinct voices.

### Supplier 07 — Sierra Verde Coffee Cooperative (coffee, Colombia)

**Messiness profile**: Warm, relationship-heavy, personal notes mixed
into business content.

**Required signals for this supplier**:
- FX DENOMINATION (USD): At least one email must include an explicit FX
  statement: "I should mention — all Sierra Verde invoices are in USD.
  I know you deal in ILS mostly, so just flag if the exchange timing ever
  creates a problem for you and we can discuss." This should feel like
  Alejandro raising it personally, not a formal notice.
- RELATIONSHIP TONE: Personal notes (asking about David's family,
  referencing a past visit to the farm), mixed into business content
  throughout. At least one email where the personal content is longer
  than the business content.
- QUALITY: Cup scores mentioned, harvest updates, micro-lot references
  that make clean structured extraction genuinely harder.
- DELIVERY: Minor delay in one shipment (a few days, well within
  tolerance) — not a "late delivery" signal, just a human delay
  (harvest timing, equipment at mill). Thread resolves warmly.

### Supplier 08 — EuroPack Solutions (packaging, Poland)

**Messiness profile**: Multi-person CC chains, spec change mid-thread.

**Required signals for this supplier**:
- PLN PRICING: All pricing in Polish Zloty (PLN). No explicit FX
  denomination statement needed (PLN is less common, but just used
  naturally in the thread).
- SPEC CHANGE DISPUTE: Supplier proposes an upgrade from ESP-CHOC-350
  to ESP-CHOC-380 board spec mid-thread, with a price impact of
  PLN 1.93/unit vs PLN 1.85/unit (4.3% increase). Strauss has not
  formally approved. Production coordinator assumes approval and starts
  scheduling the 380gsm run. Strauss explicitly tells them to stop
  and revert to original spec. This creates an unresolved change-order
  dispute.
- MULTI-PERSON CC: At least 3 EuroPack contacts across the thread
  (e.g. account manager, production coordinator, technical lead). Not
  all of them see all the relevant emails, creating a coordination gap
  that mirrors a real procurement risk.
- MOQ SECONDARY: One incidental mention of minimum run size for a
  custom spec ("custom print runs below 50,000 units are subject to
  a setup surcharge of PLN 2,800").

---

## After generation

Spot-check at least 2-3 emails per supplier file for realism before
moving on. Verify: all required signals are present and extractable,
character voices are distinct, dates are chronologically consistent,
and no thread resolves every open issue (real correspondence is messy).
