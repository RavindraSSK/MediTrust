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

function resetForm() {
  document.getElementById("riskForm").reset();

  // reset defaults
  document.getElementById("cp").value = "3";
  document.getElementById("trestbps").value = "140";
  document.getElementById("chol").value = "250";
  document.getElementById("fbs").value = "0";
  document.getElementById("restecg").value = "1";
  document.getElementById("thalach").value = "150";
  document.getElementById("exang").value = "0";
  document.getElementById("oldpeak").value = "1.2";
  document.getElementById("slope").value = "2";
  document.getElementById("ca").value = "0";
  document.getElementById("thal").value = "3";

  // clear results
  document.getElementById("riskScore").textContent = "—";
  document.getElementById("riskLevel").textContent = "—";
  document.getElementById("note").textContent = "";

  const result = document.getElementById("result");
  if (result) result.style.display = "none";

  const explanation = document.getElementById("explanationSection");
  if (explanation) explanation.style.display = "none";
}

document.getElementById("resetBtn")?.addEventListener("click", resetForm);