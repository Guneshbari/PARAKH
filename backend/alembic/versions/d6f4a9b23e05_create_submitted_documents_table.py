"""create_submitted_documents_table

Revision ID: d6f4a9b23e05
Revises: c5e3f8a12d04
Create Date: 2026-09-27 13:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd6f4a9b23e05'
down_revision: Union[str, Sequence[str], None] = 'c5e3f8a12d04'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create submitted_documents table with foreign keys and indexes."""
    op.create_table(
        'submitted_documents',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('application_id', sa.Uuid(), nullable=False),
        sa.Column('document_request_id', sa.Uuid(), nullable=False),
        sa.Column('uploaded_by', sa.Uuid(), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('stored_filename', sa.String(length=255), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('file_type', sa.String(length=50), nullable=False),
        sa.Column('mime_type', sa.String(length=100), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ['application_id'],
            ['applications.id'],
            name=op.f('fk_submitted_documents_application_id_applications'),
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['document_request_id'],
            ['document_requests.id'],
            name=op.f('fk_submitted_documents_document_request_id_document_requests'),
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['uploaded_by'],
            ['users.id'],
            name=op.f('fk_submitted_documents_uploaded_by_users'),
            ondelete='RESTRICT',
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_submitted_documents')),
    )
    op.create_index(
        op.f('ix_submitted_documents_application_id'),
        'submitted_documents',
        ['application_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_submitted_documents_document_request_id'),
        'submitted_documents',
        ['document_request_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_submitted_documents_uploaded_by'),
        'submitted_documents',
        ['uploaded_by'],
        unique=False,
    )


def downgrade() -> None:
    """Drop submitted_documents table and its indexes."""
    op.drop_index(
        op.f('ix_submitted_documents_uploaded_by'),
        table_name='submitted_documents',
    )
    op.drop_index(
        op.f('ix_submitted_documents_document_request_id'),
        table_name='submitted_documents',
    )
    op.drop_index(
        op.f('ix_submitted_documents_application_id'),
        table_name='submitted_documents',
    )
    op.drop_table('submitted_documents')
