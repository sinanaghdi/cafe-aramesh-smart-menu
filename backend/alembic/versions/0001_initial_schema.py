"""Create initial Café Aramesh domain schema.

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-10
"""

from alembic import op

from app.db.base import Base
from app import models  # noqa: F401

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Initial bootstrap; future schema changes must use explicit reviewed migrations.
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
