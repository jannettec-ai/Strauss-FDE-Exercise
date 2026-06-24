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
Two-layer approach:

**Historical series (24-month weekly):** Cocoa (CC=F) and sugar (SB=F)
pulled once via `scripts/pull_prices.py` and saved as static CSVs in
`data/prices/`. Used for trend charts on the Market Intel page and for
the 6-month benchmark in meeting packets. Dairy (DC=F) data is genuinely
thin on Yahoo Finance — the gap is documented as realistic data messiness
rather than fabricated.

**Live spot prices + FX + lending rates:** Fetched at app startup via
`utils/data_fetcher.py` using yfinance (CC=F, SB=F, DC=F), Yahoo Finance
FX tickers (USDILS=X, EURILS=X, PLNILS=X, GBPILS=X), Bank of Israel
prime rate API, and NY Fed SOFR API. Cached in `st.session_state` for
the session. All fetches are fail-safe with labeled fallbacks — if a
source is unavailable the app loads normally with a fallback value and
source label. Live data powers the Market Intel page (3_Pricing.py)
and financial analysis features. No Anthropic API quota is consumed by
these fetches — yfinance and the public rate APIs are free and keyless.

## Out of scope (deliberately)
- Negotiation strategy / pricing decisions themselves (human judgment stays
  human, the tool surfaces context, it does not recommend a negotiation move)
- Full contract lifecycle management
- Live ERP or real-time system integration (synthetic data only for this build)
