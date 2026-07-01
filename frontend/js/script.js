import {
  PAGE_SIGNUP,
  PAGE_MEDI,
  PAGE_PATIENTS,
  PAGE_FORGOT,
  PAGE_RESET,
  PAGE_CHANGE_PASSWORD,
} from "./config.js";
import { initLoginPage } from "./auth/login.js?v=20260701a";
import { initSignupPage } from "./auth/signup.js?v=20260701a";
import { initMediTrustPage } from "./meditrust/init.js?v=20260701a";
import { initPatientsPage } from "./patients.js?v=20260701a";

document.addEventListener("DOMContentLoaded", () => {
  const file = (window.location.pathname.split("/").pop() || "").toLowerCase();

  if (file === PAGE_SIGNUP) {
    initSignupPage();
  } else if (file === PAGE_MEDI) {
    initMediTrustPage();
  } else if (file === PAGE_PATIENTS) {
    initPatientsPage();
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
