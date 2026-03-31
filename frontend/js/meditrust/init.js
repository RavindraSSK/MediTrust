import { PAGE_LOGIN } from "../config.js";
import { go, $ } from "../utils.js";
import { isLoggedIn, logout } from "../auth/session.js";
import { getMediTrustElements } from "./form.js";
import { handlePrediction } from "./predict.js";
import { clearError } from "./render.js";

export function initMediTrustPage() {
  if (!isLoggedIn()) {
    go(PAGE_LOGIN);
    return;
  }

  $("logoutBtn")?.addEventListener("click", logout);

  const elements = getMediTrustElements();

  const handler = async (e) => {
    if (e) e.preventDefault();
    await handlePrediction(elements);
  };

  elements.form?.addEventListener("submit", handler);
  elements.btn?.addEventListener("click", handler);

  clearError();
}