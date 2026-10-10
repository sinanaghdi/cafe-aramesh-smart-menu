from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal
from zoneinfo import ZoneInfo

import jwt
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint, create_engine, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")
APP_ENV = os.getenv("APP_ENV", "development").lower()
JWT_SECRET = os.getenv("JWT_SECRET") or "local-development-secret-change-before-deployment"
if APP_ENV == "production" and (len(JWT_SECRET) < 32 or any(x in JWT_SECRET.lower() for x in ("change-before", "placeholder", "example", "replace-me"))):
    raise RuntimeError("Production requires a unique JWT_SECRET of at least 32 characters.")
CAFE_TIMEZONE = os.getenv("CAFE_TIMEZONE", "Asia/Tehran")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./backend/cafe_aramesh.db")
DB_OPTIONS: dict[str, Any] = {"pool_pre_ping": True}
if DATABASE_URL.startswith("sqlite"):
    DB_OPTIONS["connect_args"] = {"check_same_thread": False}
engine = create_engine(DATABASE_URL, **DB_OPTIONS)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
TOKEN_MINUTES = 8 * 60
DIGIT_TRANS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    full_name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(20), index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Category(Base):
    __tablename__ = "categories"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class Product(Base):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), index=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    subtitle: Mapped[str] = mapped_column(String(180), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    price_toman: Mapped[int] = mapped_column(Integer)
    image_key: Mapped[str] = mapped_column(String(40), default="coffee")
    available: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    visible: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    attributes: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    category: Mapped[Category] = relationship()


class Combo(Base):
    __tablename__ = "combos"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    strategy: Mapped[str] = mapped_column(String(30), default="curated")
    discount_type: Mapped[str] = mapped_column(String(20), default="none")
    discount_value: Mapped[int] = mapped_column(Integer, default=0)
    product_ids: Mapped[list[int]] = mapped_column(JSON, default=list)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


class CafeTable(Base):
    __tablename__ = "cafe_tables"
    token: Mapped[str] = mapped_column(String(40), primary_key=True)
    label: Mapped[str] = mapped_column(String(40))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class CafeOrder(Base):
    __tablename__ = "orders"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    table_token: Mapped[str] = mapped_column(ForeignKey("cafe_tables.token"), index=True)
    customer_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(30), default="pending_verification", index=True)
    total_toman: Mapped[int] = mapped_column(Integer)
    code_digest: Mapped[str] = mapped_column(String(64))
    verification_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    verification_attempts: Mapped[int] = mapped_column(Integer, default=0)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    served_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(80), unique=True, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: now_utc())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: now_utc(), onupdate=lambda: now_utc())
    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")
    table: Mapped[CafeTable] = relationship()


class OrderItem(Base):
    __tablename__ = "order_items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), nullable=True)
    kind: Mapped[str] = mapped_column(String(20), default="product")
    item_name_snapshot: Mapped[str] = mapped_column(String(160))
    unit_price_toman: Mapped[int] = mapped_column(Integer)
    quantity: Mapped[int] = mapped_column(Integer)
    options: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    order: Mapped[CafeOrder] = relationship(back_populates="items")


class OrderEvent(Base):
    __tablename__ = "order_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    from_status: Mapped[str] = mapped_column(String(30))
    to_status: Mapped[str] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: now_utc())


class WorkSession(Base):
    __tablename__ = "work_sessions"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), index=True)
    customer_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    duration_minutes: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class LoyaltyBalance(Base):
    __tablename__ = "loyalty_balances"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    points: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: now_utc(), onupdate=lambda: now_utc())


class LoyaltyEntry(Base):
    __tablename__ = "loyalty_entries"
    __table_args__ = (UniqueConstraint("order_id", "reason", name="uq_loyalty_order_reason"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    order_id: Mapped[str | None] = mapped_column(ForeignKey("orders.id"), nullable=True)
    points_delta: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: now_utc())


class MerchantSetting(Base):
    __tablename__ = "merchant_settings"
    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[dict[str, Any]] = mapped_column(JSON)


Index("ix_orders_status_created", CafeOrder.status, CafeOrder.created_at)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def aware(value: datetime | None) -> datetime | None:
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def iso(value: datetime | None) -> str | None:
    value = aware(value)
    return value.isoformat() if value else None


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 240_000).hex()
    return "pbkdf2_sha256" + "$" + salt + "$" + hashed


def check_password(password: str, stored: str) -> bool:
    try:
        _, salt, expected = stored.split("$", 2)
        current = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 240_000).hex()
        return hmac.compare_digest(current, expected)
    except (ValueError, TypeError):
        return False


def token_for(user: User) -> str:
    issued = now_utc()
    return jwt.encode({"sub": str(user.id), "role": user.role, "iat": issued,
                       "exp": issued + timedelta(minutes=TOKEN_MINUTES)}, JWT_SECRET, algorithm="HS256")


def user_data(user: User) -> dict[str, Any]:
    return {"id": user.id, "email": user.email, "full_name": user.full_name, "role": user.role}


def current_user(authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "برای ادامه وارد حساب کاربری شوید.")
    try:
        payload = jwt.decode(authorization.split(" ", 1)[1], JWT_SECRET, algorithms=["HS256"])
        user = db.get(User, int(payload.get("sub", "0")))
    except (jwt.PyJWTError, ValueError, TypeError):
        raise HTTPException(401, "نشست معتبر نیست؛ دوباره وارد شوید.")
    if not user or not user.active or user.role != payload.get("role"):
        raise HTTPException(401, "حساب کاربری فعال یا معتبر نیست.")
    return user


def optional_user(authorization: str | None, db: Session) -> User | None:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    try:
        payload = jwt.decode(authorization.split(" ", 1)[1], JWT_SECRET, algorithms=["HS256"])
        user = db.get(User, int(payload.get("sub", "0")))
        return user if user and user.active and user.role == payload.get("role") else None
    except (jwt.PyJWTError, ValueError, TypeError):
        return None


