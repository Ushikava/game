"""add characters health

Revision ID: a7cdf7392c21
Revises: afb330b38a98
Create Date: 2026-11-14 12:17:58.807875
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a7cdf7392c21"
down_revision: str | Sequence[str] | None = "afb330b38a98"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("characters", sa.Column("health", sa.Integer(), server_default="1000", nullable=False))
    op.create_check_constraint(op.f("ck_characters_health_non_negative"), "characters", "health >= 0")


def downgrade() -> None:
    op.drop_constraint(op.f("ck_characters_health_non_negative"), "characters", type_="check")
    op.drop_column("characters", "health")
