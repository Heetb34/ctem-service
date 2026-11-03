"""initial evidence + chain_heads

Revision ID: 0001
Revises:
Create Date: 2026-01-05
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "chain_heads",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("head_hash", sa.String(64), nullable=False),
        sa.Column("head_evidence_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("chain_length", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "evidence",
        sa.Column("evidence_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("exposure_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("workflow_execution_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("content_type", sa.String(255), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("s3_key", sa.Text(), nullable=False),
        sa.Column("s3_version_id", sa.Text(), nullable=True),
        sa.Column("prev_hash", sa.String(64), nullable=False),
        sa.Column("digest", sa.String(64), nullable=False, unique=True),
        sa.Column("idempotency_key", sa.String(255), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "idempotency_key", name="uq_evidence_idem"),
    )
    op.create_index("ix_evidence_tenant_created", "evidence", ["tenant_id", "created_at"])
    op.create_index("ix_evidence_exposure", "evidence", ["tenant_id", "exposure_id"])
    op.create_index("ix_evidence_wfexec", "evidence", ["tenant_id", "workflow_execution_id"])
    op.create_index("ix_evidence_tenant", "evidence", ["tenant_id"])

    # Append-only at the DB layer. The app connects as evidence (owner here); we
    # revoke UPDATE/DELETE so that even app code cannot rewrite history.
    op.execute("REVOKE UPDATE, DELETE ON TABLE evidence FROM PUBLIC")
    op.execute("REVOKE UPDATE, DELETE ON TABLE chain_heads FROM PUBLIC")

def downgrade() -> None:
    op.drop_table("evidence")
    op.drop_table("chain_heads")
