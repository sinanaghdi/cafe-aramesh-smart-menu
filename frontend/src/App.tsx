import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type FormEvent,
} from "react";

type View = "menu" | "staff" | "merchant" | "club";
type StudySessionInfo = {
  id: number;
  status: string;
  duration_minutes: number;
  expires_at: string | null;
  wifi_code: string | null;
  remaining_seconds: number;
};
type StudyModeRules = {
  enabled: boolean;
  minimum_order_amount: number;
  required_product_id: number | null;
  allowed_durations_minutes: number[];
  allowed_start_time: string;
  allowed_end_time: string;
  max_concurrent_sessions: number;
};
type LoyaltyRules = {
  enabled: boolean;
  points_per_confirmed_order: number;
  silver_threshold: number;
  gold_threshold: number;
  rewards_enabled: boolean;
};
type ClubAccount = {
  full_name: string;
  phone_masked: string;
  points_balance: number;
  tier: string;
  transactions: { points_delta: number; reason: string; created_at: string }[];
  orders: { id: number; status: string; created_at: string; total_amount: number; currency_unit: string }[];
  rewards: { id: number; name: string; description: string; points_cost: number; reward_type: string }[];
};
type OtpRequest = { request_id: number; expires_at: string; debug_code: string | null };
type StudyOrder = OrderData & { study_mode_requested?: boolean; study_session?: StudySessionInfo | null };
type Tag = { key: string; value: string };
type Category = { id: number; slug: string; name: string; sort_order: number };
type Product = {
  id: number;
  slug: string;
  name: string;
  description: string;
  price_amount: number;
  category_id: number;
  category_name: string;
  is_available: boolean;
  is_featured: boolean;
  tags: Tag[];
};
type MenuData = {
  cafe_name: string;
  cafe_slug: string;
  currency_unit: "IRT" | "IRR" | string;
  table_number: number | null;
  categories: Category[];
  products: Product[];
};
type OrderItem = {
  product_id?: number;
  product_name: string;
  quantity: number;
  unit_price_amount?: number;
  line_total_amount?: number;
};
type OrderData = {
  id: number;
  status: string;
  table_number: number;
  currency_unit?: string;
  total_amount?: number;
  created_at?: string;
  code?: string;
  code_expires_at?: string;
  study_mode_requested?: boolean;
  study_session?: StudySessionInfo | null;
  items: OrderItem[];
};
type AuthState = {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  user: {
    id: number;
    cafe_id: number;
    full_name: string;
    role: string;
    email: string | null;
  };
};
type StaffOrder = {
  id: number;
  status: string;
  table_number: number;
  created_at: string;
  notes: string | null;
  items: { product_name: string; quantity: number }[];
};

const money = (value: number) =>
  new Intl.NumberFormat("fa-IR", { maximumFractionDigits: 0 }).format(value);
const unit = (currency?: string) => (currency === "IRR" ? "ریال" : "تومان");
const statusLabels: Record<string, string> = {
  draft: "پیش‌نویس",
  pending_confirmation: "در انتظار گارسون",
  confirmed: "تأیید شده",
  preparing: "در حال آماده‌سازی",
  served: "تحویل شده",
  cancelled: "لغو شده",
  expired: "منقضی شده",
  active: "فعال",
  pending: "در انتظار تأیید",
  ended: "پایان‌یافته",
};
const tagLabels: Record<string, string> = {
  none: "بدون",
  low: "کم",
  medium: "متوسط",
  high: "زیاد",
  cold: "سرد",
  hot: "گرم",
  iced: "یخی",
  sour: "ترش",
  sweet: "شیرین",
  creamy: "خامه‌ای",
  fruity: "میوه‌ای",
  bitter: "تلخ",
};

async function errorMessage(response: Response): Promise<string> {
  try {
    const data = (await response.json()) as { detail?: string };
    return data.detail || "در انجام درخواست خطایی رخ داد.";
  } catch {
    return "ارتباط با سرور برقرار نشد.";
  }
}

async function publicJson<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (!headers.has("Content-Type"))
    headers.set("Content-Type", "application/json");
  const response = await fetch(path, {
    ...init,
    credentials: "include",
    headers,
  });
  if (!response.ok) throw new Error(await errorMessage(response));
  return (await response.json()) as T;
}

