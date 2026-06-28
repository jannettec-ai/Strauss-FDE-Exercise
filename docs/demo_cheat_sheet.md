# STRAUSS FDE DEMO — ONE-PAGER

---

## SLIDE SEQUENCE

**Before the demo:**
Problem framing → current state (manual, fragmented) → introduce the tool

**During the demo** *(live in browser)*:
→ Home page → Meeting Prep (Case 1) → Meeting Prep (Case 2) → Market Intel

**After the demo:**
ROI framing → time saved → scale argument → next steps

---

## CASE 1 — GALIL DAIRY SUPPLIERS
*Meeting July 9 · Best opener: clean, relatable, surprising insight*

**What to show:**
1. Open Meeting Prep → select Galil Dairy Suppliers
2. Point to the 4 KPI boxes: 9.8d response time, 3 open issues, +9.2% price delta, 430 days to renewal
3. Scroll to **Watch for Today** — price discrepancy flagged, click source → email opens directly
4. Scroll to **Price vs Contract** section → highlight the **💳 Early payment discount** card
   - "2% if paid within 10 days vs. net 45 — implied APR 21.3%, well above our cost of capital. The system is telling us to take it."
   - This is the insight no one would have caught manually

**Talking point:** "The procurement manager didn't ask for a financial analysis. They just opened their prep packet and it was there."

---

## CASE 2 — SIAM SUGAR PARTNERS
*Meeting July 24 · Best for: risk visibility, urgency, process breakdown*

**What to show:**
1. Open Meeting Prep → select Siam Sugar Partners
2. KPI boxes: 14.3d response time (slow), 4 open issues, +4.3% delta, 3 days to renewal (red)
3. Watch for Today — show the price ambiguity issue: per-ton vs. per-unit unresolved
   - "They're walking into a pricing meeting and no one knows what unit the quote is in"
4. Show the contract renegotiation issue — open thread, no resolution

**Talking point:** "Without this tool, they would have walked into that meeting on July 24 with an expired contract and an unresolved unit ambiguity on the price. Both invisible in the inbox."

---

## CASE 3 — IVOIRE CACAO EXPORT (backup / if time)
*Meeting July 4 · Best for: full complexity, negotiation brief*

**What to show:**
1. Open Meeting Prep → select Ivoire Cacao Export
2. KPI boxes: contract OVERDUE (−27 days), 5 open issues, +$400/ton (+15.1%)
3. Priority alert — contract expired, no active signed agreement
4. Show the **Negotiation Brief** — assembled automatically from 15 emails and a contract
5. Scroll to Commodity Benchmark — ICCO at $4,143/ton vs. quoted $3,050/ton

**Talking point:** "The market is 36% above what the supplier is even asking. The system caught that — and it changes how you walk into the room."

---

## MARKET INTEL PAGE DEMO
*Show after Case 1 or as a standalone "what else does it do" beat*

1. **Commodity Prices tab** — show cocoa trend, point to the 6-month chart
   - "Procurement now has the same benchmark view as the supplier's sales team"
2. **FX Exposure tab** — show USD/ILS rate for relevant suppliers
   - "Every dollar-denominated contract has FX risk. This surfaces it."
3. **Cost of Money tab** — scroll to Early Payment Discount Calculator
   - Pre-fill: 2% / 10 days / net 45 → show APR and verdict appear live
   - "This is what the card on the prep page is doing automatically"

---

## IF ASKED ABOUT DATA PRIVACY
"Email content is processed in memory only and not retained beyond this session."
In production: points to a dedicated supplier communications channel, not personal inboxes.

---

## WHY THE SYNTHETIC DATA WORKS
*If asked how the data was designed or how realistic it is*

1. **Messiness by design** — late replies, multiple contacts per supplier, informal price quotes that bypass the contract process
2. **Contractual gaps that match email reality** — base price in contract never matches what's quoted in email; no written amendment on file
3. **Three renewal states** — healthy (430d), urgent (3d), expired (−27d) — so the tool shows all three warning levels
4. **Split contract files on two suppliers** — expired + unsigned draft, no single source of truth
5. **One supplier per feature** — early payment discount only in Galil, price unit ambiguity only in Siam Sugar, delivery dispute only in Ivoire Cacao — so each demo case has a distinct catch
6. **KPI computability** — every thread has enough outbound/reply pairs, prices, and dates for all four KPIs to calculate without gaps

---

## Q&A READINESS — PREDICTABLE QUESTIONS

**"Where does your commodity price data come from?"**
yfinance pulling CC=F (cocoa), SB=F (sugar), DC=F (dairy) for live spot prices. Static 24-month CSVs were pulled once via a script and saved locally. No cost, no API key — entirely public and keyless.

**"What does this cost at 80 suppliers?"**
~$7/month for 8 suppliers and 14 meetings. API cost scales roughly linearly — ~$70/month at 80 suppliers. Still trivial against the ₪100k/year labor cost avoidance anchor. The math holds at scale.

**Pacing note — demo runs long:**
The demo sits before Rollout & Change Management, which the brief flags as the most scrutinised section. If you're running short on time, compress Risks (Slide 14) and Quick Wins (Slide 17) — not Change Management or ROI. Know this in advance so you don't cut the wrong slide under pressure.

---

## IF ASKED ABOUT 10 CONTRACTS VS 8 SUPPLIERS
Two suppliers (Lowlands Dairy, Cana Doce) have split contract files — an expired version and a
draft/renewal. That reflects real procurement messiness: overlapping documents, unsigned renewals,
no single source of truth. The tool handles it and flags the ambiguity as an open issue.
