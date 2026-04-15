import { PAGE_LOGIN } from "../config.js";
import { go, $, setText } from "../utils.js";
import { isLoggedIn, logout, getCurrentUser } from "../auth/session.js";
import { getMediTrustElements } from "./form.js";
import { handlePrediction } from "./predict.js";
import { clearError } from "./render.js";
import { downloadLatestRiskReport } from "./report.js";

function getDashboardPageForRole(role) {
  if (role === "Doctor") return "doctor-dashboard.html";
  if (role === "Nurse") return "nurse-dashboard.html";
  if (role === "Admin") return "admin-dashboard.html";
  return PAGE_LOGIN;
}

function applyDemoMode() {
  const params = new URLSearchParams(window.location.search);
  const isDemo = params.get("demo") === "true";
  if (!isDemo) return;

  if ($("name")) $("name").value = "Demo Patient";
  if ($("age")) $("age").value = "58";
  if ($("sex")) $("sex").value = "1";
  if ($("cp")) $("cp").value = "4";
  if ($("trestbps")) $("trestbps").value = "156";
  if ($("chol")) $("chol").value = "286";
  if ($("fbs")) $("fbs").value = "1";
  if ($("restecg")) $("restecg").value = "1";
  if ($("thalach")) $("thalach").value = "118";
  if ($("exang")) $("exang").value = "1";
  if ($("oldpeak")) $("oldpeak").value = "2.8";
  if ($("slope")) $("slope").value = "2";
  if ($("ca")) $("ca").value = "2";
  if ($("thal")) $("thal").value = "7";
}

export function initMediTrustPage() {
  if (!isLoggedIn()) {
    go(PAGE_LOGIN);
    return;
  }

  const user = getCurrentUser();

  setText($("currentUserRole"), user?.role || "Clinician");
  setText($("currentUserName"), user?.full_name || user?.email || "Signed in user");

  $("logoutBtn")?.addEventListener("click", logout);

  const returnBtn = $("returnDashboardBtn");
  if (returnBtn) {
    returnBtn.setAttribute("href", getDashboardPageForRole(user?.role));
  }

  applyDemoMode();

  const elements = getMediTrustElements();

  const handler = async (e) => {
    if (e) e.preventDefault();
    await handlePrediction(elements, user);
  };

  elements.form?.addEventListener("submit", handler);
  elements.btn?.addEventListener("click", handler);
  elements.downloadReportBtn?.addEventListener("click", () => downloadLatestRiskReport(elements, user));

  clearError();
}
