# CareFlow AI — Backend

Bilingual healthcare navigation and initial triage assistant.

## Phase 2: Foundation

Infrastructure scaffolding with clean architecture.

## Python Version

- **Declared target:** Python 3.12 (pyproject.toml).
- **Currently verified local environment:** Python 3.9.6 — the only interpreter
  available on this machine. All quality gates and tests execute on 3.9.6; the
  code uses only 3.9-compatible syntax.
- **Open requirement:** Python 3.12 verification in CI/deployment remains
  outstanding (TECH_DEBT.md ENV-001).

## Quick Start

The verified local workflow is **venv + pip** (Poetry is not installed on this
machine; `pyproject.toml` carries package metadata and tool configuration only).

```bash
# Create environment and install pinned dependencies
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt -r requirements-dev.txt

# Run tests
.venv/bin/pytest -v

# Lint and format
.venv/bin/ruff check .
.venv/bin/ruff format --check .

# Type check
.venv/bin/pyright

# Start dev server
.venv/bin/uvicorn app.main:app --reload
```

## Architecture

- `domain/` — Business logic (no external dependencies)
- `application/` — Workflows and repository ports
- `infrastructure/` — Database, LLM, authentication
- `api/` — HTTP routes and endpoints
- `core/` — Utilities (RBAC, configuration)

## Database Drivers

PostgreSQL (Supabase) is the production target. Two pinned drivers serve two
execution contexts from one plain `postgresql://` URL:

- **asyncpg** — the async application engine (`postgresql+asyncpg://`, converted
  automatically in `app/infrastructure/database.py`)
- **psycopg v3** — synchronous Alembic migrations (`postgresql+psycopg://`,
  converted automatically in `migrations/env.py`)

SQLite is supported for isolated local verification only.

## Health Checks

```bash
# Liveness
curl http://localhost:8000/health/live

# Readiness
curl http://localhost:8000/health/ready
```

See README.md for full documentation.
