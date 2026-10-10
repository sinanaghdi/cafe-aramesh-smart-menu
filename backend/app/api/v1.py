import asyncio
import json
import secrets
from datetime import timedelta
from time import monotonic
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import StreamingResponse
from jwt import InvalidTokenError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal, get_db
from app.models import (
    AuditLog, AuthSession, Cafe, CafeTable, Category, Order, OrderCode, OrderItem,
    Product, ProductTag, User,
)
from app.schemas import (
    AuthUserOut, ConfirmCodeRequest, CreateOrderRequest, LoginRequest, MenuCategoryOut,
    MenuProductOut, MenuResponse, OrderCreatedOut, OrderItemCustomerOut, OrderStatusOut,
    RefreshRequest, StaffOrderItemOut, StaffOrderOut, TokenPairOut, UpdateOrderStatusRequest,
)
from app.services.auth.dependencies import require_staff
from app.services.auth.passwords import verify_password
from app.services.auth.tokens import (
    create_access_token, create_refresh_session, decode_token, hash_token_id,
    rotate_refresh_session,
)
from app.services.orders import (
    as_utc, generate_unique_order_code, hash_order_code, transition_order, utc_now,
)
from app.services.security.rate_limit import allow_attempt

router = APIRouter(prefix="/v1")
CUSTOMER_COOKIE = "aramesh_customer_session"


def _auth_user(user: User) -> AuthUserOut:
    return AuthUserOut(id=user.id, cafe_id=user.cafe_id, full_name=user.full_name, role=user.role, email=user.email)


def _staff_order(db: Session, order: Order) -> StaffOrderOut:
    table = db.get(CafeTable, order.table_id)
    items = db.scalars(select(OrderItem).where(
        OrderItem.cafe_id == order.cafe_id,
        OrderItem.order_id == order.id,
    )).all()
    # Deliberately exclude money/revenue fields from every staff response schema.
    return StaffOrderOut(
        id=order.id,
        status=order.status,
        table_number=table.table_number if table else 0,
        created_at=order.created_at,
        notes=order.notes,
        items=[StaffOrderItemOut(product_name=item.product_name_snapshot, quantity=item.quantity) for item in items],
    )


def _customer_order(db: Session, order: Order, *, code: str | None = None) -> OrderCreatedOut | OrderStatusOut:
    table = db.get(CafeTable, order.table_id)
    cafe = db.get(Cafe, order.cafe_id)
    items = db.scalars(select(OrderItem).where(
        OrderItem.cafe_id == order.cafe_id,
        OrderItem.order_id == order.id,
    )).all()
    out_items = [
        OrderItemCustomerOut(
            product_id=item.product_id,
            product_name=item.product_name_snapshot,
            quantity=item.quantity,
            unit_price_amount=item.unit_price_amount,
            line_total_amount=item.unit_price_amount * item.quantity,
        )
        for item in items
    ]
    common: dict[str, Any] = dict(
        id=order.id,
        status=order.status,
        table_number=table.table_number if table else 0,
        currency_unit=cafe.currency_unit if cafe else "IRT",
        total_amount=order.total_amount,
        items=out_items,
    )
    if code is not None:
        code_row = db.scalar(select(OrderCode).where(OrderCode.order_id == order.id))
        if code_row is None:
            raise HTTPException(status_code=500, detail="کد تأیید ایجاد نشد")
        return OrderCreatedOut(**common, code=code, code_expires_at=code_row.expires_at)
    return OrderStatusOut(**common, created_at=order.created_at)


def _customer_session(request: Request, response: Response) -> str:
    token = request.cookies.get(CUSTOMER_COOKIE)
    if not token or len(token) < 32 or len(token) > 128:
        token = secrets.token_urlsafe(32)
    response.set_cookie(
        key=CUSTOMER_COOKIE,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.customer_session_days * 24 * 60 * 60,
        path="/",
    )
    return hash_token_id(token)


def _expire_stale_orders(db: Session, cafe_id: int) -> None:
    now = utc_now()
    stale_codes = db.scalars(select(OrderCode).where(
        OrderCode.cafe_id == cafe_id,
        OrderCode.status == "active",
        OrderCode.expires_at <= now,
    )).all()
    if not stale_codes:
        return
    for code in stale_codes:
        code.status = "expired"
        order = db.scalar(select(Order).where(
            Order.id == code.order_id,
            Order.cafe_id == cafe_id,
            Order.status == "pending_confirmation",
        ))
        if order is not None:
            order.status = transition_order(order.status, "expired")
            db.add(AuditLog(
                cafe_id=cafe_id,
                actor_user_id=None,
                action="order.expired",
                entity_type="order",
                entity_id=str(order.id),
                details={"source": "expiry_sweep"},
            ))
    db.commit()


