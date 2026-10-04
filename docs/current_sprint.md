# current_sprint.md

_Current sprint goals. Read at session start (AIConstitution §4)._

## Sprint 0 — Foundation & Runtime Docs (COMPLETE)

**Goal:** Stand up repo scaffold, toolchain + CI, Alembic bootstrap, and runtime docs.

### In Scope
- [x] A1 project scaffold
- [x] A2 toolchain + CI
- [x] A3 Alembic bootstrap
- [x] A4 runtime docs
- [x] A5 user prerequisites

## Definition of Done — Sprint 0
- [x] `docker compose up -d postgres` boots a healthy DB
- [x] `pytest` green, `ruff` + `mypy` clean, `pip-audit` clean, coverage ≥ 80%
- [x] `alembic upgrade head` idempotent
- [x] 5 runtime docs + changelog present under `docs/`

## Carried into Phase 1
- eBay developer account approval pending (blocks Phase 3 credentials only).
  See `docs/implementation.md` → Open Items / Blockers.
