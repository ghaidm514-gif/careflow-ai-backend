"""PostgreSQL append-only and deletion-policy regression tests.

Runs against ONE isolated disposable PostgreSQL instance (pgserver) shared by
the whole module. Skipped with a documented reason when pgserver is not
importable; CI must provision pgserver (requirements-dev.txt) so these execute
rather than skip.
"""

import os
import shutil
import subprocess
import tempfile
import uuid

import pytest

pgserver = pytest.importorskip(
    "pgserver",
    reason="pgserver not installed — PostgreSQL append-only tests require the "
    "pinned dev dependency (see requirements-dev.txt); CI must run these.",
)
import psycopg  # noqa: E402
from psycopg import sql  # noqa: E402

pytestmark = pytest.mark.postgresql


def _one(cur: "psycopg.Cursor") -> tuple:
    """fetchone() that asserts a row exists (INSERT..RETURNING / COUNT always do)."""
    row = cur.fetchone()
    assert row is not None
    return row


# (table, pk column, update statement) for every append-only table.
APPEND_ONLY_CASES = [
    ("conversation_messages", "message_id", "UPDATE conversation_messages SET content = 'x'"),
    ("triage_answers", "answer_id", "UPDATE triage_answers SET user_answer = 'x'"),
    ("safety_flags", "flag_id", "UPDATE safety_flags SET description = 'x'"),
    ("ai_recommendations", "recommendation_id", "UPDATE ai_recommendations SET rationale = 'x'"),
    ("staff_decisions", "decision_id", "UPDATE staff_decisions SET notes = 'x'"),
    ("audit_logs", "log_id", "UPDATE audit_logs SET action = 'x'"),
]


@pytest.fixture(scope="module")
def pg_uri():
    """One disposable PostgreSQL instance for the module; destroyed afterwards.

    Data dir must be a short, space-free path (Unix socket limit ~103 bytes),
    so it lives in a mkdtemp under /tmp rather than inside the repository.
    """
    pgdata = tempfile.mkdtemp(prefix="cfpg_", dir="/tmp")
    server = pgserver.get_server(pgdata)
    uri = server.get_uri()
    env = {**os.environ, "CAREFLOW_DATABASE_URL": uri}
    result = subprocess.run(
        [".venv/bin/alembic", "upgrade", "head"], env=env, capture_output=True, text=True
    )
    assert result.returncode == 0, f"alembic upgrade head failed: {result.stderr[-1000:]}"
    yield uri
    server.cleanup()
    shutil.rmtree(pgdata, ignore_errors=True)


@pytest.fixture(scope="module")
def seeded(pg_uri):
    """Insert one full parent graph plus one row in every append-only table."""
    ids = {}
    with psycopg.connect(pg_uri) as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO user_sessions (session_id, language, is_authenticated, created_at) "
            "VALUES (gen_random_uuid(), 'en', false, now()) RETURNING session_id"
        )
        ids["session"] = _one(cur)[0]
        cur.execute(
            "INSERT INTO service_requests (request_id, session_id, initial_description, "
            "language, status, created_at, updated_at) VALUES (gen_random_uuid(), %s, 'demo', "
            "'en', 'pending', now(), now()) RETURNING request_id",
            (ids["session"],),
        )
        rid = ids["request"] = _one(cur)[0]
        cur.execute(
            "INSERT INTO staff_users (staff_user_id, email, role, created_at) VALUES "
            "(gen_random_uuid(), %s, 'triage_nurse', now()) RETURNING staff_user_id",
            (f"nurse-{uuid.uuid4().hex[:8]}@test.local",),
        )
        staff = ids["staff"] = _one(cur)[0]
        cur.execute(
            "INSERT INTO conversation_messages (message_id, request_id, role, content, "
            "message_type, created_at) VALUES (gen_random_uuid(), %s, 'user', 'original', "
            "'user_response', now()) RETURNING message_id",
            (rid,),
        )
        ids["conversation_messages"] = _one(cur)[0]
        cur.execute(
            "INSERT INTO triage_answers (answer_id, request_id, question_id, question_text, "
            "user_answer, processed_at) VALUES (gen_random_uuid(), %s, 'q1', 'Q?', 'original', "
            "now()) RETURNING answer_id",
            (rid,),
        )
        ids["triage_answers"] = _one(cur)[0]
        cur.execute(
            "INSERT INTO safety_flags (flag_id, request_id, rule_code, severity, description, "
            "action_taken, triggered_at) VALUES (gen_random_uuid(), %s, 'TEST', 'critical', "
            "'original', 'HUMAN_REVIEW', now()) RETURNING flag_id",
            (rid,),
        )
        ids["safety_flags"] = _one(cur)[0]
        cur.execute(
            "INSERT INTO ai_recommendations (recommendation_id, request_id, sequence_number, "
            "recommended_service, urgency_level, rationale, confidence, confidence_reason, "
            "model_provider, model_name, prompt_version, workflow_version, schema_version, "
            "generated_at) VALUES (gen_random_uuid(), %s, 1, 'primary_care', 'medium', "
            "'original', 0.8, 'c', 'anthropic', 'claude', '1.0.0', '1.0.0', '1.0.0', now()) "
            "RETURNING recommendation_id",
            (rid,),
        )
        ids["ai_recommendations"] = _one(cur)[0]
        cur.execute(
            "INSERT INTO staff_decisions (decision_id, request_id, staff_user_id, "
            "decision_type, decided_at) VALUES (gen_random_uuid(), %s, %s, 'accept', now()) "
            "RETURNING decision_id",
            (rid, staff),
        )
        ids["staff_decisions"] = _one(cur)[0]
        cur.execute(
            "INSERT INTO audit_logs (log_id, request_id, actor, action, logged_at) VALUES "
            "(gen_random_uuid(), %s, 'ai_system', 'original', now()) RETURNING log_id",
            (rid,),
        )
        ids["audit_logs"] = _one(cur)[0]
        conn.commit()
    return ids