def require_roles(*roles: str):
    def guard(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(403, "برای دسترسی به این بخش مجوز ندارید.")
        return user
    return guard


def normalize_fa(value: str) -> str:
    value = value.lower().replace("ي", "ی").replace("ى", "ی").replace("ك", "ک").replace("ۀ", "ه")
    value = re.sub(r"[\u064b-\u065f\u0670]", "", value)
    value = re.sub(r"[\u200c\u200e\u200fـ\s]+", " ", value)
    return value.strip()


def product_out(product: Product) -> dict[str, Any]:
    attrs = product.attributes or {}
    temperature = {"hot": "گرم", "cold": "سرد", "room": "معمولی"}.get(attrs.get("temperature"), "نامشخص")
    caffeine = {"high": "زیاد", "medium": "متوسط", "low": "کم", "none": "بدون کافئین"}.get(attrs.get("caffeine"), "نامشخص")
    flavor_map = {"sour":"ترش", "fruity":"میوه‌ای", "bitter":"تلخ", "creamy":"خامه‌ای", "citrus":"مرکباتی", "refreshing":"تازه", "herbal":"گیاهی", "chocolate":"شکلاتی", "sweet":"شیرین"}
    flavors = [flavor_map[x] for x in attrs.get("flavors", []) if x in flavor_map]
    return {"id": product.id, "name": product.name, "subtitle": product.subtitle, "category": product.category.name if product.category else "",
            "category_id": product.category_id, "price": product.price_toman, "price_toman": product.price_toman,
            "description": product.description, "tags": product.tags or [], "flavors": flavors, "temperature": temperature,
            "caffeine": caffeine, "caffeineFree": attrs.get("caffeine") == "none", "milk": not attrs.get("dairy_free", False),
            "available": product.available, "visible": product.visible, "image_key": product.image_key, "attributes": attrs}


def combo_out(db: Session, combo: Combo) -> dict[str, Any]:
    products = db.scalars(select(Product).where(Product.id.in_(combo.product_ids or []), Product.visible.is_(True))).all() if combo.product_ids else []
    subtotal = sum(p.price_toman for p in products)
    discount = subtotal * min(combo.discount_value, 100) // 100 if combo.discount_type == "percent" else min(combo.discount_value, subtotal) if combo.discount_type == "fixed" else 0
    valid = len(products) == len(combo.product_ids or []) and all(p.available for p in products)
    return {"id": combo.id, "name": combo.name, "description": combo.description, "strategy": combo.strategy,
            "product_ids": combo.product_ids or [], "products": [product_out(p) for p in products],
            "price_toman": max(0, subtotal-discount), "discount_toman": discount, "active": combo.active and valid}


def order_out(order: CafeOrder, include_code: str | None = None) -> dict[str, Any]:
    result = {"id": order.id, "table_token": order.table_token,
              "table_label": order.table.label if order.table else order.table_token, "status": order.status,
              "total_toman": order.total_toman,
              "items": [{"id": item.id, "kind": item.kind, "name": item.item_name_snapshot, "quantity": item.quantity,
                         "unit_price_toman": item.unit_price_toman, "line_total_toman": item.unit_price_toman*item.quantity,
                         "options": item.options or {}} for item in order.items],
              "created_at": iso(order.created_at), "verification_expires_at": iso(order.verification_expires_at),
              "verification_expired": now_utc() > (aware(order.verification_expires_at) or now_utc()), "verified_at": iso(order.verified_at)}
    if include_code is not None:
        result["confirmation_code"] = include_code
    return result


def get_setting(db: Session, key: str, default: dict[str, Any]) -> dict[str, Any]:
    setting = db.get(MerchantSetting, key)
    return setting.value if setting else default


def set_setting(db: Session, key: str, value: dict[str, Any]) -> None:
    setting = db.get(MerchantSetting, key)
    if setting:
        setting.value = value
    else:
        db.add(MerchantSetting(key=key, value=value))


def seed_data(db: Session) -> None:
    if not db.scalar(select(User.id).limit(1)) and APP_ENV != "production":
        db.add_all([
            User(email="owner@aramesh.local", password_hash=hash_password("Owner@12345"), full_name="مدیر کافه آرامش", role="owner"),
            User(email="waiter@aramesh.local", password_hash=hash_password("Waiter@12345"), full_name="کارمند کافه", role="waiter"),
            User(email="member@aramesh.local", password_hash=hash_password("Member@12345"), full_name="عضو باشگاه آرامش", role="customer"),
        ])
        db.flush()
        for customer in db.scalars(select(User).where(User.role == "customer")).all():
            db.add(LoyaltyBalance(user_id=customer.id, points=0))
    if not db.scalar(select(Category.id).limit(1)):
        categories = [Category(name="قهوه گرم", slug="hot-coffee", sort_order=1), Category(name="نوشیدنی سرد", slug="cold-drinks", sort_order=2),
                      Category(name="چای و دمنوش", slug="tea", sort_order=3), Category(name="کیک و میان‌وعده", slug="snacks", sort_order=4)]
        db.add_all(categories)
        db.flush()
        c = {item.slug: item.id for item in categories}
        products = [
            Product(category_id=c["hot-coffee"], name="اسپرسو دوبل", subtitle="کوچک، جدی و دقیق", description="قهوه‌ای فشرده با طعمی عمیق.", price_toman=95000, image_key="espresso", attributes={"temperature":"hot","flavors":["bitter"],"sweetness":"low","caffeine":"high","dairy_free":True}, tags=["قهوه","قوی","تلخ","درس","کار"]),
            Product(category_id=c["hot-coffee"], name="آمریکانو", subtitle="شفاف و متعادل", description="اسپرسو با آب داغ؛ انتخابی ساده برای یک مکث آرام.", price_toman=115000, image_key="americano", attributes={"temperature":"hot","flavors":["bitter"],"sweetness":"low","caffeine":"high","dairy_free":True}, tags=["قهوه","تلخ","کار","درس"]),
            Product(category_id=c["hot-coffee"], name="لاته", subtitle="نرم و شیرمحور", description="ترکیب اسپرسو و شیر بخار داده‌شده.", price_toman=145000, image_key="latte", attributes={"temperature":"hot","flavors":["creamy"],"sweetness":"medium","caffeine":"medium","dairy_free":False}, tags=["قهوه","شیر","ملایم"]),
            Product(category_id=c["cold-drinks"], name="آیس آمریکانو", subtitle="خنک و بدون شیر", description="اسپرسو و آب سرد روی یخ.", price_toman=125000, image_key="iced-coffee", attributes={"temperature":"cold","flavors":["bitter"],"sweetness":"low","caffeine":"high","dairy_free":True}, tags=["قهوه","سرد","بدون شیر","تلخ","کار"]),
            Product(category_id=c["cold-drinks"], name="لیموناد خانگی", subtitle="ترش و تازه", description="نوشیدنی خنک با طعم غالب لیمو.", price_toman=115000, image_key="lemonade", attributes={"temperature":"cold","flavors":["sour","citrus","refreshing"],"sweetness":"low","caffeine":"none","dairy_free":True}, tags=["سرد","ترش","لیمو","خنک","بدون شیر"]),
            Product(category_id=c["cold-drinks"], name="آیس لاته", subtitle="نرم و خنک", description="اسپرسو، شیر سرد و یخ.", price_toman=155000, image_key="iced-latte", attributes={"temperature":"cold","flavors":["creamy","bitter"],"sweetness":"medium","caffeine":"medium","dairy_free":False}, tags=["سرد","قهوه","شیر"]),
            Product(category_id=c["cold-drinks"], name="چای سرد هلو", subtitle="میوه‌ای و ملایم", description="چای سرد با رایحه هلو.", price_toman=120000, image_key="peach-tea", attributes={"temperature":"cold","flavors":["fruity"],"sweetness":"medium","caffeine":"low","dairy_free":True}, tags=["سرد","میوه‌ای","هلو"]),
            Product(category_id=c["tea"], name="چای ایرانی", subtitle="آشنا و آرام", description="چای سیاه دم‌کشیده.", price_toman=65000, image_key="tea", attributes={"temperature":"hot","flavors":["earthy"],"sweetness":"low","caffeine":"medium","dairy_free":True}, tags=["چای","گرم"]),
            Product(category_id=c["tea"], name="دمنوش به‌لیمو", subtitle="معطر و گیاهی", description="دمنوش گیاهی با عطر لیمویی.", price_toman=85000, image_key="herbal-tea", attributes={"temperature":"hot","flavors":["citrus","herbal"],"sweetness":"low","caffeine":"none","dairy_free":True}, tags=["دمنوش","گیاهی","بدون کافئین"]),
            Product(category_id=c["snacks"], name="کیک شکلاتی", subtitle="یک همراه کوچک", description="برای اطلاعات آلرژن از کارکنان بپرسید.", price_toman=105000, image_key="cake", attributes={"temperature":"room","flavors":["chocolate","sweet"],"sweetness":"high","allergens_unknown":True}, tags=["کیک","شکلات"]),
            Product(category_id=c["snacks"], name="کوکی شکلاتی", subtitle="یک همراه کوچک", description="مواد اولیه و آلرژن‌ها را از کارکنان بپرسید.", price_toman=75000, image_key="cookie", attributes={"temperature":"room","flavors":["chocolate","sweet"],"sweetness":"high","allergens_unknown":True}, tags=["کوکی","شکلات"]),
        ]
        db.add_all(products)
        db.flush()
        ids = {p.name:p.id for p in products}
        db.add_all([
            Combo(name="همراه تمرکز", description="قهوه قوی در کنار یک میان‌وعده کوچک.", strategy="curated", discount_type="percent", discount_value=5, product_ids=[ids["اسپرسو دوبل"], ids["کوکی شکلاتی"]]),
            Combo(name="خنک و ترش", description="لیموناد خانگی در کنار کوکی شکلاتی.", strategy="curated", discount_type="none", discount_value=0, product_ids=[ids["لیموناد خانگی"], ids["کوکی شکلاتی"]]),
        ])
    for token, label in [("T01","میز ۱"),("T02","میز ۲"),("T03","میز ۳"),("TAKEAWAY","بیرون‌بر")]:
        if not db.get(CafeTable, token):
            db.add(CafeTable(token=token, label=label))
    defaults = {
        "work_mode": {"enabled":True,"durations":[120,180],"eligible_product_tags":["کار","درس"],"minimum_total_toman":90000,
                      "instructions":"برای راهنمایی اتصال به اینترنت از کارکنان کمک بگیرید.",
                      "terms":"زمان جلسه از تأیید کارکنان محاسبه می‌شود؛ این سامانه اتصال شبکه را کنترل نمی‌کند."},
        "loyalty": {"enabled":True,"points_per_100k_toman":1,"rewards":[{"id":"drink-20","name":"تخفیف ۲۰ هزار تومانی","points":8,"discount_toman":20000,"active":True},
                    {"id":"drink-40","name":"تخفیف ۴۰ هزار تومانی","points":15,"discount_toman":40000,"active":True}]},
    }
    for key, value in defaults.items():
        if not db.get(MerchantSetting, key):
            db.add(MerchantSetting(key=key, value=value))
    db.commit()


def init_db() -> None:
    if APP_ENV != "production" or os.getenv("AUTO_CREATE_SCHEMA", "false").lower() == "true":
        Base.metadata.create_all(bind=engine)
    if APP_ENV != "production":
        with SessionLocal() as db:
            seed_data(db)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Café Aramesh Smart Menu API", version="1.0.0", lifespan=lifespan)
origins = [x.strip() for x in os.getenv("CORS_ORIGINS", "").split(",") if x.strip()]
if origins:
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False,
                       allow_methods=["GET","POST","PUT","PATCH","DELETE","OPTIONS"],
                       allow_headers=["Authorization","Content-Type","Idempotency-Key"])


