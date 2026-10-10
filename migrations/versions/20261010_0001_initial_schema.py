"""Create the initial Café Aramesh schema.

Revision ID: 20261010_0001
Revises:
Create Date: 2026-10-10
"""
from alembic import op
from backend.app.main import Base

revision = "20261010_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
