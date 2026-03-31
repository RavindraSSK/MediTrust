import {
  PAGE_SIGNUP,
  PAGE_MEDI,
  PAGE_FORGOT,
  PAGE_RESET,
  PAGE_CHANGE_PASSWORD,
} from "./config.js";
import { initLoginPage } from "./auth/login.js";
import { initSignupPage } from "./auth/signup.js";
import { initMediTrustPage } from "./meditrust/init.js";

document.addEventListener("DOMContentLoaded", () => {
  const file = (window.location.pathname.split("/").pop() || "").toLowerCase();

  if (file === PAGE_SIGNUP) {
    initSignupPage();
  } else if (file === PAGE_MEDI) {
    initMediTrustPage();
  } else if (
    file === PAGE_FORGOT ||
    file === PAGE_RESET ||
    file === PAGE_CHANGE_PASSWORD
  ) {
    return;
  } else {
    initLoginPage();
  }
});