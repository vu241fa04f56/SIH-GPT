"""Create the WeatherGPT PostgreSQL/PostGIS schema.

Revision ID: 0001_initial
"""

from alembic import op

from data_pipeline.storage.db_models import Base

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
