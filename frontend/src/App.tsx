import { useEffect, useState } from "react";

type ApiState = "checking" | "online" | "offline";

export default function App() {
  const [apiState, setApiState] = useState<ApiState>("checking");

  useEffect(() => {
    const controller = new AbortController();

    fetch("/api/health", { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error("API request failed");
        return response.json() as Promise<{ status: string }>;
      })
      .then((data) => setApiState(data.status === "ok" ? "online" : "offline"))
      .catch(() => {
        if (!controller.signal.aborted) setApiState("offline");
      });

    return () => controller.abort();
  }, []);

  const statusText = {
    checking: "در حال بررسی اتصال",
    online: "اتصال سرویس برقرار است",
    offline: "سرویس در دسترس نیست",
  }[apiState];

  return (
    <main className="page-shell" dir="rtl">
      <header className="topbar">
        <a className="brand" href="/" aria-label="کافه آرامش، صفحه اصلی">
          <span className="brand-mark" aria-hidden="true">
            آ
          </span>
          <span>
            <strong>کافه آرامش</strong>
            <small>منوی هوشمند</small>
          </span>
        </a>
        <span className="topbar-note">تجربه‌ای برای انتخاب آگاهانه</span>
      </header>

      <section className="hero" aria-labelledby="hero-title">
        <div className="hero-copy">
          <p className="eyebrow">یک مکث برای خودت</p>
          <h1 id="hero-title">
            طعم خوب،
            <br />
            <em>انتخابِ تو.</em>
          </h1>
          <p className="hero-description">
            اینجا نقطه شروع منوی هوشمند کافه آرامش است؛ منویی فارسی، ساده و
            مشتری‌محور که برای انتخاب بهتر طراحی می‌شود.
          </p>
          <div
            className={`service-status service-status--${apiState}`}
            role="status"
          >
            <span className="status-dot" aria-hidden="true" />
            {statusText}
          </div>
        </div>

        <aside className="hero-card" aria-label="وضعیت نسخه">
          <span className="card-kicker">نسخه توسعه</span>
          <div className="cup-mark" aria-hidden="true">
            ◒
          </div>
          <h2>یک تجربه آرام‌تر</h2>
          <p>
            منو، پیشنهادهای مرتبط و تأیید حضوری سفارش در فازهای بعدی به این
            زیرساخت اضافه می‌شوند.
          </p>
          <span className="card-rule" />
          <span className="card-footnote">کافه آرامش · بابلسر</span>
        </aside>
      </section>

      <footer className="footer">
        <span>ساخته‌شده با احترام به انتخاب و زمان شما</span>
        <span>نسخه زیرساخت · هنوز سفارش واقعی ثبت نمی‌شود</span>
      </footer>
    </main>
  );
}