@router.post("/auth/login", response_model=TokenPairOut)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> TokenPairOut:
    client_ip = request.client.host if request.client else "unknown"
    identity = f"{client_ip}:{payload.email.strip().lower()}"
    if not allow_attempt("login", identity, limit=10, window_seconds=60):
        raise HTTPException(status_code=429, detail="تعداد تلاش‌ها زیاد است؛ کمی بعد دوباره امتحان کنید")

    cafe = db.scalar(select(Cafe).where(Cafe.slug == payload.cafe_slug))
    user = None
    if cafe is not None:
        user = db.scalar(select(User).where(
            User.cafe_id == cafe.id,
            User.email == payload.email.strip().lower(),
        ))
    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="ایمیل یا گذرواژه نادرست است")

    access_token, expires_in = create_access_token(user)
    refresh_token = create_refresh_session(db, user)
    db.commit()
    return TokenPairOut(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
        user=_auth_user(user),
    )


@router.post("/auth/refresh", response_model=TokenPairOut)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenPairOut:
    try:
        user, access_token, refresh_token, expires_in = rotate_refresh_session(db, payload.refresh_token)
    except (InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        db.rollback()
        raise HTTPException(status_code=401, detail="نشست منقضی یا باطل شده است") from exc
    return TokenPairOut(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
        user=_auth_user(user),
    )


@router.post("/auth/logout", status_code=204)
def logout(payload: RefreshRequest, db: Session = Depends(get_db)) -> Response:
    try:
        claims = decode_token(payload.refresh_token, expected_type="refresh")
        jti = claims.get("jti")
        if isinstance(jti, str):
            record = db.scalar(select(AuthSession).where(
                AuthSession.refresh_jti_hash == hash_token_id(jti),
                AuthSession.revoked_at.is_(None),
            ))
            if record is not None:
                record.revoked_at = utc_now()
                db.commit()
    except (InvalidTokenError, KeyError, TypeError, ValueError):
        db.rollback()
    return Response(status_code=204)


@router.get("/menu", response_model=MenuResponse)
def menu(
    table: int | None = Query(default=None, ge=1, le=500),
    db: Session = Depends(get_db),
) -> MenuResponse:
    cafe = db.scalar(select(Cafe).where(Cafe.slug == settings.default_cafe_slug))
    if cafe is None:
        raise HTTPException(status_code=503, detail="کافه هنوز پیکربندی نشده است")
    if table is not None:
        table_row = db.scalar(select(CafeTable).where(
            CafeTable.cafe_id == cafe.id,
            CafeTable.table_number == table,
            CafeTable.is_active.is_(True),
        ))
        if table_row is None:
            raise HTTPException(status_code=404, detail="میز معتبر نیست")

    categories = db.scalars(select(Category).where(
        Category.cafe_id == cafe.id,
        Category.is_active.is_(True),
    ).order_by(Category.sort_order, Category.id)).all()
    products = db.scalars(select(Product).where(
        Product.cafe_id == cafe.id,
    ).order_by(Product.is_featured.desc(), Product.id)).all()
    product_ids = [product.id for product in products]
    tags_by_product: dict[int, list[dict[str, str]]] = {product_id: [] for product_id in product_ids}
    if product_ids:
        tags = db.scalars(select(ProductTag).where(
            ProductTag.cafe_id == cafe.id,
            ProductTag.product_id.in_(product_ids),
        )).all()
        for tag in tags:
            tags_by_product[tag.product_id].append({"key": tag.tag_key, "value": tag.tag_value})
    category_names = {category.id: category.name for category in categories}
    return MenuResponse(
        cafe_name=cafe.name,
        cafe_slug=cafe.slug,
        currency_unit=cafe.currency_unit,
        table_number=table,
        categories=[
            MenuCategoryOut(id=c.id, slug=c.slug, name=c.name, sort_order=c.sort_order)
            for c in categories
        ],
        products=[
            MenuProductOut(
                id=p.id,
                slug=p.slug,
                name=p.name,
                description=p.description,
                price_amount=p.price_amount,
                category_id=p.category_id,
                category_name=category_names.get(p.category_id, "سایر"),
                is_available=p.is_available,
                is_featured=p.is_featured,
                tags=tags_by_product.get(p.id, []),
            )
            for p in products
        ],
    )


@router.post("/orders", response_model=OrderCreatedOut, status_code=201)
def create_order(
    payload: CreateOrderRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> OrderCreatedOut:
    client_ip = request.client.host if request.client else "unknown"
    if not allow_attempt("create-order", client_ip, limit=20, window_seconds=60):
        raise HTTPException(status_code=429, detail="درخواست‌های زیادی ثبت شده؛ کمی بعد تلاش کنید")

    cafe = db.scalar(select(Cafe).where(
        Cafe.slug == settings.default_cafe_slug
    ).with_for_update())
    if cafe is None:
        raise HTTPException(status_code=503, detail="کافه هنوز پیکربندی نشده است")
    table = db.scalar(select(CafeTable).where(
        CafeTable.cafe_id == cafe.id,
        CafeTable.table_number == payload.table_number,
        CafeTable.is_active.is_(True),
    ))
    if table is None:
        raise HTTPException(status_code=404, detail="میز معتبر نیست")

    requested: dict[int, int] = {}
    for item in payload.items:
        requested[item.product_id] = requested.get(item.product_id, 0) + item.quantity
    if any(quantity > 20 for quantity in requested.values()):
        raise HTTPException(status_code=422, detail="تعداد هر محصول حداکثر ۲۰ عدد است")

    products = db.scalars(select(Product).where(
        Product.cafe_id == cafe.id,
        Product.id.in_(requested.keys()),
        Product.is_available.is_(True),
    )).all()
    product_map = {product.id: product for product in products}
    if len(product_map) != len(requested):
        raise HTTPException(status_code=422, detail="یک یا چند محصول نامعتبر یا ناموجود است")

    order = Order(
        cafe_id=cafe.id,
        table_id=table.id,
        customer_session_id=_customer_session(request, response),
        status="pending_confirmation",
        total_amount=sum(product_map[pid].price_amount * qty for pid, qty in requested.items()),
        notes=payload.notes,
    )
    db.add(order)
    db.flush()
    for product_id, quantity in requested.items():
        product = product_map[product_id]
        db.add(OrderItem(
            cafe_id=cafe.id,
            order_id=order.id,
            product_id=product.id,
            product_name_snapshot=product.name,
            quantity=quantity,
            unit_price_amount=product.price_amount,
        ))

    code, code_hash = generate_unique_order_code(db, cafe)
    code_expires_at = utc_now() + timedelta(minutes=settings.order_code_ttl_minutes)
    db.add(OrderCode(
        cafe_id=cafe.id,
        order_id=order.id,
        code_hash=code_hash,
        status="active",
        expires_at=code_expires_at,
        attempts=0,
    ))
    db.add(AuditLog(
        cafe_id=cafe.id,
        actor_user_id=None,
        action="order.created",
        entity_type="order",
        entity_id=str(order.id),
        details={"status": order.status, "table_number": table.table_number, "items_count": len(requested)},
    ))
    db.commit()
    db.refresh(order)
    out = _customer_order(db, order, code=code)
    assert isinstance(out, OrderCreatedOut)
    return out


@router.get("/orders/{order_id}", response_model=OrderStatusOut)
def customer_order_status(
    order_id: int,
    request: Request,
    db: Session = Depends(get_db),
) -> OrderStatusOut:
    token = request.cookies.get(CUSTOMER_COOKIE)
    if not token:
        raise HTTPException(status_code=401, detail="نشست مشتری پیدا نشد")
    order = db.scalar(select(Order).where(
        Order.id == order_id,
        Order.customer_session_id == hash_token_id(token),
    ))
    if order is None:
        raise HTTPException(status_code=404, detail="سفارش پیدا نشد")
    code_row = db.scalar(select(OrderCode).where(OrderCode.order_id == order.id))
    if (
        order.status == "pending_confirmation"
        and code_row is not None
        and code_row.status == "active"
        and as_utc(code_row.expires_at) <= utc_now()
    ):
        code_row.status = "expired"
        order.status = transition_order(order.status, "expired")
        db.add(AuditLog(
            cafe_id=order.cafe_id,
            actor_user_id=None,
            action="order.expired",
            entity_type="order",
            entity_id=str(order.id),
            details={"source": "customer_status_check"},
        ))
        db.commit()
        db.refresh(order)
    out = _customer_order(db, order)
    assert isinstance(out, OrderStatusOut)
    return out


@router.get("/staff/orders", response_model=list[StaffOrderOut])
def staff_orders(
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
    staff: User = Depends(require_staff),
) -> list[StaffOrderOut]:
    _expire_stale_orders(db, staff.cafe_id)
    valid_statuses = {"draft", "pending_confirmation", "confirmed", "preparing", "served", "cancelled", "expired"}
    if status is not None and status not in valid_statuses:
        raise HTTPException(status_code=422, detail="فیلتر وضعیت معتبر نیست")
    stmt = select(Order).where(Order.cafe_id == staff.cafe_id)
    if status:
        stmt = stmt.where(Order.status == status)
    orders = db.scalars(stmt.order_by(Order.created_at.desc()).limit(100)).all()
    return [_staff_order(db, order) for order in orders]


@router.post("/staff/orders/{order_id}/confirm", response_model=StaffOrderOut)
def staff_confirm_order(
    order_id: int,
    payload: ConfirmCodeRequest,
    request: Request,
    db: Session = Depends(get_db),
    staff: User = Depends(require_staff),
) -> StaffOrderOut:
    client_ip = request.client.host if request.client else "unknown"
    if not allow_attempt("order-confirm", f"{staff.cafe_id}:{client_ip}", limit=30, window_seconds=60):
        raise HTTPException(status_code=429, detail="تعداد تلاش‌ها زیاد است؛ کمی بعد دوباره امتحان کنید")
    order = db.scalar(select(Order).where(
        Order.id == order_id,
        Order.cafe_id == staff.cafe_id,
    ).with_for_update())
    if order is None:
        raise HTTPException(status_code=404, detail="سفارش پیدا نشد")
    if order.status != "pending_confirmation":
        raise HTTPException(status_code=409, detail="این سفارش در انتظار تأیید نیست")
    code_record = db.scalar(select(OrderCode).where(
        OrderCode.order_id == order.id,
        OrderCode.cafe_id == staff.cafe_id,
    ).with_for_update())
    if code_record is None or code_record.status != "active":
        raise HTTPException(status_code=410, detail="کد معتبر نیست یا قبلاً استفاده شده است")
    if as_utc(code_record.expires_at) <= utc_now():
        code_record.status = "expired"
        order.status = transition_order(order.status, "expired")
        db.commit()
        raise HTTPException(status_code=410, detail="مهلت کد تأیید تمام شده است")

    if not secrets.compare_digest(code_record.code_hash, hash_order_code(payload.code)):
        code_record.attempts += 1
        if code_record.attempts >= settings.order_code_max_attempts:
            code_record.status = "locked"
        db.commit()
        if code_record.status == "locked":
            raise HTTPException(status_code=429, detail="تعداد تلاش‌ها تمام شد؛ سفارش نیاز به بررسی دارد")
        raise HTTPException(status_code=400, detail="کد تأیید نادرست است")

    code_record.status = "consumed"
    code_record.consumed_at = utc_now()
    order.status = transition_order(order.status, "confirmed")
    order.confirmed_at = utc_now()
    db.add(AuditLog(
        cafe_id=staff.cafe_id,
        actor_user_id=staff.id,
        action="order.confirmed",
        entity_type="order",
        entity_id=str(order.id),
        details={"from": "pending_confirmation", "to": "confirmed"},
    ))
    db.commit()
    db.refresh(order)
    return _staff_order(db, order)


@router.patch("/staff/orders/{order_id}/status", response_model=StaffOrderOut)
def staff_update_order_status(
    order_id: int,
    payload: UpdateOrderStatusRequest,
    db: Session = Depends(get_db),
    staff: User = Depends(require_staff),
) -> StaffOrderOut:
    order = db.scalar(select(Order).where(
        Order.id == order_id,
        Order.cafe_id == staff.cafe_id,
    ).with_for_update())
    if order is None:
        raise HTTPException(status_code=404, detail="سفارش پیدا نشد")
    if payload.status == "cancelled" and not payload.reason:
        raise HTTPException(status_code=422, detail="برای لغو سفارش، دلیل لازم است")
    previous = order.status
    try:
        order.status = transition_order(order.status, payload.status)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail="تغییر وضعیت مجاز نیست") from exc
    if payload.status == "served":
        order.served_at = utc_now()
    if payload.status == "cancelled":
        order.cancelled_at = utc_now()
        order.cancellation_reason = payload.reason
    db.add(AuditLog(
        cafe_id=staff.cafe_id,
        actor_user_id=staff.id,
        action=f"order.{payload.status}",
        entity_type="order",
        entity_id=str(order.id),
        details={"from": previous, "to": payload.status, "reason": payload.reason},
    ))
    db.commit()
    db.refresh(order)
    return _staff_order(db, order)


@router.get("/staff/events")
def staff_order_events(
    request: Request,
    staff: User = Depends(require_staff),
) -> StreamingResponse:
    cafe_id = staff.cafe_id
    stream_deadline = monotonic() + settings.jwt_access_minutes * 60

    async def event_stream():
        previous_payload = ""
        while not await request.is_disconnected() and monotonic() < stream_deadline:
            with SessionLocal() as db:
                _expire_stale_orders(db, cafe_id)
                stmt = select(Order).where(
                    Order.cafe_id == cafe_id,
                    Order.status.in_(["pending_confirmation", "confirmed", "preparing"]),
                ).order_by(Order.created_at.desc()).limit(100)
                orders = db.scalars(stmt).all()
                payload = json.dumps(
                    [_staff_order(db, order).model_dump(mode="json") for order in orders],
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            if payload != previous_payload:
                yield f"event: orders\ndata: {payload}\n\n"
                previous_payload = payload
            else:
                yield ": keep-alive\n\n"
            await asyncio.sleep(3)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