class LoginInput(BaseModel):
    email: str
    password: str


class RegisterInput(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=120)


class ProductInput(BaseModel):
    category_id: int
    name: str = Field(min_length=2, max_length=120)
    subtitle: str = Field(default="", max_length=180)
    description: str = Field(default="", max_length=2000)
    price_toman: int = Field(ge=0, le=100_000_000)
    image_key: str = "coffee"
    available: bool = True
    visible: bool = True
    attributes: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list, max_length=40)

    @field_validator("attributes")
    @classmethod
    def validate_attributes(cls, value: dict[str, Any]) -> dict[str, Any]:
        choices = {"temperature":{"hot","cold","room",None},"sweetness":{"low","medium","high",None},
                   "caffeine":{"none","low","medium","high",None}}
        for key, allowed in choices.items():
            if key in value and value[key] not in allowed:
                raise ValueError(f"مقدار ویژگی {key} معتبر نیست.")
        allowed_flavors = {"sour","fruity","bitter","creamy","citrus","refreshing","herbal","chocolate","earthy","sweet"}
        flavors = value.get("flavors", [])
        if not isinstance(flavors, list) or any(not isinstance(x, str) or x not in allowed_flavors for x in flavors):
            raise ValueError("ویژگی‌های طعمی معتبر نیستند.")
        return value


