# منوی هوشمند کافه آرامش | Café Aramesh Smart Menu

منوی دیجیتال فارسی، راست‌چین و موبایل‌محور برای کمک به انتخاب بهتر مشتری؛ با تأیید حضوری گارسون و پیشنهادهایی که فقط با تأیید صاحب کافه منتشر می‌شوند.

## وضعیت فعلی

این مخزن فعلاً دو مسیر رابط دارد که عمداً از هم جدا نگه داشته شده‌اند:

- **پروتوتایپ استاتیک موجود در ریشه** — فایل‌های `index.html`، `app.js` و `styles.css` برای نمایش و بررسی سریع UI و انتشار از طریق GitHub Pages. این نسخه نمایشی است و به بک‌اند وصل نیست؛ سبد، پنل‌ها یا اعداد نمایشی سفارش واقعی یا فروش واقعی نیستند.
- **زیرساخت Full-stack جدید** — پوشه‌های `frontend/` و `backend/`، پایگاه داده، مهاجرت و Docker Compose. این بخش اکنون فاز صفر را تکمیل کرده است؛ منوی زنده، احراز هویت و جریان سفارش واقعی هنوز پیاده‌سازی نشده‌اند.

پیشرفت بر اساس فازبندی در [PLAN.md](PLAN.md) ثبت شده است. هیچ قابلیتی خارج از این وضعیت را عملیاتی فرض نکنید.

## اجرای زیرساخت Full-stack

پیش‌نیاز: Docker و Docker Compose.

```bash
docker compose up --build
```

پس از بالا آمدن سرویس‌ها:

- رابط React داخل Docker: http://localhost:8080
- سلامت API: http://localhost:8000/health
- آمادگی API و اتصال PostgreSQL: http://localhost:8000/ready
- مستندات API: http://localhost:8000/docs

Compose سرویس‌های PostgreSQL و Redis را بالا می‌آورد، مهاجرت Alembic را اجرا می‌کند و ۲۵ محصول نمونه فارسی با تگ‌های ساختاریافته، ۵ دسته و ۸ میز آزمایشی را seed می‌کند. اولین build برای دریافت وابستگی‌ها به اینترنت نیاز دارد. مقادیر فایل `.env.example` فقط برای توسعه محلی هستند.

## بررسی‌ها و تست‌ها

در پوشه `backend/`:

```bash
pip install -e ".[dev]"
ruff check .
mypy app
pytest
```

در پوشه `frontend/`:

```bash
npm install
npm run lint
npm run typecheck
npm run build
npm run format:check
```

CI همین بررسی‌ها را اجرا می‌کند و علاوه بر build، اجرای واقعی Compose، اتصال دیتابیس و وجود داده‌های seed را هم smoke-test می‌کند.

## مرزهای محصول

- **Customer:** مشاهده منو بدون ثبت‌نام اجباری؛ عضویت باشگاه در آینده اختیاری است.
- **Staff:** فقط عملیات سفارش و تأیید حضوری؛ نباید به درآمد یا تحلیل فروش دسترسی داشته باشد.
- **Merchant:** مدیریت منو و قوانین و مشاهده تحلیل مبتنی بر داده واقعی؛ تأیید انسانی برای پیشنهادهای AI الزامی است.
- هیچ درگاه پرداخت، POS، انبار، حسابداری یا CRM کامل در MVP ساخته نمی‌شود.
- درخواست ثبت‌شده معادل سفارش تأییدشده یا فروش نهایی نیست.
- هوش مصنوعی اختیاری است؛ مسیر قاعده‌محور باید بدون سرویس خارجی کار کند.

## مستندات

- [PLAN.md](PLAN.md) — برنامه و معیارهای پذیرش فازها
- [مشخصات محصول](docs/PRODUCT-SPEC.md)
- [معماری](docs/ARCHITECTURE.md)
- [قرارداد API و وضعیت پیاده‌سازی](docs/API.md)
- [معماری AI](docs/AI.md)
- [تصمیم‌های معماری](docs/DECISIONS.md)
- [نقشه راه](docs/ROADMAP.md)
- [راهنمای مشارکت](CONTRIBUTING.md)

## هشدار استقرار

پیش از انتشار عملیاتی، کلیدها و رمزهای مدیریت‌شده، HTTPS، CORS محدود، احراز هویت و مجوزدهی سمت سرور، چرخش توکن‌های QR آزمایشی، پشتیبان‌گیری و سیاست نگهداری داده باید بررسی و پیکربندی شوند. هیچ رمز واقعی یا کلید API نباید در مخزن قرار بگیرد.

---

## English

Café Aramesh Smart Menu is a Persian-first, RTL, mobile-first menu designed around deliberate in-person staff confirmation and merchant-approved recommendations.

The repository preserves the existing static GitHub Pages prototype at the root (`index.html`, `app.js`, `styles.css`) and adds a separate React/Vite + FastAPI stack under `frontend/` and `backend/`. The root prototype is presentation-only. The full-stack app is currently at Phase 0: migrations, seed data, health checks, and infrastructure are implemented, but live ordering, authentication, NLP, smart combos, Wi-Fi vouchers, and business analytics are not implemented yet.

Run the local stack:

```bash
docker compose up --build
```

Open the React app at http://localhost:8080, API health at http://localhost:8000/health, readiness at http://localhost:8000/ready, and API docs at http://localhost:8000/docs. Seed values are development fixtures, not real business data.

This is not a POS, payment system, accounting package, inventory system, or full CRM. See PLAN.md and docs/ROADMAP.md for the phase gates.