@pytest.mark.parametrize(("table", "pk", "update_sql"), APPEND_ONLY_CASES)
def test_update_blocked(pg_uri, seeded, table, pk, update_sql):
    """UPDATE on every append-only table raises and leaves the row unchanged."""
    row_id = seeded[table]
    count_q = sql.SQL("SELECT COUNT(*) FROM {} WHERE {} = %s").format(
        sql.Identifier(table), sql.Identifier(pk)
    )
    update_q = sql.SQL("{} WHERE {} = %s").format(sql.SQL(update_sql), sql.Identifier(pk))
    with psycopg.connect(pg_uri) as conn:
        with pytest.raises(psycopg.errors.RaiseException, match="append-only"):
            with conn.cursor() as cur:
                cur.execute(update_q, (row_id,))
        conn.rollback()
        with conn.cursor() as cur:
            cur.execute(count_q, (row_id,))
            assert _one(cur)[0] == 1


@pytest.mark.parametrize(("table", "pk", "update_sql"), APPEND_ONLY_CASES)
def test_delete_blocked(pg_uri, seeded, table, pk, update_sql):
    """DELETE on every append-only table (incl. ai_recommendations) raises."""
    row_id = seeded[table]
    delete_q = sql.SQL("DELETE FROM {} WHERE {} = %s").format(
        sql.Identifier(table), sql.Identifier(pk)
    )
    count_q = sql.SQL("SELECT COUNT(*) FROM {} WHERE {} = %s").format(
        sql.Identifier(table), sql.Identifier(pk)
    )
    with psycopg.connect(pg_uri) as conn:
        with pytest.raises(psycopg.errors.RaiseException, match="append-only"):
            with conn.cursor() as cur:
                cur.execute(delete_q, (row_id,))
        conn.rollback()
        with conn.cursor() as cur:
            cur.execute(count_q, (row_id,))
            assert _one(cur)[0] == 1


def test_deleting_parent_request_cannot_remove_history(pg_uri, seeded):
    """DELETE on service_requests is blocked while historical children exist."""
    with psycopg.connect(pg_uri) as conn:
        with pytest.raises((psycopg.errors.ForeignKeyViolation, psycopg.errors.RaiseException)):
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM service_requests WHERE request_id = %s", (seeded["request"],)
                )
        conn.rollback()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM audit_logs WHERE request_id = %s", (seeded["request"],)
            )
            assert _one(cur)[0] == 1, "audit history must survive parent deletion attempts"


def test_deleting_session_cannot_remove_requests(pg_uri, seeded):
    """DELETE on user_sessions is blocked while requests reference it."""
    with psycopg.connect(pg_uri) as conn:
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            with conn.cursor() as cur:
                cur.execute("DELETE FROM user_sessions WHERE session_id = %s", (seeded["session"],))
        conn.rollback()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM service_requests WHERE session_id = %s",
                (seeded["session"],),
            )
            assert _one(cur)[0] == 1


async def test_repository_adapters_on_postgresql_via_asyncpg(pg_uri):
    """The SQLAlchemy adapters work end-to-end on PostgreSQL through asyncpg —
    the production driver path (create → flush → query → map to entities)."""
    from uuid import uuid4

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.domain.entities import AIRecommendation, ServiceRequest, UserSession
    from app.domain.enums import (
        Language,
        RecommendedService,
        RequestStatus,
        UrgencyLevel,
    )
    from app.infrastructure.repositories import (
        SQLAlchemyAIRecommendationRepository,
        SQLAlchemyServiceRequestRepository,
        SQLAlchemyUserSessionRepository,
    )

    async_url = pg_uri.replace("postgresql://", "postgresql+asyncpg://", 1)
    engine = create_async_engine(async_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as session:
            user_session = await SQLAlchemyUserSessionRepository(session).create(
                UserSession(session_id=uuid4(), language=Language.ARABIC)
            )
            request = await SQLAlchemyServiceRequestRepository(session).create(
                ServiceRequest(
                    request_id=uuid4(),
                    session_id=user_session.session_id,
                    initial_description="أريد إعادة جدولة موعدي",
                    language=Language.ARABIC,
                    status=RequestStatus.PENDING,
                )
            )
            rec_repo = SQLAlchemyAIRecommendationRepository(session)
            for seq in (1, 2):
                await rec_repo.add(
                    AIRecommendation(
                        recommendation_id=uuid4(),
                        request_id=request.request_id,
                        recommended_service=RecommendedService.ADMINISTRATIVE_SERVICE,
                        urgency_level=UrgencyLevel.LOW,
                        rationale=f"rev {seq}",
                        confidence=0.9,
                        confidence_reason="clear administrative request",
                        sequence_number=seq,
                    )
                )
            latest = await rec_repo.get_latest_for_request(request.request_id)
            assert latest is not None
            assert latest.sequence_number == 2
            assert latest.generated_at.tzinfo is not None  # timestamptz round-trip
            fetched = await SQLAlchemyServiceRequestRepository(session).get_by_id(
                request.request_id
            )
            assert fetched is not None
            assert fetched.initial_description == "أريد إعادة جدولة موعدي"  # UTF-8 Arabic
            await session.commit()
    finally:
        await engine.dispose()
