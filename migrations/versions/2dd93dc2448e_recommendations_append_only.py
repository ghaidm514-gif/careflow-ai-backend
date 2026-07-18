"""recommendations append only

Corrects AIRecommendation cardinality: one request may hold many immutable
recommendation rows, ordered by sequence_number. Drops the old one-per-request
unique constraint, adds (request_id, sequence_number) uniqueness, and extends
PostgreSQL append-only trigger protection to ai_recommendations.

Revision ID: 2dd93dc2448e
Revises: f6f6706f024d
Create Date: 2026-07-18 17:48:15.798742
"""

from collections.abc import Sequence
from typing import Optional, Union

import sqlalchemy as sa
from alembic import op

revision: str = "2dd93dc2448e"
down_revision: Optional[str] = "f6f6706f024d"
branch_labels: Optional[Union[str, Sequence[str]]] = None
depends_on: Optional[Union[str, Sequence[str]]] = None

# Naming convention lets SQLite batch mode identify the previously unnamed
# UNIQUE(request_id) constraint during table recreation.
NAMING = {"uq": "uq_%(table_name)s_%(column_0_name)s"}


def upgrade() -> None:
    dialect = op.get_bind().dialect.name

    # 1. Drop the old one-recommendation-per-request unique constraint.
    if dialect == "postgresql":
        op.drop_constraint(
            "ai_recommendations_request_id_key", "ai_recommendations", type_="unique"
        )
    else:
        with op.batch_alter_table("ai_recommendations", naming_convention=NAMING) as batch_op:
            batch_op.drop_constraint("uq_ai_recommendations_request_id", type_="unique")

    # 2. Add sequence_number (server_default guards non-empty tables) and the
    #    composite uniqueness + supporting index.
    with op.batch_alter_table("ai_recommendations") as batch_op:
        batch_op.add_column(
            sa.Column("sequence_number", sa.Integer(), nullable=False, server_default="1")
        )
        batch_op.create_index("ix_ai_recommendations_request_id", ["request_id"], unique=False)
        batch_op.create_unique_constraint(
            "uq_ai_recommendations_request_sequence", ["request_id", "sequence_number"]
        )

    # 3. ai_recommendations is now append-only: extend trigger protection (PG only).
    if dialect == "postgresql":
        op.execute(
            """
            CREATE TRIGGER trg_ai_recommendations_append_only
            BEFORE UPDATE OR DELETE ON ai_recommendations
            FOR EACH ROW EXECUTE FUNCTION careflow_block_mutation();
            """
        )


def downgrade() -> None:
    dialect = op.get_bind().dialect.name

    if dialect == "postgresql":
        op.execute(
            "DROP TRIGGER IF EXISTS trg_ai_recommendations_append_only ON ai_recommendations;"
        )

    with op.batch_alter_table("ai_recommendations") as batch_op:
        batch_op.drop_constraint("uq_ai_recommendations_request_sequence", type_="unique")
        batch_op.drop_index("ix_ai_recommendations_request_id")
        batch_op.drop_column("sequence_number")

    # Restore the original one-per-request constraint.
    if dialect == "postgresql":
        op.create_unique_constraint(
            "ai_recommendations_request_id_key", "ai_recommendations", ["request_id"]
        )
    else:
        with op.batch_alter_table("ai_recommendations", naming_convention=NAMING) as batch_op:
            batch_op.create_unique_constraint("uq_ai_recommendations_request_id", ["request_id"])
