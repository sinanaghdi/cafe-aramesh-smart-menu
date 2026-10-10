"""Seed the local development database only; never run demo seeds in production."""
from backend.app.main import APP_ENV, init_db

if APP_ENV == "production":
    raise SystemExit("Refusing to seed sample café data in production.")

init_db()
print("داده‌های توسعه کافه آرامش آماده‌اند؛ سفارش تاریخی ساختگی ایجاد نشده است.")
