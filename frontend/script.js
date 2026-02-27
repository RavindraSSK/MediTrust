
// MediTrust Frontend Script 


const API_BASE = "http://127.0.0.1:8000";

// Pages
const PAGE_SIGNUP = "signup.html";
const PAGE_LOGIN  = "index.html";
const PAGE_MEDI   = "meditrust.html";

// ---------- Helpers ----------
function $(id) {
  return document.getElementById(id);
}

function pickId(...ids) {
  for (const id of ids) {
    const el = document.getElementById(id);
    if (el) return el;
  }
  return null;
}

function show(el, isVisible) {
  if (!el) return;
  el.style.display = isVisible ? "block" : "none";
}

function setText(el, text) {
  if (!el) return;
  el.textContent = text;
}

function safeNumber(val) {
  const n = Number(val);
  return Number.isFinite(n) ? n : null;
}

function go(page) {
  window.location.href = page;
}

// ---------- Session (simple frontend flag) ----------
function isLoggedIn() {
  return localStorage.getItem("mt_logged_in") === "true";
}

function setLoggedIn(flag, email = "") {
  localStorage.setItem("mt_logged_in", flag ? "true" : "false");
  if (flag && email) localStorage.setItem("mt_user_email", email);
  if (!flag) localStorage.removeItem("mt_user_email");
}

// Make any logout button / onclick="logout()" work
window.logout = function () {
  setLoggedIn(false);
  go(PAGE_LOGIN);
};

// ---------- AUTH API (FastAPI) ----------
async function registerUser(fullName, email, password) {
  const res = await fetch(`${API_BASE}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ full_name: fullName, email, password }),
  });

  if (!res.ok) {
    const txt = await res.text();
    throw new Error(txt || `Register failed (${res.status})`);
  }

  // FastAPI returns: { ok: bool, message: str }
  return await res.json();
}

async function loginUser(email, password) {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  if (!res.ok) {
    const txt = await res.text();
    throw new Error(txt || `Login failed (${res.status})`);
  }

  // FastAPI returns: { ok: bool, message: str }
  return await res.json();
}

// ---------- RISK API ----------
async function assessRisk(fullName, age) {
  const res = await fetch(`${API_BASE}/assess`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ full_name: fullName, age }),
  });

  if (!res.ok) {
    const txt = await res.text();
    throw new Error(`Risk API error ${res.status}: ${txt}`);
  }
  return await res.json();
}

// ---------- MediTrust UI ----------
function renderRiskResult(data) {
  const riskLevelEl = pickId("riskLevel");
  const riskScoreEl = pickId("riskScore");

  const badgeEl   = pickId("riskBadge", "badge");
  const adviceEl  = pickId("riskAdvice", "note");
  const barEl     = pickId("riskBarFill", "bar");
  const resultSec = pickId("resultSection", "result");

  const riskLevel = data.risk_level || "-";
  const score = safeNumber(data.risk_score);

  setText(riskLevelEl, riskLevel);
  setText(riskScoreEl, score !== null ? `${Math.round(score * 100)}%` : "-");

  if (badgeEl) {
    badgeEl.textContent = riskLevel === "High" ? "Needs attention" : "Low concern";
    badgeEl.className = riskLevel === "High" ? "badge badge-high" : "badge badge-low";
  }

  if (adviceEl) {
    adviceEl.textContent =
      riskLevel === "High"
        ? "Consider scheduling a checkup. If you have symptoms or concerns, seek medical guidance."
        : "Maintain healthy habits and follow routine checkups as recommended.";
  }

  if (barEl && score !== null) {
    const pct = Math.min(100, Math.max(0, Math.round(score * 100)));
    barEl.style.width = `${pct}%`;
  }

  // Your CSS uses .result.show and/or .result.visible
  if (resultSec) {
    resultSec.classList.add("show");
    requestAnimationFrame(() => resultSec.classList.add("visible"));
  }
}

function renderError(msg) {
  const errEl = pickId("errorBox", "alert");
  if (!errEl) {
    alert(msg);
    return;
  }
  errEl.textContent = msg;
  show(errEl, true);
}

function clearError() {
  const errEl = pickId("errorBox", "alert");
  if (!errEl) return;
  errEl.textContent = "";
  show(errEl, false);
}

// ---------- Page initializers ----------
function initSignupPage() {
  const form = $("signupForm");
  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const first = ($("firstName")?.value || "").trim();
    const last  = ($("lastName")?.value || "").trim();
    const email = ($("email")?.value || "").trim();
    const pass  = ($("password")?.value || "").trim();
    const conf  = ($("confirmPassword")?.value || "").trim();

    if (!first || !last || !email || !pass || !conf) {
      alert("Please fill all fields.");
      return;
    }
    if (pass !== conf) {
      alert("Passwords do not match.");
      return;
    }

    try {
      const out = await registerUser(`${first} ${last}`, email, pass);

      if (!out.ok) {
        alert(out.message);
        return;
      }

      alert(out.message); // "Account created successfully."
      go(PAGE_LOGIN);
    } catch (err) {
      alert("Registration failed: " + (err?.message || err));
    }
  });
}

function initLoginPage() {
  const form = $("loginForm");
  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const email = ($("email")?.value || "").trim();
    const pass  = ($("password")?.value || "").trim();

    if (!email || !pass) {
      alert("Enter email and password.");
      return;
    }

    try {
      const out = await loginUser(email, pass);

      if (!out.ok) {
        alert(out.message);
        return;
      }

      setLoggedIn(true, email);
      go(PAGE_MEDI);
    } catch (err) {
      alert("Login failed: " + (err?.message || err));
    }
  });
}

function initMediTrustPage() {
  if (!isLoggedIn()) {
    go(PAGE_LOGIN);
    return;
  }

  $("logoutBtn")?.addEventListener("click", () => window.logout());

  const nameEl = pickId("patientName", "name");
  const ageEl  = pickId("patientAge", "age");
  const btn    = pickId("checkRiskBtn", "btn");
  const form   = pickId("riskForm"); // may be null

  const handler = async (e) => {
    if (e) e.preventDefault();
    clearError();

    const name = (nameEl?.value || "").trim();
    const age = safeNumber(ageEl?.value);

    if (!name) return renderError("Please enter patient name.");
    if (age === null || age < 1 || age > 120) return renderError("Please enter a valid age (1–120).");

    if (btn) {
      btn.disabled = true;
      btn.textContent = "Checking...";
    }

    try {
      const data = await assessRisk(name, age);
      renderRiskResult(data);
    } catch (err) {
      console.error(err);
      renderError("Unable to reach API. Make sure FastAPI is running on port 8000.");
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.textContent = "Check Risk";
      }
    }
  };

  form?.addEventListener("submit", handler);
  btn?.addEventListener("click", handler);
}

// ---------- Detect current page ----------
document.addEventListener("DOMContentLoaded", () => {
  clearError();

  const file = (window.location.pathname.split("/").pop() || "").toLowerCase();

  if (file === PAGE_SIGNUP) initSignupPage();
  else if (file === PAGE_MEDI) initMediTrustPage();
  else initLoginPage();
});