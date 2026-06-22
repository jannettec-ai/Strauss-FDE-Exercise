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

| Stakeholder | Role | What they need | My read |
|---|---|---|---|
| Procurement Manager | Primary user, internal champion | Speed and accuracy; visible conflict flags; tool that doesn't embarrass them in front of a supplier | Likely the strongest ally — they named the problem themselves ("I want my team on judgment, not logistics"). Will adopt quickly if the first packet catches something real. Risk: if the first demo packet has a factual error, trust is hard to rebuild. |
| Procurement Analyst | Day-to-day user, also the person most threatened | Reduction in manual work; enough trust in the output to stake their prep on it | The highest adoption risk in the room. Will not say they feel threatened — will say "the output is wrong" or "it adds a review step." Counter this by involving them in Phase 1 QA, making the correction feature visibly theirs, and framing their role as reviewer not recipient. |
| IT / Systems | Enabler for any production path | Security review, data access governance, API key management | Not a blocker for the prototype, but a critical gating stakeholder for Phase 2 onward. Needs early visibility. The static-file architecture of this prototype is a feature here — nothing touches live systems, so the Phase 1 security surface is minimal. |
| Legal / Compliance | Risk owners | Confidence that AI-extracted contract terms are not treated as authoritative without human review | Potentially cautious. The source-attribution design (every fact traceable to its source) and the correction mechanism are the direct answer to their concern. Need to frame this as "surfaces contract terms for human review" not "interprets contracts." |
| Finance / CFO | Approver of ongoing cost | Measurable ROI in 90 days | Not a day-one stakeholder but the right person to bring the ROI case to in Phase 3. The numbers (₪51k/year in analyst time reclaimed) are an honest, conservative anchor — lead with labor cost avoidance, not speculative negotiation savings. |
| Supplier contacts | Indirect | No direct interaction | Not a stakeholder in adoption, but worth noting: better-prepared Strauss negotiators means suppliers face more informed counterparts. A well-run supplier relationship is a mutual benefit. |

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

## Week 1 plan — five things before touching technology

The assignment asks what the first five things are before writing a line of
code. These are they, in order:

**1. Shadow a prep session in real time.**
Sit next to an analyst while they prepare for an actual upcoming supplier
meeting. Don't ask them to describe the process — watch them do it. Note
which tabs they have open, how long each step takes, where they get stuck,
and what they skip when they're short on time. The stated process and the
actual process are almost always different.

**2. Interview the Procurement Manager separately.**
The manager and the analyst have different pain points. The manager's quote
("I want my team on judgment and relationships, not logistics") tells you
the desired outcome but not the failure mode. Ask: what has gone wrong in a
meeting because prep was incomplete? What did you wish you'd known walking
in? What would you never trust a tool to get right? The second and third
questions are as important as the first.

**3. Audit the actual data sources, not descriptions of them.**
Request read-only access to: one supplier's email thread in Outlook, one
contract file on SharePoint (or wherever they live), and the current price
benchmark spreadsheet. Look at real messiness — how many email threads exist
per supplier, what the contract file naming convention actually is, whether
the price spreadsheet is owned by one person or many. You cannot design a
robust extraction layer without seeing the raw input.

**4. Map what a "good packet" looks like by working backwards.**
Pick the three highest-stakes upcoming meetings from the calendar and ask
the manager: if you had one page of perfect context for each of these, what
would be on it? This surfaces the prioritisation the tool needs to make —
what to include and, equally important, what to leave out.

**5. Identify the first real meeting to demo against.**
Before building anything, agree on a specific upcoming meeting that will
serve as the success test for Phase 1. This forces the stakeholder to commit
to an evaluation moment and gives you a concrete target. It also means the
first demo is not a toy example — it's something the manager actually cares
about walking into.

---

## Build schedule (after the above five steps)

| Day | Focus |
|---|---|
| 1 | Data generation: supplier roster, emails (8 suppliers), contracts (8 + split files), calendar, price pull |
| 2 | Backend: extraction.py (AI extraction pass), packet_generator.py (per-meeting packet assembly) |
| 3 | Frontend: Streamlit app.py, end-to-end demo packet, QA on golden-path and edge cases |
