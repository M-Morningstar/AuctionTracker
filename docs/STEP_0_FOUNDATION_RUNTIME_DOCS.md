# STEP 0 — Foundation & Runtime Docs (Sprint 0)

> Maps to the approved plan **Group A (Sprint 0)**: scaffold, toolchain + CI, Alembic bootstrap, constitution runtime docs, and user prerequisites.
> This file is a build blueprint — follow it top to bottom, in order. Do not skip a step. Each step ends with a **Verify** block; only move on when it passes.

---

## 0. What you're building (and why)

Sprint 0 does **not** build any scraping or valuation logic. It builds the **foundation** every later phase stands on:

- A clean monorepo layout (`backend/`, `frontend/`, `docs/`).
- A local PostgreSQL 16 database running in Docker.
- A Python toolchain that lints, type-checks, tests, and security-scans on every push.
- A working Alembic migration setup (empty baseline).
- The five "constitution" documents the AI orchestrator reads at the start of every session (see `Rules/01-AIConstitution.md` §4).

**Stack (locked):** FastAPI (Python 3.12) + SQLAlchemy 2.0 async + Alembic + PostgreSQL 16 + `uv` for dependency management.

---

## 1. Pre-flight — tools you need

Run these checks in a terminal. Every command should succeed before you start.

```bash
python3 --version        # expect 3.12.x
uv --version             # expect something like uv 0.x
docker --version
docker compose version
git --version
```

If `uv` is missing: `curl -LsSf https://astral.sh/uv/install.sh | sh` (then restart your shell).

Work from the project root for the whole of this document:

```bash
cd /home/mert/Desktop/Project/AuctionTracker
```

> Note: this directory is a git repo already (it has `.commandcode/`). If it is not yet a git repo, run `git init` first.

---

## 2. A1 — Project scaffold

### 2.1 Create the directory layout

```bash
mkdir -p backend/app/core backend/app/models backend/tests backend/alembic/versions backend/scripts
mkdir -p frontend docs .github/workflows
```

You will end up with:

```
AuctionTracker/
├── backend/
│   ├── app/
│   │   ├── core/
│   │   └── models/
│   ├── tests/
│   ├── alembic/
│   │   └── versions/
│   └── scripts/
├── frontend/
├── docs/
└── .github/workflows/
```

### 2.2 `.gitignore`

Create `/home/mert/Desktop/Project/AuctionTracker/.gitignore` with this content:

```gitignore
# Python
__pycache__/
*.py[cod]
*.egg-info/
.venv/
venv/
.mypy_cache/
.pytest_cache/
.ruff_cache/
.coverage
htmlcov/

# Env / secrets
.env
.env.*

# Node / frontend (used from Phase 5)
node_modules/
frontend/dist/

# OS / IDE
.DS_Store
.vscode/
.idea/

# Docker data volume
pgdata/
```

### 2.3 `.env.example` (placeholders ONLY — never real secrets)

Create `/home/mert/Desktop/Project/AuctionTracker/.env.example`:

```dotenv
# Database (PostgreSQL 16 in Docker)
POSTGRES_USER=auction
POSTGRES_PASSWORD=auction
POSTGRES_DB=auction

# Used by local host-side tooling (alembic / uvicorn run from your machine).
# The docker-compose FastAPI service overrides this to point at the container.
DATABASE_URL=postgresql+asyncpg://auction:auction@localhost:5433/auction

# --- Added in later phases (keep as empty placeholders for now) ---
# Phase 1: HiBid scraper needs no secret.
# Phase 2: local Ollama endpoint.
OLLAMA_BASE_URL=http://localhost:11434
# Phase 3: eBay developer credentials.
EBAY_CLIENT_ID=your_ebay_client_id_here
EBAY_CLIENT_SECRET=your_ebay_client_secret_here
# Phase 5: Discord webhook.
DISCORD_WEBHOOK_URL=your_discord_webhook_url_here
```

Now create your local `.env` (gitignored) from the example:

```bash
cp .env.example .env
```

### 2.4 `docker-compose.yml` (Postgres only for Sprint 0)

Create `/home/mert/Desktop/Project/AuctionTracker/docker-compose.yml`:

