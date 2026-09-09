import { useBodyClass } from "../hooks/useBodyClass.js";

export default function AuthShell({ title, subtitle, children }) {
  useBodyClass("login-page");
  return (
    <>
      <div className="page-bg" />
      <div className="page-overlay" />
      <main className="page-shell">
        <section className="login-card">
          <header className="login-header">
            <h1 className="brand-title">MediTrust</h1>
            <div className="header-divider" />
            <h2 className="portal-title">{title}</h2>
            {subtitle ? <p className="portal-subtitle">{subtitle}</p> : null}
          </header>
          {children}
        </section>
      </main>
    </>
  );
}
