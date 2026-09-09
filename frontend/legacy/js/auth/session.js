import { PAGE_LOGIN } from "../config.js";
import { go } from "../utils.js";

function normalizeUser(user) {
  if (!user || typeof user !== "object") return null;

  const firstName = String(user.first_name || "").trim();
  const lastName = String(user.last_name || "").trim();
  const fullName = String(user.full_name || [firstName, lastName].filter(Boolean).join(" ")).trim();
  const email = String(user.email || localStorage.getItem("mt_user_email") || "").trim();
  const role = String(user.role || localStorage.getItem("mt_user_role") || "").trim();

  return {
    ...user,
    ok: Boolean(user.ok),
    email,
    role,
    full_name: fullName,
    first_name: firstName || (fullName ? fullName.split(/\s+/)[0] : ""),
    last_name: lastName || (fullName ? fullName.split(/\s+/).slice(1).join(" ") : ""),
  };
}

export function storeCurrentUser(user) {
  const normalized = normalizeUser(user);
  if (!normalized) return;

  localStorage.setItem("meditrust_user", JSON.stringify(normalized));
  if (normalized.email) localStorage.setItem("mt_user_email", normalized.email);
  if (normalized.role) localStorage.setItem("mt_user_role", normalized.role);
  if (normalized.full_name) localStorage.setItem("mt_user_name", normalized.full_name);
}

export function isLoggedIn() {
  try {
    const user = normalizeUser(JSON.parse(localStorage.getItem("meditrust_user") || "null"));
    return !!(user && user.ok);
  } catch {
    return false;
  }
}

export function getCurrentUser() {
  try {
    const user = normalizeUser(JSON.parse(localStorage.getItem("meditrust_user") || "null"));
    if (!user) return null;
    storeCurrentUser(user);
    return user;
  } catch {
    return null;
  }
}

export function setLoggedIn(flag, email = "", role = "", fullName = "") {
  if (flag) {
    const [firstName = "", ...rest] = String(fullName || "").trim().split(/\s+/);
    storeCurrentUser({
      ok: true,
      email,
      role,
      full_name: fullName,
      first_name: firstName,
      last_name: rest.join(" ")
    });
  } else {
    localStorage.removeItem("meditrust_user");
  }
}

export function logout() {
  localStorage.removeItem("meditrust_user");
  localStorage.removeItem("mt_logged_in");
  localStorage.removeItem("mt_user_email");
  localStorage.removeItem("mt_user_role");
  localStorage.removeItem("mt_user_name");
  go(PAGE_LOGIN);
}
