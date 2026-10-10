from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class ProductTagOut(BaseModel):
    key: str
    value: str


class MenuCategoryOut(BaseModel):
    id: int
    slug: str
    name: str
    sort_order: int


class MenuProductOut(BaseModel):
    id: int
    slug: str
    name: str
    description: str
    price_amount: int
    category_id: int
    category_name: str
    is_available: bool
    is_featured: bool
    tags: list[ProductTagOut]


class MenuResponse(BaseModel):
    cafe_name: str
    cafe_slug: str
    currency_unit: str
    table_number: int | None
    categories: list[MenuCategoryOut]
    products: list[MenuProductOut]


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=256)
    cafe_slug: str = Field(default="cafe-aramesh", min_length=1, max_length=100)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=20, max_length=4096)


class AuthUserOut(BaseModel):
    id: int
    cafe_id: int
    full_name: str
    role: str
    email: str | None


class TokenPairOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: AuthUserOut


class CartItemIn(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(ge=1, le=20)


class CreateOrderRequest(BaseModel):
    table_number: int = Field(gt=0, le=500)
    items: list[CartItemIn] = Field(min_length=1, max_length=50)
    notes: str | None = Field(default=None, max_length=300)

    @field_validator("notes")
    @classmethod
    def normalize_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


class OrderItemCustomerOut(BaseModel):
    product_id: int
    product_name: str
    quantity: int
    unit_price_amount: int
    line_total_amount: int


class OrderCreatedOut(BaseModel):
    id: int
    status: str
    table_number: int
    currency_unit: str
    total_amount: int
    code: str
    code_expires_at: datetime
    items: list[OrderItemCustomerOut]


class OrderStatusOut(BaseModel):
    id: int
    status: str
    table_number: int
    currency_unit: str
    total_amount: int
    created_at: datetime
    items: list[OrderItemCustomerOut]


class StaffOrderItemOut(BaseModel):
    product_name: str
    quantity: int


class StaffOrderOut(BaseModel):
    id: int
    status: str
    table_number: int
    created_at: datetime
    notes: str | None
    items: list[StaffOrderItemOut]


class ConfirmCodeRequest(BaseModel):
    code: str = Field(min_length=3, max_length=4)

    @field_validator("code")
    @classmethod
    def only_ascii_digits(cls, value: str) -> str:
        if len(value) not in (3, 4) or not value.isascii() or not value.isdigit():
            raise ValueError("کد باید ۳ یا ۴ رقم انگلیسی باشد")
        return value


class UpdateOrderStatusRequest(BaseModel):
    status: str
    reason: str | None = Field(default=None, max_length=300)

    @field_validator("status")
    @classmethod
    def allowed_status(cls, value: str) -> str:
        if value not in {"preparing", "served", "cancelled"}:
            raise ValueError("وضعیت درخواستی پشتیبانی نمی‌شود")
        return value

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None