export default function App() {
  const [view, setView] = useState<View>("menu");
  const [menu, setMenu] = useState<MenuData | null>(null);
  const [loadError, setLoadError] = useState("");
  const [query, setQuery] = useState("");
  const [activeCategory, setActiveCategory] = useState<number | "all">("all");
  const [cart, setCart] = useState<Record<number, number>>({});
  const [cartOpen, setCartOpen] = useState(false);
  const [sendingOrder, setSendingOrder] = useState(false);
  const [orderError, setOrderError] = useState("");
  const [submittedOrder, setSubmittedOrder] = useState<StudyOrder | null>(null);
  const [studyModeRequested, setStudyModeRequested] = useState(false);
  const [studyDurationMinutes, setStudyDurationMinutes] = useState(120);
  const [clockNow, setClockNow] = useState(Date.now());

  const tableParam = new URLSearchParams(window.location.search).get("table");
  const tableNumber =
    tableParam && /^\d{1,3}$/.test(tableParam) && Number(tableParam) > 0
      ? Number(tableParam)
      : null;

  useEffect(() => {
    const controller = new AbortController();
    const queryString = tableNumber ? `?table=${tableNumber}` : "";
    fetch(`/api/v1/menu${queryString}`, {
      signal: controller.signal,
      credentials: "include",
    })
      .then(async (response) => {
        if (!response.ok) throw new Error(await errorMessage(response));
        return (await response.json()) as MenuData;
      })
      .then(setMenu)
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          setLoadError(
            error instanceof Error ? error.message : "بارگذاری منو ناموفق بود.",
          );
        }
      });
    return () => controller.abort();
  }, [tableNumber]);

  useEffect(() => {
    if (!submittedOrder) return;
    const controller = new AbortController();
    const timer = window.setInterval(async () => {
      try {
        const latest = await publicJson<StudyOrder>(
          `/api/v1/orders/${submittedOrder.id}`,
          { signal: controller.signal },
        );
        setSubmittedOrder((current) =>
          current && current.id === latest.id
            ? { ...current, ...latest }
            : current,
        );
      } catch {
        // Keep the existing receipt visible if a status refresh is temporarily unavailable.
      }
    }, 7000);
    return () => {
      controller.abort();
      window.clearInterval(timer);
    };
  }, [submittedOrder?.id]);

  useEffect(() => {
    if (!submittedOrder?.study_session?.expires_at) return;
    const timer = window.setInterval(() => setClockNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [submittedOrder?.study_session?.expires_at]);

  const products = menu?.products ?? [];
  const filteredProducts = useMemo(() => {
    const search = query.trim().toLocaleLowerCase("fa-IR");
    return products.filter((product) => {
      const categoryMatch =
        activeCategory === "all" || product.category_id === activeCategory;
      const searchMatch =
        !search ||
        product.name.toLocaleLowerCase("fa-IR").includes(search) ||
        product.description.toLocaleLowerCase("fa-IR").includes(search) ||
        product.category_name.toLocaleLowerCase("fa-IR").includes(search);
      return categoryMatch && searchMatch;
    });
  }, [products, activeCategory, query]);

  const cartItems = products.filter((product) => (cart[product.id] ?? 0) > 0);
  const cartCount = Object.values(cart).reduce((sum, count) => sum + count, 0);
  const cartTotal = cartItems.reduce(
    (sum, product) => sum + product.price_amount * (cart[product.id] ?? 0),
    0,
  );

  const changeQuantity = (productId: number, change: number) => {
    setCart((current) => {
      const next = { ...current };
      const value = (next[productId] ?? 0) + change;
      if (value <= 0) delete next[productId];
      else next[productId] = Math.min(20, value);
      return next;
    });
  };

  const submitOrder = async () => {
    if (!menu || !tableNumber || cartItems.length === 0) return;
    setSendingOrder(true);
    setOrderError("");
    try {
      const order = await publicJson<StudyOrder>("/api/v1/orders", {
        method: "POST",
        body: JSON.stringify({
          table_number: tableNumber,
          items: cartItems.map((product) => ({
            product_id: product.id,
            quantity: cart[product.id],
          })),
          study_mode_requested: studyModeRequested,
          study_duration_minutes: studyModeRequested ? studyDurationMinutes : null,
        }),
      });
      setSubmittedOrder(order);
      setStudyModeRequested(false);
      setStudyDurationMinutes(120);
      setCart({});
      setCartOpen(false);
    } catch (error) {
      setOrderError(
        error instanceof Error ? error.message : "ثبت درخواست ناموفق بود.",
      );
    } finally {
      setSendingOrder(false);
    }
  };

  if (view === "staff") {
    return <StaffPanel onBack={() => setView("menu")} />;
  }
  if (view === "merchant") {
    return <MerchantPanel onBack={() => setView("menu")} />;
  }
  if (view === "club") {
    return <ClubPanel onBack={() => setView("menu")} />;
  }

  return (
    <main className="app-shell" dir="rtl">
      <header className="site-header">
        <a className="brand-lockup" href="/" aria-label="کافه آرامش">
          <span className="brand-symbol" aria-hidden="true">
            آ
          </span>
          <span>
            <strong>کافه آرامش</strong>
            <small>قهوه، مکث، حال خوب</small>
          </span>
        </a>
        <nav className="header-actions" aria-label="ناوبری اصلی">
          <span className="table-pill">
            <span className="table-dot" />
            {tableNumber ? `میز ${money(tableNumber)}` : "مشاهده منو"}
          </span>
          <button
            className="button button-outline button-small"
            onClick={() => setView("merchant")}
          >
            پنل صاحب کافه
          </button>
          <button
            className="button button-dark button-small"
            onClick={() => setView("staff")}
          >
            پنل گارسون
          </button>
          <button
            className="button button-outline button-small"
            onClick={() => setView("club")}
          >
            باشگاه
          </button>
          <button
            className="cart-trigger"
            onClick={() => setCartOpen(true)}
            aria-label={`سبد درخواست، ${cartCount} آیتم`}
          >
            سبد <span>{money(cartCount)}</span>
          </button>
        </nav>
      </header>

      <section className="menu-hero">
        <div className="hero-copy">
          <p className="eyebrow">
            <span /> منوی کافه آرامش
          </p>
          <h1>
            امروز دلت
            <br />
            <em>چه طعمی می‌خواهد؟</em>
          </h1>
          <p className="hero-intro">
            انتخابت را با حال‌وهوایت هماهنگ کن. نوشیدنی‌های تازه، طعم‌های روشن و
            انتخاب‌هایی برای لحظه‌ای که مال خودت است.
          </p>
          <a className="text-link" href="#menu-list">
            دیدن منو <span aria-hidden="true">←</span>
          </a>
        </div>
        <div className="hero-art" aria-label="نمای گرافیکی فنجان قهوه">
          <div className="art-orbit orbit-one" />
          <div className="art-orbit orbit-two" />
          <div className="coffee-saucer" />
          <div className="coffee-cup">
            <span className="coffee-swirl" />
          </div>
          <div className="cup-handle" />
          <span className="art-stamp">
            SLOW
            <br />
            MOMENT
          </span>
          <span className="art-caption">هر فنجان، یک مکث</span>
        </div>
      </section>

      <section className="menu-section" id="menu-list">
        <div className="section-heading">
          <div>
            <p className="eyebrow">با حوصله انتخاب کن</p>
            <h2>منوی امروز</h2>
          </div>
          <span className="result-count">
            {money(filteredProducts.length)} انتخاب
          </span>
        </div>
        {tableNumber === null && (
          <div className="notice notice-soft">
            برای ثبت درخواست، منو را با QR روی میز باز کن. در حال حاضر فقط
            می‌توانی منو را ببینی.
          </div>
        )}
        <label className="search-box">
          <span aria-hidden="true">⌕</span>
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="نام نوشیدنی یا طعمی که دوست داری..."
            aria-label="جست‌وجو در منو"
          />
          {query && (
            <button onClick={() => setQuery("")} aria-label="پاک کردن جست‌وجو">
              ×
            </button>
          )}
        </label>
        <div className="category-scroll" aria-label="دسته‌بندی محصولات">
          <button
            className={
              activeCategory === "all"
                ? "category-chip active"
                : "category-chip"
            }
            onClick={() => setActiveCategory("all")}
          >
            همه
          </button>
          {(menu?.categories ?? []).map((category) => (
            <button
              key={category.id}
              className={
                activeCategory === category.id
                  ? "category-chip active"
                  : "category-chip"
              }
              onClick={() => setActiveCategory(category.id)}
            >
              {category.name}
            </button>
          ))}
        </div>

        {loadError && <div className="notice notice-error">{loadError}</div>}
        {!menu && !loadError && (
          <div className="loading-panel">در حال آماده‌کردن منوی کافه...</div>
        )}
        {menu && (
          <div className="product-grid">
            {filteredProducts.map((product, index) => {
              const quantity = cart[product.id] ?? 0;
              const caffeine = product.tags.find(
                (tag) => tag.key === "caffeine",
              )?.value;
              const taste = product.tags.find(
                (tag) => tag.key === "taste",
              )?.value;
              return (
                <article className="product-card" key={product.id}>
                  <div className={`product-art product-art-${index % 5}`}>
                    <span className="product-art-index">
                      {String(index + 1).padStart(2, "0")}
                    </span>
                    <span className="product-art-ring" />
                    <span className="product-art-cup">
                      {["◒", "◉", "◍", "◌", "◓"][index % 5]}
                    </span>
                    {product.is_featured && (
                      <span className="feature-ribbon">پیشنهاد کافه</span>
                    )}
                  </div>
                  <div className="product-content">
                    <div className="product-meta">
                      <span>{product.category_name}</span>
                      {caffeine === "none" && (
                        <span className="tag-muted">بدون کافئین</span>
                      )}
                      {caffeine === "high" && (
                        <span className="tag-muted">کافئین بالا</span>
                      )}
                    </div>
                    <h3>{product.name}</h3>
                    <p className="product-description">{product.description}</p>
                    {taste && (
                      <p className="taste-line">
                        حال‌وهوا: {tagLabels[taste] ?? taste}
                      </p>
                    )}
                    <div className="product-footer">
                      <span className="price">
                        {money(product.price_amount)}{" "}
                        <small>{unit(menu.currency_unit)}</small>
                      </span>
                      {quantity === 0 ? (
                        <button
                          className="add-button"
                          disabled={!product.is_available}
                          onClick={() => changeQuantity(product.id, 1)}
                          aria-label={`افزودن ${product.name} به سبد`}
                        >
                          +
                        </button>
                      ) : (
                        <div
                          className="quantity-control"
                          aria-label={`تعداد ${product.name}`}
                        >
                          <button
                            onClick={() => changeQuantity(product.id, 1)}
                            aria-label="افزایش تعداد"
                          >
                            +
                          </button>
                          <span>{money(quantity)}</span>
                          <button
                            onClick={() => changeQuantity(product.id, -1)}
                            aria-label="کاهش تعداد"
                          >
                            −
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
        )}
        {menu && filteredProducts.length === 0 && (
          <div className="empty-state">
            چیزی با این مشخصات پیدا نکردیم. عبارت دیگری را امتحان کن.
          </div>
        )}
      </section>

      <footer className="site-footer">
        <div className="footer-brand">
          <span className="brand-symbol">آ</span>
          <strong>کافه آرامش</strong>
        </div>
        <span>با احترام به انتخاب و زمان شما</span>
        <span>منوی دیجیتال · نسخه اولیه</span>
      </footer>

      {cartOpen && (
        <div
          className="drawer-backdrop"
          role="presentation"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) setCartOpen(false);
          }}
        >
          <section
            className="cart-drawer"
            role="dialog"
            aria-modal="true"
            aria-labelledby="cart-title"
          >
            <header className="drawer-header">
              <div>
                <p className="eyebrow">قبل از ثبت درخواست</p>
                <h2 id="cart-title">سبد انتخابت</h2>
              </div>
              <button
                className="icon-button"
                onClick={() => setCartOpen(false)}
                aria-label="بستن سبد"
              >
                ×
              </button>
            </header>
            {cartItems.length === 0 ? (
              <div className="empty-state">
                سبدت هنوز خالی است. از منو چیزی انتخاب کن.
              </div>
            ) : (
              <div className="cart-lines">
                {cartItems.map((product) => (
                  <div className="cart-line" key={product.id}>
                    <div className="cart-line-icon">◒</div>
                    <div className="cart-line-info">
                      <strong>{product.name}</strong>
                      <span>
                        {money(product.price_amount)}{" "}
                        {unit(menu?.currency_unit)}
                      </span>
                      <div className="quantity-control">
                        <button
                          onClick={() => changeQuantity(product.id, 1)}
                          aria-label="افزایش تعداد"
                        >
                          +
                        </button>
                        <span>{money(cart[product.id] ?? 0)}</span>
                        <button
                          onClick={() => changeQuantity(product.id, -1)}
                          aria-label="کاهش تعداد"
                        >
                          −
                        </button>
                      </div>
                    </div>
                    <strong className="line-total">
                      {money(product.price_amount * (cart[product.id] ?? 0))}
                    </strong>
                  </div>
                ))}
              </div>
            )}
            <div className="cart-summary">
              <div>
                <span>جمع نمایشی سبد</span>
                <strong>
                  {money(cartTotal)} {unit(menu?.currency_unit)}
                </strong>
              </div>
              <p>
                مبلغ نهایی هنگام ثبت درخواست در سرور دوباره محاسبه می‌شود؛
                پرداخت آنلاین انجام نمی‌شود.
              </p>
              <div className="study-option">
                <label className="study-toggle">
                  <input
                    type="checkbox"
                    checked={studyModeRequested}
                    onChange={(event) => setStudyModeRequested(event.target.checked)}
                  />
                  <span>
                    <strong>استادی‌مود / ورک‌مود</strong>
                    <small>درخواست دسترسی زمان‌دار وای‌فای؛ فعال‌سازی فقط پس از تأیید گارسون</small>
                  </span>
                </label>
                {studyModeRequested && (
                  <label className="field-label">
                    مدت درخواستی
                    <select
                      value={studyDurationMinutes}
                      onChange={(event) => setStudyDurationMinutes(Number(event.target.value))}
                    >
                      <option value={120}>۲ ساعت</option>
                      <option value={180}>۳ ساعت</option>
                      <option value={240}>۴ ساعت</option>
                    </select>
                  </label>
                )}
              </div>
              {!tableNumber && (
                <p className="inline-error">
                  برای ثبت درخواست باید از QR میز وارد شوی.
                </p>
              )}
              {orderError && <p className="inline-error">{orderError}</p>}
              <button
                className="button button-dark button-wide"
                disabled={
                  !tableNumber || cartItems.length === 0 || sendingOrder
                }
                onClick={submitOrder}
              >
                {sendingOrder ? "در حال ثبت..." : "ثبت درخواست برای گارسون"}
              </button>
            </div>
          </section>
        </div>
      )}

      {submittedOrder && (
        <div className="drawer-backdrop receipt-backdrop">
          <section
            className="receipt-card"
            role="dialog"
            aria-modal="true"
            aria-labelledby="receipt-title"
          >
            <button
              className="icon-button receipt-close"
              onClick={() => setSubmittedOrder(null)}
              aria-label="بستن رسید"
            >
              ×
            </button>
            <div className="receipt-check">✓</div>
            <p className="eyebrow">درخواست ثبت شد</p>
            <h2 id="receipt-title">حالا نوبت گارسون است</h2>
            <p className="receipt-copy">
              برای تأیید نهایی، گارسون به میزت می‌آید. کد زیر را فقط به او نشان
              بده.
            </p>
            {submittedOrder.code && (
              <div className="verification-code" aria-label="کد تأیید سفارش">
                {submittedOrder.code.split("").map((digit, index) => (
                  <span key={index}>{digit}</span>
                ))}
              </div>
            )}
            <div className="receipt-details">
              <span>شماره درخواست</span>
              <strong>#{money(submittedOrder.id)}</strong>
              <span>میز</span>
              <strong>{money(submittedOrder.table_number)}</strong>
              <span>وضعیت</span>
              <strong>
                <span className="status-pill">
                  {statusLabels[submittedOrder.status] ?? submittedOrder.status}
                </span>
              </strong>
              <span>مبلغ</span>
              <strong>
                {money(submittedOrder.total_amount ?? 0)}{" "}
                {unit(submittedOrder.currency_unit)}
              </strong>
            </div>
            {submittedOrder.study_mode_requested && (
              <div className="study-receipt">
                <strong>درخواست استادی‌مود</strong>
                {!submittedOrder.study_session && submittedOrder.status === "pending_confirmation" && (
                  <p>پس از تأیید گارسون، در صورت واجد شرایط بودن، کد وای‌فای نمایش داده می‌شود.</p>
                )}
                {submittedOrder.study_session && (
                  <>
                    <p>وضعیت جلسه: {statusLabels[submittedOrder.study_session.status] ?? submittedOrder.study_session.status}</p>
                    {submittedOrder.study_session.wifi_code && submittedOrder.study_session.status === "active" && (
                      <div className="wifi-voucher-code">
                        <span>کد وای‌فای آزمایشی</span>
                        <strong>{submittedOrder.study_session.wifi_code}</strong>
                      </div>
                    )}
                    {submittedOrder.study_session.expires_at && submittedOrder.study_session.status === "active" && (() => {
                      const remaining = Math.max(0, Math.ceil((Date.parse(submittedOrder.study_session.expires_at) - clockNow) / 1000));
                      const hours = Math.floor(remaining / 3600);
                      const minutes = Math.floor((remaining % 3600) / 60);
                      const seconds = remaining % 60;
                      return (
                        <p className={remaining <= 600 ? "receipt-warning" : "study-countdown"}>
                          زمان باقی‌مانده: {money(hours)}:{String(minutes).padStart(2, "0")}:{String(seconds).padStart(2, "0")}
                          {remaining > 0 && remaining <= 600 ? " — کمتر از ۱۰ دقیقه باقی مانده است." : ""}
                          {remaining === 0 ? " — جلسه به پایان رسیده است." : ""}
                        </p>
                      );
                    })()}
                  </>
                )}
              </div>
            )}
            {submittedOrder.study_mode_requested && submittedOrder.status === "confirmed" && !submittedOrder.study_session && (
              <p className="receipt-warning">سفارش تأیید شده، اما قوانین یا ظرفیت استادی‌مود در زمان تأیید اجازه صدور ووچر نداد.</p>
            )}
            {submittedOrder.code_expires_at &&
              submittedOrder.status === "pending_confirmation" && (
                <p className="receipt-warning">
                  کد تا{" "}
                  {new Date(submittedOrder.code_expires_at).toLocaleTimeString(
                    "fa-IR",
                    { hour: "2-digit", minute: "2-digit" },
                  )}{" "}
                  اعتبار دارد. این کد فقط همین بار نمایش داده می‌شود.
                </p>
              )}
            <button
              className="button button-dark button-wide"
              onClick={() => setSubmittedOrder(null)}
            >
              متوجه شدم
            </button>
          </section>
        </div>
      )}
    </main>
  );
}

function StaffPanel({ onBack }: { onBack: () => void }) {
  const [email, setEmail] = useState("staff@aramesh.local");
  const [password, setPassword] = useState("");
  const [auth, setAuth] = useState<AuthState | null>(null);
  const [authError, setAuthError] = useState("");
  const [orders, setOrders] = useState<StaffOrder[]>([]);
  const [filter, setFilter] = useState("pending_confirmation");
  const [codes, setCodes] = useState<Record<number, string>>({});
  const [busyOrder, setBusyOrder] = useState<number | null>(null);
  const [notice, setNotice] = useState("");
  const [staffError, setStaffError] = useState("");

  const authedFetch = useCallback(
    async (path: string, init: RequestInit = {}): Promise<Response> => {
      if (!auth) throw new Error("ابتدا وارد پنل شوید.");
      const perform = (accessToken: string) => {
        const headers = new Headers(init.headers);
        if (!headers.has("Content-Type"))
          headers.set("Content-Type", "application/json");
        headers.set("Authorization", `Bearer ${accessToken}`);
        return fetch(path, { ...init, headers });
      };
      let response = await perform(auth.access_token);
      if (response.status === 401) {
        const refreshResponse = await fetch("/api/v1/auth/refresh", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: auth.refresh_token }),
        });
        if (!refreshResponse.ok) {
          setAuth(null);
          throw new Error("نشست منقضی شده است؛ دوباره وارد شوید.");
        }
        const renewed = (await refreshResponse.json()) as AuthState;
        setAuth(renewed);
        response = await perform(renewed.access_token);
      }
      return response;
    },
    [auth],
  );

  const loadOrders = useCallback(async () => {
    const response = await authedFetch("/api/v1/staff/orders");
    if (!response.ok) throw new Error(await errorMessage(response));
    setOrders((await response.json()) as StaffOrder[]);
  }, [authedFetch]);

  useEffect(() => {
    if (!auth) return;
    const controller = new AbortController();
    let pollTimer: number | undefined;
    const startPolling = () => {
      if (pollTimer) return;
      void loadOrders().catch((error: unknown) => {
        setStaffError(
          error instanceof Error
            ? error.message
            : "بارگذاری سفارش‌ها ناموفق بود.",
        );
      });
      pollTimer = window.setInterval(() => {
        void loadOrders().catch((error: unknown) => {
          setStaffError(
            error instanceof Error
              ? error.message
              : "بارگذاری سفارش‌ها ناموفق بود.",
          );
        });
      }, 5000);
    };

    const streamOrders = async () => {
      try {
        const response = await authedFetch("/api/v1/staff/events", {
          signal: controller.signal,
        });
        if (!response.ok || !response.body) throw new Error("SSE unavailable");
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        while (!controller.signal.aborted) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const blocks = buffer.split("\n\n");
          buffer = blocks.pop() ?? "";
          for (const block of blocks) {
            const dataLine = block
              .split("\n")
              .find((line) => line.startsWith("data: "));
            if (!dataLine) continue;
            try {
              setOrders(JSON.parse(dataLine.slice(6)) as StaffOrder[]);
              setStaffError("");
            } catch {
              // Ignore malformed stream frames; the next snapshot will repair the view.
            }
          }
        }
      } catch {
        if (!controller.signal.aborted) startPolling();
      }
    };
    void streamOrders();
    return () => {
      controller.abort();
      if (pollTimer) window.clearInterval(pollTimer);
    };
  }, [auth, authedFetch, loadOrders]);

  const login = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setAuthError("");
    try {
      const result = await publicJson<AuthState>("/api/v1/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password, cafe_slug: "cafe-aramesh" }),
      });
      if (result.user.role !== "staff") {
        setAuthError("این پنل فقط برای گارسون‌هاست.");
        return;
      }
      setAuth(result);
      setPassword("");
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : "ورود ناموفق بود.");
    }
  };

  const confirmOrder = async (orderId: number) => {
    setBusyOrder(orderId);
    setStaffError("");
    setNotice("");
    try {
      const response = await authedFetch(
        `/api/v1/staff/orders/${orderId}/confirm`,
        {
          method: "POST",
          body: JSON.stringify({ code: codes[orderId] ?? "" }),
        },
      );
      if (!response.ok) throw new Error(await errorMessage(response));
      setCodes((current) => ({ ...current, [orderId]: "" }));
      setNotice(`درخواست شماره ${money(orderId)} تأیید شد.`);
      await loadOrders();
    } catch (error) {
      setStaffError(
        error instanceof Error ? error.message : "تأیید سفارش ناموفق بود.",
      );
    } finally {
      setBusyOrder(null);
    }
  };

  const changeOrderStatus = async (
    orderId: number,
    status: "preparing" | "served" | "cancelled",
  ) => {
    setBusyOrder(orderId);
    setStaffError("");
    setNotice("");
    let reason: string | undefined;
    if (status === "cancelled") {
      reason = window.prompt("دلیل لغو سفارش را بنویسید:")?.trim();
      if (!reason) {
        setBusyOrder(null);
        return;
      }
    }
    try {
      const response = await authedFetch(
        `/api/v1/staff/orders/${orderId}/status`,
        {
          method: "PATCH",
          body: JSON.stringify({ status, reason }),
        },
      );
      if (!response.ok) throw new Error(await errorMessage(response));
      setNotice("وضعیت درخواست به‌روز شد.");
      await loadOrders();
    } catch (error) {
      setStaffError(
        error instanceof Error ? error.message : "تغییر وضعیت ناموفق بود.",
      );
    } finally {
      setBusyOrder(null);
    }
  };

  const logout = async () => {
    if (auth) {
      await fetch("/api/v1/auth/logout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: auth.refresh_token }),
      }).catch(() => undefined);
    }
    setAuth(null);
    setOrders([]);
  };

  const displayedOrders = orders.filter(
    (order) => filter === "all" || order.status === filter,
  );
  const pendingCount = orders.filter(
    (order) => order.status === "pending_confirmation",
  ).length;

  return (
    <main className="staff-shell" dir="rtl">
      <header className="site-header staff-header">
        <a
          className="brand-lockup"
          href="/"
          onClick={(event) => {
            event.preventDefault();
            onBack();
          }}
        >
          <span className="brand-symbol">آ</span>
          <span>
            <strong>کافه آرامش</strong>
            <small>میز خدمت کارکنان</small>
          </span>
        </a>
        <div className="header-actions">
          <span className="staff-only-label">پنل عملیاتی سفارش</span>
          <button
            className="button button-outline button-small"
            onClick={onBack}
          >
            بازگشت به منو
          </button>
          {auth && (
            <button
              className="button button-dark button-small"
              onClick={() => void logout()}
            >
              خروج
            </button>
          )}
        </div>
      </header>

      {!auth ? (
        <section className="staff-login-layout">
          <div className="staff-intro">
            <p className="eyebrow">
              <span /> میز خدمت
            </p>
            <h1>
              سفارش‌ها را
              <br />
              <em>با دقت دنبال کن.</em>
            </h1>
            <p>
              تأیید نهایی پس از تطبیق کد با مشتری انجام می‌شود. این پنل فقط برای
              عملیات سفارش است و آمار فروش یا درآمد نمایش نمی‌دهد.
            </p>
          </div>
          <form className="login-card" onSubmit={login}>
            <p className="eyebrow">ورود کارکنان</p>
            <h2>ورود به پنل گارسون</h2>
            <label className="field-label">
              ایمیل سازمانی
              <input
                type="email"
                autoComplete="username"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </label>
            <label className="field-label">
              گذرواژه
              <input
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </label>
            {authError && <p className="inline-error">{authError}</p>}
            <button className="button button-dark button-wide" type="submit">
              ورود امن
            </button>
            <p className="login-footnote">
              محیط توسعه محلی: اطلاعات ورود نمونه در فایل README ثبت شده است.
            </p>
          </form>
        </section>
      ) : (
        <section className="staff-workspace">
          <div className="staff-page-heading">
            <div>
              <p className="eyebrow">نمای زنده سفارش‌ها</p>
              <h1>سلام، {auth.user.full_name}</h1>
              <p>
                درخواست‌ها را ببین، کد را تطبیق بده و فقط وضعیت مجاز را تغییر
                بده.
              </p>
            </div>
            <div className="pending-counter">
              <strong>{money(pendingCount)}</strong>
              <span>در انتظار تأیید</span>
            </div>
          </div>
          <div className="staff-privacy-note">
            <span>●</span> دسترسی این نقش فقط به اطلاعات عملیاتی سفارش محدود
            است.
          </div>
          <div className="staff-filter-row">
            {[
              ["pending_confirmation", "در انتظار تأیید"],
              ["confirmed", "تأیید شده"],
              ["preparing", "در حال آماده‌سازی"],
              ["all", "همه"],
            ].map(([value, label]) => (
              <button
                key={value}
                className={
                  filter === value ? "filter-button active" : "filter-button"
                }
                onClick={() => setFilter(value)}
              >
                {label}
              </button>
            ))}
            <button
              className="refresh-button"
              onClick={() => void loadOrders()}
            >
              ↻ تازه‌سازی
            </button>
          </div>
          {notice && <div className="notice notice-success">{notice}</div>}
          {staffError && (
            <div className="notice notice-error">{staffError}</div>
          )}
          {displayedOrders.length === 0 ? (
            <div className="staff-empty">
              <span>◌</span>
              <h2>درخواستی در این فهرست نیست</h2>
              <p>در صورت ثبت درخواست جدید، فهرست به‌روزرسانی می‌شود.</p>
            </div>
          ) : (
            <div className="staff-order-list">
              {displayedOrders.map((order) => (
                <article className="staff-order-card" key={order.id}>
                  <div className="staff-order-top">
                    <div>
                      <span className="order-reference">
                        درخواست #{money(order.id)}
                      </span>
                      <span className="status-pill">
                        {statusLabels[order.status] ?? order.status}
                      </span>
                    </div>
                    <strong className="table-badge">
                      میز {money(order.table_number)}
                    </strong>
                  </div>
                  <div className="staff-order-items">
                    {order.items.map((item, index) => (
                      <div key={index}>
                        <span>{item.product_name}</span>
                        <strong>× {money(item.quantity)}</strong>
                      </div>
                    ))}
                  </div>
                  {order.notes && (
                    <p className="staff-note">یادداشت مشتری: {order.notes}</p>
                  )}
                  <div className="staff-order-bottom">
                    <span className="order-time">
                      {new Date(order.created_at).toLocaleString("fa-IR", {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </span>
                    <div className="staff-order-actions">
                      {order.status === "pending_confirmation" && (
                        <form
                          className="confirm-inline"
                          onSubmit={(event) => {
                            event.preventDefault();
                            void confirmOrder(order.id);
                          }}
                        >
                          <input
                            inputMode="numeric"
                            autoComplete="off"
                            maxLength={4}
                            pattern="[0-9]{3,4}"
                            aria-label={`کد تأیید درخواست ${order.id}`}
                            placeholder="کد ۴ رقمی"
                            value={codes[order.id] ?? ""}
                            onChange={(event) =>
                              setCodes((current) => ({
                                ...current,
                                [order.id]: event.target.value
                                  .replace(/[^0-9]/g, "")
                                  .slice(0, 4),
                              }))
                            }
                            required
                          />
                          <button
                            className="button button-dark button-small"
                            disabled={busyOrder === order.id}
                          >
                            تأیید کد
                          </button>
                        </form>
                      )}
                      {order.status === "confirmed" && (
                        <button
                          className="button button-dark button-small"
                          disabled={busyOrder === order.id}
                          onClick={() =>
                            void changeOrderStatus(order.id, "preparing")
                          }
                        >
                          شروع آماده‌سازی
                        </button>
                      )}
                      {order.status === "preparing" && (
                        <button
                          className="button button-dark button-small"
                          disabled={busyOrder === order.id}
                          onClick={() =>
                            void changeOrderStatus(order.id, "served")
                          }
                        >
                          تحویل شد
                        </button>
                      )}
                      {[
                        "pending_confirmation",
                        "confirmed",
                        "preparing",
                      ].includes(order.status) && (
                        <button
                          className="button-link-danger"
                          disabled={busyOrder === order.id}
                          onClick={() =>
                            void changeOrderStatus(order.id, "cancelled")
                          }
                        >
                          لغو
                        </button>
                      )}
                    </div>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>
      )}
    </main>
  );
}


function MerchantPanel({ onBack }: { onBack: () => void }) {
  const [email, setEmail] = useState("merchant@aramesh.local");
  const [password, setPassword] = useState("");
  const [auth, setAuth] = useState<AuthState | null>(null);
  const [authError, setAuthError] = useState("");
  const [panelError, setPanelError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [menu, setMenu] = useState<MenuData | null>(null);
  const [study, setStudy] = useState<StudyModeRules | null>(null);
  const [loyalty, setLoyalty] = useState<LoyaltyRules | null>(null);

  const authedFetch = useCallback(async (path: string, init: RequestInit = {}): Promise<Response> => {
    if (!auth) throw new Error("ابتدا وارد پنل شوید.");
    const perform = (accessToken: string) => {
      const headers = new Headers(init.headers);
      if (!headers.has("Content-Type")) headers.set("Content-Type", "application/json");
      headers.set("Authorization", `Bearer ${accessToken}`);
      return fetch(path, { ...init, headers });
    };
    let response = await perform(auth.access_token);
    if (response.status === 401) {
      const refreshResponse = await fetch("/api/v1/auth/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: auth.refresh_token }),
      });
      if (!refreshResponse.ok) {
        setAuth(null);
        throw new Error("نشست منقضی شده است؛ دوباره وارد شوید.");
      }
      const renewed = (await refreshResponse.json()) as AuthState;
      setAuth(renewed);
      response = await perform(renewed.access_token);
    }
    return response;
  }, [auth]);

  const loadSettings = useCallback(async () => {
    const [studyResponse, loyaltyResponse, menuResponse] = await Promise.all([
      authedFetch("/api/v1/merchant/study-rules"),
      authedFetch("/api/v1/merchant/loyalty-rules"),
      fetch("/api/v1/menu"),
    ]);
    if (!studyResponse.ok) throw new Error(await errorMessage(studyResponse));
    if (!loyaltyResponse.ok) throw new Error(await errorMessage(loyaltyResponse));
    if (!menuResponse.ok) throw new Error(await errorMessage(menuResponse));
    setStudy((await studyResponse.json()) as StudyModeRules);
    setLoyalty((await loyaltyResponse.json()) as LoyaltyRules);
    setMenu((await menuResponse.json()) as MenuData);
  }, [authedFetch]);

  useEffect(() => {
    if (!auth) return;
    void loadSettings().catch((error: unknown) =>
      setPanelError(error instanceof Error ? error.message : "بارگذاری تنظیمات ناموفق بود."),
    );
  }, [auth?.access_token, loadSettings]);

  const login = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setAuthError("");
    try {
      const result = await publicJson<AuthState>("/api/v1/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password, cafe_slug: "cafe-aramesh" }),
      });
      if (result.user.role !== "merchant") {
        setAuthError("این پنل فقط برای صاحب کافه است.");
        return;
      }
      setAuth(result);
      setPassword("");
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : "ورود ناموفق بود.");
    }
  };

  const saveStudy = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!study) return;
    setBusy(true);
    setPanelError("");
    setNotice("");
    try {
      const response = await authedFetch("/api/v1/merchant/study-rules", {
        method: "PUT",
        body: JSON.stringify(study),
      });
      if (!response.ok) throw new Error(await errorMessage(response));
      setStudy((await response.json()) as StudyModeRules);
      setNotice("قوانین استادی‌مود ذخیره شد.");
    } catch (error) {
      setPanelError(error instanceof Error ? error.message : "ذخیره قوانین ناموفق بود.");
    } finally {
      setBusy(false);
    }
  };

  const saveLoyalty = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!loyalty) return;
    setBusy(true);
    setPanelError("");
    setNotice("");
    try {
      const response = await authedFetch("/api/v1/merchant/loyalty-rules", {
        method: "PUT",
        body: JSON.stringify(loyalty),
      });
      if (!response.ok) throw new Error(await errorMessage(response));
      setLoyalty((await response.json()) as LoyaltyRules);
      setNotice("قوانین باشگاه مشتریان ذخیره شد.");
    } catch (error) {
      setPanelError(error instanceof Error ? error.message : "ذخیره قوانین ناموفق بود.");
    } finally {
      setBusy(false);
    }
  };

  const logout = async () => {
    if (auth) {
      await fetch("/api/v1/auth/logout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: auth.refresh_token }),
      }).catch(() => undefined);
    }
    setAuth(null);
    setStudy(null);
    setLoyalty(null);
  };

  return (
    <main className="staff-shell" dir="rtl">
      <header className="site-header staff-header">
        <a className="brand-lockup" href="/" onClick={(event) => { event.preventDefault(); onBack(); }}>
          <span className="brand-symbol">آ</span>
          <span><strong>کافه آرامش</strong><small>تنظیمات صاحب کافه</small></span>
        </a>
        <div className="header-actions">
          <button className="button button-outline button-small" onClick={onBack}>بازگشت به منو</button>
          {auth && <button className="button button-dark button-small" onClick={() => void logout()}>خروج</button>}
        </div>
      </header>

      {!auth ? (
        <section className="staff-login-layout">
          <div className="staff-intro">
            <p className="eyebrow"><span /> پنل مدیریت</p>
            <h1>قوانین و تجربه<br /><em>کافه را تنظیم کن.</em></h1>
            <p>این پنل فعلاً قوانین استادی‌مود و باشگاه مشتریان را مدیریت می‌کند؛ گزارش فروش در فاز ۴ اضافه خواهد شد.</p>
          </div>
          <form className="login-card" onSubmit={login}>
            <p className="eyebrow">ورود مدیریت</p>
            <h2>ورود صاحب کافه</h2>
            <label className="field-label">ایمیل
              <input type="email" autoComplete="username" value={email} onChange={(event) => setEmail(event.target.value)} required />
            </label>
            <label className="field-label">گذرواژه
              <input type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required />
            </label>
            {authError && <p className="inline-error">{authError}</p>}
            <button className="button button-dark button-wide" type="submit">ورود امن</button>
            <p className="login-footnote">ورود نمونه فقط برای محیط توسعه محلی است.</p>
          </form>
        </section>
      ) : (
        <section className="merchant-workspace">
          <div className="staff-page-heading">
            <div><p className="eyebrow">تنظیمات محصول</p><h1>سلام، {auth.user.full_name}</h1><p>قواعد پیشنهادشده برای مشتری از سمت کافه کنترل می‌شوند.</p></div>
            <span className="staff-only-label">مدیریت کافه · فاز ۲</span>
          </div>
          {notice && <div className="notice notice-success">{notice}</div>}
          {panelError && <div className="notice notice-error">{panelError}</div>}
          {!study || !loyalty || !menu ? (
            <div className="loading-panel">در حال بارگذاری تنظیمات...</div>
          ) : (
            <div className="merchant-settings-grid">
              <form className="settings-card" onSubmit={(event) => void saveStudy(event)}>
                <p className="eyebrow">استادی‌مود / ورک‌مود</p>
                <h2>قوانین استفاده از وای‌فای</h2>
                <label className="study-toggle">
                  <input type="checkbox" checked={study.enabled} onChange={(event) => setStudy({ ...study, enabled: event.target.checked })} />
                  <span><strong>فعال‌سازی استادی‌مود</strong><small>صدور ووچر فقط پس از تأیید گارسون</small></span>
                </label>
                <label className="field-label">حداقل خرید به تومان
                  <input type="number" min="0" value={study.minimum_order_amount} onChange={(event) => setStudy({ ...study, minimum_order_amount: Number(event.target.value) })} required />
                </label>
                <label className="field-label">محصول الزامی (اختیاری)
                  <select value={study.required_product_id ?? ""} onChange={(event) => setStudy({ ...study, required_product_id: event.target.value ? Number(event.target.value) : null })}>
                    <option value="">بدون محصول الزامی</option>
                    {menu.products.map((product) => <option key={product.id} value={product.id}>{product.name}</option>)}
                  </select>
                </label>
                <fieldset className="duration-options">
                  <legend>مدت‌های مجاز</legend>
                  {[120, 180, 240].map((duration) => (
                    <label key={duration}>
                      <input
                        type="checkbox"
                        checked={study.allowed_durations_minutes.includes(duration)}
                        onChange={(event) => setStudy({
                          ...study,
                          allowed_durations_minutes: event.target.checked
                            ? [...study.allowed_durations_minutes, duration].sort((a, b) => a - b)
                            : study.allowed_durations_minutes.filter((value) => value !== duration),
                        })}
                      />
                      {duration / 60} ساعت
                    </label>
                  ))}
                </fieldset>
                <div className="settings-two-column">
                  <label className="field-label">شروع مجاز
                    <input type="time" value={study.allowed_start_time} onChange={(event) => setStudy({ ...study, allowed_start_time: event.target.value })} required />
                  </label>
                  <label className="field-label">پایان مجاز
                    <input type="time" value={study.allowed_end_time} onChange={(event) => setStudy({ ...study, allowed_end_time: event.target.value })} required />
                  </label>
                </div>
                <label className="field-label">ظرفیت هم‌زمان
                  <input type="number" min="1" max="500" value={study.max_concurrent_sessions} onChange={(event) => setStudy({ ...study, max_concurrent_sessions: Number(event.target.value) })} required />
                </label>
                <p className="settings-help">کد وای‌فای فعلاً توسط آداپتور Mock تولید می‌شود و به روتر واقعی متصل نیست.</p>
                <button className="button button-dark button-wide" type="submit" disabled={busy || study.allowed_durations_minutes.length === 0}>ذخیره قوانین استادی‌مود</button>
              </form>

              <form className="settings-card" onSubmit={(event) => void saveLoyalty(event)}>
                <p className="eyebrow">باشگاه مشتریان</p>
                <h2>قوانین امتیاز و پاداش</h2>
                <label className="study-toggle">
                  <input type="checkbox" checked={loyalty.enabled} onChange={(event) => setLoyalty({ ...loyalty, enabled: event.target.checked })} />
                  <span><strong>فعال‌سازی امتیازدهی</strong><small>امتیاز پس از تأیید معتبر گارسون</small></span>
                </label>
                <label className="field-label">امتیاز برای هر سفارش تأییدشده
                  <input type="number" min="0" max="10000" value={loyalty.points_per_confirmed_order} onChange={(event) => setLoyalty({ ...loyalty, points_per_confirmed_order: Number(event.target.value) })} required />
                </label>
                <div className="settings-two-column">
                  <label className="field-label">آستانه نقره‌ای
                    <input type="number" min="0" value={loyalty.silver_threshold} onChange={(event) => setLoyalty({ ...loyalty, silver_threshold: Number(event.target.value) })} required />
                  </label>
                  <label className="field-label">آستانه طلایی
                    <input type="number" min={loyalty.silver_threshold} value={loyalty.gold_threshold} onChange={(event) => setLoyalty({ ...loyalty, gold_threshold: Number(event.target.value) })} required />
                  </label>
                </div>
                <label className="study-toggle">
                  <input type="checkbox" checked={loyalty.rewards_enabled} onChange={(event) => setLoyalty({ ...loyalty, rewards_enabled: event.target.checked })} />
                  <span><strong>فعال‌سازی بازخرید پاداش</strong><small>کسر امتیاز در تراکنش اتمیک و با کلید یکتا</small></span>
                </label>
                <p className="settings-help">عضویت مشتری اختیاری است و بدون رضایت صریح و تأیید OTP ایجاد نمی‌شود.</p>
                <button className="button button-dark button-wide" type="submit" disabled={busy}>ذخیره قوانین باشگاه</button>
              </form>
            </div>
          )}
        </section>
      )}
    </main>
  );
}

