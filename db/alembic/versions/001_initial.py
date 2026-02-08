"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2026-02-07

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Measurements table
    op.create_table(
        'measurements',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('location_name', sa.String(length=100), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('pm25', sa.Float(), nullable=True),
        sa.Column('pm10', sa.Float(), nullable=True),
        sa.Column('no2', sa.Float(), nullable=True),
        sa.Column('o3', sa.Float(), nullable=True),
        sa.Column('co', sa.Float(), nullable=True),
        sa.Column('temperature', sa.Float(), nullable=True),
        sa.Column('humidity', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_measurements_id', 'measurements', ['id'])
    op.create_index('ix_measurements_location_name', 'measurements', ['location_name'])
    op.create_index('ix_measurements_timestamp', 'measurements', ['timestamp'])
    op.create_index('idx_location_timestamp', 'measurements', ['location_name', 'timestamp'])
    
    # Forecasts table
    op.create_table(
        'forecasts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('location_name', sa.String(length=100), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('forecast_time', sa.DateTime(), nullable=False),
        sa.Column('predicted_pm25', sa.Float(), nullable=True),
        sa.Column('predicted_pm10', sa.Float(), nullable=True),
        sa.Column('predicted_aqi', sa.Integer(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_forecasts_id', 'forecasts', ['id'])
    op.create_index('ix_forecasts_forecast_time', 'forecasts', ['forecast_time'])
    
    # Alerts table
    op.create_table(
        'alerts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('location_name', sa.String(length=100), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('alert_type', sa.String(length=50), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('value', sa.Float(), nullable=True),
        sa.Column('threshold', sa.Float(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_alerts_id', 'alerts', ['id'])
    op.create_index('ix_alerts_is_active', 'alerts', ['is_active'])
    op.create_index('ix_alerts_created_at', 'alerts', ['created_at'])


def downgrade() -> None:
    op.drop_index('ix_alerts_created_at', table_name='alerts')
    op.drop_index('ix_alerts_is_active', table_name='alerts')
    op.drop_index('ix_alerts_id', table_name='alerts')
    op.drop_table('alerts')
    
    op.drop_index('ix_forecasts_forecast_time', table_name='forecasts')
    op.drop_index('ix_forecasts_id', table_name='forecasts')
    op.drop_table('forecasts')
    
    op.drop_index('idx_location_timestamp', table_name='measurements')
    op.drop_index('ix_measurements_timestamp', table_name='measurements')
    op.drop_index('ix_measurements_location_name', table_name='measurements')
    op.drop_index('ix_measurements_id', table_name='measurements')
    op.drop_table('measurements')