```yaml
services:
  postgres:
    image: postgres:16
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-auction}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-auction}
      POSTGRES_DB: ${POSTGRES_DB:-auction}
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "127.0.0.1:5433:5432"   # localhost only — never expose publicly
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-auction} -d ${POSTGRES_DB:-auction}"]
      interval: 5s
      timeout: 5s
      retries: 10

volumes:
  pgdata:
```

> The `fastapi` service is added in Phase 5 (Group H). Sprint 0 only needs the database up.

### 2.5 `README.md` (skeleton)

Create `/home/mert/Desktop/Project/AuctionTracker/README.md`:

```markdown
# AuctionTracker

Automated pipeline that scrapes Calgary HiBid auctions, normalizes titles, values items against
multiple secondary markets, and delivers a daily high-ROI hotlist via Discord + a local dashboard.

## Stack
FastAPI (Python 3.12) · PostgreSQL 16 · SQLAlchemy 2.0 async · Alembic · Crawl4AI · Local Ollama ·
Vite + React + TS dashboard.

## Status
Sprint 0 — foundation in progress. See `docs/implementation.md`.

## Quick start (dev)
1. `cp .env.example .env`
2. `docker compose up -d postgres`
3. `cd backend && uv sync && alembic upgrade head`
4. `uvicorn app.main:app --reload`
```

### 2.6 Verify A1

```bash
docker compose up -d postgres
docker compose ps          # postgres should be "Up" (healthy)
```

If you see a healthy `postgres` container, A1 is done.

---

## 3. A2 — Python toolchain + CI

### 3.1 Create the virtual environment

```bash
cd backend
uv venv --python 3.12
source .venv/bin/activate        # Windows: .venv\Scripts\activate
```

> Keep this terminal (or re-run `source .venv/bin/activate`) for all later `uv`/`alembic`/`pytest` commands. `(auctiontracker-backend)` should appear in your prompt.

### 3.2 Dependencies

Create `/home/mert/Desktop/Project/AuctionTracker/backend/requirements.txt`:

```text
fastapi==0.136.0
starlette==1.3.1
uvicorn[standard]==0.34.0
sqlalchemy[asyncio]==2.0.38
asyncpg==0.30.0
alembic==1.14.1
pydantic==2.10.5
pydantic-settings==2.7.1
httpx==0.28.1
```

Create `/home/mert/Desktop/Project/AuctionTracker/backend/requirements-dev.txt`:

```text
-r requirements.txt

pytest==8.3.4
pytest-asyncio==0.25.0
respx==0.22.0
pytest-cov==6.0.0
ruff==0.9.4
mypy==1.14.1
pip-audit==2.7.3
```

Install:

```bash
uv pip install -r requirements.txt -r requirements-dev.txt
```

> **Security gate (mandatory):** these pins were audited clean at plan time. After install, run
> `pip-audit -r requirements.txt`. If it reports an advisory, bump the affected pin to a fixed
> version, reinstall, and re-run until it prints **"No known vulnerabilities found"**. Never leave
> a known-vulnerable pin in place.

### 3.3 `pyproject.toml` (tool config — not dependency management here)

Create `/home/mert/Desktop/Project/AuctionTracker/backend/pyproject.toml`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
addopts = "-q"
# Session-scoped loops: Phase 1 introduces a shared asyncpg engine. Tests and
# fixtures must live on the SAME event loop, otherwise asyncpg connections
# created in a fixture fail with "Future attached to a different loop" when
# used inside function-scoped tests.
asyncio_default_fixture_loop_scope = "session"
asyncio_default_test_loop_scope = "session"

[tool.ruff]
line-length = 110
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM"]

[tool.mypy]
python_version = "3.12"
plugins = ["pydantic.mypy"]
warn_unused_configs = true
strict = true
exclude = ["alembic/"]

[tool.coverage.run]
source = ["app"]
omit = ["app/models/*"]
# SQLAlchemy async runs coroutines inside greenlets; coverage must be told to
# track that concurrency model or every line after an `await` is falsely
# reported as uncovered. "thread" covers httpx/ASGI test transport internals.
concurrency = ["greenlet", "thread"]

