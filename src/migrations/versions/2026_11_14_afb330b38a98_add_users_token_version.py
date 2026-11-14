"""add users token_version

Revision ID: afb330b38a98
Revises: 0fd7f9fd32a7
Create Date: 2026-11-14 10:43:55.914678
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "afb330b38a98"
down_revision: str | Sequence[str] | None = "0fd7f9fd32a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("token_version", sa.Integer(), server_default="0", nullable=False))


def downgrade() -> None:
    op.drop_column("users", "token_version")