class CategoryInput(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    slug: str = Field(min_length=2, max_length=80, pattern=r"^[a-z0-9-]+$")
    sort_order: int = Field(default=0, ge=0, le=1000)


class ComboInput(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=1000)
    strategy: Literal["curated","popular","promote"] = "curated"
    discount_type: Literal["none","percent","fixed"] = "none"
    discount_value: int = Field(default=0, ge=0, le=100_000_000)
    product_ids: list[int] = Field(min_length=2, max_length=10)
    active: bool = True


class OrderLineInput(BaseModel):
    kind: Literal["product","combo"] = "product"
    id: int
    quantity: int = Field(ge=1, le=20)


class OrderInput(BaseModel):
    table_token: str = Field(min_length=2, max_length=40)
    items: list[OrderLineInput] = Field(min_length=1, max_length=30)
    idempotency_key: str | None = Field(default=None, max_length=80)


class VerifyInput(BaseModel):
    code: str = Field(min_length=4, max_length=4, pattern=r"^\d{4}$")

    @field_validator("code", mode="before")
    @classmethod
    def normalize_code(cls, value: Any) -> Any:
        return value.translate(DIGIT_TRANS) if isinstance(value, str) else value


class StatusInput(BaseModel):
    status: Literal["preparing","ready","served","cancelled"]


class WorkSessionInput(BaseModel):
    order_id: str
    duration_minutes: int = Field(ge=30, le=240)


class SettingInput(BaseModel):
    value: dict[str, Any]


class RedeemInput(BaseModel):
    reward_id: str


@app.get("/api/health")
def health():
    return {"status":"ok","service":"cafe-aramesh","environment":APP_ENV}


@app.post("/api/auth/login")
def login(data: LoginInput, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == data.email.strip().lower()))
    if not user or not user.active or not check_password(data.password, user.password_hash):
        raise HTTPException(401, "ایمیل یا گذرواژه درست نیست.")
    return {"access_token":token_for(user),"token_type":"bearer","user":user_data(user)}


@app.post("/api/auth/register")
def register(data: RegisterInput, db: Session = Depends(get_db)):
    email = data.email.strip().lower()
    if "@" not in email:
        raise HTTPException(422, "ایمیل معتبر وارد کنید.")
    if db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(409, "این ایمیل قبلاً ثبت شده است.")
    user = User(email=email, password_hash=hash_password(data.password), full_name=data.full_name.strip(), role="customer")
    db.add(user)
    db.flush()
    db.add(LoyaltyBalance(user_id=user.id, points=0))
    db.commit()
    db.refresh(user)
    return {"access_token":token_for(user),"token_type":"bearer","user":user_data(user)}


@app.get("/api/auth/me")
def me(user: User = Depends(current_user)):
    return user_data(user)


@app.get("/api/categories")
def list_categories(db: Session = Depends(get_db)):
    rows = db.scalars(select(Category).order_by(Category.sort_order, Category.name)).all()
    return [{"id":x.id,"name":x.name,"slug":x.slug,"sort_order":x.sort_order} for x in rows]


@app.get("/api/menu")
def menu(category_id: int | None = None, q: str | None = None, db: Session = Depends(get_db)):
    query = select(Product).where(Product.visible.is_(True))
    if category_id is not None:
        query = query.where(Product.category_id == category_id)
    products = db.scalars(query.order_by(Product.category_id, Product.name)).all()
    if q:
        needle = normalize_fa(q)
        products = [p for p in products if needle in normalize_fa(" ".join([p.name,p.subtitle,p.description," ".join(p.tags or [])]))]
    return {"products":[product_out(p) for p in products],"categories":list_categories(db)}


@app.get("/api/combos")
def combos(db: Session = Depends(get_db)):
    rows = db.scalars(select(Combo).where(Combo.active.is_(True)).order_by(Combo.id)).all()
    result = []
    for combo in rows:
        item = combo_out(db, combo)
        if item["active"]:
            item["recommendation_reason"] = "ترکیبی که کافه با دقت انتخاب کرده است."
            result.append(item)
    return result[:6]


@app.get("/api/search/natural")
def natural_search(query: str = Query(min_length=1, max_length=240), db: Session = Depends(get_db)):
    raw = normalize_fa(query)
    products = db.scalars(select(Product).where(Product.visible.is_(True), Product.available.is_(True))).all()
    rules = {"temperature":("سرد","خنک","یخ","آیس"),"sour":("ترش","لیمو","مرکبات"),
             "fruity":("میوه","هلو","بری"),"low_sweet":("کم شیرین","کمشیرین","شیرین نباشه","بدون شکر","کم شکر"),
             "strong":("قوی","پرکافئین","کافئین بالا","درس خوندن","کار کردن","تمرکز"),
             "dairy_free":("بدون شیر","بدون لبنیات","غیرلبنی","شیر نداشته"),
             "no_caffeine":("بدون کافئین","کافئین نداشته"),"hot":("گرم","داغ")}
    requested = {key for key, terms in rules.items() if any(normalize_fa(term) in raw for term in terms)}
    results = []
    for p in products:
        attrs = p.attributes or {}
        checks = []
        if "temperature" in requested: checks.append((attrs.get("temperature") == "cold", "دمای سرد"))
        if "hot" in requested: checks.append((attrs.get("temperature") == "hot", "دمای گرم"))
        if "sour" in requested: checks.append(("sour" in attrs.get("flavors", []), "طعم ترش"))
        if "fruity" in requested: checks.append(("fruity" in attrs.get("flavors", []), "طعم میوه‌ای"))
        if "low_sweet" in requested: checks.append((attrs.get("sweetness") == "low", "شیرینی کمتر"))
        if "strong" in requested: checks.append((attrs.get("caffeine") == "high", "کافئین بالا"))
        if "dairy_free" in requested: checks.append((attrs.get("dairy_free") is True, "بدون شیر بر اساس داده منو"))
        if "no_caffeine" in requested: checks.append((attrs.get("caffeine") == "none", "بدون کافئین"))
        if checks and not all(ok for ok, _ in checks):
            continue
        text = normalize_fa(" ".join([p.name,p.subtitle,p.description," ".join(p.tags or [])]))
        stop_words = {"یه","یک","نوشیدنی","چیز","چیزی","خیلی","دنبال","پیشنهاد","بده","بده","خوام","می","میخوام","میخوام","می خوام","برای","من","تو","سلیقه","یه","و","با","رو","را","از","به","یه","لطفا"}
        meaningful_terms = [term for term in raw.split() if len(term) > 2 and term not in stop_words]
        soft = sum(1 for term in meaningful_terms if term in text)
        # Generic request words must not create a false match on their own.
        score = len(checks)*3 + soft
        has_attribute_match = bool(checks) and all(ok for ok, _ in checks)
        if (has_attribute_match and score > 0) or (not requested and soft > 0):
            results.append((score,p,[label for ok,label in checks if ok] or ["شباهت با عبارت جست‌وجو"]))
    results.sort(key=lambda x:(-x[0],x[1].price_toman,x[1].name))
    return {"query":query,"provider":"rule-based","supported_preferences":bool(requested),
            "matches":[{**product_out(p),"match_score":score,"match_reasons":reason} for score,p,reason in results[:8]],
            "message":"این پیشنهادها از ویژگی‌های ثبت‌شده در منوی کافه انتخاب شده‌اند." if results else
                      "گزینه دقیقی پیدا نشد. عبارت‌هایی مثل «نوشیدنی سرد»، «قهوه قوی» یا «بدون شیر» را امتحان کنید."}


