"""initial_schema

Revision ID: fd385d59e799
Revises: 
Create Date: 2026-09-21 23:58:39.724100

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'fd385d59e799'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to initial PARAKH domain model."""
    # 1. users
    op.create_table(
        'users',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=True),
        sa.Column('role', sa.Enum('APPLICANT', 'REVIEWER', name='userrole', native_enum=False, length=50), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # 2. applicant_profiles
    op.create_table(
        'applicant_profiles',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('gig_work_type', sa.String(length=100), nullable=False),
        sa.Column('years_working', sa.Numeric(precision=4, scale=1), nullable=True),
        sa.Column('average_working_days', sa.Integer(), nullable=True),
        sa.Column('business_or_loan_purpose', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
    )
    op.create_index(op.f('ix_applicant_profiles_user_id'), 'applicant_profiles', ['user_id'], unique=True)

    # 3. applications
    op.create_table(
        'applications',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('applicant_profile_id', sa.Uuid(), nullable=False),
        sa.Column('requested_loan_amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('loan_purpose', sa.String(length=255), nullable=True),
        sa.Column('preferred_repayment_period', sa.Integer(), nullable=True),
        sa.Column('status', sa.Enum('DRAFT', 'SUBMITTED', 'UNDER_REVIEW', 'ASSESSED', 'MANUAL_REVIEW', 'COMPLETED', name='applicationstatus', native_enum=False, length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('requested_loan_amount > 0', name='check_positive_loan_amount'),
        sa.ForeignKeyConstraint(['applicant_profile_id'], ['applicant_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_applications_applicant_profile_id'), 'applications', ['applicant_profile_id'], unique=False)
    op.create_index(op.f('ix_applications_status'), 'applications', ['status'], unique=False)

    # 4. consents
    op.create_table(
        'consents',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('application_id', sa.Uuid(), nullable=True),
        sa.Column('applicant_profile_id', sa.Uuid(), nullable=True),
        sa.Column('data_source', sa.Enum('PLATFORM', 'FINANCIAL_ACTIVITY', 'UTILITY', name='consentdatasource', native_enum=False, length=50), nullable=False),
        sa.Column('purpose', sa.String(length=255), nullable=False),
        sa.Column('granted', sa.Boolean(), nullable=False),
        sa.Column('granted_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['applicant_profile_id'], ['applicant_profiles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_consents_applicant_profile_id'), 'consents', ['applicant_profile_id'], unique=False)
    op.create_index(op.f('ix_consents_application_id'), 'consents', ['application_id'], unique=False)

    # 5. financial_signals
    op.create_table(
        'financial_signals',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('application_id', sa.Uuid(), nullable=False),
        sa.Column('applicant_profile_id', sa.Uuid(), nullable=True),
        sa.Column('source', sa.Enum('PLATFORM', 'FINANCIAL_ACTIVITY', 'UTILITY', 'DERIVED', name='signalsource', native_enum=False, length=50), nullable=False),
        sa.Column('measurement_period_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('measurement_period_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('average_income', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('median_income', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('income_volatility', sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column('income_trend', sa.String(length=50), nullable=True),
        sa.Column('active_days', sa.Integer(), nullable=True),
        sa.Column('payment_regularity', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('cashflow_buffer', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('existing_obligation', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('platform_rating', sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column('repayment_reliability', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('signal_metadata', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('average_income IS NULL OR average_income >= 0', name='check_positive_avg_income'),
        sa.CheckConstraint('median_income IS NULL OR median_income >= 0', name='check_positive_median_income'),
        sa.CheckConstraint('existing_obligation IS NULL OR existing_obligation >= 0', name='check_positive_existing_obligation'),
        sa.CheckConstraint('cashflow_buffer IS NULL OR cashflow_buffer >= 0', name='check_positive_cashflow_buffer'),
        sa.ForeignKeyConstraint(['applicant_profile_id'], ['applicant_profiles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_financial_signals_applicant_profile_id'), 'financial_signals', ['applicant_profile_id'], unique=False)
    op.create_index(op.f('ix_financial_signals_application_id'), 'financial_signals', ['application_id'], unique=False)
    op.create_index(op.f('ix_financial_signals_source'), 'financial_signals', ['source'], unique=False)

    # 6. model_versions
    op.create_table(
        'model_versions',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('model_name', sa.String(length=100), nullable=False),
        sa.Column('version', sa.String(length=50), nullable=False),
        sa.Column('algorithm', sa.String(length=100), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    # 7. credit_assessments
    op.create_table(
        'credit_assessments',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('application_id', sa.Uuid(), nullable=False),
        sa.Column('model_version_id', sa.Uuid(), nullable=False),
        sa.Column('credit_score', sa.Integer(), nullable=True),
        sa.Column('risk_probability', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('risk_level', sa.Enum('LOWER', 'MODERATE', 'HIGHER', 'INSUFFICIENT', name='risklevel', native_enum=False, length=50), nullable=False),
        sa.Column('confidence', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('debt_to_income', sa.Numeric(precision=6, scale=4), nullable=True),
        sa.Column('utilization', sa.Numeric(precision=6, scale=4), nullable=True),
        sa.Column('income_stability', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('repayment_reliability', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('assessment_status', sa.String(length=50), nullable=False),
        sa.Column('assessed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('credit_score IS NULL OR credit_score >= 0', name='check_positive_credit_score'),
        sa.CheckConstraint('risk_probability IS NULL OR (risk_probability >= 0 AND risk_probability <= 1)', name='check_risk_probability_range'),
        sa.CheckConstraint('confidence IS NULL OR (confidence >= 0 AND confidence <= 1)', name='check_confidence_range'),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['model_version_id'], ['model_versions.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_credit_assessments_application_id'), 'credit_assessments', ['application_id'], unique=False)
    op.create_index(op.f('ix_credit_assessments_model_version_id'), 'credit_assessments', ['model_version_id'], unique=False)

    # 8. review_outcomes
    op.create_table(
        'review_outcomes',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('application_id', sa.Uuid(), nullable=False),
        sa.Column('reviewer_id', sa.Uuid(), nullable=False),
        sa.Column('outcome', sa.Enum('REVIEWED', 'ESCALATED', 'ADDITIONAL_INFORMATION_REQUIRED', name='reviewoutcometype', native_enum=False, length=50), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewer_id'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_review_outcomes_application_id'), 'review_outcomes', ['application_id'], unique=False)
    op.create_index(op.f('ix_review_outcomes_reviewer_id'), 'review_outcomes', ['reviewer_id'], unique=False)

    # 9. audit_logs
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=True),
        sa.Column('application_id', sa.Uuid(), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('entity_type', sa.String(length=100), nullable=False),
        sa.Column('entity_id', sa.String(length=100), nullable=True),
        sa.Column('metadata', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_audit_logs_action'), 'audit_logs', ['action'], unique=False)
    op.create_index(op.f('ix_audit_logs_application_id'), 'audit_logs', ['application_id'], unique=False)
    op.create_index(op.f('ix_audit_logs_created_at'), 'audit_logs', ['created_at'], unique=False)
    op.create_index(op.f('ix_audit_logs_user_id'), 'audit_logs', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema by dropping all PARAKH domain tables in reverse dependency order."""
    op.drop_index(op.f('ix_audit_logs_user_id'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_created_at'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_application_id'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_action'), table_name='audit_logs')
    op.drop_table('audit_logs')

    op.drop_index(op.f('ix_review_outcomes_reviewer_id'), table_name='review_outcomes')
    op.drop_index(op.f('ix_review_outcomes_application_id'), table_name='review_outcomes')
    op.drop_table('review_outcomes')

    op.drop_index(op.f('ix_credit_assessments_model_version_id'), table_name='credit_assessments')
    op.drop_index(op.f('ix_credit_assessments_application_id'), table_name='credit_assessments')
    op.drop_table('credit_assessments')

    op.drop_table('model_versions')

    op.drop_index(op.f('ix_financial_signals_source'), table_name='financial_signals')
    op.drop_index(op.f('ix_financial_signals_application_id'), table_name='financial_signals')
    op.drop_index(op.f('ix_financial_signals_applicant_profile_id'), table_name='financial_signals')
    op.drop_table('financial_signals')

    op.drop_index(op.f('ix_consents_application_id'), table_name='consents')
    op.drop_index(op.f('ix_consents_applicant_profile_id'), table_name='consents')
    op.drop_table('consents')

    op.drop_index(op.f('ix_applications_status'), table_name='applications')
    op.drop_index(op.f('ix_applications_applicant_profile_id'), table_name='applications')
    op.drop_table('applications')

    op.drop_index(op.f('ix_applicant_profiles_user_id'), table_name='applicant_profiles')
    op.drop_table('applicant_profiles')

    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
