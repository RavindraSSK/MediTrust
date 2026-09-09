import { Link, useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthContext.jsx";
import { useBodyClass } from "../hooks/useBodyClass.js";

export default function DashboardShell({ title, subtitle, userLabel, links = [], children, fixed = false }) {
  useBodyClass(fixed ? "dashboard-page admin-fixed-page" : "dashboard-page");
  const { logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/", { replace: true });
  };

  return (
    <>
      <div className="page-bg" />
      <div className="page-overlay" />
      <main className="dashboard-shell">
        <section className="dashboard-card">
          <header className="dashboard-header">
            <div>
              <h1 className="dashboard-title">{title}</h1>
              {subtitle ? <p className="dashboard-subtitle">{subtitle}</p> : null}
            </div>
            <div className="dashboard-user-box">
              <span>{userLabel}</span>
              {links.map((link) => (
                <Link key={link.to} className="mini-btn" to={link.to}>
                  {link.label}
                </Link>
              ))}
              <button id="logoutBtn" className="mini-btn" type="button" onClick={handleLogout}>
                Logout
              </button>
            </div>
          </header>
          {children}
        </section>
      </main>
    </>
  );
}
