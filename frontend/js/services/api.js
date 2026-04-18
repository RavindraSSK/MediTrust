import { API_BASE } from "../config.js";

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

  return await res.json();
}

export async function loginUser(email, password) {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  return await res.json();
}

export async function requestPasswordReset(email) {
  const res = await fetch(`${API_BASE}/auth/request-reset`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });

  return await res.json();
}

export async function verifyResetCode(email, code) {
  const res = await fetch(`${API_BASE}/auth/verify-reset-code`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, code }),
  });

  return await res.json();
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

  return await res.json();
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

  return await res.json();
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
