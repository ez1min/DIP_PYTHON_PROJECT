"""add mypage preferences recommendations and suitability

Revision ID: f778bb38a150
Revises: 98c7cfebad4f
Create Date: 2026-08-22 13:04:49.493589

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f778bb38a150'
down_revision: Union[str, Sequence[str], None] = '98c7cfebad4f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('applications', sa.Column('application_type', sa.Enum('VISIT', 'USE', name='applicationtype', native_enum=False, length=20), nullable=False, server_default='VISIT'))
    op.add_column('applications', sa.Column('applicant_name', sa.String(length=100), nullable=True))
    op.add_column('applications', sa.Column('applicant_phone', sa.String(length=30), nullable=True))
    op.add_column('applications', sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('spaces', sa.Column('address', sa.String(length=300), nullable=False, server_default=''))
    op.add_column('spaces', sa.Column('category_name', sa.String(length=100), nullable=False, server_default=''))
    op.add_column('spaces', sa.Column('deposit', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('spaces', sa.Column('maintenance_fee', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('spaces', sa.Column('parking', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('spaces', sa.Column('parking_spaces', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('spaces', sa.Column('main_image_url', sa.Text(), nullable=True))
    op.add_column('spaces', sa.Column('description', sa.Text(), nullable=True))
    op.create_index(op.f('ix_spaces_parking'), 'spaces', ['parking'], unique=False)
    op.add_column('users', sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        'user_preferences',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('preferred_district', sa.String(length=50), nullable=True),
        sa.Column('preferred_category', sa.String(length=50), nullable=True),
        sa.Column('max_monthly_rent', sa.Integer(), nullable=True),
        sa.Column('min_area', sa.Float(), nullable=True),
        sa.Column('parking_required', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('project_summary', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id'),
    )
    op.create_table(
        'recommendation_weight_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('version', sa.String(length=30), nullable=False),
        sa.Column('purpose_category', sa.String(length=50), nullable=True),
        sa.Column('base_score', sa.Integer(), nullable=False, server_default='15'),
        sa.Column('district_weight', sa.Integer(), nullable=False, server_default='25'),
        sa.Column('category_weight', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('budget_weight', sa.Integer(), nullable=False, server_default='20'),
        sa.Column('near_budget_weight', sa.Integer(), nullable=False, server_default='8'),
        sa.Column('area_weight', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('parking_weight', sa.Integer(), nullable=False, server_default='8'),
        sa.Column('parking_optional_weight', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('score_cap', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('version'),
    )
    op.create_index(op.f('ix_recommendation_weight_configs_is_active'), 'recommendation_weight_configs', ['is_active'], unique=False)
    op.create_index(op.f('ix_recommendation_weight_configs_purpose_category'), 'recommendation_weight_configs', ['purpose_category'], unique=False)
    op.create_table(
        'recommendation_runs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('preferred_district', sa.String(length=50), nullable=False, server_default='ALL'),
        sa.Column('purpose_category', sa.String(length=50), nullable=False),
        sa.Column('max_monthly_rent', sa.Integer(), nullable=False),
        sa.Column('min_area', sa.Float(), nullable=False),
        sa.Column('parking_required', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('weight_config_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['weight_config_id'], ['recommendation_weight_configs.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_recommendation_runs_user_id'), 'recommendation_runs', ['user_id'], unique=False)
    op.create_table(
        'recommendation_results',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('run_id', sa.Integer(), nullable=False),
        sa.Column('space_id', sa.String(length=30), nullable=False),
        sa.Column('rank', sa.Integer(), nullable=False),
        sa.Column('raw_score', sa.Integer(), nullable=False),
        sa.Column('normalized_score', sa.Integer(), nullable=False),
        sa.Column('reasons', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['recommendation_runs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['space_id'], ['spaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('run_id', 'rank', name='uq_recommendation_run_rank'),
    )
    op.create_index(op.f('ix_recommendation_results_run_id'), 'recommendation_results', ['run_id'], unique=False)
    op.create_index(op.f('ix_recommendation_results_space_id'), 'recommendation_results', ['space_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_recommendation_results_space_id'), table_name='recommendation_results')
    op.drop_index(op.f('ix_recommendation_results_run_id'), table_name='recommendation_results')
    op.drop_table('recommendation_results')
    op.drop_index(op.f('ix_recommendation_runs_user_id'), table_name='recommendation_runs')
    op.drop_table('recommendation_runs')
    op.drop_index(op.f('ix_recommendation_weight_configs_purpose_category'), table_name='recommendation_weight_configs')
    op.drop_index(op.f('ix_recommendation_weight_configs_is_active'), table_name='recommendation_weight_configs')
    op.drop_table('recommendation_weight_configs')
    op.drop_table('user_preferences')
    op.drop_column('users', 'last_login_at')
    op.drop_index(op.f('ix_spaces_parking'), table_name='spaces')
    op.drop_column('spaces', 'description')
    op.drop_column('spaces', 'main_image_url')
    op.drop_column('spaces', 'parking_spaces')
    op.drop_column('spaces', 'parking')
    op.drop_column('spaces', 'maintenance_fee')
    op.drop_column('spaces', 'deposit')
    op.drop_column('spaces', 'category_name')
    op.drop_column('spaces', 'address')
    op.drop_column('applications', 'cancelled_at')
    op.drop_column('applications', 'applicant_phone')
    op.drop_column('applications', 'applicant_name')
    op.drop_column('applications', 'application_type')
