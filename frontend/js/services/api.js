<<<<<<< HEAD
import { API_BASE } from "../config.js";

export async function registerUser(fullName, email, password, role = "Doctor", hospitalName = "") {
  const res = await fetch(`${API_BASE}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      full_name: fullName,
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

export async function assessRisk(fullName, age) {
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
=======
import { API_BASE } from "../config.js";

export async function registerUser(fullName, email, password, role = "Doctor", hospitalName = "") {
  const res = await fetch(`${API_BASE}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      full_name: fullName,
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

export async function assessRisk(fullName, age) {
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
>>>>>>> 942fa41 (Restore frontend files from VS Code timeline)
}