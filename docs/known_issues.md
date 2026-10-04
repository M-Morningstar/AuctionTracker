# known_issues.md

_Recurring bugs and their solutions. Read at session start (AIConstitution §4)._

## `alembic init` fails: "Directory alembic already exists and is not empty"
- **Symptom:** `alembic init alembic` aborts and creates no `alembic.ini` / `env.py` / `script.py.mako`.
- **Cause:** Step 2.1 pre-creates `backend/alembic/versions/`, so the target dir is non-empty before init
  (`alembic init` refuses to initialize into a non-empty directory).
- **Fix:** remove the empty pre-created dir (`rm -rf backend/alembic`) then re-run `alembic init alembic`
  from `backend/`.

## `NoSuchModuleError: Can't load plugin: sqlalchemy.dialects:driver`
- **Symptom:** every Alembic command crashes because the dialect resolves to the literal name `driver`.
- **Cause:** `alembic/env.py` never overrides the URL, so Alembic uses the `alembic.ini` placeholder
  `sqlalchemy.url = driver://user:pass@localhost/dbname` instead of the real asyncpg URL from `.env`.
- **Fix:** ensure `env.py` contains `config.set_main_option("sqlalchemy.url", settings.database_url)`
  and `target_metadata = Base.metadata` (the Step 4.2 async template).

## pytest warning: "Unknown config option: asyncio_default_test_loop_scope"
- **Symptom:** `PytestConfigWarning` on every run with `pytest-asyncio==0.25.0`.
- **Cause:** `pyproject.toml` sets `asyncio_default_test_loop_scope`, which is only supported by
  `pytest-asyncio >= 0.26`.
- **Fix:** harmless for Sprint 0 (tests still pass). In Phase 1, when session-scoped loops become
  necessary for the shared asyncpg engine, bump `pytest-asyncio` to `>= 0.26`.
