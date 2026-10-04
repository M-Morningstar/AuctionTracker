# implementation.md

_Active development plan — managed with "To Do" / "In Progress" / "Done" / "Blocked" statuses (AIConstitution §4, §5 FLOW 2B). Read at session start._

**Status legend:** `[ ]` To Do · `[~]` In Progress · `[x]` Done · `[B]` Blocked
**Authoritative spec:** `~/.commandcode/plans/auctiontracker-implementation-plan.md`

## Group A — Project Foundation & Runtime Docs
- [x] A1: Project scaffold (monorepo, docker-compose postgres, .env.example, .gitignore, README)
- [x] A2: Python toolchain + CI (pytest/ruff/mypy/coverage, pip-audit, GitHub Actions)
- [x] A3: Alembic bootstrap (async engine, empty baseline, verified idempotent)
- [x] A4: Constitution runtime docs (5 + changelog)
- [x] A5: User prerequisites (eBay creds, Ollama model, Discord webhook)

### Open Items / Blockers
- **[B] eBay developer account — pending approval.** `EBAY_CLIENT_ID` / `EBAY_CLIENT_SECRET` cannot be
  issued until eBay approves the application. Blocks **Phase 3** (eBay sold-comps valuation) only; Sprint 0
  does not depend on it. Placeholders remain in `.env`.

## Execution Rules (AIConstitution)
1. Execute SEQUENTIALLY.
2. Each completed task → update status here + commit (conventional message).
3. Security review MUST precede coverage gate.
4. Debugging: max 3 attempts per issue (FLOW 2C), then escalate.
