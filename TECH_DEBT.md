# Technical Debt Register

## PHASE3-BLOCKER-001 — Alembic migration proof (deferred from Phase 2)

**Status:** IN PROGRESS (Step 3.1)
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

## ENV-002 — PostgreSQL unavailable locally

No Docker or PostgreSQL on this machine. Migration verification runs against a
disposable SQLite database with dialect-portable column types. PostgreSQL-only
protections (append-only triggers) are dialect-guarded in migrations and must
be re-verified against a real PostgreSQL instance before deployment.