function ClubPanel({ onBack }: { onBack: () => void }) {
  const [phone, setPhone] = useState("");
  const [code, setCode] = useState("");
  const [consent, setConsent] = useState(false);
  const [otpRequested, setOtpRequested] = useState<OtpRequest | null>(null);
  const [account, setAccount] = useState<ClubAccount | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);

  const refreshAccount = async () => {
    const data = await publicJson<ClubAccount>("/api/v1/club/account");
    setAccount(data);
  };

  useEffect(() => {
    void refreshAccount().catch(() => undefined);
  }, []);

  const requestOtp = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const result = await publicJson<OtpRequest>("/api/v1/club/otp/request", {
        method: "POST",
        body: JSON.stringify({ phone, consent }),
      });
      setOtpRequested(result);
      setNotice("کد یک‌بارمصرف صادر شد. در محیط توسعه، کد آزمایشی در همین صفحه نمایش داده می‌شود.");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "درخواست کد ناموفق بود.");
    } finally {
      setBusy(false);
    }
  };

  const verifyOtp = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const result = await publicJson<ClubAccount>("/api/v1/club/otp/verify", {
        method: "POST",
        body: JSON.stringify({ phone, code }),
      });
      setAccount(result);
      setOtpRequested(null);
      setCode("");
      setNotice("عضویت با رضایت شما فعال شد.");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "تأیید کد ناموفق بود.");
    } finally {
      setBusy(false);
    }
  };

  const redeem = async (rewardId: number) => {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await publicJson("/api/v1/club/rewards/" + rewardId + "/redeem", {
        method: "POST",
        body: JSON.stringify({ idempotency_key: crypto.randomUUID() }),
      });
      await refreshAccount();
      setNotice("درخواست بازخرید ثبت شد.");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "بازخرید ناموفق بود.");
    } finally {
      setBusy(false);
    }
  };

  const deleteAccount = async () => {
    if (!window.confirm("حساب باشگاه، شماره موبایل و تاریخچه امتیازهای حساب حذف می‌شود. ادامه می‌دهید؟")) return;
    setBusy(true);
    setError("");
    try {
      const response = await fetch("/api/v1/club/account/delete", { method: "POST", credentials: "include" });
      if (!response.ok) throw new Error(await errorMessage(response));
      setAccount(null);
      setOtpRequested(null);
      setNotice("حساب باشگاه حذف شد.");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "حذف حساب ناموفق بود.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="staff-shell" dir="rtl">
      <header className="site-header staff-header">
        <a className="brand-lockup" href="/" onClick={(event) => { event.preventDefault(); onBack(); }}>
          <span className="brand-symbol">آ</span>
          <span><strong>کافه آرامش</strong><small>باشگاه مشتریان</small></span>
        </a>
        <button className="button button-outline button-small" onClick={onBack}>بازگشت به منو</button>
      </header>
      <section className="club-workspace">
        <div className="staff-page-heading">
          <div><p className="eyebrow">عضویت اختیاری</p><h1>انتخاب‌های تو،<br /><em>ارزشمندتر.</em></h1><p>با رضایت صریح عضو شو، برای درخواست‌های تأییدشده امتیاز بگیر و هر زمان خواستی حسابت را حذف کن.</p></div>
          {account && <div className="pending-counter"><strong>{money(account.points_balance)}</strong><span>امتیاز فعلی · {account.tier === "gold" ? "طلایی" : account.tier === "silver" ? "نقره‌ای" : "برنزی"}</span></div>}
        </div>
        {notice && <div className="notice notice-success">{notice}</div>}
        {error && <div className="notice notice-error">{error}</div>}
        {!account ? (
          <div className="club-auth-grid">
            <form className="settings-card" onSubmit={requestOtp}>
              <p className="eyebrow">مرحله اول</p><h2>شماره موبایل</h2>
              <label className="field-label">شماره موبایل ایران
                <input autoComplete="tel" inputMode="tel" value={phone} onChange={(event) => setPhone(event.target.value)} placeholder="۰۹۱۲۱۲۳۴۵۶۷" required />
              </label>
              <label className="consent-label">
                <input type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)} required />
                <span>با عضویت اختیاری در باشگاه و نگهداری شماره موبایلم برای این منظور موافقم. می‌توانم هر زمان حسابم را حذف کنم.</span>
              </label>
              <button className="button button-dark button-wide" type="submit" disabled={busy || !consent}>دریافت کد یک‌بارمصرف</button>
              {otpRequested?.debug_code && (
                <div className="dev-otp">
                  <span>کد آزمایشی توسعه</span><strong>{otpRequested.debug_code}</strong>
                  <small>در محیط تولید، این کد در پاسخ API نمایش داده نمی‌شود.</small>
                </div>
              )}
            </form>
            {otpRequested && (
              <form className="settings-card" onSubmit={verifyOtp}>
                <p className="eyebrow">مرحله دوم</p><h2>تأیید شماره</h2>
                <p className="settings-help">کد ۶ رقمی را وارد کن. کد کوتاه‌عمر و یک‌بارمصرف است.</p>
                <label className="field-label">کد یک‌بارمصرف
                  <input dir="ltr" inputMode="numeric" autoComplete="one-time-code" maxLength={6} pattern="[0-9]{6}" value={code} onChange={(event) => setCode(event.target.value.replace(/[^0-9]/g, "").slice(0, 6))} required />
                </label>
                <button className="button button-dark button-wide" type="submit" disabled={busy || code.length !== 6}>تأیید و عضویت</button>
              </form>
            )}
          </div>
        ) : (
          <div className="club-account-grid">
            <div className="settings-card">
              <p className="eyebrow">حساب باشگاه</p><h2>{account.full_name}</h2>
              <p className="settings-help">شماره ثبت‌شده: {account.phone_masked}</p>
              <div className="club-points"><strong>{money(account.points_balance)}</strong><span>امتیاز</span></div>
              <div className="club-tier">سطح فعلی: {account.tier === "gold" ? "طلایی" : account.tier === "silver" ? "نقره‌ای" : "برنزی"}</div>
              <button className="button button-outline button-wide" onClick={() => void deleteAccount()} disabled={busy}>حذف حساب و داده‌های شناسایی</button>
            </div>
            <div className="settings-card">
              <p className="eyebrow">پاداش‌ها</p><h2>امتیازهایت را استفاده کن</h2>
              {account.rewards.length === 0 ? <p className="settings-help">فعلاً پاداش فعالی تعریف نشده است.</p> : account.rewards.map((reward) => (
                <div className="reward-row" key={reward.id}>
                  <div><strong>{reward.name}</strong><small>{reward.description}</small><span>{money(reward.points_cost)} امتیاز</span></div>
                  <button className="button button-dark button-small" disabled={busy || account.points_balance < reward.points_cost} onClick={() => void redeem(reward.id)}>دریافت</button>
                </div>
              ))}
            </div>
            <div className="settings-card">
              <p className="eyebrow">تاریخچه امتیاز</p><h2>تراکنش‌های باشگاه</h2>
              {account.transactions.length === 0 ? <p className="settings-help">هنوز تراکنش امتیازی ثبت نشده است.</p> : account.transactions.map((item,index) => (
                <div className="history-row" key={index}><span>{item.reason === "confirmed_order" ? "سفارش تأییدشده" : item.reason.startsWith("reward_redemption:") ? "بازخرید پاداش" : item.reason}</span><strong className={item.points_delta < 0 ? "points-negative" : "points-positive"}>{item.points_delta > 0 ? "+" : ""}{money(item.points_delta)}</strong></div>
              ))}
            </div>
            <div className="settings-card">
              <p className="eyebrow">سفارش‌های قبلی</p><h2>تاریخچه درخواست‌ها</h2>
              {account.orders.length === 0 ? <p className="settings-help">سفارشی به حساب باشگاه متصل نشده است.</p> : account.orders.map((item) => (
                <div className="history-row" key={item.id}><span>#{money(item.id)} · {statusLabels[item.status] ?? item.status}<small>{new Date(item.created_at).toLocaleDateString("fa-IR")}</small></span><strong>{money(item.total_amount)} {unit(item.currency_unit)}</strong></div>
              ))}
            </div>
          </div>
        )}
      </section>
    </main>
  );
}
