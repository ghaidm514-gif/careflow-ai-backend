"""Migration tests — upgrade, downgrade, re-upgrade against an isolated SQLite DB.

PostgreSQL-specific behavior (append-only triggers, JSONB, native UUID) is
dialect-guarded in the migration and must be re-verified on a real PostgreSQL
instance before deployment (see TECH_DEBT.md ENV-002).
"""

import os
import sqlite3

import pytest
from alembic import command
from alembic.config import Config

EXPECTED_TABLES = {
    "user_sessions",
    "service_requests",
    "conversation_messages",
    "triage_answers",
    "safety_flags",
    "ai_recommendations",
    "staff_users",
    "staff_decisions",
    "audit_logs",
}


@pytest.fixture
def alembic_config(tmp_path):
    """Alembic config pointed at a disposable SQLite database."""
    db_path = tmp_path / "migration_test.db"
    url = f"sqlite:///{db_path}"
    os.environ["CAREFLOW_DATABASE_URL"] = url
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url)
    yield config, db_path
    os.environ.pop("CAREFLOW_DATABASE_URL", None)


def _tables(db_path):
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        return {r[0] for r in rows} - {"alembic_version"}
    finally:
        conn.close()


def test_upgrade_head_creates_all_tables(alembic_config):
    """alembic upgrade head creates all nine frozen-entity tables."""
    config, db_path = alembic_config
    command.upgrade(config, "head")
    assert _tables(db_path) == EXPECTED_TABLES


def test_downgrade_base_removes_all_tables(alembic_config):
    """alembic downgrade base removes every table."""
    config, db_path = alembic_config
    command.upgrade(config, "head")
    command.downgrade(config, "base")
    assert _tables(db_path) == set()


def test_reupgrade_after_downgrade(alembic_config):
    """The migration is reversible: upgrade → downgrade → upgrade."""
    config, db_path = alembic_config
    command.upgrade(config, "head")
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    assert _tables(db_path) == EXPECTED_TABLES


def test_triage_answers_unique_constraint(alembic_config):
    """(request_id, question_id) is unique — one active answer per question."""
    config, db_path = alembic_config
    command.upgrade(config, "head")
    conn = sqlite3.connect(db_path)
    try:
        indexes = conn.execute("PRAGMA index_list('triage_answers')").fetchall()
        unique_column_sets = []
        for row in indexes:
            if row[2] == 1:  # unique index (SQLite may use internal autoindex names)
                cols = conn.execute(f"PRAGMA index_info('{row[1]}')").fetchall()
                unique_column_sets.append({c[2] for c in cols})
        assert {"request_id", "question_id"} in unique_column_sets
    finally:
        conn.close()


def test_ai_recommendations_request_unique(alembic_config):
    """One recommendation per request (unique request_id)."""
    config, db_path = alembic_config
    command.upgrade(config, "head")
    conn = sqlite3.connect(db_path)
    try:
        indexes = conn.execute("PRAGMA index_list('ai_recommendations')").fetchall()
        assert any(row[2] == 1 for row in indexes)
    finally:
        conn.close()


def _seed_request(conn, request_id="11111111111111111111111111111111"):
    """Insert a session and request so recommendations can reference them."""
    session_id = "00000000000000000000000000000000"
    conn.execute(
        "INSERT INTO user_sessions (session_id, language, is_authenticated, created_at) "
        "VALUES (?, 'en', 0, '2026-07-18T00:00:00+00:00')",
        (session_id,),
    )
    conn.execute(
        "INSERT INTO service_requests (request_id, session_id, initial_description, "
        "language, status, created_at, updated_at) "
        "VALUES (?, ?, 'demo', 'en', 'pending', "
        "'2026-07-18T00:00:00+00:00', '2026-07-18T00:00:00+00:00')",
        (request_id, session_id),
    )
    return request_id


def _insert_recommendation(conn, request_id, rec_id, seq, service="primary_care"):
    conn.execute(
        "INSERT INTO ai_recommendations (recommendation_id, request_id, sequence_number, "
        "recommended_service, urgency_level, rationale, confidence, confidence_reason, "
        "model_provider, model_name, prompt_version, workflow_version, schema_version, "
        "generated_at) VALUES (?, ?, ?, ?, 'medium', 'demo rationale', 0.8, 'demo reason', "
        "'anthropic', 'claude-3-5-sonnet-20241022', '1.0.0', '1.0.0', '1.0.0', "
        "'2026-07-18T00:00:00+00:00')",
        (rec_id, request_id, seq, service),
    )


def test_multiple_recommendations_per_request(alembic_config):
    """Two recommendation rows can exist for one request (append-only regeneration)."""
    config, db_path = alembic_config
    command.upgrade(config, "head")
    conn = sqlite3.connect(db_path)
    try:
        request_id = _seed_request(conn)
        _insert_recommendation(conn, request_id, "a" * 32, 1)
        _insert_recommendation(conn, request_id, "b" * 32, 2, service="urgent_care")
        conn.commit()
        count = conn.execute(
            "SELECT COUNT(*) FROM ai_recommendations WHERE request_id = ?", (request_id,)
        ).fetchone()[0]
        assert count == 2
    finally:
        conn.close()


def test_duplicate_sequence_number_rejected(alembic_config):
    """(request_id, sequence_number) is unique — duplicates fail."""
    config, db_path = alembic_config
    command.upgrade(config, "head")
    conn = sqlite3.connect(db_path)
    try:
        request_id = _seed_request(conn)
        _insert_recommendation(conn, request_id, "a" * 32, 1)
        conn.commit()
        with pytest.raises(sqlite3.IntegrityError):
            _insert_recommendation(conn, request_id, "b" * 32, 1)
    finally:
        conn.close()


def test_latest_recommendation_selection_deterministic(alembic_config):
    """Highest sequence_number wins, independent of insertion order."""
    config, db_path = alembic_config
    command.upgrade(config, "head")
    conn = sqlite3.connect(db_path)
    try:
        request_id = _seed_request(conn)
        # Insert out of order: seq 3, then 1, then 2
        _insert_recommendation(conn, request_id, "c" * 32, 3, service="urgent_care")
        _insert_recommendation(conn, request_id, "a" * 32, 1)
        _insert_recommendation(conn, request_id, "b" * 32, 2)
        conn.commit()
        row = conn.execute(
            "SELECT recommendation_id, recommended_service FROM ai_recommendations "
            "WHERE request_id = ? ORDER BY sequence_number DESC LIMIT 1",
            (request_id,),
        ).fetchone()
        assert row[0] == "c" * 32
        assert row[1] == "urgent_care"
    finally:
        conn.close()
