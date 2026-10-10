# Café Aramesh — منوی هوشمند کافه آرامش

منوی دیجیتال فارسی، راست‌چین و موبایل‌محور برای **کافه آرامش**؛ با منوی پویا، پیشنهادهای ترکیبی، جست‌وجوی ترجیح‌محور فارسی و گردش درخواست سفارش با تأیید حضوری کارکنان.

> **وضعیت پروژه:** MVP کاربردی برای توسعه و ارزیابی محلی. قابلیت‌های اصلی مشتری، کارکنان و مدیر کافه پیاده‌سازی شده‌اند؛ با این حال، پیش از استفادهٔ تجاری باید الزامات امنیتی، استقرار، داده‌های واقعی کافه و محدودیت‌های درج‌شده در این سند بررسی شوند.

[![Backend quality checks](https://github.com/sinanaghdi/cafe-aramesh-smart-menu/actions/workflows/backend-tests.yml/badge.svg?branch=main)](https://github.com/sinanaghdi/cafe-aramesh-smart-menu/actions/workflows/backend-tests.yml)
[![GitHub Pages preview](https://github.com/sinanaghdi/cafe-aramesh-smart-menu/actions/workflows/pages.yml/badge.svg?branch=main)](https://github.com/sinanaghdi/cafe-aramesh-smart-menu/actions/workflows/pages.yml)

## قابلیت‌ها

### تجربهٔ مشتری
- منوی فارسی با جهت راست‌به‌چپ، دسته‌بندی، جست‌وجو و نمایش قیمت به تومان.
- پیشنهاد ترکیب‌های تأییدشدهٔ کافه؛ قیمت ترکیب از محصولات و قواعد تخفیف محاسبه می‌شود.
- جست‌وجوی ترجیح‌محور فارسی برای ویژگی‌هایی مانند سرد/گرم، ترش، کم‌شیرین، قهوهٔ قوی و بدون شیر؛ نتیجه فقط از محصولات موجود و ویژگی‌های ثبت‌شده انتخاب می‌شود.
- سبد درخواست سفارش و نمایش کد تأیید مشتری. **پرداخت اینترنتی انجام نمی‌شود** و درخواست باید حضوری توسط کارکنان تأیید شود.
- عضویت اختیاری مشتری، مشاهدهٔ امتیاز و تاریخچه، و درخواست دریافت پاداش.
- حالت مطالعه و کار وابسته به سفارش واجد شرایط و تأییدشده.

### پنل کارکنان
- صف درخواست‌های منتظر تأیید، میز، اقلام، مبلغ و مدت انتظار.
- بررسی کدی که مشتری حضوری اعلام می‌کند؛ کد صحیح پیش از تأیید در صف نمایش داده نمی‌شود.
- گردش وضعیت کنترل‌شده از تأیید تا آماده‌سازی و تحویل.
- بدون دسترسی به گزارش‌های تجمیعی و بخش مدیریتی صاحب کافه.

### پنل صاحب کافه
- ایجاد و ویرایش دسته‌ها و محصولات، قیمت، موجودی، نمایش و ویژگی‌های محصول.
- ایجاد، ویرایش و غیرفعال‌سازی ترکیب‌ها و تخفیف‌های محدودشده.
- تنظیم قواعد حالت مطالعه و کار و باشگاه مشتریان.
- مدیریت پاداش‌ها.
- گزارش سفارش‌های تحویل‌شده و پیشنهادهای قاعده‌محور با اعلام کمبود داده.

## فناوری‌ها

- **Frontend:** HTML، CSS و JavaScript بدون نیاز به build framework.
- **Backend:** Python، FastAPI و Pydantic.
- **Database:** SQLAlchemy 2.x؛ SQLite برای توسعهٔ محلی و PostgreSQL برای استقرار پایدار.
- **Migrations:** Alembic.
- **Authentication:** هش گذرواژه، JWT و کنترل نقش در سمت API.
- **Testing/CI:** pytest، بررسی نحوی JavaScript، کامپایل Python و بررسی مهاجرت پایگاه داده با GitHub Actions.
- **Deployment:** Docker و فایل پیکربندی نمونه برای Render.

## ساختار مخزن

```text
.
├── index.html                 # منوی مشتری
├── styles.css                 # طراحی فارسی و RTL
├── app.js                     # رفتار رابط مشتری
├── config.js                  # نشانی عمومی API برای مرورگر
├── staff.html                 # پنل کارکنان
├── staff.js
├── merchant.html              # پنل صاحب کافه
├── merchant.js
├── role.css
├── role-client.js
├── backend/
│   └── app/
│       ├── main.py            # API، مدل‌ها و منطق MVP
│       └── seed.py            # دادهٔ توسعه
├── migrations/                # مهاجرت‌های Alembic
├── tests/                     # آزمون‌های API و قرارداد رابط
├── docs/
│   ├── DEPLOYMENT.md
│   ├── IMPLEMENTATION-STATUS.md
│   ├── PRODUCT-SPEC.md
│   └── ROADMAP.md
├── .github/workflows/         # آزمون و پیش‌نمایش GitHub Pages
├── Dockerfile
├── render.yaml
├── requirements.txt
└── alembic.ini
```

## اجرای محلی در Windows (PowerShell)

پیش‌نیاز: Python 3.11 یا جدیدتر و Node.js برای بررسی نحوی JavaScript.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
alembic upgrade head
python -m backend.app.seed
uvicorn backend.app.main:app --reload
```

سپس این نشانی‌ها را باز کن:

- برنامه: http://127.0.0.1:8000
- مستندات تعاملی API: http://127.0.0.1:8000/docs
- بررسی سلامت سرویس: http://127.0.0.1:8000/api/health

اگر PowerShell اجازهٔ فعال‌کردن محیط مجازی نداد، در همان ترمینال می‌توانی از `.venv\Scripts\python.exe` و `.venv\Scripts\uvicorn.exe` استفاده کنی.

## اجرای محلی در macOS/Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
python -m backend.app.seed
uvicorn backend.app.main:app --reload
```

فرمان seed فقط داده‌های منو، تنظیمات توسعه و حساب‌های نمایشی را درج می‌کند. **سفارش تاریخی ساختگی برای زیبا نشان‌دادن گزارش‌ها ساخته نمی‌شود.** اجرای seed در محیط `production` رد می‌شود.

## حساب‌های نمایشی توسعه

این حساب‌ها فقط برای اجرای محلی هستند؛ رمزهای آن‌ها را در محیط عملیاتی استفاده نکن.

| نقش | ایمیل | گذرواژه |
|---|---|---|
| صاحب کافه | `owner@aramesh.local` | `Owner@12345` |
| کارکنان | `waiter@aramesh.local` | `Waiter@12345` |
| عضو مشتریان | `member@aramesh.local` | `Member@12345` |

مرور منو به حساب نیاز ندارد. پنل کارکنان و پنل مدیریت کافه از مسیرهای مستقل خود باز می‌شوند و مجوز هر نقش در بک‌اند نیز کنترل می‌شود.

## تنظیمات محیطی

فایل `.env.example` نمونه است؛ مقادیر محرمانه را در `.env` محلی یا تنظیمات محیطی سرویس میزبانی قرار بده و هرگز آن‌ها را Commit نکن.

| متغیر | کاربرد |
|---|---|
| `APP_ENV` | `development` برای توسعه؛ `production` برای استقرار |
| `DATABASE_URL` | آدرس SQLite محلی یا PostgreSQL میزبانی‌شده |
| `JWT_SECRET` | کلید محرمانه و تصادفی JWT؛ در تولید حداقل ۳۲ نویسه |
| `CAFE_TIMEZONE` | منطقهٔ زمانی؛ پیش‌فرض `Asia/Tehran` |
| `CORS_ORIGINS` | فهرست دقیق Originهای مجاز که با کاما جدا شده‌اند |
| `AUTO_CREATE_SCHEMA` | برای تولید خاموش بماند؛ در استقرار از مهاجرت استفاده کن |

برای ساخت کلید تصادفی محلی:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

## پایگاه داده و مهاجرت

برای ایجاد یا ارتقای schema:

```bash
alembic upgrade head
```

پس از تغییر مدل‌ها، revision تازهٔ Alembic ایجاد و بررسی کن. پیش از مهاجرت روی دادهٔ واقعی، پشتیبان بگیر. فایل SQLite برای توسعه است؛ در استقرار، پایگاه دادهٔ پایدار و مدیریت‌شده را ترجیح بده.

## آزمون و کنترل کیفیت

برای جلوگیری از حذف یا تغییر تصادفی اطلاعات یک پایگاه دادهٔ واقعی، آزمون‌ها را با پایگاه دادهٔ جداگانه اجرا کن.

PowerShell:

```powershell
$env:DATABASE_URL = "sqlite:///./backend/test_cafe_aramesh.db"
python -m compileall -q backend migrations tests
node --check app.js
node --check staff.js
node --check merchant.js
pytest -q
alembic upgrade head
Remove-Item Env:DATABASE_URL
```

macOS/Linux:

```bash
DATABASE_URL=sqlite:///./backend/test_cafe_aramesh.db python -m compileall -q backend migrations tests
node --check app.js
node --check staff.js
node --check merchant.js
DATABASE_URL=sqlite:///./backend/test_cafe_aramesh.db pytest -q
DATABASE_URL=sqlite:///./backend/test_cafe_aramesh.db alembic upgrade head
```

توجه: fixtureهای آزمون schema پایگاه داده را بازسازی می‌کنند؛ `DATABASE_URL` را به پایگاه دادهٔ عملیاتی یا فایل حاوی اطلاعات واقعی اشاره نده. GitHub Actions نیز تست‌ها، بررسی نحوی فایل‌های JavaScript و مهاجرت تازه را اجرا می‌کند.

## استقرار و GitHub Pages

### برنامه و API در یک سرویس

با Docker:

```bash
docker build -t cafe-aramesh .
docker run --rm -p 8000:8000 --env-file .env cafe-aramesh
```

یا با سرویس میزبانی سازگار با ASGI، دستور شروع زیر را استفاده کن:

```bash
alembic upgrade head && uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT
```

متغیرهای محیطی، پورت، دیتابیس پایدار و health check را در پلتفرم میزبانی تنظیم کن. فایل `render.yaml` فقط پیکربندی استقرار پیشنهادی است؛ هزینه و در دسترس‌بودن پلن دیتابیس و سرویس را پیش از ایجاد منابع بررسی کن.

### Frontend روی GitHub Pages و API جداگانه

GitHub Pages فقط فایل‌های ایستا را میزبانی می‌کند؛ FastAPI یا دیتابیس را اجرا نمی‌کند. برای کارکرد ثبت سفارش و پنل‌های احراز هویت‌شده:

1. بک‌اند و دیتابیس را روی یک سرویس جداگانه مستقر کن.
2. `APP_ENV=production`، کلید امن `JWT_SECRET`، `DATABASE_URL` و Origin دقیق فرانت‌اند را تنظیم کن.
3. مقدار `apiBaseUrl` در `config.js` را به مبدأ HTTPS بک‌اند تغییر بده؛ برای مثال `https://api.example.com`.
4. پس از بررسی CORS، سلامت API و مهاجرت دیتابیس، تغییر را Commit و Push کن.

با `apiBaseUrl` خالی، فرانت‌اند API را از همان مبدأ صفحه درخواست می‌کند؛ این حالت برای اجرای یکپارچهٔ محلی است، نه برای GitHub Pages بدون بک‌اند. در صورت عدم دسترسی به API، رابط باید حالت پیش‌نمایش را صریح اعلام کند و ادعا نکند که سفارش واقعی ثبت شده است.

راهنمای تکمیلی در [راهنمای استقرار](docs/DEPLOYMENT.md) قرار دارد.

## مرزهای فعلی MVP

- جست‌وجو **قاعده‌محور** است؛ اتصال LLM یا سرویس پولی هوش مصنوعی تنظیم نشده است.
- پرداخت آنلاین، تطبیق صندوق فروش (POS) و حسابداری وجود ندارند؛ ارزش سفارش تحویل‌شده معادل کل درآمد کافه نیست.
- حالت مطالعه زمان جلسه و دستورالعمل را مدیریت می‌کند اما به روتر یا Captive Portal متصل نیست و دسترسی واقعی Wi-Fi را خودکار قطع نمی‌کند.
- دریافت پاداش، درخواست برای بررسی کارکنان است؛ تخفیف را خودکار در صندوق اعمال نمی‌کند.
- سرویس واقعی پیامک/ایمیل برای تأیید هویت یا بازیابی گذرواژه تنظیم نشده است.
- قبل از استفادهٔ تجاری، کنترل دسترسی و نرخ درخواست‌ها، پشتیبان‌گیری و پایش، HTTPS، مدیریت نشست‌ها، بررسی امنیتی و آزمون بصری روی موبایل/دسکتاپ باید تکمیل شوند.

جزئیات موارد انجام‌شده و باقی‌مانده در [وضعیت پیاده‌سازی](docs/IMPLEMENTATION-STATUS.md)، تصمیم‌های محصول در [مشخصات محصول](docs/PRODUCT-SPEC.md) و کارهای آتی در [نقشهٔ راه](docs/ROADMAP.md) آمده‌اند.

## مشارکت در توسعه

- تغییر را در شاخه‌ای با نام مشخص انجام بده.
- نام Commit را بر اساس Conventional Commits انتخاب کن؛ مانند `fix(cart): keep drawer hidden by default` یا `docs: expand local setup guide`.
- قبل از Push، آزمون‌های مرتبط را اجرا کن و خروجی موفق یا محدودیت واقعی را ثبت کن.
- هیچ فایل `.env`، پایگاه دادهٔ محلی، رمز، کلید API یا اطلاعات مشتری را Commit نکن.

## مجوز

این پروژه تحت مجوز MIT ارائه می‌شود؛ متن کامل در فایل [LICENSE](LICENSE) است.
