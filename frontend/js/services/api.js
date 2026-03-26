import { API_BASE } from "../config.js";

export async function registerUser(fullName, email, password) {
  const res = await fetch(`${API_BASE}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ full_name: fullName, email, password }),
  });

  if (!res.ok) {
    const txt = await res.text();
    throw new Error(txt || `Register failed (${res.status})`);
  }

  return await res.json();
}

export async function loginUser(email, password) {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  if (!res.ok) {
    const txt = await res.text();
    throw new Error(txt || `Login failed (${res.status})`);
  }

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
}