@app.post("/api/orders")
def create_order(data: OrderInput, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    if data.idempotency_key:
        old = db.scalar(select(CafeOrder).where(CafeOrder.idempotency_key == data.idempotency_key))
        if old: raise HTTPException(409, "این درخواست قبلاً ثبت شده است؛ کد پیگیری را بررسی کنید.")
    table = db.get(CafeTable, data.table_token)
    if not table or not table.active: raise HTTPException(422, "میز انتخاب‌شده معتبر نیست.")
    user = optional_user(authorization, db)
    if user and user.role != "customer": user = None
    resolved: list[tuple[str,int|None,str,int,int,dict[str,Any]]] = []
    total = 0
    for line in data.items:
        if line.kind == "product":
            p = db.get(Product, line.id)
            if not p or not p.visible or not p.available: raise HTTPException(409, "یکی از محصولات سبد دیگر موجود نیست؛ منو را تازه‌سازی کنید.")
            resolved.append(("product",p.id,p.name,p.price_toman,line.quantity,{})); total += p.price_toman*line.quantity
        else:
            combo = db.get(Combo, line.id)
            if not combo or not combo.active: raise HTTPException(409, "این ترکیب دیگر فعال نیست.")
            c = combo_out(db, combo)
            if not c["active"]: raise HTTPException(409, "یکی از اقلام این ترکیب موجود نیست.")
            resolved.append(("combo",None,combo.name,c["price_toman"],line.quantity,{"product_ids":combo.product_ids}))
            total += c["price_toman"]*line.quantity
    if total <= 0: raise HTTPException(422, "مبلغ درخواست معتبر نیست.")
    code = f"{secrets.randbelow(9999)+1:04d}"
    digest = hashlib.sha256((JWT_SECRET+code).encode()).hexdigest()
    order = CafeOrder(id=secrets.token_hex(16).upper(),table_token=table.token,customer_user_id=user.id if user else None,
                      status="pending_verification",total_toman=total,code_digest=digest,
                      verification_expires_at=now_utc()+timedelta(minutes=15),idempotency_key=data.idempotency_key)
    db.add(order); db.flush()
    for kind,pid,name,price,qty,options in resolved:
        db.add(OrderItem(order_id=order.id,product_id=pid,kind=kind,item_name_snapshot=name,unit_price_toman=price,quantity=qty,options=options))
    db.add(OrderEvent(order_id=order.id,from_status="created",to_status="pending_verification"))
    try: db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "درخواست تکراری است. وضعیت درخواست قبلی را بررسی کنید.")
    db.refresh(order)
    return {**order_out(order,code),"message":"درخواست شما ثبت شد. لطفاً کد تأیید را هنگام مراجعه به گارسون اعلام کنید. پرداختی انجام نشده است."}


@app.get("/api/orders/{order_id}")
def get_order(order_id: str, db: Session = Depends(get_db)):
    order = db.get(CafeOrder, order_id.upper())
    if not order: raise HTTPException(404, "درخواست موردنظر پیدا نشد.")
    return order_out(order)


