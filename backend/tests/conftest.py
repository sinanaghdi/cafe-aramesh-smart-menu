from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import Cafe, CafeTable, Category, LoyaltyRule, Product, ProductTag, Reward, StudyModeRule, User
from app.services.auth.passwords import hash_password


@pytest.fixture
def api_env() -> Generator[tuple[TestClient, sessionmaker, int, int], None, None]:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    with TestingSession() as db:
        cafe = Cafe(name="کافه آزمایشی", slug="cafe-aramesh", currency_unit="IRT", timezone="Asia/Tehran")
        db.add(cafe)
        db.flush()
        table = CafeTable(
            cafe_id=cafe.id, table_number=5, label="میز ۵",
            qr_token="test-table-token", is_active=True,
        )
        category = Category(cafe_id=cafe.id, name="قهوه", slug="coffee", sort_order=1, is_active=True)
        db.add_all([table, category])
        db.flush()
        product = Product(
            cafe_id=cafe.id, category_id=category.id, slug="americano",
            name="آمریکانو", description="قهوه آزمایشی", price_amount=120000,
            margin_amount=50000, is_available=True, is_featured=True,
        )
        product2 = ProductTag(
            cafe_id=cafe.id, product_id=1, tag_key="temperature", tag_value="hot"
        )
        staff = User(
            cafe_id=cafe.id, full_name="گارسون تست", role="staff",
            email="staff@aramesh.local", password_hash=hash_password("StaffTestPass123!"),
            is_active=True,
        )
        merchant = User(
            cafe_id=cafe.id, full_name="صاحب تست", role="merchant",
            email="merchant@aramesh.local", password_hash=hash_password("MerchantTestPass123!"),
            is_active=True,
        )
        db.add(product)
        db.flush()
        product2.product_id = product.id
        db.add_all([product2, staff, merchant])
        db.add_all([
            StudyModeRule(
                cafe_id=cafe.id, enabled=True, minimum_order_amount=0,
                allowed_durations_minutes=[120, 180], allowed_start_time="00:00",
                allowed_end_time="23:59", max_concurrent_sessions=8,
            ),
            LoyaltyRule(
                cafe_id=cafe.id, enabled=True, points_per_confirmed_order=10,
                silver_threshold=30, gold_threshold=60, rewards_enabled=True,
            ),
            Reward(
                cafe_id=cafe.id, name="قهوه رایگان آزمایشی", description="پاداش تست",
                points_cost=5, reward_type="free_product", is_active=True,
            ),
        ])
        db.commit()
        product_id = product.id
        cafe_id = cafe.id

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            yield client, TestingSession, product_id, cafe_id
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()
