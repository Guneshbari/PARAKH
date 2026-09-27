"""create_document_requests_table

Revision ID: c5e3f8a12d04
Revises: b7c1e9a24d03
Create Date: 2026-09-27 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'c5e3f8a12d04'
down_revision: Union[str, Sequence[str], None] = 'b7c1e9a24d03'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create document_requests table with foreign keys and indexes."""
    op.create_table(
        'document_requests',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('application_id', sa.Uuid(), nullable=False),
        sa.Column('review_id', sa.Uuid(), nullable=True),
        sa.Column('requested_by', sa.Uuid(), nullable=False),
        sa.Column(
            'document_type',
            sa.Enum(
                'BANK_STATEMENT',
                'INCOME_PROOF',
                'TRANSACTION_STATEMENT',
                'BUSINESS_RECORD',
                'OTHER',
                name='documenttype',
                native_enum=False,
                length=50,
            ),
            nullable=False,
        ),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column(
            'allowed_file_types',
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'),
            nullable=False,
        ),
        sa.Column(
            'status',
            sa.Enum(
                'PENDING',
                'SUBMITTED',
                'REJECTED',
                'ACCEPTED',
                name='documentrequeststatus',
                native_enum=False,
                length=50,
            ),
            nullable=False,
        ),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['review_id'], ['review_outcomes.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['requested_by'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_document_requests_application_id'), 'document_requests', ['application_id'], unique=False)
    op.create_index(op.f('ix_document_requests_review_id'), 'document_requests', ['review_id'], unique=False)
    op.create_index(op.f('ix_document_requests_requested_by'), 'document_requests', ['requested_by'], unique=False)
    op.create_index(op.f('ix_document_requests_status'), 'document_requests', ['status'], unique=False)


def downgrade() -> None:
    """Drop document_requests table and its indexes."""
    op.drop_index(op.f('ix_document_requests_status'), table_name='document_requests')
    op.drop_index(op.f('ix_document_requests_requested_by'), table_name='document_requests')
    op.drop_index(op.f('ix_document_requests_review_id'), table_name='document_requests')
    op.drop_index(op.f('ix_document_requests_application_id'), table_name='document_requests')
    op.drop_table('document_requests')
