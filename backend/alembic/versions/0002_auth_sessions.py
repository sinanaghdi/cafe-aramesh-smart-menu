"""Add refresh-token session storage.

Revision ID: 0002_auth_sessions
Revises: 0001_initial
Create Date: 2026-10-10
"""

from alembic import op

from app.models.entities import AuthSession

revision = "0002_auth_sessions"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    AuthSession.__table__.create(bind=op.get_bind(), checkfirst=True)


def downgrade() -> None:
    AuthSession.__table__.drop(bind=op.get_bind(), checkfirst=True)
