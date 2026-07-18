"""restrict deletion policy

Replaces CASCADE with RESTRICT on every business-history foreign key so that
historical healthcare, decision, and audit records can never disappear through
parent deletion. user_sessions.staff_user_id keeps SET NULL (nullable actor
reference). ServiceRequest closing is a status transition, never a deletion.

PostgreSQL-only DDL: SQLite does not enforce foreign keys by default and is
used solely for local structural verification; Alembic autogenerate does not
compare ondelete, so alembic check stays consistent on both dialects.

Revision ID: 3ab41c9de001
Revises: 2dd93dc2448e
Create Date: 2026-07-18
"""

from collections.abc import Sequence
from typing import Optional, Union

from alembic import op

revision: str = "3ab41c9de001"
down_revision: Optional[str] = "2dd93dc2448e"
branch_labels: Optional[Union[str, Sequence[str]]] = None
depends_on: Optional[Union[str, Sequence[str]]] = None

# (table, constraint, column, referred table, referred column)
RESTRICT_FKS = [
    (
        "service_requests",
        "service_requests_session_id_fkey",
        "session_id",
        "user_sessions",
        "session_id",
    ),
    (
        "conversation_messages",
        "conversation_messages_request_id_fkey",
        "request_id",
        "service_requests",
        "request_id",
    ),
    (
        "triage_answers",
        "triage_answers_request_id_fkey",
        "request_id",
        "service_requests",
        "request_id",
    ),
    (
        "safety_flags",
        "safety_flags_request_id_fkey",
        "request_id",
        "service_requests",
        "request_id",
    ),
    (
        "ai_recommendations",
        "ai_recommendations_request_id_fkey",
        "request_id",
        "service_requests",
        "request_id",
    ),
    (
        "staff_decisions",
        "staff_decisions_request_id_fkey",
        "request_id",
        "service_requests",
        "request_id",
    ),
    ("audit_logs", "audit_logs_request_id_fkey", "request_id", "service_requests", "request_id"),
]


def _swap_ondelete(target: str) -> None:
    for table, constraint, column, ref_table, ref_column in RESTRICT_FKS:
        op.drop_constraint(constraint, table, type_="foreignkey")
        op.create_foreign_key(constraint, table, ref_table, [column], [ref_column], ondelete=target)


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    _swap_ondelete("RESTRICT")


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    _swap_ondelete("CASCADE")
