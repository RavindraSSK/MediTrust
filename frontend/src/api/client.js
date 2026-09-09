/**
 * Minimal fetch wrapper for the MediTrust API.
 *
 * - Resolves the API base URL (VITE_API_BASE at build time, otherwise the
 *   local backend during development or `<origin>/api` behind nginx).
 * - Attaches the JWT bearer token stored by the AuthProvider.
 * - Normalises errors into ApiError(status, message, errors[]).
 * - Broadcasts "meditrust:unauthorized" so the AuthProvider can sign out when a
 *   token expires.
 */

const LOCAL_DEV_ORIGINS = new Set([
  "http://127.0.0.1:5173",
  "http://localhost:5173",
  "http://127.0.0.1:4173",
  "http://localhost:4173",
  "http://127.0.0.1:5500",
  "http://localhost:5500",
  "http://127.0.0.1:5501",
  "http://localhost:5501",
]);

export const TOKEN_KEY = "meditrust_token";
export const USER_KEY = "meditrust_user";

function resolveApiBase() {
  const configured = (import.meta.env.VITE_API_BASE || "").trim();
  if (configured) {
    return configured.replace(/\/+$/, "");
  }
  if (typeof window !== "undefined" && LOCAL_DEV_ORIGINS.has(window.location.origin)) {
    return "http://127.0.0.1:8001";
  }
  if (typeof window !== "undefined") {
    return `${window.location.origin}/api`;
  }
  return "/api";
}

export const API_BASE = resolveApiBase();

export class ApiError extends Error {
  constructor(status, message, errors = [], data = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.errors = errors;
    this.data = data;
  }
}

export function getStoredToken() {
  try {
    return localStorage.getItem(TOKEN_KEY) || "";
  } catch {
    return "";
  }
}

export function getStoredUser() {
  try {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function storeSession(token, user) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    if (user) localStorage.setItem(USER_KEY, JSON.stringify(user));
  } catch {
    /* storage unavailable (private mode) */
  }
}

export function clearSession() {
  try {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    ["mt_user_email", "mt_user_role", "mt_user_name", "mt_logged_in"].forEach((key) => localStorage.removeItem(key));
  } catch {
    /* ignore */
  }
}

function looksLikeHtml(text) {
  const trimmed = text.trim().toLowerCase();
  return trimmed.startsWith("<!doctype html") || trimmed.startsWith("<html");
}

export async function apiFetch(path, { method = "GET", body, auth = true, headers = {}, signal } = {}) {
  const requestHeaders = { Accept: "application/json", ...headers };
  if (body !== undefined) {
    requestHeaders["Content-Type"] = "application/json";
  }
  const token = auth ? getStoredToken() : "";
  if (token) {
    requestHeaders.Authorization = `Bearer ${token}`;
  }

  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method,
      headers: requestHeaders,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal,
    });
  } catch (error) {
    throw new ApiError(0, `Unable to reach the MediTrust API at ${API_BASE}.`, [], error);
  }

  const raw = await response.text();
  let data = null;
  if (raw && !looksLikeHtml(raw)) {
    try {
      data = JSON.parse(raw);
    } catch {
      data = null;
    }
  }

  if (response.status === 401 && auth && token) {
    window.dispatchEvent(new CustomEvent("meditrust:unauthorized"));
  }

  if (!response.ok) {
    const message =
      (data && (data.message || data.detail)) ||
      (raw && !looksLikeHtml(raw) ? raw.slice(0, 200) : "") ||
      `Request failed (${response.status}).`;
    throw new ApiError(response.status, typeof message === "string" ? message : JSON.stringify(message), data?.errors || [], data);
  }

  return data ?? {};
}

export const api = {
  get: (path, options) => apiFetch(path, { ...options, method: "GET" }),
  post: (path, body, options) => apiFetch(path, { ...options, method: "POST", body }),
  patch: (path, body, options) => apiFetch(path, { ...options, method: "PATCH", body }),
  delete: (path, options) => apiFetch(path, { ...options, method: "DELETE" }),
};
