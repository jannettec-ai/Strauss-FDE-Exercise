# Email Generation Spec — Suppliers 2-8

Reference: `data/suppliers-roster.md` for supplier names, categories, and
messiness profiles. Reference: `data/emails/supplier_01_ivoire_cacao.json`
as the exact quality bar and JSON format to match.

## Instructions for Claude Code

For each of suppliers 2-8, generate a JSON file at
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

**Per-supplier messiness to bake in** (pull directly from the roster, but
as a reminder):

- **Supplier 2 (Golden Coast Cocoa Traders)**: unresolved delivery/quality
  complaint. The thread should NOT reach a clean resolution by the end,
  that's realistic and useful for the prototype to surface as "open issue."
- **Supplier 3 (Lowlands Dairy Co-op)**: mid-renegotiation on volume
  commitments. At least one email should propose new volume terms that
  partially conflict with what's in the existing contract.
- **Supplier 4 (Galil Dairy Suppliers)**: critical, this is the planted
  inconsistency. The contract (`data/contracts/supplier_04_galil_dairy.md`,
  already written) caps the price at ₪14.20/kg (~$3.85/kg) per Section 4.2,
  no increase valid without a written amendment. One email must mention a
  new price above that, e.g. ₪15.50/kg or ~$4.20/kg, framed casually
  ("given where the market is, we'll need to move to..."), with no
  reference to a written amendment or Strauss approval. Keep it natural,
  don't make it obviously flagged, the AI extraction logic should be the
  one to catch it.
- **Supplier 5 (Cana Doce Açúcar)**: formal, polished, professional tone
  throughout, contrast with the others. The conflict here lives in dates,
  not tone, a renewal date mentioned in emails should not quite match the
  contract's renewal date (off by a few weeks).
- **Supplier 6 (Siam Sugar Partners)**: English-as-second-language
  phrasing throughout (grammatically imperfect but understandable). At
  least one price quote should be ambiguous about unit (per ton vs per
  unit) in a way a careful reader would have to question.
- **Supplier 7 (Sierra Verde Coffee Cooperative)**: warm, relationship-
  heavy emails, personal notes (asking about David's family, referencing
  a past visit) mixed into business content, making clean extraction
  genuinely harder.
- **Supplier 8 (EuroPack Solutions)**: multi-person CC chains (3-4 people
  across emails), a spec or scope change partway through the thread that
  isn't clearly acknowledged by all parties.

## Sender consistency

Use `david.cohen@strauss-group.com` as the Strauss-side procurement
contact across all suppliers, matching supplier_01, for consistency.

## After generation

Spot-check at least 2-3 emails per supplier file for realism before moving
on, don't assume the first pass is usable as-is.
