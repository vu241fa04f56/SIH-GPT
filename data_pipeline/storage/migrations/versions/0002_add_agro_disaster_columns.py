"""Add individual API columns to agro_records and disaster_records.

Revision ID: 0002_add_agro_disaster_columns
Revises: 0001_initial

This migration is idempotent: it inspects the live schema before adding
each column or index so it is safe to run even when the tables were
already created with full columns by migration 0001_initial (create_all).
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0002_add_agro_disaster_columns"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def _existing_columns(table_name: str) -> set[str]:
    """Return the set of column names currently on *table_name*."""
    conn = op.get_bind()
    insp = inspect(conn)
    return {col["name"] for col in insp.get_columns(table_name)}


def _existing_indexes(table_name: str) -> set[str]:
    """Return the set of index names currently on *table_name*."""
    conn = op.get_bind()
    insp = inspect(conn)
    return {idx["name"] for idx in insp.get_indexes(table_name)}


def upgrade() -> None:
    # ── agro_records — new individual weather + context columns ───────────────
    agro_cols = _existing_columns("agro_records")
    agro_idxs = _existing_indexes("agro_records")

    with op.batch_alter_table("agro_records") as batch_op:
        if "month" not in agro_cols:
            batch_op.add_column(sa.Column("month", sa.Integer(), nullable=True))
        if "season" not in agro_cols:
            batch_op.add_column(sa.Column("season", sa.String(length=16), nullable=True))
        if "temperature_2m" not in agro_cols:
            batch_op.add_column(sa.Column("temperature_2m", sa.Float(), nullable=True))
        if "relative_humidity_2m" not in agro_cols:
            batch_op.add_column(sa.Column("relative_humidity_2m", sa.Float(), nullable=True))
        if "precipitation" not in agro_cols:
            batch_op.add_column(sa.Column("precipitation", sa.Float(), nullable=True))
        if "et0_fao_evapotranspiration" not in agro_cols:
            batch_op.add_column(sa.Column("et0_fao_evapotranspiration", sa.Float(), nullable=True))
        if "wind_speed_10m" not in agro_cols:
            batch_op.add_column(sa.Column("wind_speed_10m", sa.Float(), nullable=True))
        if "cloud_cover" not in agro_cols:
            batch_op.add_column(sa.Column("cloud_cover", sa.Float(), nullable=True))
        if "uv_index" not in agro_cols:
            batch_op.add_column(sa.Column("uv_index", sa.Float(), nullable=True))
        if "shortwave_radiation" not in agro_cols:
            batch_op.add_column(sa.Column("shortwave_radiation", sa.Float(), nullable=True))
        if "elevation_m" not in agro_cols:
            batch_op.add_column(sa.Column("elevation_m", sa.Float(), nullable=True))
        if "ix_agro_city_ts" not in agro_idxs:
            batch_op.create_index("ix_agro_city_ts", ["city_id", "timestamp"])
        if "ix_agro_crop" not in agro_idxs:
            batch_op.create_index("ix_agro_crop", ["crop_type"])

    # ── disaster_records — new individual extreme-weather columns ─────────────
    dis_cols = _existing_columns("disaster_records")

    with op.batch_alter_table("disaster_records") as batch_op:
        if "cape" not in dis_cols:
            batch_op.add_column(sa.Column("cape", sa.Float(), nullable=True))
        if "wind_gusts_10m" not in dis_cols:
            batch_op.add_column(sa.Column("wind_gusts_10m", sa.Float(), nullable=True))
        if "precipitation" not in dis_cols:
            batch_op.add_column(sa.Column("precipitation", sa.Float(), nullable=True))
        if "lifted_index" not in dis_cols:
            batch_op.add_column(sa.Column("lifted_index", sa.Float(), nullable=True))
        if "pressure_msl" not in dis_cols:
            batch_op.add_column(sa.Column("pressure_msl", sa.Float(), nullable=True))
        if "rain" not in dis_cols:
            batch_op.add_column(sa.Column("rain", sa.Float(), nullable=True))
        if "snowfall" not in dis_cols:
            batch_op.add_column(sa.Column("snowfall", sa.Float(), nullable=True))


def downgrade() -> None:
    dis_cols = _existing_columns("disaster_records")
    with op.batch_alter_table("disaster_records") as batch_op:
        for col in ["cape", "wind_gusts_10m", "precipitation", "lifted_index",
                    "pressure_msl", "rain", "snowfall"]:
            if col in dis_cols:
                batch_op.drop_column(col)

    agro_cols = _existing_columns("agro_records")
    agro_idxs = _existing_indexes("agro_records")
    with op.batch_alter_table("agro_records") as batch_op:
        if "ix_agro_crop" in agro_idxs:
            batch_op.drop_index("ix_agro_crop")
        if "ix_agro_city_ts" in agro_idxs:
            batch_op.drop_index("ix_agro_city_ts")
        for col in ["month", "season", "temperature_2m", "relative_humidity_2m",
                    "precipitation", "et0_fao_evapotranspiration", "wind_speed_10m",
                    "cloud_cover", "uv_index", "shortwave_radiation", "elevation_m"]:
            if col in agro_cols:
                batch_op.drop_column(col)