@app.get("/api/staff/orders")
def staff_orders(view: Literal["pending","active","history"]="pending", user: User=Depends(require_roles("waiter")), db: Session=Depends(get_db)):
    states={"pending":["pending_verification"],"active":["confirmed","preparing","ready"],"history":["served","cancelled","expired"]}[view]
    rows=db.scalars(select(CafeOrder).where(CafeOrder.status.in_(states)).order_by(CafeOrder.created_at.desc()).limit(100)).all()
    output=[]
    for order in rows:
        row=order_out(order);row["waiting_minutes"]=max(0,int((now_utc()-(aware(order.created_at) or now_utc())).total_seconds()//60));output.append(row)
    return output


@app.post("/api/staff/orders/{order_id}/verify")
def verify_order(order_id: str,data: VerifyInput,user: User=Depends(require_roles("waiter")),db: Session=Depends(get_db)):
    order=db.get(CafeOrder,order_id.upper())
    if not order or order.status!="pending_verification":raise HTTPException(400,"درخواست قابل تأیید نیست.")
    if order.verification_attempts>=5 or now_utc()>(aware(order.verification_expires_at) or now_utc()):
        order.status="expired";db.add(OrderEvent(order_id=order.id,actor_user_id=user.id,from_status="pending_verification",to_status="expired"));db.commit()
        raise HTTPException(400,"مهلت تأیید این درخواست پایان یافته است.")
    supplied=hashlib.sha256((JWT_SECRET+data.code).encode()).hexdigest()
    if not hmac.compare_digest(supplied,order.code_digest):
        order.verification_attempts+=1
        if order.verification_attempts>=5:
            order.status="expired";db.add(OrderEvent(order_id=order.id,actor_user_id=user.id,from_status="pending_verification",to_status="expired"))
        db.commit()
        raise HTTPException(400,"کد واردشده صحیح نیست. کد را از مشتری دوباره بپرسید.")
    order.status="confirmed";order.verified_at=now_utc()
    db.add(OrderEvent(order_id=order.id,actor_user_id=user.id,from_status="pending_verification",to_status="confirmed"))
    db.commit();db.refresh(order)
    return {"message":"کد تأیید شد؛ درخواست برای آماده‌سازی ثبت شد.","order":order_out(order)}


TRANSITIONS={"confirmed":{"preparing","cancelled"},"preparing":{"ready","cancelled"},"ready":{"served","cancelled"},"pending_verification":{"cancelled","expired"}}


@app.patch("/api/staff/orders/{order_id}/status")
def change_order_status(order_id: str,data: StatusInput,user: User=Depends(require_roles("waiter")),db: Session=Depends(get_db)):
    order=db.get(CafeOrder,order_id.upper())
    if not order:raise HTTPException(404,"درخواست پیدا نشد.")
    if data.status not in TRANSITIONS.get(order.status,set()):raise HTTPException(409,"تغییر وضعیت درخواست مجاز نیست.")
    old=order.status;order.status=data.status
    if data.status=="served":
        order.served_at=now_utc()
        if order.customer_user_id:
            cfg=get_setting(db,"loyalty",{"enabled":True,"points_per_100k_toman":1})
            existing=db.scalar(select(LoyaltyEntry.id).where(LoyaltyEntry.order_id==order.id,LoyaltyEntry.reason=="order_earned"))
            if cfg.get("enabled",True) and not existing:
                pts=max(1,(order.total_toman//100000)*max(1,int(cfg.get("points_per_100k_toman",1))))
                db.execute(update(LoyaltyBalance).where(LoyaltyBalance.user_id==order.customer_user_id).values(points=LoyaltyBalance.points+pts))
                db.add(LoyaltyEntry(user_id=order.customer_user_id,order_id=order.id,points_delta=pts,reason="order_earned"))
    db.add(OrderEvent(order_id=order.id,actor_user_id=user.id,from_status=old,to_status=data.status))
    db.commit();db.refresh(order)
    return {"message":"وضعیت درخواست به‌روزرسانی شد.","order":order_out(order)}


@app.get("/api/work-mode")
def work_mode_info(db: Session=Depends(get_db)):
    return get_setting(db,"work_mode",{"enabled":False,"durations":[],"instructions":"","terms":""})


@app.post("/api/work-mode/sessions")
def start_work_session(data: WorkSessionInput,authorization: str|None=Header(default=None),db: Session=Depends(get_db)):
    cfg=get_setting(db,"work_mode",{})
    if not cfg.get("enabled"):raise HTTPException(409,"حالت مطالعه و کار اکنون فعال نیست.")
    if data.duration_minutes not in [int(x) for x in cfg.get("durations",[])]:raise HTTPException(422,"مدت انتخاب‌شده در تنظیمات کافه وجود ندارد.")
    user=optional_user(authorization,db);order=db.get(CafeOrder,data.order_id.upper())
    if not order or order.status not in {"confirmed","preparing","ready","served"}:raise HTTPException(403,"ابتدا باید درخواست سفارش شما توسط کارکنان تأیید شود.")
    if user and user.role=="customer" and order.customer_user_id not in (None,user.id):raise HTTPException(403,"این درخواست به حساب شما تعلق ندارد.")
    if user and user.role=="customer":
        active=db.scalar(select(WorkSession).where(WorkSession.customer_user_id==user.id,WorkSession.status=="active",WorkSession.expires_at>now_utc()))
        if active:raise HTTPException(409,"برای حساب شما یک جلسه فعال وجود دارد.")
    if order.total_toman<int(cfg.get("minimum_total_toman",0)):raise HTTPException(403,"مبلغ سفارش به حداقل لازم برای حالت مطالعه و کار نمی‌رسد.")
    tags=set(cfg.get("eligible_product_tags",[]));eligible=False
    for item in order.items:
        ids=[item.product_id] if item.product_id else item.options.get("product_ids",[])
        if ids:
            for p in db.scalars(select(Product).where(Product.id.in_(ids))).all():
                if tags.intersection(p.tags or []):eligible=True
    if not eligible:raise HTTPException(403,"اقلام این سفارش برای حالت مطالعه و کار واجد شرایط نیستند.")
    start=now_utc()
    session=WorkSession(id=secrets.token_hex(16).upper(),order_id=order.id,customer_user_id=user.id if user and user.role=="customer" else None,
                        duration_minutes=data.duration_minutes,status="active",starts_at=start,expires_at=start+timedelta(minutes=data.duration_minutes))
    db.add(session);db.commit()
    return {"id":session.id,"order_id":order.id,"status":"active","duration_minutes":session.duration_minutes,
            "starts_at":iso(session.starts_at),"expires_at":iso(session.expires_at),"instructions":cfg.get("instructions",""),
            "terms":cfg.get("terms",""),"notice":"زمان‌بندی جلسه ثبت می‌شود؛ این نسخه اتصال یا قطع خودکار اینترنت را کنترل نمی‌کند."}


@app.get("/api/work-mode/sessions/{session_id}")
def work_session_status(session_id: str,db: Session=Depends(get_db)):
    session=db.get(WorkSession,session_id.upper())
    if not session:raise HTTPException(404,"جلسه پیدا نشد.")
    if session.status=="active" and now_utc()>=(aware(session.expires_at) or now_utc()):session.status="expired";db.commit()
    cfg=get_setting(db,"work_mode",{})
    return {"id":session.id,"order_id":session.order_id,"status":session.status,"duration_minutes":session.duration_minutes,
            "starts_at":iso(session.starts_at),"expires_at":iso(session.expires_at),"instructions":cfg.get("instructions","")}


@app.get("/api/loyalty/me")
def loyalty_me(user: User=Depends(require_roles("customer")),db: Session=Depends(get_db)):
    cfg=get_setting(db,"loyalty",{"enabled":False,"rewards":[]});balance=db.get(LoyaltyBalance,user.id)
    entries=db.scalars(select(LoyaltyEntry).where(LoyaltyEntry.user_id==user.id).order_by(LoyaltyEntry.created_at.desc()).limit(100)).all()
    return {"enabled":cfg.get("enabled",False),"member":{"name":user.full_name,"email":user.email},"points":balance.points if balance else 0,
            "rewards":[r for r in cfg.get("rewards",[]) if r.get("active",True)],
            "history":[{"points_delta":e.points_delta,"reason":e.reason,"created_at":iso(e.created_at)} for e in entries]}


@app.post("/api/loyalty/redeem")
def loyalty_redeem(data: RedeemInput,user: User=Depends(require_roles("customer")),db: Session=Depends(get_db)):
    cfg=get_setting(db,"loyalty",{"enabled":False,"rewards":[]})
    if not cfg.get("enabled"):raise HTTPException(409,"باشگاه مشتریان اکنون غیرفعال است.")
    reward=next((r for r in cfg.get("rewards",[]) if r.get("id")==data.reward_id and r.get("active",True)),None)
    if not reward:raise HTTPException(404,"پاداش فعال پیدا نشد.")
    cost=int(reward["points"])
    changed=db.execute(update(LoyaltyBalance).where(LoyaltyBalance.user_id==user.id,LoyaltyBalance.points>=cost).values(points=LoyaltyBalance.points-cost))
    if changed.rowcount!=1:
        db.rollback();raise HTTPException(409,"امتیاز شما برای دریافت این پاداش کافی نیست.")
    db.add(LoyaltyEntry(user_id=user.id,order_id=None,points_delta=-cost,reason="reward_redeemed:"+str(reward["id"])))
    db.commit();balance=db.get(LoyaltyBalance,user.id)
    return {"message":"درخواست پاداش برای بررسی کارکنان ثبت شد.","points":balance.points,"reward":reward,"note":"اعمال تخفیف نهایی در صندوق باید توسط کارکنان انجام شود."}


@app.get("/api/merchant/categories")
def merchant_categories(user: User=Depends(require_roles("owner")),db: Session=Depends(get_db)):
    return list_categories(db)


@app.post("/api/merchant/categories",status_code=201)
def create_category(data: CategoryInput,user: User=Depends(require_roles("owner")),db: Session=Depends(get_db)):
    category=Category(name=data.name.strip(),slug=data.slug,sort_order=data.sort_order);db.add(category)
    try:db.commit()
    except IntegrityError:
        db.rollback();raise HTTPException(409,"نام یا شناسه دسته‌بندی قبلاً استفاده شده است.")
    db.refresh(category);return {"id":category.id,"name":category.name,"slug":category.slug,"sort_order":category.sort_order}


@app.put("/api/merchant/categories/{category_id}")
def update_category(category_id: int,data: CategoryInput,user: User=Depends(require_roles("owner")),db: Session=Depends(get_db)):
    category=db.get(Category,category_id)
    if not category:raise HTTPException(404,"دسته‌بندی پیدا نشد.")
    category.name,category.slug,category.sort_order=data.name.strip(),data.slug,data.sort_order
    try:db.commit()
    except IntegrityError:
        db.rollback();raise HTTPException(409,"نام یا شناسه دسته‌بندی قبلاً استفاده شده است.")
    return {"id":category.id,"name":category.name,"slug":category.slug,"sort_order":category.sort_order}


@app.get("/api/merchant/products")
def merchant_products(user: User=Depends(require_roles("owner")),db: Session=Depends(get_db)):
    return [product_out(p) for p in db.scalars(select(Product).order_by(Product.category_id,Product.name)).all()]


@app.post("/api/merchant/products",status_code=201)
def create_product(data: ProductInput,user: User=Depends(require_roles("owner")),db: Session=Depends(get_db)):
    if not db.get(Category,data.category_id):raise HTTPException(422,"دسته‌بندی انتخاب‌شده معتبر نیست.")
    product=Product(**data.model_dump());db.add(product);db.commit();db.refresh(product);return product_out(product)


@app.put("/api/merchant/products/{product_id}")
def update_product(product_id: int,data: ProductInput,user: User=Depends(require_roles("owner")),db: Session=Depends(get_db)):
    product=db.get(Product,product_id)
    if not product:raise HTTPException(404,"محصول پیدا نشد.")
    if not db.get(Category,data.category_id):raise HTTPException(422,"دسته‌بندی انتخاب‌شده معتبر نیست.")
    for key,value in data.model_dump().items():setattr(product,key,value)
    db.commit();db.refresh(product);return product_out(product)


@app.delete("/api/merchant/products/{product_id}")
def delete_product(product_id: int,user: User=Depends(require_roles("owner")),db: Session=Depends(get_db)):
    product=db.get(Product,product_id)
    if not product:raise HTTPException(404,"محصول پیدا نشد.")
    if db.scalar(select(OrderItem.id).where(OrderItem.product_id==product_id).limit(1)):
        product.visible=False;product.available=False;db.commit()
        return {"message":"محصول از منو پنهان شد؛ تاریخچه سفارش‌ها حفظ شد."}
    for combo in db.scalars(select(Combo)).all():
        if product_id in (combo.product_ids or []):combo.active=False
    db.delete(product);db.commit();return {"message":"محصول حذف شد."}


@app.get("/api/merchant/combos")
def merchant_combos(user: User=Depends(require_roles("owner")),db: Session=Depends(get_db)):
    return [combo_out(db,c) for c in db.scalars(select(Combo).order_by(Combo.id.desc())).all()]


def validate_combo_products(db: Session,data: ComboInput):
    if data.discount_type=="percent" and data.discount_value>100:raise HTTPException(422,"تخفیف درصدی نمی‌تواند بیش از ۱۰۰ درصد باشد.")
    products=db.scalars(select(Product).where(Product.id.in_(data.product_ids))).all()
    if len({p.id for p in products})!=len(set(data.product_ids)):raise HTTPException(422,"یکی از محصولات انتخابی وجود ندارد.")


@app.post("/api/merchant/combos",status_code=201)
def create_combo(data: ComboInput,user: User=Depends(require_roles("owner")),db: Session=Depends(get_db)):
    validate_combo_products(db,data);combo=Combo(**data.model_dump());db.add(combo);db.commit();db.refresh(combo);return combo_out(db,combo)


@app.put("/api/merchant/combos/{combo_id}")
def update_combo(combo_id: int,data: ComboInput,user: User=Depends(require_roles("owner")),db: Session=Depends(get_db)):
    combo=db.get(Combo,combo_id)
    if not combo:raise HTTPException(404,"ترکیب پیدا نشد.")
    validate_combo_products(db,data)
    for key,value in data.model_dump().items():setattr(combo,key,value)
    db.commit();db.refresh(combo);return combo_out(db,combo)


@app.delete("/api/merchant/combos/{combo_id}")
def deactivate_combo(combo_id: int,user: User=Depends(require_roles("owner")),db: Session=Depends(get_db)):
    combo=db.get(Combo,combo_id)
    if not combo:raise HTTPException(404,"ترکیب پیدا نشد.")
    combo.active=False;db.commit();return {"message":"ترکیب غیرفعال شد."}


@app.get("/api/merchant/settings")
def merchant_settings(user: User=Depends(require_roles("owner")),db: Session=Depends(get_db)):
    return {"work_mode":get_setting(db,"work_mode",{}),"loyalty":get_setting(db,"loyalty",{})}


@app.put("/api/merchant/settings/{key}")
def update_setting(key: str,data: SettingInput,user: User=Depends(require_roles("owner")),db: Session=Depends(get_db)):
    if key not in {"work_mode","loyalty"}:raise HTTPException(404,"این تنظیم پشتیبانی نمی‌شود.")
    value=data.value
    if key=="work_mode":
        durations=value.get("durations",[])
        if not isinstance(durations,list) or not durations or any(not isinstance(x,int) or x<30 or x>240 for x in durations):raise HTTPException(422,"مدت‌های مجاز باید بین ۳۰ تا ۲۴۰ دقیقه باشند.")
        value["minimum_total_toman"]=max(0,int(value.get("minimum_total_toman",0)))
    else:
        rate=int(value.get("points_per_100k_toman",1));rewards=value.get("rewards",[])
        if rate<1 or rate>1000 or not isinstance(rewards,list) or len(rewards)>20:raise HTTPException(422,"قواعد باشگاه مشتریان معتبر نیست.")
        ids=set()
        for reward in rewards:
            rid=str(reward.get("id",""))
            if not re.fullmatch(r"[A-Za-z0-9_-]{2,40}",rid) or rid in ids or not str(reward.get("name","")).strip():raise HTTPException(422,"شناسه یا نام پاداش معتبر و یکتا نیست.")
            if int(reward.get("points",0))<1 or int(reward.get("discount_toman",0))<0:raise HTTPException(422,"امتیاز و مبلغ پاداش باید معتبر باشند.")
            ids.add(rid)
    set_setting(db,key,value);db.commit();return {"key":key,"value":value,"message":"تنظیمات ذخیره شد."}


def period_bounds(period: str):
    tz=ZoneInfo(CAFE_TIMEZONE);current=datetime.now(tz)
    if period=="day":
        start=current.replace(hour=0,minute=0,second=0,microsecond=0);previous=start-timedelta(days=1)
    elif period=="week":
        start=(current-timedelta(days=current.weekday())).replace(hour=0,minute=0,second=0,microsecond=0);previous=start-timedelta(days=7)
    else:
        start=current.replace(day=1,hour=0,minute=0,second=0,microsecond=0);previous=(start-timedelta(days=1)).replace(day=1)
    return start.astimezone(timezone.utc),current.astimezone(timezone.utc),previous.astimezone(timezone.utc),start.astimezone(timezone.utc)


def summarize_orders(orders: list[CafeOrder]) -> dict[str,Any]:
    counts: dict[str,int]={};value=0
    for order in orders:
        value+=order.total_toman
        for item in order.items:counts[item.item_name_snapshot]=counts.get(item.item_name_snapshot,0)+item.quantity
    return {"completed_orders":len(orders),"recorded_completed_order_value_toman":value,
            "average_completed_order_toman":value//len(orders) if orders else 0,
            "top_products":[{"name":n,"quantity":q} for n,q in sorted(counts.items(),key=lambda x:(-x[1],x[0]))[:5]]}


@app.get("/api/merchant/analytics")
def analytics(period: Literal["day","week","month"]="day",user: User=Depends(require_roles("owner")),db: Session=Depends(get_db)):
    start,end,prev_start,prev_end=period_bounds(period)
    current=db.scalars(select(CafeOrder).where(CafeOrder.status=="served",CafeOrder.served_at>=start,CafeOrder.served_at<end)).all()
    previous=db.scalars(select(CafeOrder).where(CafeOrder.status=="served",CafeOrder.served_at>=prev_start,CafeOrder.served_at<prev_end)).all()
    a,b=summarize_orders(current),summarize_orders(previous)
    def change(key): return None if not b[key] else round((a[key]-b[key])*100/b[key],1)
    return {"period":period,"timezone":CAFE_TIMEZONE,"current_period":{"start":start.isoformat(),"end":end.isoformat(),**a},
            "previous_period":{"start":prev_start.isoformat(),"end":prev_end.isoformat(),**b},
            "changes":{"completed_orders_percent":change("completed_orders"),"recorded_value_percent":change("recorded_completed_order_value_toman")},
            "data_note":"فقط درخواست‌های تحویل‌شده محاسبه می‌شوند؛ این رقم لزوماً معادل کل درآمد کافه نیست."}


@app.get("/api/merchant/insights")
def insights(period: Literal["day","week","month"]="month",user: User=Depends(require_roles("owner")),db: Session=Depends(get_db)):
    start,end,_,_=period_bounds(period)
    orders=db.scalars(select(CafeOrder).where(CafeOrder.status=="served",CafeOrder.served_at>=start,CafeOrder.served_at<end)).all()
    if len(orders)<10:
        rows=[{"id":"insufficient-data","priority":"info","title":"برای نتیجه‌گیری داده کافی نیست",
               "explanation":f"در این بازه فقط {len(orders)} سفارش تکمیل‌شده ثبت شده؛ پیشنهاد درباره عملکرد محصول قابل اتکا نیست.",
               "evidence":{"completed_orders":len(orders),"period":period},"action":"پس از ثبت سفارش‌های بیشتر گزارش را دوباره بررسی کنید.","certainty":"پایین"}]
    else:
        first=summarize_orders(orders)["top_products"][0]
        rows=[{"id":"top-product","priority":"normal","title":"محصول پرتقاضا را در دید نگه دارید",
               "explanation":f"«{first['name']}» در این بازه {first['quantity']} عدد در سفارش‌های تکمیل‌شده داشته است.",
               "evidence":{"product":first["name"],"quantity":first["quantity"],"period":period},
               "action":"بررسی کنید محصول در منو به‌سادگی پیدا می‌شود.","certainty":"متوسط"}]
    return {"provider":"rule-based","period":period,"insights":rows,"note":"پیشنهادها بر اساس داده ثبت‌شده‌اند و نتیجه مالی را تضمین نمی‌کنند."}


app.mount("/", StaticFiles(directory=str(ROOT), html=True), name="site")
