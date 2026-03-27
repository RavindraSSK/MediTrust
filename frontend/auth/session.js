import { PAGE_LOGIN } from "../config.js";
import { go } from "../utils.js";

export function isLoggedIn() {
  return localStorage.getItem("mt_logged_in") === "true";
}

export function setLoggedIn(flag, email = "") {
  localStorage.setItem("mt_logged_in", flag ? "true" : "false");
  if (flag && email) {
    localStorage.setItem("mt_user_email", email);
  }
  if (!flag) {
    localStorage.removeItem("mt_user_email");
  }
}

export function logout() {
  setLoggedIn(false);
  go(PAGE_LOGIN);
}