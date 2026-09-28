"""add_operational_alerts_table

Revision ID: d9e2f3a4b5c6
Revises: c8d1e2f3a4b5
Create Date: 2026-09-26 22:50:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "d9e2f3a4b5c6"
down_revision: Union[str, Sequence[str], None] = "c8d1e2f3a4b5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create operational_alerts table and indexes."""
    op.create_table(
        "operational_alerts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("alert_type", sa.String(length=50), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="OPEN", nullable=False),
        sa.Column("application_id", sa.Uuid(), nullable=True),
        sa.Column("assessment_id", sa.Uuid(), nullable=True),
        sa.Column(
            "metadata",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["applications.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["assessment_id"],
            ["credit_assessments.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_operational_alerts_alert_type"),
        "operational_alerts",
        ["alert_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_operational_alerts_severity"),
        "operational_alerts",
        ["severity"],
        unique=False,
    )
    op.create_index(
        op.f("ix_operational_alerts_status"),
        "operational_alerts",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_operational_alerts_application_id"),
        "operational_alerts",
        ["application_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_operational_alerts_assessment_id"),
        "operational_alerts",
        ["assessment_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_operational_alerts_created_at"),
        "operational_alerts",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Drop operational_alerts table and indexes."""
    op.drop_index(op.f("ix_operational_alerts_created_at"), table_name="operational_alerts")
    op.drop_index(op.f("ix_operational_alerts_assessment_id"), table_name="operational_alerts")
    op.drop_index(op.f("ix_operational_alerts_application_id"), table_name="operational_alerts")
    op.drop_index(op.f("ix_operational_alerts_status"), table_name="operational_alerts")
    op.drop_index(op.f("ix_operational_alerts_severity"), table_name="operational_alerts")
    op.drop_index(op.f("ix_operational_alerts_alert_type"), table_name="operational_alerts")
    op.drop_table("operational_alerts")
