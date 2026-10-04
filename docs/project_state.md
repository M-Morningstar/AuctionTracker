# project_state.md

_Managed by the AI orchestrator. Read at session start (AIConstitution §4). Updated at every gate/commit._

## Project Identity
- **Name:** AuctionTracker — HiBid Arbitrage Engine
- **Type:** Single-user, local, self-hosted analysis tool
- **Goal:** Scrape Calgary HiBid auctions, normalize titles, value against multiple secondary markets, deliver a daily high-ROI hotlist.
- **Phase:** Sprint 0 (foundation) — COMPLETE
- **Governance:** Rules/01-AIConstitution, 00-ProjectDevelopmentWorkflow, 14-TechStack, 15-AgentOrchestration, 19-SecurityGovernance

## Confirmed Decisions
1. Backend: FastAPI (Python 3.12) — mandated by Crawl4AI being Python-only.
2. Database: PostgreSQL 16 (Docker) + SQLAlchemy 2.0 async + Alembic.
3. LLM normalization: local Ollama (offline).
4. Valuation: multi-source — eBay sold + Amazon/BestBuy/Walmart new + Facebook Marketplace used.
5. Delivery: Discord webhook + local Vite+React+TS dashboard.

## Current Status
- Sprint 0 complete: monorepo scaffold, Dockerized PostgreSQL 16, Python toolchain + GitHub Actions CI,
  async Alembic bootstrap (empty baseline, verified idempotent), and six runtime docs under `docs/`.
- Next: Phase 1 (scraping) — not started. See `docs/implementation.md`.

## Blockers / Open Items
- **eBay developer account — pending approval.** `EBAY_CLIENT_ID` / `EBAY_CLIENT_SECRET` cannot be issued
  until eBay approves the application. Blocks **Phase 3** (eBay sold-comps valuation) only; Sprint 0 does
  not depend on it. Placeholders remain in `.env`.

## Rules in Effect
- Security review MUST precede the coverage gate (FLOW 2B).
- No plaintext secrets; `.env.example` placeholders only.
- API versioned `/api/v1`.
- Coverage ≥ 80%.
