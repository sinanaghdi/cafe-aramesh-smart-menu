from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON, Boolean, CheckConstraint, DateTime, Float, ForeignKey, Index, Integer,
    String, Text, UniqueConstraint, func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class Cafe(Base, TimestampMixin):
    __tablename__ = "cafes"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    currency_unit: Mapped[str] = mapped_column(String(3), default="IRT")
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Tehran")
    __table_args__ = (CheckConstraint("currency_unit IN ('IRT', 'IRR')", name="ck_cafes_currency_unit"),)


class User(Base, TimestampMixin):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    cafe_id: Mapped[int] = mapped_column(ForeignKey("cafes.id"), index=True)
    full_name: Mapped[str] = mapped_column(String(160))
    role: Mapped[str] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (
        CheckConstraint("role IN ('customer', 'staff', 'merchant')", name="ck_users_role"),
        UniqueConstraint("cafe_id", "email", name="uq_users_cafe_email"),
        UniqueConstraint("cafe_id", "phone", name="uq_users_cafe_phone"),
    )


class CafeTable(Base, TimestampMixin):
    __tablename__ = "cafe_tables"
    id: Mapped[int] = mapped_column(primary_key=True)
    cafe_id: Mapped[int] = mapped_column(ForeignKey("cafes.id"), index=True)
    table_number: Mapped[int] = mapped_column(Integer)
    label: Mapped[str | None] = mapped_column(String(80), nullable=True)
    qr_token: Mapped[str] = mapped_column(String(128), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (
        UniqueConstraint("cafe_id", "table_number", name="uq_cafe_tables_cafe_number"),
        CheckConstraint("table_number > 0", name="ck_cafe_tables_positive_number"),
    )


class Category(Base, TimestampMixin):
    __tablename__ = "categories"
    id: Mapped[int] = mapped_column(primary_key=True)
    cafe_id: Mapped[int] = mapped_column(ForeignKey("cafes.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(100))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (UniqueConstraint("cafe_id", "slug", name="uq_categories_cafe_slug"),)


class Product(Base, TimestampMixin):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(primary_key=True)
    cafe_id: Mapped[int] = mapped_column(ForeignKey("cafes.id"), index=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), index=True)
    slug: Mapped[str] = mapped_column(String(120))
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text, default="")
    price_amount: Mapped[int] = mapped_column(Integer)
    margin_amount: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    __table_args__ = (
        UniqueConstraint("cafe_id", "slug", name="uq_products_cafe_slug"),
        CheckConstraint("price_amount >= 0", name="ck_products_price_nonnegative"),
        CheckConstraint("margin_amount IS NULL OR margin_amount >= 0", name="ck_products_margin_nonnegative"),
    )


class ProductTag(Base):
    __tablename__ = "product_tags"
    id: Mapped[int] = mapped_column(primary_key=True)
    cafe_id: Mapped[int] = mapped_column(ForeignKey("cafes.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    tag_key: Mapped[str] = mapped_column(String(40))
    tag_value: Mapped[str] = mapped_column(String(80))
    __table_args__ = (
        UniqueConstraint("product_id", "tag_key", "tag_value", name="uq_product_tags_value"),
        Index("ix_product_tags_lookup", "cafe_id", "tag_key", "tag_value"),
    )


class ProductVariant(Base, TimestampMixin):
    __tablename__ = "product_variants"
    id: Mapped[int] = mapped_column(primary_key=True)
    cafe_id: Mapped[int] = mapped_column(ForeignKey("cafes.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(100))
    price_delta_amount: Mapped[int] = mapped_column(Integer, default=0)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (
        CheckConstraint("price_delta_amount >= 0", name="ck_variants_price_delta_nonnegative"),
        UniqueConstraint("product_id", "name", name="uq_product_variants_name"),
    )


class Combo(Base, TimestampMixin):
    __tablename__ = "combos"
    id: Mapped[int] = mapped_column(primary_key=True)
    cafe_id: Mapped[int] = mapped_column(ForeignKey("cafes.id"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text, default="")
    strategy: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(20), default="draft")
    discount_amount: Mapped[int] = mapped_column(Integer, default=0)
    discount_percent: Mapped[int] = mapped_column(Integer, default=0)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (
        CheckConstraint("strategy IN ('BOOST_BESTSELLER', 'PUSH_SLOW_MOVER')", name="ck_combos_strategy"),
        CheckConstraint("status IN ('draft', 'approved', 'rejected', 'archived')", name="ck_combos_status"),
        CheckConstraint("discount_amount >= 0", name="ck_combos_discount_amount"),
        CheckConstraint("discount_percent BETWEEN 0 AND 100", name="ck_combos_discount_percent"),
    )


class ComboItem(Base):
    __tablename__ = "combo_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    cafe_id: Mapped[int] = mapped_column(ForeignKey("cafes.id"), index=True)
    combo_id: Mapped[int] = mapped_column(ForeignKey("combos.id", ondelete="CASCADE"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    __table_args__ = (
        UniqueConstraint("combo_id", "product_id", name="uq_combo_items_product"),
        CheckConstraint("quantity > 0", name="ck_combo_items_quantity_positive"),
    )


class Order(Base, TimestampMixin):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(primary_key=True)
    cafe_id: Mapped[int] = mapped_column(ForeignKey("cafes.id"), index=True)
    table_id: Mapped[int] = mapped_column(ForeignKey("cafe_tables.id"), index=True)
    customer_session_id: Mapped[str] = mapped_column(String(128), index=True)
    status: Mapped[str] = mapped_column(String(32), default="draft")
    total_amount: Mapped[int] = mapped_column(Integer, default=0)
    study_mode_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    served_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancellation_reason: Mapped[str | None] = mapped_column(String(300), nullable=True)
    __table_args__ = (
        CheckConstraint("status IN ('draft', 'pending_confirmation', 'confirmed', 'preparing', 'served', 'cancelled', 'expired')", name="ck_orders_status"),
        CheckConstraint("total_amount >= 0", name="ck_orders_total_nonnegative"),
        Index("ix_orders_cafe_status_created", "cafe_id", "status", "created_at"),
    )


class OrderItem(Base):
    __tablename__ = "order_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    cafe_id: Mapped[int] = mapped_column(ForeignKey("cafes.id"), index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    variant_id: Mapped[int | None] = mapped_column(ForeignKey("product_variants.id"), nullable=True)
    product_name_snapshot: Mapped[str] = mapped_column(String(160))
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price_amount: Mapped[int] = mapped_column(Integer)
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_order_items_quantity_positive"),
        CheckConstraint("unit_price_amount >= 0", name="ck_order_items_price_nonnegative"),
    )


class OrderCode(Base):
    __tablename__ = "order_codes"
    id: Mapped[int] = mapped_column(primary_key=True)
    cafe_id: Mapped[int] = mapped_column(ForeignKey("cafes.id"), index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), unique=True)
    code_hash: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(16), default="active")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (
        CheckConstraint("status IN ('active', 'consumed', 'expired', 'locked')", name="ck_order_codes_status"),
        CheckConstraint("attempts >= 0", name="ck_order_codes_attempts_nonnegative"),
        Index("uq_order_codes_active_hash", "cafe_id", "code_hash", unique=True, postgresql_where=(status == "active")),
    )


class StudyModeRule(Base, TimestampMixin):
    __tablename__ = "study_mode_rules"
    id: Mapped[int] = mapped_column(primary_key=True)
    cafe_id: Mapped[int] = mapped_column(ForeignKey("cafes.id"), unique=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    minimum_order_amount: Mapped[int] = mapped_column(Integer, default=0)
    required_product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), nullable=True)
    allowed_durations_minutes: Mapped[list[int]] = mapped_column(JSON, default=lambda: [120, 180])
    allowed_start_time: Mapped[str] = mapped_column(String(5), default="08:00")
    allowed_end_time: Mapped[str] = mapped_column(String(5), default="22:00")
    max_concurrent_sessions: Mapped[int] = mapped_column(Integer, default=10)
    __table_args__ = (
        CheckConstraint("minimum_order_amount >= 0", name="ck_study_rules_min_order_nonnegative"),
        CheckConstraint("max_concurrent_sessions > 0", name="ck_study_rules_capacity_positive"),
    )


class StudySession(Base, TimestampMixin):
    __tablename__ = "study_sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    cafe_id: Mapped[int] = mapped_column(ForeignKey("cafes.id"), index=True)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"), nullable=True)
    table_id: Mapped[int] = mapped_column(ForeignKey("cafe_tables.id"), index=True)
    customer_session_id: Mapped[str] = mapped_column(String(128), index=True)
    duration_minutes: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (
        CheckConstraint("duration_minutes > 0", name="ck_study_sessions_duration_positive"),
        CheckConstraint("status IN ('pending', 'active', 'expired', 'ended', 'cancelled')", name="ck_study_sessions_status"),
    )


class WifiVoucher(Base):
    __tablename__ = "wifi_vouchers"
    id: Mapped[int] = mapped_column(primary_key=True)
    cafe_id: Mapped[int] = mapped_column(ForeignKey("cafes.id"), index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), unique=True)
    study_session_id: Mapped[int | None] = mapped_column(ForeignKey("study_sessions.id"), nullable=True)
    code: Mapped[str] = mapped_column(String(128))
    adapter_type: Mapped[str] = mapped_column(String(40), default="mock")
    status: Mapped[str] = mapped_column(String(16), default="active")
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    redeemed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (CheckConstraint("status IN ('active', 'redeemed', 'expired', 'revoked')", name="ck_wifi_vouchers_status"),)