[tool.coverage.report]
fail_under = 80
```

### 3.4 The app package (minimal, health-check only)

Create these files.

`/home/mert/Desktop/Project/AuctionTracker/backend/app/__init__.py` (empty):

```python
```

`/home/mert/Desktop/Project/AuctionTracker/backend/app/core/__init__.py` (empty):

```python
```

`/home/mert/Desktop/Project/AuctionTracker/backend/app/core/config.py`:

```python
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# config.py lives at backend/app/core/config.py
BACKEND_DIR = Path(__file__).resolve().parents[2]   # .../backend
ROOT_DIR = BACKEND_DIR.parent                       # .../AuctionTracker (repo root)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "AuctionTracker"
    database_url: str = "postgresql+asyncpg://auction:auction@localhost:5433/auction"


settings = Settings()
```

`/home/mert/Desktop/Project/AuctionTracker/backend/app/main.py`:

```python
from fastapi import FastAPI

from app.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name)
    register_routes(app)
    return app


def register_routes(app: FastAPI) -> None:
    @app.get("/healthz")
    async def healthz() -> dict:
        return {"status": "ok", "app": settings.app_name}


app = create_app()
```

`/home/mert/Desktop/Project/AuctionTracker/backend/app/db.py`:

```python
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings

engine = create_async_engine(settings.database_url, echo=False)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)
```

> `get_session()` (the FastAPI dependency) is added in Phase 1 when the first endpoint actually
> touches the database. Keeping the Sprint 0 surface minimal keeps the coverage gate green.

`/home/mert/Desktop/Project/AuctionTracker/backend/app/models/__init__.py`:

```python
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for all ORM models (tables are added from Phase 1)."""
```

### 3.5 Tests

Create `/home/mert/Desktop/Project/AuctionTracker/backend/tests/__init__.py` (empty):

```python
```

Create `/home/mert/Desktop/Project/AuctionTracker/backend/tests/test_healthz.py`:

```python
from httpx import ASGITransport, AsyncClient

from app.main import app


async def test_healthz() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "app": "AuctionTracker"}
```

Create `/home/mert/Desktop/Project/AuctionTracker/backend/tests/test_db.py`:

```python
import app.db as db


def test_engine_and_session_factory_configured() -> None:
    assert db.engine is not None
    assert db.async_session_factory is not None
```

> `pytest` is in `asyncio_mode = "auto"`, so `async def test_...` needs no extra marker.

### 3.6 Run the toolchain locally

```bash
pytest                                   # expect 2 passed
ruff check app tests                     # expect "All checks passed!"
mypy app                                 # expect "Success: no issues found"
pip-audit -r requirements.txt            # expect "No known vulnerabilities found"
pytest --cov=app --cov-report=term-missing
```

Fix anything that fails before continuing.

### 3.7 CI workflow (runs on every push)

Create `/home/mert/Desktop/Project/AuctionTracker/.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
  pull_request:

jobs:
  # Order matters (AIConstitution FLOW 2B): security FIRST, coverage LAST.
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install deps
        run: |
          cd backend
          pip install -r requirements.txt -r requirements-dev.txt
      - name: pip-audit (dependency vulnerability scan)
        run: |
          cd backend
          pip-audit -r requirements.txt

  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install ruff
      - run: cd backend && ruff check app tests

  typecheck:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: cd backend && pip install -r requirements.txt -r requirements-dev.txt
      - run: cd backend && mypy app

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: cd backend && pip install -r requirements.txt -r requirements-dev.txt
      - run: cd backend && pytest

  coverage:
    needs: [security, lint, typecheck, test]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: cd backend && pip install -r requirements.txt -r requirements-dev.txt
      - run: cd backend && pytest --cov=app --cov-report=term-missing --cov-fail-under=80
```

### 3.8 Verify A2

- All five local commands in §3.6 pass.
- Commit and push; the `CI` run on GitHub is green (all 5 jobs).

---

## 4. A3 — Alembic bootstrap

Alembic manages database schema changes as versioned migrations. Sprint 0 sets up an **empty baseline**; real tables arrive in Phase 1.

### 4.1 Initialize Alembic

From `backend/` (with the venv active):

```bash
alembic init alembic
```

This creates `alembic.ini`, `alembic/env.py`, `alembic/script.py.mako`, and `alembic/versions/`.

Edit `alembic.ini` — confirm (or add) these two lines:

```ini
script_location = alembic
prepend_sys_path = .
```

`prepend_sys_path = .` lets `env.py` import `from app.core.config import settings` when Alembic runs from `backend/`.

### 4.2 Make `env.py` async

Replace the entire content of `backend/alembic/env.py` with:

```python
import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

from app.core.config import settings
from app.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Single source of truth: the URL comes from app settings (reads .env).
config.set_main_option("sqlalchemy.url", settings.database_url)

# Empty in Sprint 0 — models are added from Phase 1 onward, then autogenerate
# will pick them up automatically.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Emit SQL without a live database (for review / CI)."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

### 4.3 Create the empty baseline migration

```bash
alembic revision -m "baseline"
```

This creates `backend/alembic/versions/<random-hex>_baseline.py`. Open it and confirm:

- `revision = "<random-hex>"` — a random id like `a1b2c3d4e5f6`.
- `down_revision = None`.
- `upgrade()` and `downgrade()` are empty (`pass`).

> **Important:** never hand-set `revision` to the literal string `"base"` or `"head"` — those are
> reserved internal symbols and will crash every Alembic command (see example project ADR-015).

### 4.4 Apply and verify

Make sure Postgres is up (`docker compose up -d postgres`), then from `backend/`:

```bash
alembic upgrade head      # applies the baseline (creates alembic_version table)
alembic upgrade head      # second run: "No migrations to apply" (idempotent)
alembic history           # shows "base -> <hex> (head)"
alembic heads             # shows the single head revision id
```

Also verify the offline SQL path works without touching the DB:

```bash
alembic upgrade head --sql
```

### 4.5 Verify A3

- `alembic upgrade head` succeeds twice (idempotent).
- `alembic history` / `alembic heads` show one clean linear chain.
- `docker compose exec postgres psql -U auction -d auction -c '\dt'` shows the `alembic_version` table.

---

## 5. A4 — Constitution runtime docs

The orchestrator reads five files at the start of every session (`Rules/01-AIConstitution.md` §4).
Create all five **plus** a changelog under `docs/`. Fill them in as you work; start with these skeletons.

### `docs/project_state.md`

```markdown
# project_state.md

_Managed by the AI orchestrator. Read at session start (AIConstitution §4). Updated at every gate/commit._

## Project Identity
- **Name:** AuctionTracker — HiBid Arbitrage Engine
- **Type:** Single-user, local, self-hosted analysis tool
- **Goal:** Scrape Calgary HiBid auctions, normalize titles, value against multiple secondary markets, deliver a daily high-ROI hotlist.
- **Phase:** Sprint 0 (foundation) — IN PROGRESS
- **Governance:** Rules/01-AIConstitution, 00-ProjectDevelopmentWorkflow, 14-TechStack, 15-AgentOrchestration, 19-SecurityGovernance

## Confirmed Decisions
1. Backend: FastAPI (Python 3.12) — mandated by Crawl4AI being Python-only.
2. Database: PostgreSQL 16 (Docker) + SQLAlchemy 2.0 async + Alembic.
3. LLM normalization: local Ollama (offline).
4. Valuation: multi-source — eBay sold + Amazon/BestBuy/Walmart new + Facebook Marketplace used.
5. Delivery: Discord webhook + local Vite+React+TS dashboard.

## Current Status
- Sprint 0 in progress. See `docs/implementation.md`.

## Rules in Effect
- Security review MUST precede the coverage gate (FLOW 2B).
- No plaintext secrets; `.env.example` placeholders only.
- API versioned `/api/v1`.
- Coverage ≥ 80%.
```

### `docs/implementation.md`

```markdown
# implementation.md

_Active development plan — managed with "To Do" / "In Progress" / "Done" / "Blocked" statuses (AIConstitution §4, §5 FLOW 2B). Read at session start._

**Status legend:** `[ ]` To Do · `[~]` In Progress · `[x]` Done · `[B]` Blocked
**Authoritative spec:** `~/.commandcode/plans/auctiontracker-implementation-plan.md`

## Group A — Project Foundation & Runtime Docs
- [ ] A1: Project scaffold (monorepo, docker-compose postgres, .env.example, .gitignore, README)
- [ ] A2: Python toolchain + CI (pytest/ruff/mypy/coverage, pip-audit, GitHub Actions)
- [ ] A3: Alembic bootstrap (async engine, empty baseline, verified idempotent)
- [ ] A4: Constitution runtime docs (5 + changelog)
- [ ] A5: User prerequisites (eBay creds, Ollama model, Discord webhook)

## Execution Rules (AIConstitution)
1. Execute SEQUENTIALLY.
2. Each completed task → update status here + commit (conventional message).
3. Security review MUST precede coverage gate.
4. Debugging: max 3 attempts per issue (FLOW 2C), then escalate.
```

### `docs/decisions.md`

```markdown
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
```

### `docs/current_sprint.md`

```markdown
# current_sprint.md

_Current sprint goals. Read at session start (AIConstitution §4)._

## Sprint 0 — Foundation & Runtime Docs (IN PROGRESS)

**Goal:** Stand up repo scaffold, toolchain + CI, Alembic bootstrap, and runtime docs.

### In Scope
- [ ] A1 project scaffold
- [ ] A2 toolchain + CI
- [ ] A3 Alembic bootstrap
- [ ] A4 runtime docs
- [ ] A5 user prerequisites

## Definition of Done — Sprint 0
- [ ] `docker compose up -d postgres` boots a healthy DB
- [ ] `pytest` green, `ruff` + `mypy` clean, `pip-audit` clean, coverage ≥ 80%
- [ ] `alembic upgrade head` idempotent
- [ ] 5 runtime docs + changelog present under `docs/`
```

### `docs/known_issues.md`

```markdown
# known_issues.md

_Recurring bugs and their solutions. Read at session start (AIConstitution §4)._

<!-- Record issues as you find them, e.g.:
## alembic AssertionError
- **Symptom:** every alembic command crashes with `AssertionError`.
- **Cause:** a migration set `revision = "base"` (reserved symbol).
- **Fix:** use a pseudo-SHA id instead.
-->
```

### `docs/changelog.md`

```markdown
# changelog.md

All notable changes to AuctionTracker.

## [Unreleased]
### Added
- Sprint 0 foundation (in progress).
```

### Verify A4

```bash
ls docs
# expect: changelog.md, current_sprint.md, decisions.md, implementation.md, known_issues.md, project_state.md, STEP_0_FOUNDATION_RUNTIME_DOCS.md
```

---

## 6. A5 — User prerequisites (no code; collect credentials)

These are things **you** (the owner) must provide, stored only in the gitignored `.env`. The AI/developer cannot generate them.

1. **eBay developer credentials** (Phase 3): create an app at the eBay Developer Portal, note the **App ID (Client ID)** and **Cert ID (Client Secret)**. Put them in `.env` as `EBAY_CLIENT_ID` / `EBAY_CLIENT_SECRET`.
2. **Ollama model** (Phase 2): install Ollama and pull a model, e.g. `ollama pull qwen2.5:7b`. Put the endpoint in `.env` as `OLLAMA_BASE_URL`.
3. **Discord webhook** (Phase 5): create a webhook in a Discord server, copy the URL into `.env` as `DISCORD_WEBHOOK_URL`.

> You do **not** need these for Sprint 0 — just know where they go. Values must never be committed or logged.

---

## 7. Definition of Done — Sprint 0

All of these must be true before moving to Phase 1:

- [ ] Monorepo layout exists (`backend/`, `frontend/`, `docs/`, `.github/`).
- [ ] `docker compose up -d postgres` → healthy container on `127.0.0.1:5433`.
- [ ] `pytest` → 2 passed.
- [ ] `ruff check app tests` → clean.
- [ ] `mypy app` → no issues.
- [ ] `pip-audit -r requirements.txt` → no known vulnerabilities.
- [ ] `pytest --cov=app --cov-fail-under=80` → green.
- [ ] `alembic upgrade head` → idempotent (runs twice cleanly).
- [ ] Five runtime docs + changelog present under `docs/`.
- [ ] `ci.yml` committed; CI green on push.
- [ ] `.env` is gitignored; `.env.example` contains placeholders only.

When done, mark Group A tasks `[x]` in `docs/implementation.md`, commit with `feat(scaffold): set up Sprint 0 foundation`, and update `project_state.md` / `current_sprint.md`.
