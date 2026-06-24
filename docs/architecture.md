# Architecture — Production Data Infrastructure

## Overview

The prototype uses flat files and static CSVs for demo reliability. This
document describes what the production architecture would look like at
real Strauss scale (hundreds of suppliers, thousands of emails, multiple
procurement teams).

## End-to-end data flow

```
Source systems
     |
     v
Data Lake (Azure Blob / S3)
Raw emails, contracts, prices
in original format, append-only
     |
     v
Processing layer
Extraction, OCR, structuring
Claude API calls happen here
     |
     v
Data Warehouse (BigQuery / Postgres)
Structured facts: contract terms,
price snapshots, meeting metadata
     |
     v
Vector Store (Pinecone / pgvector)
Embedded email bodies and
contract clause text for
semantic search
     |
     v
Packet Generator
Pulls from both stores,
assembles the brief
```

## Layer by layer

### Ingestion layer

Three source systems, each with a different connector:

- **Emails**: Microsoft Graph API scoped to shared procurement mailboxes
  only, never personal inboxes. Scheduled pull or push subscription
  triggering on new mail from supplier domains. Returns structured JSON
  natively (sender, recipients, subject, body, timestamp). HTML-to-
  plaintext cleanup before storage.
- **Contracts**: SharePoint or Icertis connector pulling PDFs and Word
  docs from the document store. OCR pass for scanned documents before
  extraction. Original file archived untouched, extracted structure
  written separately.
- **Commodity prices**: Bloomberg, Refinitiv, or ICE feed. Already
  structured time-series data, minimal transformation beyond normalizing
  to a common schema (date, commodity, price, unit, source).

MCP connectors are the standardization layer in front of all three
sources, so the rest of the system doesn't care which source changes or
gets replaced.

### Data lake (Azure Blob / S3)

Raw, unprocessed data in its original format, append-only. Nothing gets
deleted. This is the audit trail and reprocessing source.

Two reasons this matters specifically in a procurement context:

1. **Auditability**: if there is ever a dispute about what a supplier
   said or agreed to, the original email or contract is here, untouched,
   with its original timestamp.
2. **Reprocessability**: if extraction logic improves (better prompts,
   better models), the raw files can be reprocessed without going back
   to the source system. This is how you improve packet quality over time
   without a re-ingestion project.

### Processing layer

Two pipeline stages:

**Extraction pipeline** (runs on ingestion):
- New email arrives, gets parsed, key facts extracted via Claude API,
  structured records written to the data warehouse.
- New contract uploaded, OCR if scanned, structured extraction pass,
  fields (payment terms, volume commitments, penalty clauses, renewal
  dates, price caps) written to the data warehouse.

**Packet assembly pipeline** (runs on demand, triggered by upcoming
meeting in the calendar):
- Pulls structured facts from the data warehouse for that supplier.
- Does semantic retrieval from the vector store for relevant email
  context ("what has this supplier said about pricing in the last 6
  months").
- Cross-references emails against contract terms for conflicts.
- Generates the one-page brief.

### Storage split

| Store | What goes here | Why |
|---|---|---|
| Data lake (Blob/S3) | Raw emails, PDFs, price CSVs | Audit trail, reprocessing source |
| Data warehouse (BigQuery/Postgres) | Extracted structured facts: contract terms, price snapshots, meeting metadata | Exact lookups, not approximate matching. A price cap clause needs a precise value. |
| Vector store (Pinecone/pgvector) | Chunked, embedded email bodies and contract clause text | Semantic retrieval: pull what's relevant to a supplier without scanning every document |

### Orchestration

- **Airflow or Prefect** for scheduled ingestion pipelines (daily price
  pull, hourly email sync).
- **Event-driven** for packet generation: an upcoming meeting in the
  calendar triggers packet creation automatically, not a batch job.

### Security and governance

- Row-level security in the data warehouse so analysts only see their
  own supplier data.
- All Claude API calls go through a proxy that strips PII before logging.
- Contract PDFs stay in the data lake with access-controlled signed URLs,
  they never get copied into the app layer.
- Full audit log of every packet generated, every field corrected, every
  analyst override, this feeds directly into the correction rate KPI.

### Monitoring

- **Correction rate** (from the KPI data dictionary) doubles as a
  production health metric: a spike in corrections signals extraction
  quality has degraded, triggering a prompt review before it affects
  more meetings.
- Packet generation latency tracked per supplier.
- Cost per packet tracked against budget.
- Data freshness alerts if email sync or price feed stops updating.

## What the prototype simplifies, and why

| Production | Prototype | Reason for simplification |
|---|---|---|
| Graph API + SharePoint connector | Flat JSON + markdown files | Demo reliability, no live auth dependencies |
| Data lake (Blob/S3) | Local file system | Not needed at 8-supplier scale |
| Data warehouse (BigQuery) | Direct file reads | Overkill for synthetic data volume |
| Vector store (Pinecone) | Single extraction pass | Justified at ~120 emails, changes at thousands |
| Live commodity feed (Bloomberg/Refinitiv) | Two-layer: static 24-month CSV for trend history (always available offline) + live fetch via yfinance and public central bank APIs for spot prices, FX rates, and lending rates at startup | Static history eliminates demo-day network risk for charts; live fetch keeps spot and FX current with fail-safe fallbacks |
| Airflow orchestration | Manual trigger in Streamlit | Not needed for a single-team prototype |

Every simplification is right-sized for 8 suppliers and a 3-day build,
not a shortcut born of not knowing the production pattern.
