# منوی هوشمند کافه آرامش | Café Aramesh Smart Menu

منوی دیجیتال فارسی، راست‌چین و موبایل‌محور برای کمک به مشتری در انتخاب بهتر؛ با تأیید حضوری گارسون و پیشنهادهای کنترل‌شده توسط صاحب کافه.

> وضعیت فعلی: زیرساخت فاز صفر. هنوز سفارش واقعی، احراز هویت، جست‌وجوی NLP، کمبو، ووچر یا تحلیل فروش پیاده‌سازی نشده است. این صفحه یا داده‌های seed را داده واقعی کسب‌وکار تلقی نکنید.

## اجرای محلی

پیش‌نیاز: Docker و Docker Compose.

1. در ریشه مخزن اجرا کنید: `docker compose up --build`
2. رابط وب: http://localhost:8080
3. سلامت API: http://localhost:8000/health
4. آمادگی API و اتصال پایگاه داده: http://localhost:8000/ready
5. مستندات API در محیط اجرا: http://localhost:8000/docs

Compose پایگاه داده PostgreSQL و Redis را اجرا می‌کند، مهاجرت Alembic را اعمال می‌کند و داده نمونه فارسی را به‌صورت تکرارپذیر seed می‌کند. اولین build برای دریافت وابستگی‌ها به اینترنت نیاز دارد.

### اجرای تست‌ها

در پوشه backend، وابستگی‌های توسعه را نصب و تست‌ها را اجرا کنید:

    pip install -e ".[dev]"
    ruff check .
    mypy app
    pytest

در پوشه frontend:

    npm install
    npm run lint
    npm run typecheck
    npm run build
    npm run format:check

## محدوده محصول

- مشتری: منوی QR بدون ثبت‌نام اجباری؛ ثبت‌نام باشگاه اختیاری.
- گارسون: مدیریت عملیاتی سفارش و تأیید حضوری؛ بدون دسترسی به تحلیل فروش.
- صاحب کافه: مدیریت منو، کمبو و قوانین؛ تحلیل‌های داده‌محور و تأیید پیشنهادهای AI.
- سفارش آنلاین پرداخت‌شده، POS، حسابداری، انبار و CRM کامل خارج از محدوده‌اند.
- هوش مصنوعی هیچ تغییر تجاری را خودکار منتشر نمی‌کند؛ مسیر rule-based بدون سرویس خارجی باید کار کند.

## مستندات

- [PLAN.md](PLAN.md) — برنامه و معیارهای تکمیل فازها
- [مشخصات محصول](docs/PRODUCT-SPEC.md)
- [معماری](docs/ARCHITECTURE.md)
- [قرارداد API و وضعیت پیاده‌سازی](docs/API.md)
- [معماری AI](docs/AI.md)
- [تصمیم‌های معماری](docs/DECISIONS.md)
- [نقشه راه](docs/ROADMAP.md)
- [راهنمای مشارکت](CONTRIBUTING.md)

## هشدار پیکربندی

مقادیر موجود در Compose و فایل .env.example فقط برای توسعه محلی‌اند. پیش از استقرار، رمزهای قوی و مدیریت‌شده، HTTPS، محدودیت CORS مناسب، پشتیبان‌گیری امن و بررسی مجوزها ضروری‌اند.

---

## English

Café Aramesh Smart Menu is a Persian-first, RTL, mobile-first digital cafe menu. It is designed around customer choice, deliberate in-person staff confirmation, and merchant-controlled recommendations.

Current status: Phase 0 foundation only. Live order placement, authentication, NLP, smart combos, Wi-Fi vouchers, and sales analytics are not implemented yet. Seed values are demonstration data, not real business records.

Run the stack with Docker Compose:

    docker compose up --build

Open the web app at http://localhost:8080, API health at http://localhost:8000/health, and API documentation at http://localhost:8000/docs.

The application is not a POS, payment system, accounting package, inventory system, or full CRM. See PLAN.md and docs/ROADMAP.md for phase gates and scope.
