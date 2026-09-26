"""add_telemetry_series_to_financial_signals

Revision ID: c8d1e2f3a4b5
Revises: b7c1e9a24d03
Create Date: 2026-09-26 21:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'c8d1e2f3a4b5'
down_revision: Union[str, Sequence[str], None] = 'b7c1e9a24d03'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add telemetry_series JSONB column to financial_signals table."""
    op.add_column(
        'financial_signals',
        sa.Column(
            'telemetry_series',
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Remove telemetry_series column from financial_signals table."""
    op.drop_column('financial_signals', 'telemetry_series')
