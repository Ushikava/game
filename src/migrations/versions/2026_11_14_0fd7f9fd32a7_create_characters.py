"""create characters

Revision ID: 0fd7f9fd32a7
Revises: 4ddc3667f94e
Create Date: 2026-11-14 10:10:02.090205
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0fd7f9fd32a7"
down_revision: str | Sequence[str] | None = "4ddc3667f94e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "characters",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("slot", sa.SmallInteger(), nullable=False),
        sa.Column("name", sa.String(length=16), nullable=False),
        sa.Column("x", sa.Double(), nullable=False),
        sa.Column("y", sa.Double(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("slot >= 0 AND slot < 5", name=op.f("ck_characters_slot_range")),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_characters_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_characters")),
        sa.UniqueConstraint("user_id", "slot", name=op.f("uq_characters_user_id_slot")),
    )
    op.create_index(op.f("ix_characters_user_id"), "characters", ["user_id"], unique=False)
    op.create_index("uq_characters_name_lower", "characters", [sa.literal_column("lower(name)")], unique=True)


def downgrade() -> None:
    op.drop_index("uq_characters_name_lower", table_name="characters")
    op.drop_index(op.f("ix_characters_user_id"), table_name="characters")
    op.drop_table("characters")
