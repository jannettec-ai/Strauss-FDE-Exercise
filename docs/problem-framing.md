# Problem Framing (Part 1)

## The pain point

Strauss Group's Procurement team manages roughly 80+ active supplier
relationships across cocoa, dairy, sugar, coffee, and packaging. Ahead of
each supplier negotiation meeting, a Procurement Manager or analyst manually
assembles the context they need to walk in prepared:

- Pull recent email history with that supplier from Outlook (searching by
  supplier name or domain across a shared mailbox)
- Find the relevant contract (stored in SharePoint or a network drive, often
  with multiple versions — expired, draft, renewed)
- Look up the commodity price benchmark for the supplier's category
  (separate spreadsheet, sometimes stale)
- Mentally synthesize these into a coherent picture of: where things stand,
  what was agreed, what's unresolved, and what to watch out for

**Time cost:** In interviews and brief observation, this assembly process
takes 45–90 minutes per meeting. The Procurement Manager explicitly described
this as "information logistics" — work that stands between them and the
actual judgment call they're paid to make.

**Frequency:** The team runs 10–20 supplier meetings per month. At 45–90
minutes of prep each, this is a recurring 8–30 hour/month information
assembly burden across the team.

## The specific failure modes

The manual process fails in consistent and predictable ways:

1. **Missed contract clauses.** The manager pulls the wrong contract version,
   or doesn't notice a penalty clause that's relevant to a current dispute.
   Example pattern: supplier quotes a new price casually over email; manager
   doesn't cross-check against the contract's price cap clause before the
   meeting.

2. **Open threads go cold.** A delivery dispute or quality complaint is raised
   over email, acknowledged, and then no one follows up. By the time the
   next meeting arrives, the thread has dropped out of working memory and
   isn't surfaced in prep.

3. **Benchmark data is stale or missing.** The commodity price spreadsheet
   is updated inconsistently. Managers sometimes walk into cocoa or sugar
   negotiations without knowing where the market has moved since the last
   meeting.

4. **No active contract flagged too late.** A contract expires and renewal
   negotiations drag. The team continues operating on informal terms for
   months before someone notices there's no signed document in force.

## Who this is for

**Primary user:** Procurement Manager (non-technical). Receives the packet,
reviews it before the meeting, possibly flags corrections. Does not need to
understand how the extraction works, only needs to trust what it surfaces
and be able to challenge it when something looks wrong.

**Secondary user (prototype scope):** The same person, also running the tool
— selecting the upcoming meeting from the calendar and triggering packet
generation. In production, this would be automated ahead of every scheduled
supplier meeting.

## Stakeholder map

| Stakeholder | Role | What they need from this tool |
|---|---|---|
| Procurement Manager | Primary user | Accurate, fast prep; visible flags for conflicts and open issues |
| Procurement Analyst | Secondary user / data owner | Reduced manual assembly; clean output to work from |
| Legal / Compliance | Downstream | Confidence that contract terms are being read and surfaced, not ignored |
| Finance | Downstream | Price benchmarking and contract delta visible; not buried in email chains |
| Supplier contacts | Indirect | No direct interaction, but quality of Strauss's negotiation prep affects relationship outcomes |

## Why AI, why now

The bottleneck is not analysis — it's assembly. The Procurement Manager
is capable of synthesizing supplier context once it's in front of them.
The problem is that getting it in front of them takes too long and misses
things. This is exactly the task profile where AI extraction adds value:
processing unstructured text (email bodies, contract clauses) at a per-
meeting cost of seconds rather than minutes, with consistent coverage of
every field every time.

The risk is blind trust — if the extraction is wrong and the manager doesn't
notice, the prep packet actively misleads. The design response to this risk
is: source attribution on every field, explicit conflict flagging when sources
disagree, and a visible correction action in the UI. The tool should make
the manager faster to get to judgment, not replace their judgment.

## Week 1 plan (prototype scope)

| Day | Focus |
|---|---|
| 1 | Data generation: supplier roster, emails (8 suppliers), contracts (8 + split files), calendar, price pull |
| 2 | Backend: extraction.py (AI extraction pass), packet_generator.py (per-meeting packet assembly) |
| 3 | Frontend: Streamlit app.py, end-to-end demo packet, QA on golden-path and edge cases |
