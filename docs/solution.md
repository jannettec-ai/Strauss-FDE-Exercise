# Solution (Part 2)

## The pitch

An automated negotiation prep packet, generated ahead of every upcoming
supplier meeting, that pulls together the relevant email history,
contract terms, and price benchmark for that specific supplier into a
single one-page brief. It's built for the procurement analysts and
managers who currently spend hours before each negotiation manually
digging through inboxes, contract files, and spreadsheets, time the
Procurement Manager explicitly wants redirected toward judgment and
relationship-building instead of logistics. The packet doesn't make
decisions, it removes the busywork that stands between a procurement
professional and the negotiation table.

## What we considered and rejected

| Considered | Rejected because | Tradeoff accepted |
|---|---|---|
| A standalone commodity pricing dashboard | Answers an adjacent problem, not the manager's actual stated pain point (information work and logistics, not pricing accuracy). Also the most obvious build, every candidate likely gravitates here, low differentiation. | Pricing is folded in as one input to the packet instead of the centerpiece. A Market Intel page was added as supporting depth (accessible from the packet), not as a standalone feature. |
| A general "tracking what was agreed and with whom" feature | This is a system-of-record problem, not an AI problem, better solved by a database than a model. | Solved indirectly, the packet pulls from accurate, current contract terms rather than maintaining a separate tracking layer. |
| Teams chat as a fourth data source | Scope creep risk. The brief specifies four sources deliberately; adding a fifth, unprompted, late in a 3-day build, risks looking like I didn't trust the scope I was given. | Documented as a Phase 2 idea (see strategy.md) instead of built now. |
| Live MCP connector for pricing inside the prototype itself | A live demo depending on a third-party server responding correctly in the room is unnecessary risk for zero added insight value. | Two-layer approach instead: a one-time static pull for 24-month historical trend series (demo-day reliability), plus a fail-safe live fetch at startup via yfinance and public central bank APIs for spot prices, FX rates, and lending rates. MCP referenced narratively as the production-path upgrade, not built into this prototype. |
| Building real semantic layer / dbt-style metrics infrastructure | Solves a problem (multiple downstream consumers needing one consistent metric definition) that doesn't exist yet at this stage, one packet, one team, one prototype screen. | A lightweight metrics data dictionary instead (`.claude/rules/metrics.md`), same governance discipline, zero infrastructure overhead. |
| Vector store + live connectors in the prototype | Premature for the actual data volume here (8 suppliers, ~120 emails). Real value at hundreds of suppliers and thousands of emails, not this scale. | Local extraction pass against flat files for the prototype; vector store called out explicitly as the production-scale answer in the architecture section. |
| Full contract lifecycle management | Too broad a problem for the time available, and not the actual time-sink the brief describes. | Contract terms are read and surfaced, not managed end to end. |

Common thread across all seven: every cut traces back to either the
specific pain point in the brief, the three-day time constraint, or
live-demo reliability, not a general "didn't think of it" gap.

## How it works (architecture)

### Production data flow

Three source systems, each needing a different ingestion approach:

**Emails** — Microsoft Graph API (Outlook/Exchange) or Gmail API, scoped
to specific shared procurement mailboxes or folders, never personal
inboxes. Returns structured JSON natively (sender, recipients, subject,
body, timestamp). Scheduled pull or push subscription for new mail
matching supplier domains. Body text needs HTML-to-plaintext cleanup.

**Contracts** — live as PDFs/Word docs in a document store (SharePoint,
a contract management system like Icertis, or a network drive). Pipeline:
connector pulls the file, PDF text extraction (OCR if scanned), then an
LLM-based structured extraction pass pulls specific fields (payment
terms, volume commitments, penalty clauses, renewal dates) into a fixed
schema. Original document stays archived for audit; the extracted
structure is what the system actually queries day to day.

**Pricing** — a paid market data feed (Bloomberg, Refinitiv, ICE) or a
cheaper aggregator API. Already structured time-series data, minimal
conversion beyond normalizing into a common schema (date, commodity,
price, unit, source).

MCP connectors are the common plumbing layer across all three sources,
standardized tool interface, swappable backend per source, consistent
with how this would eventually plug into Strauss's real systems.

### Storage split

- **Structured/relational store** (e.g. BigQuery) for exact facts:
  contract terms, price points, KPI inputs. You want precise lookups
  here, not approximate matching, a price cap clause needs an exact
  value, not a "close enough" semantic match.
- **Vector store** for free text you want to search semantically: email
  bodies, contract clause language. Chunked and embedded so the packet
  generator can pull "what's relevant to Supplier X" without
  reprocessing every email live.

### Flow, end to end

```
[Email inbox]      --(Graph/Gmail API)-->      [Raw email JSON]
[Contract store]    --(connector + OCR/extraction)--> [Structured contract schema]
[Market data feed] --(Bloomberg/Refinitiv/ICE)--> [Normalized price series]
                                |
                                v
        [Structured store: exact facts]   [Vector store: searchable free text]
                                |
                                v
        [Packet Generator: per upcoming meeting, pulls relevant
         supplier emails + contract terms + price benchmark]
                                |
                                v
        [Negotiation Prep Packet — Streamlit interface]
                                |
                                v
        [Procurement Manager reviews, corrects, overrides]
```

### What's simplified in this prototype, and why

No live connectors, no vector store, no market data subscription, all
deliberate scope cuts for a 3-day embedded build, not architectural
ignorance:

- Synthetic emails as local JSON files instead of a live Graph/Gmail pull
- Synthetic contracts as local markdown instead of a document store + OCR
  pipeline
- Static CSV (one-time public data pull) instead of a live MCP pricing
  connector, removes demo-day network risk (see CLAUDE.md)
- A single local extraction pass instead of a vector store, justified at
  this data volume (8 suppliers, ~120 emails), would need to change at
  real scale (hundreds of suppliers, thousands of emails)

This is the version of the architecture answer to give if asked "why
doesn't your prototype look like what you just described": the
production design is right-sized for this prototype's actual data
volume and time constraint, not a simplification born of not knowing
the real pattern.

## The human in the loop

The packet is advisory only. It never sends an email, updates a
contract, or takes any action on the manager's behalf, every decision
stays with the human, the tool's only job is to remove the manual
assembly work in front of that decision.

**Source attribution, not silent facts.** Every figure in the packet is
traceable back to where it came from (e.g. "$3,050/ton, quoted by Amara
Koffi, email dated March 10," not just "$3,050/ton"). Nothing is
presented as settled ground truth without a visible source the manager
can click into and verify.

**Explicit flagging when sources conflict, not silent resolution.** The
Galil Dairy contract/email price discrepancy is the concrete example:
when the contract's price cap and an email's quoted price disagree, the
packet surfaces both and flags the conflict rather than picking one
number and presenting it cleanly. Same logic applies to the Siam Sugar
per-ton vs per-unit ambiguity, the packet states the ambiguity exists
instead of guessing an interpretation.

**A correction action built into the interface, not an afterthought.**
The manager can mark any field as wrong or flag it for review directly
in the packet view. This isn't just a UX nicety, it's the direct input
for the override/correction rate KPI, the system gets a real, visible
trust signal instead of an assumed one.

**What stops blind trust, concretely**: the combination of source
attribution and visible conflict-flagging means the tool's failure mode
is "this needs your judgment," not "this is silently wrong and looks
right." A manager who never looks past the headline number could still
be misled by any tool, what this prototype does is make sure looking
past the headline number is one click away, not buried.

