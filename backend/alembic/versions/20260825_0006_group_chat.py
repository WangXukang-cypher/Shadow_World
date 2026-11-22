"""group chat support

Revision ID: 20260825_0006
Revises: 20260821_0005
Create Date: 2026-08-25
"""

import sqlalchemy as sa

from alembic import op

revision = "20260825_0006"
down_revision = "20260821_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("conversations") as batch:
        batch.add_column(sa.Column("is_group", sa.Boolean, nullable=False, server_default="0"))
        batch.add_column(sa.Column("persona_ids", sa.JSON, nullable=True))

    with op.batch_alter_table("messages") as batch:
        batch.add_column(sa.Column("persona_name", sa.String(100), nullable=True))
        batch.add_column(sa.Column("persona_avatar", sa.Text, nullable=True))
        batch.add_column(sa.Column("reply_to_id", sa.String(36), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("messages") as batch:
        batch.drop_column("reply_to_id")
        batch.drop_column("persona_avatar")
        batch.drop_column("persona_name")
    with op.batch_alter_table("conversations") as batch:
        batch.drop_column("persona_ids")
        batch.drop_column("is_group")
