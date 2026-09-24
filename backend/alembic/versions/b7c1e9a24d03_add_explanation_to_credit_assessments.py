"""add_explanation_to_credit_assessments

Revision ID: b7c1e9a24d03
Revises: fd385d59e799
Create Date: 2026-09-24 06:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'b7c1e9a24d03'
down_revision: Union[str, Sequence[str], None] = 'fd385d59e799'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add explanation JSONB column to credit_assessments."""
    op.add_column(
        'credit_assessments',
        sa.Column(
            'explanation',
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Remove explanation column from credit_assessments."""
    op.drop_column('credit_assessments', 'explanation')
