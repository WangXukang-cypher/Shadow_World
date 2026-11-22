"""people and social commitments

Revision ID: 20260821_0005
Revises: 20260821_0004
Create Date: 2026-08-21
"""

import sqlalchemy as sa

from alembic import op

revision = "20260821_0005"
down_revision = "20260821_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "people",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("nickname", sa.String(100), nullable=True),
        sa.Column("relationship", sa.String(50), nullable=False, server_default="朋友"),
        sa.Column("traits", sa.String(500), nullable=True),
        sa.Column("birthday", sa.String(20), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("mention_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_mentioned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "name", name="uq_people_user_name"),
        sa.Index("ix_people_user", "user_id"),
    )

    op.create_table(
        "social_commitments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "person_id",
            sa.String(36),
            sa.ForeignKey("people.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("source_message_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Index("ix_social_commitments_user", "user_id", "status"),
    )


def downgrade() -> None:
    op.drop_table("social_commitments")
    op.drop_table("people")
