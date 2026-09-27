"""add_reviewer_notes_to_document_requests

Revision ID: e7f5b0c34d16
Revises: d6f4a9b23e05
Create Date: 2026-09-27 17:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e7f5b0c34d16'
down_revision: Union[str, Sequence[str], None] = 'd6f4a9b23e05'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add reviewer_notes column to document_requests table."""
    op.add_column(
        'document_requests',
        sa.Column('reviewer_notes', sa.Text(), nullable=True),
    )


def downgrade() -> None:
    """Remove reviewer_notes column from document_requests table."""
    op.drop_column('document_requests', 'reviewer_notes')
