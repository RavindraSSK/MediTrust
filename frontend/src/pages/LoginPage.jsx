import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { dashboardPathForRole, useAuth } from "../auth/AuthContext.jsx";
import AuthShell from "../components/AuthShell.jsx";
import FormMessage from "../components/FormMessage.jsx";
import PasswordField from "../components/PasswordField.jsx";
import { errorMessage } from "../lib/format.js";

export default function LoginPage() {
  const { login, isAuthenticated, dashboardPath } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (isAuthenticated) navigate(dashboardPath, { replace: true });
  }, [isAuthenticated, dashboardPath, navigate]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setMessage("");
    if (!email.trim() || !password.trim()) {
      setMessage("Please enter your work email and password.");
      return;
    }
    setBusy(true);
    try {
      const result = await login(email.trim(), password.trim());
      if (!result.ok) {
        setMessage(result.message || "Invalid email or password.");
        return;
      }
      navigate(dashboardPathForRole(result.user.role), { replace: true });
    } catch (error) {
      setMessage(error?.status ? errorMessage(error) : "Unable to connect to the server. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell title="Clinician Portal" subtitle="Secure clinical access for patient cardiovascular risk assessment">
      <form id="loginForm" className="login-form" noValidate onSubmit={handleSubmit}>
        <div className="field">
          <label htmlFor="email">Work Email</label>
          <div className="input-wrap">
            <span className="input-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none">
                <path d="M4 6H20V18H4V6Z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
                <path d="M4 7L12 13L20 7" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </span>
            <input
              type="email"
              id="email"
              name="email"
              placeholder="Enter your work email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              autoComplete="username"
              required
            />
          </div>
        </div>

        <PasswordField id="password" label="Password" value={password} onChange={setPassword} withIcon />

        <div className="utility-row">
          <label className="remember">
            <input type="checkbox" id="rememberMe" defaultChecked />
            <span>Remember me</span>
          </label>
          <Link to="/forgot-password" className="text-link">
            Forgot Password?
          </Link>
        </div>

        <FormMessage id="loginMessage" text={message} />

        <button type="submit" id="loginBtn" className="signin-btn" disabled={busy}>
          {busy ? "Signing In..." : "Sign In"}
        </button>
      </form>

      <div className="section-line" />
      <div className="secondary-row">
        <p>
          New to MediTrust?{" "}
          <Link to="/signup" className="text-link strong-link">
            Create Clinician Account
          </Link>
        </p>
      </div>
      <div className="section-line" />
      <div className="trust-row">
        <p>Authorized healthcare personnel only</p>
        <p>Session monitoring enabled</p>
      </div>
      <div className="section-line" />
      <div className="demo-row">
        <Link to="/demo" className="explore-demo">
          Explore Demo
        </Link>
      </div>
    </AuthShell>
  );
}
