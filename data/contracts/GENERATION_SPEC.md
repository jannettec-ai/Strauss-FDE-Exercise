# Generation Spec — data/contracts/

## What these files are
Each file is a realistic markdown summary of a Strauss supplier contract.
These are not full legal PDFs — they are structured extracts capturing the
fields relevant to negotiation prep: payment terms, volume commitments,
pricing, penalty clauses, and renewal dates. The format is intentionally
human-readable so the AI extraction layer and a non-technical Procurement
Manager can both use them directly.

## Source of truth for supplier list
See `data/suppliers-roster.md` for the full supplier list, categories, and
messiness profiles. Each contract file maps to exactly one supplier by
number (e.g., supplier_01_*, supplier_04_*). Do not invent new suppliers.

## Split-file suppliers
Two suppliers have more than one contract file:

- **Supplier 03 (Lowlands Dairy)** — two files: OLD + DRAFT
  The OLD file is the expired contract (STR-DAIRY-2024-007, lapsed Dec 2024).
  The DRAFT file is an unsigned renewal under negotiation as of June 2026.
  The prototype must surface the fact that NO active signed contract exists
  for this supplier — only a lapsed contract and an unsigned draft. This
  is a real compliance risk that should be explicitly flagged.

- **Supplier 05 (Cana Doce)** — two files: OLD + RENEWED
  The OLD file is the expired original contract.
  The RENEWED file is the currently active contract (STR-SUGAR-2025-018,
  effective October 2025). The prototype should use the RENEWED file as
  the source of truth for current terms, and flag any discrepancy between
  the two (e.g., minimum volume increased from 50 to 55 MT/quarter).

## Cross-reference notes requirement
Every contract's Notes section must name the specific inconsistency the
AI extraction logic is designed to surface — the exact field, the exact
discrepancy, and what the prototype should flag. Generic notes are not
acceptable. Each note should answer: "what should appear in the
negotiation prep packet for this supplier?"

## Format
Follow the header structure of supplier_01_ivoire_cacao.md exactly:
Contract ID, Supplier, Category, Effective Date, Term, Renewal Date,
then sections: Payment Terms / Volume Commitment / Pricing / Penalty
Clauses / Notes.
