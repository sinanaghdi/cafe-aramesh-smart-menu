"""Create the Phase 0 domain schema.

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-10

This is intentionally frozen. Tables introduced later must be created by new revisions.
"""

from alembic import op

from app.db.base import Base
from app import models  # noqa: F401

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

INITIAL_TABLE_NAMES = (
    "cafes",
    "users",
    "cafe_tables",
    "categories",
    "products",
    "product_tags",
    "product_variants",
    "combos",
    "combo_items",
    "orders",
    "order_items",
    "order_codes",
    "study_mode_rules",
    "study_sessions",
    "wifi_vouchers",
    "loyalty_accounts",
    "loyalty_transactions",
    "rewards",
    "nlp_query_logs",
    "ai_insights",
    "audit_logs",
)


def upgrade() -> None:
    tables = [Base.metadata.tables[name] for name in INITIAL_TABLE_NAMES]
    Base.metadata.create_all(bind=op.get_bind(), tables=tables, checkfirst=True)


def downgrade() -> None:
    tables = [Base.metadata.tables[name] for name in reversed(INITIAL_TABLE_NAMES)]
    Base.metadata.drop_all(bind=op.get_bind(), tables=tables, checkfirst=True)
