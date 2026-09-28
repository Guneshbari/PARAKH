"""add_applicant_consent_preferences_table

Revision ID: e0f1a2b3c4d5
Revises: d9e2f3a4b5c6
Create Date: 2026-09-27 00:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e0f1a2b3c4d5"
down_revision: Union[str, Sequence[str], None] = "d9e2f3a4b5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create applicant_consent_preferences table and indexes."""
    op.create_table(
        "applicant_consent_preferences",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("applicant_profile_id", sa.Uuid(), nullable=True),
        sa.Column("preference_key", sa.String(length=100), nullable=False),
        sa.Column("granted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("consented_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["applicant_profile_id"],
            ["applicant_profiles.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "preference_key", name="uq_user_preference_key"),
    )
    op.create_index(
        op.f("ix_applicant_consent_preferences_user_id"),
        "applicant_consent_preferences",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_applicant_consent_preferences_applicant_profile_id"),
        "applicant_consent_preferences",
        ["applicant_profile_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_applicant_consent_preferences_preference_key"),
        "applicant_consent_preferences",
        ["preference_key"],
        unique=False,
    )


def downgrade() -> None:
    """Drop applicant_consent_preferences table and indexes."""
    op.drop_index(
        op.f("ix_applicant_consent_preferences_preference_key"),
        table_name="applicant_consent_preferences",
    )
    op.drop_index(
        op.f("ix_applicant_consent_preferences_applicant_profile_id"),
        table_name="applicant_consent_preferences",
    )
    op.drop_index(
        op.f("ix_applicant_consent_preferences_user_id"),
        table_name="applicant_consent_preferences",
    )
    op.drop_table("applicant_consent_preferences")
