# منوی هوشمند کافه آرامش | Café Aramesh Smart Menu

منوی دیجیتال فارسی، راست‌چین و موبایل‌محور برای کمک به انتخاب بهتر مشتری؛ با تأیید حضوری گارسون و پیشنهادهایی که فقط با تأیید صاحب کافه منتشر می‌شوند.

## وضعیت فعلی

مخزن دو رابط جدا دارد:

- **پروتوتایپ استاتیک ریشه:** فایل‌های `index.html`، `app.js` و `styles.css` برای مرور طرح و انتشار از طریق GitHub Pages. این نسخه نمایشی است و سفارش واقعی ثبت نمی‌کند.
- **اپ Full-stack در `frontend/` و `backend/`:** فاز ۱ شامل منوی متصل به PostgreSQL، سبد با مبلغ محاسبه‌شده در سرور، کد کوتاه تأیید، ورود کارکنان، صف سفارش‌ها و گردش وضعیت را فراهم می‌کند. استادی‌مود، باشگاه مشتریان، NLP، کمبو و آنالیتیکس Merchant هنوز در فازهای بعد هستند.

## اجرای محلی

پیش‌نیاز: Docker و Docker Compose.

```bash
docker compose up --build
```

- رابط React: http://localhost:8080
- سلامت API: http://localhost:8000/health
- آمادگی API و دیتابیس: http://localhost:8000/ready
- مستندات API: http://localhost:8000/docs

در شروع، Compose مهاجرت‌های Alembic را اجرا می‌کند و ۲۵ محصول نمونه فارسی، تگ‌ها، دسته‌ها، میزهای آزمایشی و کاربران آزمایشی را seed می‌کند. اعداد و داده‌های نمونه واقعی نیستند.

### ورود محلی پنل گارسون

- ایمیل: `staff@aramesh.local`
- گذرواژه: `StaffDemo!2026`

حساب صاحب کافه برای فازهای بعدی:

- ایمیل: `merchant@aramesh.local`
- گذرواژه: `MerchantDemo!2026`

این اطلاعات فقط برای توسعهٔ محلی‌اند. از آن‌ها در محیط عمومی یا عملیاتی استفاده نکنید؛ متغیرهای مربوطه را در `.env` تغییر دهید. seed در `ENVIRONMENT=production` کاربران نمونه ایجاد نمی‌کند و استقرار عملیاتی به کلیدهای قوی، HTTPS و `COOKIE_SECURE=true` نیاز دارد.

## رفتار سفارش

1. مشتری از QR میز وارد منو می‌شود: `?table=5`.
2. محصولات را انتخاب و درخواست را ثبت می‌کند؛ قیمت هر آیتم از دیتابیس خوانده می‌شود.
3. کد ۳ یا ۴ رقمی یک بار نشان داده می‌شود. سرور فقط HMAC کد را ذخیره می‌کند.
4. گارسون کد مشتری را وارد می‌کند. کد منقضی، مصرف‌شده یا قفل‌شده پذیرفته نمی‌شود.
5. پس از تأیید، وضعیت سفارش طبق state machine جلو می‌رود: تأیید شده، آماده‌سازی، تحویل.
6. API پنل گارسون مبلغ، درآمد یا تحلیل فروش را برنمی‌گرداند.

هیچ درگاه پرداختی وجود ندارد. ثبت درخواست معادل فروش نهایی یا حسابداری نیست.

## تست‌ها

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

CI علاوه بر lint و build، بالا آمدن واقعی Compose، اجرای migration، آمادگی API و وجود داده‌های seed را بررسی می‌کند.

## محدوده محصول

- **Customer:** منوی QR بدون ثبت‌نام اجباری.
- **Staff:** عملیات سفارش و تأیید حضوری؛ بدون آمار فروش یا درآمد.
- **Merchant:** مدیریت منو و قوانین و گزارش داده‌محور در فاز ۴.
- پرداخت آنلاین، POS، انبار، حسابداری و CRM کامل خارج از محدوده‌اند.
- قابلیت‌های AI اختیاری‌اند و تغییر تجاری را بدون تأیید صریح Merchant اعمال نمی‌کنند.

## مستندات

- [PLAN.md](PLAN.md)
- [مشخصات محصول](docs/PRODUCT-SPEC.md)
- [معماری](docs/ARCHITECTURE.md)
- [قرارداد API و وضعیت پیاده‌سازی](docs/API.md)
- [معماری AI](docs/AI.md)
- [تصمیم‌های معماری](docs/DECISIONS.md)
- [نقشه راه](docs/ROADMAP.md)
- [راهنمای مشارکت](CONTRIBUTING.md)

---

## English

Café Aramesh Smart Menu is a Persian-first, RTL, mobile-first cafe menu built around deliberate in-person staff confirmation.

The existing root HTML/CSS/JavaScript prototype remains presentation-only for GitHub Pages. The full-stack app lives under `frontend/` and `backend/`. Phase 1 implements the database-backed menu, server-priced request cart, short-lived HMAC-backed confirmation code, staff login, operations-only order queue, SSE snapshots, and tested status transitions. Study mode and the optional loyalty club are implemented on the Phase 2 branch. Persian NLP, smart combos, and merchant analytics remain later phases.

Start locally with `docker compose up --build`. Visit the React app at http://localhost:8080, API health at http://localhost:8000/health, readiness at http://localhost:8000/ready, and API docs at http://localhost:8000/docs.

Development-only login:
- Staff: `staff@aramesh.local` / `StaffDemo!2026`
- Merchant: `merchant@aramesh.local` / `MerchantDemo!2026`

Do not use those credentials outside local development. The app is not a payment system, POS, accounting package, inventory system, or full CRM. Wi-Fi is currently a mock voucher and does not grant real router access; the console SMS adapter is development-only.
