import { PAGE_LOGIN } from "../config.js";
import { go } from "../utils.js";

export function isLoggedIn() {
  try {
    const user = JSON.parse(localStorage.getItem("meditrust_user") || "null");
    return !!(user && user.ok);
  } catch {
    return false;
  }
}

export function getCurrentUser() {
  try {
    return JSON.parse(localStorage.getItem("meditrust_user") || "null");
  } catch {
    return null;
  }
}

export function setLoggedIn(flag, email = "", role = "", fullName = "") {
  if (flag) {
    localStorage.setItem(
      "meditrust_user",
      JSON.stringify({
        ok: true,
        email,
        role,
        full_name: fullName
      })
    );
  } else {
    localStorage.removeItem("meditrust_user");
  }
}

export function logout() {
  localStorage.removeItem("meditrust_user");
  localStorage.removeItem("mt_logged_in");
  localStorage.removeItem("mt_user_email");
  go(PAGE_LOGIN);
}