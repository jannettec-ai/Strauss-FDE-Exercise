# Strategy (Part 4)

## Rollout phases

**Phase 1 — Controlled pilot (weeks 1-4)**
One analyst, two to three suppliers with the richest data (Ivoire Cacao,
Galil Dairy, Golden Coast), packets generated manually triggered by the
FDE before each meeting. Goal: prove the packet is useful and catches
real things, not just that it runs. Success gate: analyst uses it for
all three meetings and reports it saved meaningful prep time. Adoption
rate and correction rate tracked from day one.

**Phase 2 — Expanded pilot (weeks 5-8)**
All 14 upcoming meetings, all analysts, packets now auto-triggered from
the negotiation calendar (meeting scheduled = packet generated). Manager
reviews packet quality weekly with the FDE. Correction rate should be
dropping from Phase 1 baseline as extraction prompts get refined.
Success gate: packet adoption rate above 80% across the 14 meetings,
correction rate below 15%.

**Phase 3 — Handover and sustainability (weeks 9-12)**
FDE steps back. One internal analyst or IT contact owns the tool going
forward. Runbook written. Monitoring in place (packet generation logs,
correction rate tracked automatically). ROI case presented to
Procurement Director using 90-day actuals, not projections.

## Resistance plan

The highest-risk group is the individual procurement analysts, not the
manager. Three likely resistance patterns and how to address each:

**"This is going to replace me."** Address before it surfaces, not after.
Frame the tool in the first team session explicitly: it removes the
boring part (three hours of information assembly), it does not touch the
judgment part (what to say in the room, how to read a supplier, when to
push back). The correction/override feature is a visible signal that the
analyst's judgment stays in the loop, they're not just accepting AI
output, they're reviewing it.

**"The packet will be wrong and I'll look bad in the meeting."** This is
a legitimate concern, not paranoia. Counter it with two things: source
attribution on every fact (so the analyst can spot-check in 30 seconds
rather than trusting blindly), and a soft launch where packets are
optional and supplementary for the first two meetings before they become
the default. Build trust with the tool before making it the standard.

**"This adds work, not removes it."** If the analyst has to review a
packet full of errors, it costs more time than it saves. This is why the
correction rate KPI exists and why Phase 1 is small and controlled, you
want to catch a high error rate before it touches all 14 meetings, not
after.

## ROI case

**Assumptions (stated, not hidden):**
- Manual prep time per meeting: 2.5 hours (based on Procurement Manager's
  framing, no measured baseline exists pre-tool)
- AI-assisted prep time per meeting: estimated 20 minutes (packet review
  plus any corrections)
- Time saved per meeting: 2.17 hours
- Meetings per quarter: 14 (based on the negotiation calendar)
- Fully loaded hourly rate, senior procurement analyst Israel: ₪140/hour
  (based on published market data: avg ₪73-166/hour gross for procurement
  roles in Israel, midpoint ₪100-110 gross, x1.35 employer cost multiplier)
- Number of analysts doing this prep work: 3 (assumption, state if
  different)

**Calculation:**
- Per analyst per quarter: 2.17hrs x 14 meetings x ₪140 = ₪4,253
- Across 3 analysts per quarter: ₪12,759
- Annually: ~₪51,000 (~$14,000)

**What this number is and isn't:**
This is labor cost avoidance, time reclaimed from logistics and
redirected to judgment and relationships. It is not a claim of direct
negotiation savings. Attributing a commodity cost reduction to this tool
in 90 days is not defensible given market price movement as a confound.
The leading indicator for commercial upside is negotiation coverage:
what percentage of meetings did the manager walk into with full context
versus partial or none. Better-prepared negotiations correlate with
better outcomes; this tool increases preparation coverage. The dollar
impact of that is a Phase 3 hypothesis, not a Phase 1 claim.

**The honest version of the pitch to the CFO:**
"In 90 days we reclaimed approximately ₪51,000 in annual analyst time
currently spent on information work. We also increased full-context
preparation coverage from an estimated 40% of meetings to 93% of
meetings. We believe that coverage improvement has a commercial value,
but we are not ready to put a number on it yet."

## Phase 2 ideas (not in current scope)

- **Teams chat integration**: internal Teams chats are a natural next data
  source once the core packet earns trust, since they often contain
  undocumented context (an analyst mentioning a verbal price concession,
  a flagged delivery issue). Deliberately excluded from the initial build
  to avoid scope creep and to stay within the four data sources specified
  in the brief. Revisit only after adoption is proven on the core packet.
