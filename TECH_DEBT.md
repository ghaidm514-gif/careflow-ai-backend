# Technical Debt Register

## PHASE3-BLOCKER-001 — Alembic migration proof (deferred from Phase 2)

**Status:** RESOLVED (Step 3.1 — verified on SQLite and real PostgreSQL)
**Approved deferral:** Phase 2 was frozen without applied migrations because ORM
models did not yet exist.

Required before repository implementations:
1. Define SQLAlchemy Base and ORM models.
2. Configure alembic.ini with correct target_metadata.
3. Generate and review the initial revision.
4. Apply to an isolated development/test database (never production Supabase).
5. Prove `alembic upgrade head`, `alembic current`, `alembic check`.
6. Prove downgrade and re-upgrade in the isolated environment.

## ENV-001 — Python 3.12 unavailable

Declared target is Python 3.12; only 3.9.6 exists on this machine. Ruff
target-version pinned to py39. Bump to py312 and apply pyupgrade fixes when a
3.12 interpreter is provisioned.

## ENV-002 — PostgreSQL unavailable locally — RESOLVED

Resolved via `pgserver` (pip-installed, self-contained PostgreSQL running as an
isolated disposable instance; pinned in requirements-dev.txt). Verified on real
PostgreSQL: full migration cycle (upgrade/current/check/downgrade/re-upgrade),
append-only triggers blocking UPDATE/DELETE, multi-row recommendations, JSONB
and native UUID column types. Note: the instance data dir must live in a short,
space-free path (Unix socket limit); tests use a temp dir outside the repo.
Production Supabase remains untouched.
