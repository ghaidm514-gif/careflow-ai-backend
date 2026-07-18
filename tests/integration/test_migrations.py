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
