import { PAGE_SIGNUP, PAGE_MEDI } from "./config.js";
import { initLoginPage } from "./auth/login.js";
import { initSignupPage } from "./auth/signup.js";
import { initMediTrustPage } from "./meditrust/init.js";

document.addEventListener("DOMContentLoaded", () => {
  const file = (window.location.pathname.split("/").pop() || "").toLowerCase();

  if (file === PAGE_SIGNUP) {
    initSignupPage();
  } else if (file === PAGE_MEDI) {
    initMediTrustPage();
  } else {
    initLoginPage();
  }
});