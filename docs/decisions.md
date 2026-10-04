# decisions.md

_Architecture Decision Record (ADR) + approvals. Read at session start (AIConstitution §4)._

## Stack Summary (Sprint 0)

| Component | Decision | License | Status |
|---|---|---|---|
| Backend | FastAPI (Python 3.12) + Uvicorn | MIT | Accepted |
| Database | PostgreSQL 16 (Docker) | PostgreSQL License | Approved by user |
| ORM/migrations | SQLAlchemy 2.0 async + Alembic | MIT | Accepted |
| Scraping | Crawl4AI | Apache-2.0 | Pre-approved by brief |
| LLM normalization | Local Ollama | MIT | Approved by user |
| Valuation | Multi-source (eBay/retail/Facebook) | BSD-3 / Apache-2.0 / MIT | Approved by user |
| Delivery | Discord webhook + Vite+React+TS dashboard | MIT | Approved by user |

## ADR Entries
- **ADR-001 Backend:** FastAPI over Django — async I/O for scraping/valuation, native OpenAPI, Python-mandated by Crawl4AI.

## Package Approvals
All permissive licenses. Human approval required for anything not listed in the plan.
