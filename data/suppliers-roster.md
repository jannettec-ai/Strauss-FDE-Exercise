# Supplier Roster (reference for all synthetic data generation)

8 suppliers across 5 categories and multiple geographies, matching the
brief. Every email, contract, price reference, and calendar entry must use
these exact supplier names and categories, no inventing new ones mid-build.

| # | Supplier | Category | Geography | Messiness profile |
|---|---|---|---|---|
| 1 | Ivoire Cacao Export | Cocoa | Côte d'Ivoire | Slow responder (2-5 day email gaps), two contacts (sales rep + ops manager) who don't coordinate, occasionally contradict each other |
| 2 | Golden Coast Cocoa Traders | Cocoa | Ghana | Recent delivery issue (late shipment, quality complaint) still unresolved across the email thread, no clean resolution |
| 3 | Lowlands Dairy Co-op | Dairy | Netherlands | Mid-renegotiation on volume commitments, contract terms and recent emails partially conflict |
| 4 | Galil Dairy Suppliers | Dairy | Israel | One email mentions a price increase that contradicts the contract's price cap clause, planted inconsistency for the AI to surface |
| 5 | Cana Doce Açúcar | Sugar | Brazil | Very formal, clean correspondence, but a renewal date conflict exists between the contract and a calendar meeting |
| 6 | Siam Sugar Partners | Sugar | Thailand | English-as-second-language phrasing, slightly inconsistent terminology, occasional ambiguity in quoted prices (per ton vs per unit unclear) |
| 7 | Sierra Verde Coffee Cooperative | Coffee | Colombia | Relationship-heavy emails, personal/relational notes mixed into business content, harder to extract structured facts cleanly |
| 8 | EuroPack Solutions | Packaging | Poland | Multi-person CC chains, scope/spec changed mid-negotiation, thread gets harder to follow over time |

## Notes for data generation

- Categories map to the pricing data we'll use: cocoa (suppliers 1-2),
  dairy (3-4), sugar (5-6). Coffee and packaging (7-8) have no commodity
  price benchmark in scope, contract terms and email history only for
  those two.
- Each supplier should have somewhere between 10-20 emails across the
  6-month window (not evenly distributed, real correspondence is bursty).
- Each of the 8 suppliers gets exactly one contract.
- The 14 negotiation meetings (calendar) should weight toward the
  suppliers with the most "story" (1, 2, 3, 4) since those make for the
  strongest demo packets, but all 8 should appear at least once.
