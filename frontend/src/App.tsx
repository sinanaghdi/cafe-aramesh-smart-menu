import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";

type View = "menu" | "staff";
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
  items: OrderItem[];
};
type AuthState = {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  user: { id: number; cafe_id: number; full_name: string; role: string; email: string | null };
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
  if (!headers.has("Content-Type")) headers.set("Content-Type", "application/json");
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
  const [submittedOrder, setSubmittedOrder] = useState<OrderData | null>(null);

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
          setLoadError(error instanceof Error ? error.message : "بارگذاری منو ناموفق بود.");
        }
      });
    return () => controller.abort();
  }, [tableNumber]);

  useEffect(() => {
    if (!submittedOrder) return;
    const controller = new AbortController();
    const timer = window.setInterval(async () => {
      try {
        const latest = await publicJson<OrderData>(
          `/api/v1/orders/${submittedOrder.id}`,
          { signal: controller.signal },
        );
        setSubmittedOrder((current) =>
          current && current.id === latest.id ? { ...current, ...latest } : current,
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
      const order = await publicJson<OrderData>("/api/v1/orders", {
        method: "POST",
        body: JSON.stringify({
          table_number: tableNumber,
          items: cartItems.map((product) => ({
            product_id: product.id,
            quantity: cart[product.id],
          })),
        }),
      });
      setSubmittedOrder(order);
      setCart({});
      setCartOpen(false);
    } catch (error) {
      setOrderError(error instanceof Error ? error.message : "ثبت درخواست ناموفق بود.");
    } finally {
      setSendingOrder(false);
    }
  };

  if (view === "staff") {
    return <StaffPanel onBack={() => setView("menu")} />;
  }

  return (
    <main className="app-shell" dir="rtl">
      <header className="site-header">
        <a className="brand-lockup" href="/" aria-label="کافه آرامش">
          <span className="brand-symbol" aria-hidden="true">آ</span>
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
          <button className="button button-dark button-small" onClick={() => setView("staff")}>
            پنل گارسون
          </button>
          <button className="cart-trigger" onClick={() => setCartOpen(true)} aria-label={`سبد درخواست، ${cartCount} آیتم`}>
            سبد <span>{money(cartCount)}</span>
          </button>
        </nav>
      </header>

      <section className="menu-hero">
        <div className="hero-copy">
          <p className="eyebrow"><span /> منوی کافه آرامش</p>
          <h1>امروز دلت<br /><em>چه طعمی می‌خواهد؟</em></h1>
          <p className="hero-intro">
            انتخابت را با حال‌وهوایت هماهنگ کن. نوشیدنی‌های تازه، طعم‌های روشن
            و انتخاب‌هایی برای لحظه‌ای که مال خودت است.
          </p>
          <a className="text-link" href="#menu-list">دیدن منو <span aria-hidden="true">←</span></a>
        </div>
        <div className="hero-art" aria-label="نمای گرافیکی فنجان قهوه">
          <div className="art-orbit orbit-one" />
          <div className="art-orbit orbit-two" />
          <div className="coffee-saucer" />
          <div className="coffee-cup"><span className="coffee-swirl" /></div>
          <div className="cup-handle" />
          <span className="art-stamp">SLOW<br />MOMENT</span>
          <span className="art-caption">هر فنجان، یک مکث</span>
        </div>
      </section>

      <section className="menu-section" id="menu-list">
        <div className="section-heading">
          <div>
            <p className="eyebrow">با حوصله انتخاب کن</p>
            <h2>منوی امروز</h2>
          </div>
          <span className="result-count">{money(filteredProducts.length)} انتخاب</span>
        </div>
        {tableNumber === null && (
          <div className="notice notice-soft">
            برای ثبت درخواست، منو را با QR روی میز باز کن. در حال حاضر فقط می‌توانی منو را ببینی.
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
          {query && <button onClick={() => setQuery("")} aria-label="پاک کردن جست‌وجو">×</button>}
        </label>
        <div className="category-scroll" aria-label="دسته‌بندی محصولات">
          <button
            className={activeCategory === "all" ? "category-chip active" : "category-chip"}
            onClick={() => setActiveCategory("all")}
          >همه</button>
          {(menu?.categories ?? []).map((category) => (
            <button
              key={category.id}
              className={activeCategory === category.id ? "category-chip active" : "category-chip"}
              onClick={() => setActiveCategory(category.id)}
            >{category.name}</button>
          ))}
        </div>

        {loadError && <div className="notice notice-error">{loadError}</div>}
        {!menu && !loadError && <div className="loading-panel">در حال آماده‌کردن منوی کافه...</div>}
        {menu && (
          <div className="product-grid">
            {filteredProducts.map((product, index) => {
              const quantity = cart[product.id] ?? 0;
              const caffeine = product.tags.find((tag) => tag.key === "caffeine")?.value;
              const taste = product.tags.find((tag) => tag.key === "taste")?.value;
              return (
                <article className="product-card" key={product.id}>
                  <div className={`product-art product-art-${index % 5}`}>
                    <span className="product-art-index">{String(index + 1).padStart(2, "0")}</span>
                    <span className="product-art-ring" />
                    <span className="product-art-cup">{["◒", "◉", "◍", "◌", "◓"][index % 5]}</span>
                    {product.is_featured && <span className="feature-ribbon">پیشنهاد کافه</span>}
                  </div>
                  <div className="product-content">
                    <div className="product-meta">
                      <span>{product.category_name}</span>
                      {caffeine === "none" && <span className="tag-muted">بدون کافئین</span>}
                      {caffeine === "high" && <span className="tag-muted">کافئین بالا</span>}
                    </div>
                    <h3>{product.name}</h3>
                    <p className="product-description">{product.description}</p>
                    {taste && <p className="taste-line">حال‌وهوا: {tagLabels[taste] ?? taste}</p>}
                    <div className="product-footer">
                      <span className="price">{money(product.price_amount)} <small>{unit(menu.currency_unit)}</small></span>
                      {quantity === 0 ? (
                        <button
                          className="add-button"
                          disabled={!product.is_available}
                          onClick={() => changeQuantity(product.id, 1)}
                          aria-label={`افزودن ${product.name} به سبد`}
                        >+</button>
                      ) : (
                        <div className="quantity-control" aria-label={`تعداد ${product.name}`}>
                          <button onClick={() => changeQuantity(product.id, 1)} aria-label="افزایش تعداد">+</button>
                          <span>{money(quantity)}</span>
                          <button onClick={() => changeQuantity(product.id, -1)} aria-label="کاهش تعداد">−</button>
                        </div>
                      )}
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
        )}
        {menu && filteredProducts.length === 0 && <div className="empty-state">چیزی با این مشخصات پیدا نکردیم. عبارت دیگری را امتحان کن.</div>}
      </section>

      <footer className="site-footer">
        <div className="footer-brand"><span className="brand-symbol">آ</span><strong>کافه آرامش</strong></div>
        <span>با احترام به انتخاب و زمان شما</span>
        <span>منوی دیجیتال · نسخه اولیه</span>
      </footer>

      {cartOpen && (
        <div className="drawer-backdrop" role="presentation" onMouseDown={(event) => {
          if (event.target === event.currentTarget) setCartOpen(false);
        }}>
          <section className="cart-drawer" role="dialog" aria-modal="true" aria-labelledby="cart-title">
            <header className="drawer-header">
              <div><p className="eyebrow">قبل از ثبت درخواست</p><h2 id="cart-title">سبد انتخابت</h2></div>
              <button className="icon-button" onClick={() => setCartOpen(false)} aria-label="بستن سبد">×</button>
            </header>
            {cartItems.length === 0 ? (
              <div className="empty-state">سبدت هنوز خالی است. از منو چیزی انتخاب کن.</div>
            ) : (
              <div className="cart-lines">
                {cartItems.map((product) => (
                  <div className="cart-line" key={product.id}>
                    <div className="cart-line-icon">◒</div>
                    <div className="cart-line-info">
                      <strong>{product.name}</strong>
                      <span>{money(product.price_amount)} {unit(menu?.currency_unit)}</span>
                      <div className="quantity-control">
                        <button onClick={() => changeQuantity(product.id, 1)} aria-label="افزایش تعداد">+</button>
                        <span>{money(cart[product.id] ?? 0)}</span>
                        <button onClick={() => changeQuantity(product.id, -1)} aria-label="کاهش تعداد">−</button>
                      </div>
                    </div>
                    <strong className="line-total">{money(product.price_amount * (cart[product.id] ?? 0))}</strong>
                  </div>
                ))}
              </div>
            )}
            <div className="cart-summary">
              <div><span>جمع نمایشی سبد</span><strong>{money(cartTotal)} {unit(menu?.currency_unit)}</strong></div>
              <p>مبلغ نهایی هنگام ثبت درخواست در سرور دوباره محاسبه می‌شود؛ پرداخت آنلاین انجام نمی‌شود.</p>
              {!tableNumber && <p className="inline-error">برای ثبت درخواست باید از QR میز وارد شوی.</p>}
              {orderError && <p className="inline-error">{orderError}</p>}
              <button
                className="button button-dark button-wide"
                disabled={!tableNumber || cartItems.length === 0 || sendingOrder}
                onClick={submitOrder}
              >{sendingOrder ? "در حال ثبت..." : "ثبت درخواست برای گارسون"}</button>
            </div>
          </section>
        </div>
      )}

      {submittedOrder && (
        <div className="drawer-backdrop receipt-backdrop">
          <section className="receipt-card" role="dialog" aria-modal="true" aria-labelledby="receipt-title">
            <button className="icon-button receipt-close" onClick={() => setSubmittedOrder(null)} aria-label="بستن رسید">×</button>
            <div className="receipt-check">✓</div>
            <p className="eyebrow">درخواست ثبت شد</p>
            <h2 id="receipt-title">حالا نوبت گارسون است</h2>
            <p className="receipt-copy">برای تأیید نهایی، گارسون به میزت می‌آید. کد زیر را فقط به او نشان بده.</p>
            {submittedOrder.code && (
              <div className="verification-code" aria-label="کد تأیید سفارش">
                {submittedOrder.code.split("").map((digit, index) => <span key={index}>{digit}</span>)}
              </div>
            )}
            <div className="receipt-details">
              <span>شماره درخواست</span><strong>#{money(submittedOrder.id)}</strong>
              <span>میز</span><strong>{money(submittedOrder.table_number)}</strong>
              <span>وضعیت</span><strong><span className="status-pill">{statusLabels[submittedOrder.status] ?? submittedOrder.status}</span></strong>
              <span>مبلغ</span><strong>{money(submittedOrder.total_amount ?? 0)} {unit(submittedOrder.currency_unit)}</strong>
            </div>
            {submittedOrder.code_expires_at && submittedOrder.status === "pending_confirmation" && (
              <p className="receipt-warning">کد تا {new Date(submittedOrder.code_expires_at).toLocaleTimeString("fa-IR", { hour: "2-digit", minute: "2-digit" })} اعتبار دارد. این کد فقط همین بار نمایش داده می‌شود.</p>
            )}
            <button className="button button-dark button-wide" onClick={() => setSubmittedOrder(null)}>متوجه شدم</button>
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
        setStaffError(error instanceof Error ? error.message : "بارگذاری سفارش‌ها ناموفق بود.");
      });
      pollTimer = window.setInterval(() => {
        void loadOrders().catch((error: unknown) => {
          setStaffError(error instanceof Error ? error.message : "بارگذاری سفارش‌ها ناموفق بود.");
        });
      }, 5000);
    };

    const streamOrders = async () => {
      try {
        const response = await authedFetch("/api/v1/staff/events", { signal: controller.signal });
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
            const dataLine = block.split("\n").find((line) => line.startsWith("data: "));
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
      const response = await authedFetch(`/api/v1/staff/orders/${orderId}/confirm`, {
        method: "POST",
        body: JSON.stringify({ code: codes[orderId] ?? "" }),
      });
      if (!response.ok) throw new Error(await errorMessage(response));
      setCodes((current) => ({ ...current, [orderId]: "" }));
      setNotice(`درخواست شماره ${money(orderId)} تأیید شد.`);
      await loadOrders();
    } catch (error) {
      setStaffError(error instanceof Error ? error.message : "تأیید سفارش ناموفق بود.");
    } finally {
      setBusyOrder(null);
    }
  };

  const changeOrderStatus = async (orderId: number, status: "preparing" | "served" | "cancelled") => {
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
      const response = await authedFetch(`/api/v1/staff/orders/${orderId}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status, reason }),
      });
      if (!response.ok) throw new Error(await errorMessage(response));
      setNotice("وضعیت درخواست به‌روز شد.");
      await loadOrders();
    } catch (error) {
      setStaffError(error instanceof Error ? error.message : "تغییر وضعیت ناموفق بود.");
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

  const displayedOrders = orders.filter((order) => filter === "all" || order.status === filter);
  const pendingCount = orders.filter((order) => order.status === "pending_confirmation").length;

  return (
    <main className="staff-shell" dir="rtl">
      <header className="site-header staff-header">
        <a className="brand-lockup" href="/" onClick={(event) => { event.preventDefault(); onBack(); }}>
          <span className="brand-symbol">آ</span>
          <span><strong>کافه آرامش</strong><small>میز خدمت کارکنان</small></span>
        </a>
        <div className="header-actions">
          <span className="staff-only-label">پنل عملیاتی سفارش</span>
          <button className="button button-outline button-small" onClick={onBack}>بازگشت به منو</button>
          {auth && <button className="button button-dark button-small" onClick={() => void logout()}>خروج</button>}
        </div>
      </header>

      {!auth ? (
        <section className="staff-login-layout">
          <div className="staff-intro">
            <p className="eyebrow"><span /> میز خدمت</p>
            <h1>سفارش‌ها را<br /><em>با دقت دنبال کن.</em></h1>
            <p>تأیید نهایی پس از تطبیق کد با مشتری انجام می‌شود. این پنل فقط برای عملیات سفارش است و آمار فروش یا درآمد نمایش نمی‌دهد.</p>
          </div>
          <form className="login-card" onSubmit={login}>
            <p className="eyebrow">ورود کارکنان</p>
            <h2>ورود به پنل گارسون</h2>
            <label className="field-label">ایمیل سازمانی
              <input type="email" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} required />
            </label>
            <label className="field-label">گذرواژه
              <input type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required />
            </label>
            {authError && <p className="inline-error">{authError}</p>}
            <button className="button button-dark button-wide" type="submit">ورود امن</button>
            <p className="login-footnote">محیط توسعه محلی: اطلاعات ورود نمونه در فایل README ثبت شده است.</p>
          </form>
        </section>
      ) : (
        <section className="staff-workspace">
          <div className="staff-page-heading">
            <div><p className="eyebrow">نمای زنده سفارش‌ها</p><h1>سلام، {auth.user.full_name}</h1><p>درخواست‌ها را ببین، کد را تطبیق بده و فقط وضعیت مجاز را تغییر بده.</p></div>
            <div className="pending-counter"><strong>{money(pendingCount)}</strong><span>در انتظار تأیید</span></div>
          </div>
          <div className="staff-privacy-note"><span>●</span> دسترسی این نقش فقط به اطلاعات عملیاتی سفارش محدود است.</div>
          <div className="staff-filter-row">
            {[
              ["pending_confirmation", "در انتظار تأیید"],
              ["confirmed", "تأیید شده"],
              ["preparing", "در حال آماده‌سازی"],
              ["all", "همه"],
            ].map(([value, label]) => (
              <button key={value} className={filter === value ? "filter-button active" : "filter-button"} onClick={() => setFilter(value)}>{label}</button>
            ))}
            <button className="refresh-button" onClick={() => void loadOrders()}>↻ تازه‌سازی</button>
          </div>
          {notice && <div className="notice notice-success">{notice}</div>}
          {staffError && <div className="notice notice-error">{staffError}</div>}
          {displayedOrders.length === 0 ? (
            <div className="staff-empty"><span>◌</span><h2>درخواستی در این فهرست نیست</h2><p>در صورت ثبت درخواست جدید، فهرست به‌روزرسانی می‌شود.</p></div>
          ) : (
            <div className="staff-order-list">
              {displayedOrders.map((order) => (
                <article className="staff-order-card" key={order.id}>
                  <div className="staff-order-top">
                    <div><span className="order-reference">درخواست #{money(order.id)}</span><span className="status-pill">{statusLabels[order.status] ?? order.status}</span></div>
                    <strong className="table-badge">میز {money(order.table_number)}</strong>
                  </div>
                  <div className="staff-order-items">
                    {order.items.map((item, index) => <div key={index}><span>{item.product_name}</span><strong>× {money(item.quantity)}</strong></div>)}
                  </div>
                  {order.notes && <p className="staff-note">یادداشت مشتری: {order.notes}</p>}
                  <div className="staff-order-bottom">
                    <span className="order-time">{new Date(order.created_at).toLocaleString("fa-IR", { hour: "2-digit", minute: "2-digit" })}</span>
                    <div className="staff-order-actions">
                      {order.status === "pending_confirmation" && (
                        <form className="confirm-inline" onSubmit={(event) => { event.preventDefault(); void confirmOrder(order.id); }}>
                          <input
                            inputMode="numeric"
                            autoComplete="off"
                            maxLength={4}
                            pattern="[0-9]{3,4}"
                            aria-label={`کد تأیید درخواست ${order.id}`}
                            placeholder="کد ۴ رقمی"
                            value={codes[order.id] ?? ""}
                            onChange={(event) => setCodes((current) => ({ ...current, [order.id]: event.target.value.replace(/[^0-9]/g, "").slice(0, 4) }))}
                            required
                          />
                          <button className="button button-dark button-small" disabled={busyOrder === order.id}>تأیید کد</button>
                        </form>
                      )}
                      {order.status === "confirmed" && <button className="button button-dark button-small" disabled={busyOrder === order.id} onClick={() => void changeOrderStatus(order.id, "preparing")}>شروع آماده‌سازی</button>}
                      {order.status === "preparing" && <button className="button button-dark button-small" disabled={busyOrder === order.id} onClick={() => void changeOrderStatus(order.id, "served")}>تحویل شد</button>}
                      {["pending_confirmation", "confirmed", "preparing"].includes(order.status) && <button className="button-link-danger" disabled={busyOrder === order.id} onClick={() => void changeOrderStatus(order.id, "cancelled")}>لغو</button>}
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
