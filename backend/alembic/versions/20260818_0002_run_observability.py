"""run observability, cancellation and tool-call audit

Revision ID: 20260818_0002
Revises: 20260817_0001
Create Date: 2026-08-18
"""

import sqlalchemy as sa

from alembic import op

revision = "20260818_0002"
down_revision = "20260817_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("agent_runs") as batch:
        batch.add_column(
            sa.Column("model_name", sa.String(length=120), nullable=False, server_default="")
        )
        batch.add_column(
            sa.Column("iteration_count", sa.Integer(), nullable=False, server_default="0")
        )
        batch.add_column(
            sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0")
        )
        batch.add_column(
            sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default="0")
        )
        batch.add_column(
            sa.Column("cancel_requested_at", sa.DateTime(timezone=True), nullable=True)
        )

    op.create_table(
        "tool_calls",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("call_id", sa.String(length=120), nullable=False),
        sa.Column("tool_name", sa.String(length=120), nullable=False),
        sa.Column("arguments", sa.JSON(), nullable=False),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("model_content", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("side_effect", sa.String(length=30), nullable=False),
        sa.Column("idempotency_key", sa.String(length=64), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key"),
    )
    op.create_index("ix_tool_calls_run_created", "tool_calls", ["run_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_tool_calls_run_created", table_name="tool_calls")
    op.drop_table("tool_calls")
    with op.batch_alter_table("agent_runs") as batch:
        batch.drop_column("cancel_requested_at")
        batch.drop_column("completion_tokens")
        batch.drop_column("prompt_tokens")
        batch.drop_column("iteration_count")
        batch.drop_column("model_name")
