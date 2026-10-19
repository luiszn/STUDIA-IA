"""add tags to flashcards

Revision ID: acc58bb46804
Revises: 2734fe234a62
Create Date: 2026-10-05
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "acc58bb46804"
down_revision: str | None = "2734fe234a62"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Existing rows get an empty list, hence the server default.
    with op.batch_alter_table("flashcards", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "tags",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'[]'"),
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("flashcards", schema=None) as batch_op:
        batch_op.drop_column("tags")
