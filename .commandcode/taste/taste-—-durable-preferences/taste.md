# Taste — durable preferences
- Follows a rules-driven development methodology: consults the `Rules/` directory (AI Constitution, project development workflow, TechStack, runtime working documents) and conforms the plan to those rules before implementing. Confidence: 0.9
- Prefers a formal planning workflow: enters plan mode and writes a saved implementation plan before writing any code. Confidence: 0.85
- Prefers to be asked clarifying questions on open decisions (e.g., delivery channel, database, LLM provider) rather than having the agent assume — especially when a choice would deviate from the permitted TechStack. Confidence: 0.75
- Uses reference/example projects (e.g., MobileNutritionTracking) as templates for runtime working documents and project conventions. Confidence: 0.7
- Default backend stack: Python 3.12 + FastAPI + PostgreSQL (Docker) + SQLAlchemy 2.0 async + Alembic. Confidence: 0.7
- Prefers a monorepo layout (`backend/`, `frontend/`, `docs/`, `docker-compose.yml`, `.env.example`). Confidence: 0.65
- CI quality gates ordered security → lint → typecheck → test → coverage, with ≥80% coverage and dependency audits (pip-audit/npm audit). Confidence: 0.6
- Leans toward local/offline tools (e.g., Local Ollama) over cloud APIs when a task can run without an API key. Confidence: 0.7
- Prefers step-by-step, highly detailed implementation instructions written so a junior developer can follow along independently — copy-paste-able file contents, exact commands, and per-step verification/checklist gates. Confidence: 0.75
