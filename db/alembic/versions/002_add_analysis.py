"""add_analysis_table

Revision ID: 002
Revises: 001
Create Date: 2026-02-08

"""
from alembic import op
import sqlalchemy as sa

revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'analyses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('analysis_type', sa.String(length=50), nullable=False),
        sa.Column('location_name', sa.String(length=100), nullable=False),
        sa.Column('pm25_trend', sa.String(length=20), nullable=True),
        sa.Column('pm25_avg', sa.Float(), nullable=True),
        sa.Column('anomalies_count', sa.Integer(), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('detailed_analysis', sa.Text(), nullable=True),
        sa.Column('period_start', sa.DateTime(), nullable=False),
        sa.Column('period_end', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_analyses_id', 'analyses', ['id'])
    op.create_index('ix_analyses_location_name', 'analyses', ['location_name'])
    op.create_index('ix_analyses_created_at', 'analyses', ['created_at'])
    op.create_unique_constraint('unique_analysis', 'analyses', ['location_name', 'created_at'])


def downgrade() -> None:
    op.drop_constraint('unique_analysis', 'analyses', type_='unique')
    op.drop_index('ix_analyses_created_at', table_name='analyses')
    op.drop_index('ix_analyses_location_name', table_name='analyses')
    op.drop_index('ix_analyses_id', table_name='analyses')
    op.drop_table('analyses')
