# Project: Strauss Procurement Negotiation Prep Packet

## What this is
An FDE take-home exercise prototype for Strauss Group. The Procurement team
spends too much time on information work (chasing supplier emails, pulling
price benchmarks, summarizing contracts, tracking what was agreed) instead of
judgment and relationships. This prototype auto-generates a one-page
negotiation prep packet ahead of each upcoming supplier meeting, combining:
supplier email history, relevant contract terms, and the public commodity
price benchmark for that supplier's category.

## Who it's for
A non-technical Procurement Manager. The interface must be usable without
any explanation of how the underlying logic works.

## Tech stack
- Python backend
- Streamlit interface
- Claude API for email/contract extraction and summarization
- Synthetic data only, generated for this exercise, no real Strauss data

## Data conventions
- All synthetic data lives in `/data` (emails, contracts, prices, calendar)
- Data must be realistically messy: inconsistent formatting, late replies,
  ambiguous phrasing, at least one supplier who is hard to reach. Do not
  generate clean, uniform records.
- No placeholder fields. Every field referenced in the prototype must be
  populated by real (synthetic) data, not assumed or hardcoded at demo time.

## Hard constraints
- Solo build, no collaboration tools or shared repos with others
- No real Strauss data or confidential information of any kind
- Every line of generated code must be something Claude (the candidate) can
  explain and defend in a live Q&A

## Metrics
KPI definitions, formulas, and source fields are NOT in this file.
See `.claude/rules/metrics.md` and load it before writing any calculation
logic. All KPI math in the codebase must match that dictionary exactly,
do not redefine a metric inline.

## Reference docs (not loaded into build context, see docs/)
- `docs/problem-framing.md` — pain points, stakeholder map, Week 1 plan
- `docs/strategy.md` — rollout phases, risks, ROI case, change management

## Pricing data decision
Cocoa (CC=F) and sugar (SB=F) futures: pulled once via a one-time script
(yfinance or similar), saved as static CSV in /data/prices. The live
prototype reads from that CSV, not a live API or MCP connection, to remove
demo-day network risk. Dairy data is genuinely thin/inconsistent on public
sources, do not fabricate clean dairy numbers, document the gap as real
data messiness instead. MCP is referenced only in the architecture
narrative (docs/strategy.md), as the production-path upgrade, not built
into this prototype.

## Out of scope (deliberately)
- Negotiation strategy / pricing decisions themselves (human judgment stays
  human, the tool surfaces context, it does not recommend a negotiation move)
- Full contract lifecycle management
- Live ERP or real-time system integration (synthetic data only for this build)