class LoyaltyAccount(Base, TimestampMixin):
    __tablename__ = "loyalty_accounts"
    id: Mapped[int] = mapped_column(primary_key=True)
    cafe_id: Mapped[int] = mapped_column(ForeignKey("cafes.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    points_balance: Mapped[int] = mapped_column(Integer, default=0)
    tier: Mapped[str] = mapped_column(String(20), default="bronze")
    consent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        UniqueConstraint("cafe_id", "user_id", name="uq_loyalty_accounts_user"),
        CheckConstraint("points_balance >= 0", name="ck_loyalty_points_nonnegative"),
        CheckConstraint("tier IN ('bronze', 'silver', 'gold')", name="ck_loyalty_tier"),
    )


class LoyaltyTransaction(Base):
    __tablename__ = "loyalty_transactions"
    id: Mapped[int] = mapped_column(primary_key=True)
    cafe_id: Mapped[int] = mapped_column(ForeignKey("cafes.id"), index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("loyalty_accounts.id"))
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"), nullable=True)
    points_delta: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint("cafe_id", "account_id", "order_id", "reason", name="uq_loyalty_txn_idempotency"),)


class Reward(Base, TimestampMixin):
    __tablename__ = "rewards"
    id: Mapped[int] = mapped_column(primary_key=True)
    cafe_id: Mapped[int] = mapped_column(ForeignKey("cafes.id"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text, default="")
    points_cost: Mapped[int] = mapped_column(Integer)
    reward_type: Mapped[str] = mapped_column(String(40))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (CheckConstraint("points_cost > 0", name="ck_rewards_points_cost_positive"),)


class NlpQueryLog(Base):
    __tablename__ = "nlp_query_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    cafe_id: Mapped[int] = mapped_column(ForeignKey("cafes.id"), index=True)
    query_normalized: Mapped[str] = mapped_column(String(500))
    result_count: Mapped[int] = mapped_column(Integer, default=0)
    answered: Mapped[bool] = mapped_column(Boolean, default=False)
    detected_intent: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (CheckConstraint("result_count >= 0", name="ck_nlp_result_count_nonnegative"),)


class AIInsight(Base):
    __tablename__ = "ai_insights"
    id: Mapped[int] = mapped_column(primary_key=True)
    cafe_id: Mapped[int] = mapped_column(ForeignKey("cafes.id"), index=True)
    insight_type: Mapped[str] = mapped_column(String(60))
    title: Mapped[str] = mapped_column(String(200))
    explanation: Mapped[str] = mapped_column(Text)
    evidence: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    reviewed_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (
        CheckConstraint("confidence BETWEEN 0 AND 1", name="ck_ai_insights_confidence"),
        CheckConstraint("status IN ('pending', 'approved', 'rejected')", name="ck_ai_insights_status"),
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    cafe_id: Mapped[int] = mapped_column(ForeignKey("cafes.id"), index=True)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(100))
    entity_type: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[str] = mapped_column(String(80))
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
