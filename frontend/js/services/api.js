const LOCAL_FRONTEND_ORIGINS = new Set([
  "http://127.0.0.1:5500",
  "http://localhost:5500",
  "http://127.0.0.1:5501",
  "http://localhost:5501",
  "http://127.0.0.1:5173",
  "http://localhost:5173",
]);

const PRODUCTION_API_BASE =
  typeof window !== "undefined"
    ? (
        window.location.hostname === "meditrust.ddns.net"
          ? "https://meditrust.ddns.net/api"
          : `${window.location.origin}/api`
      )
    : "https://meditrust.ddns.net/api";

export const API_BASE =
  typeof window !== "undefined" && LOCAL_FRONTEND_ORIGINS.has(window.location.origin)
    ? "http://127.0.0.1:8001"
    : PRODUCTION_API_BASE;

async function readAuthResponse(res, fallbackMessage = "Request failed.") {
  const raw = await res.text();
  let data = {};
  const trimmed = raw.trim();
  const looksLikeHtml =
    trimmed.startsWith("<!DOCTYPE html") ||
    trimmed.startsWith("<html") ||
    trimmed.startsWith("<HTML");

  if (raw) {
    try {
      data = JSON.parse(raw);
    } catch {
      data = {};
    }
  }

  if (!res.ok) {
    return {
      ok: false,
      message:
        data.message ||
        data.detail ||
        (!looksLikeHtml ? trimmed : "") ||
        fallbackMessage,
    };
  }

  return Object.keys(data).length ? data : { ok: true };
}

export async function registerUser(firstName, lastName, email, password, role = "Doctor", hospitalName = "") {
  const res = await fetch(`${API_BASE}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      first_name: firstName,
      last_name: lastName,
      email,
      password,
      role,
      hospital_name: hospitalName
    }),
  });

  return await readAuthResponse(res, "Registration failed.");
}

export async function loginUser(email, password) {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  return await readAuthResponse(res, "Login failed.");
}

export async function requestPasswordReset(email) {
  const res = await fetch(`${API_BASE}/auth/request-reset`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });

  return await readAuthResponse(res, "Unable to request reset code.");
}

export async function verifyResetCode(email, code) {
  const res = await fetch(`${API_BASE}/auth/verify-reset-code`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, code }),
  });

  return await readAuthResponse(res, "Unable to verify reset code.");
}

export async function resetPassword(email, newPassword) {
  const res = await fetch(`${API_BASE}/auth/reset-password`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email,
      new_password: newPassword
    }),
  });

  return await readAuthResponse(res, "Unable to reset password.");
}

export async function changePassword(email, currentPassword, newPassword) {
  const res = await fetch(`${API_BASE}/auth/change-password`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email,
      current_password: currentPassword,
      new_password: newPassword
    }),
  });

  return await readAuthResponse(res, "Unable to change password.");
}

export async function assessRisk(firstName, lastName, age) {
  const res = await fetch(`${API_BASE}/assess`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ first_name: firstName, last_name: lastName, age }),
  });

  if (!res.ok) {
    const txt = await res.text();
    throw new Error(`Risk API error ${res.status}: ${txt}`);
  }

  return await res.json();
}

export async function predictRisk(payload) {
  const res = await fetch(`${API_BASE}/predict`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const txt = await res.text();
    throw new Error(`Predict API error ${res.status}: ${txt}`);
  }

  return await res.json();
}
