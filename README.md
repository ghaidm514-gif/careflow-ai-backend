# CareFlow AI — Backend

Bilingual healthcare navigation and initial triage assistant.

## Phase 2: Foundation

Infrastructure scaffolding with clean architecture.

## Quick Start

```bash
# Install dependencies
poetry install

# Run tests
poetry run pytest -v

# Lint and format
poetry run ruff check .
poetry run ruff format .

# Type check
poetry run pyright

# Start dev server
poetry run uvicorn app.main:app --reload
```

## Architecture

- `domain/` — Business logic (no external dependencies)
- `application/` — Workflows and repository ports
- `infrastructure/` — Database, LLM, authentication
- `api/` — HTTP routes and endpoints
- `core/` — Utilities (RBAC, configuration)

## Health Checks

```bash
# Liveness
curl http://localhost:8000/health/live

# Readiness
curl http://localhost:8000/health/ready
```

See README.md for full documentation.
