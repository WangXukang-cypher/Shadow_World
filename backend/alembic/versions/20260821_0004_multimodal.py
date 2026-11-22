"""multimodal memories, knowledge graph, evolved skills

Revision ID: 20260821_0004
Revises: 20260819_0003
Create Date: 2026-08-21
"""

import sqlalchemy as sa

from alembic import op

revision = "20260821_0004"
down_revision = "20260819_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Messages: attachments for multimodal ---
    with op.batch_alter_table("messages") as batch:
        batch.add_column(sa.Column("attachments", sa.JSON, nullable=True))

    # --- Memories: multimodal + knowledge graph ---
    with op.batch_alter_table("memories") as batch:
        batch.add_column(sa.Column("image_path", sa.String(500), nullable=True))
        batch.add_column(sa.Column("image_description", sa.Text, nullable=True))
        batch.add_column(sa.Column("tags", sa.String(500), nullable=True))
        batch.add_column(sa.Column("entity_type", sa.String(50), nullable=True))

    # --- Skills: self-evolution metadata ---
    with op.batch_alter_table("skills") as batch:
        batch.add_column(
            sa.Column("source", sa.String(50), nullable=False, server_default="user")
        )
        batch.add_column(sa.Column("trigger_pattern", sa.String(200), nullable=True))

    # --- Memory Relations: knowledge graph edges ---
    op.create_table(
        "memory_relations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_memory_id",
            sa.String(36),
            sa.ForeignKey("memories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "target_memory_id",
            sa.String(36),
            sa.ForeignKey("memories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("relation_type", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Index("ix_memory_relations_user", "user_id"),
        sa.Index("ix_memory_relations_source", "source_memory_id"),
        sa.Index("ix_memory_relations_target", "target_memory_id"),
    )


def downgrade() -> None:
    op.drop_table("memory_relations")
    with op.batch_alter_table("skills") as batch:
        batch.drop_column("source")
        batch.drop_column("trigger_pattern")
    with op.batch_alter_table("memories") as batch:
        batch.drop_column("image_path")
        batch.drop_column("image_description")
        batch.drop_column("tags")
        batch.drop_column("entity_type")
    with op.batch_alter_table("messages") as batch:
        batch.drop_column("attachments")
