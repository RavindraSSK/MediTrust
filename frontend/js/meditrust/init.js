import { PAGE_LOGIN } from "../config.js?v=20260609a";
import { go, $, setText } from "../utils.js?v=20260609a";
import { isLoggedIn, logout, getCurrentUser } from "../auth/session.js?v=20260609a";
import { getMediTrustElements } from "./form.js?v=20260609a";
import { handlePrediction } from "./predict.js?v=20260609a";
import { clearError } from "./render.js?v=20260609a";
import { downloadLatestRiskReport } from "./report.js?v=20260609a";

function getDashboardPageForRole(role) {
  if (role === "Doctor") return "doctor-dashboard.html";
  if (role === "Nurse") return "nurse-dashboard.html";
  if (role === "Admin") return "admin-dashboard.html";
  return PAGE_LOGIN;
}

function getDisplayName(user) {
  if (!user) return "";
  const combined = [user.first_name, user.last_name].filter(Boolean).join(" ").trim();
  return combined || user.full_name || user.email || "";
}

function applyDemoMode() {
  const params = new URLSearchParams(window.location.search);
  const isDemo = params.get("demo") === "true";
  if (!isDemo) return;

  if ($("patientFirstName")) $("patientFirstName").value = "Demo";
  if ($("patientLastName")) $("patientLastName").value = "Patient";
  if ($("firstName")) $("firstName").value = "Demo";
  if ($("lastName")) $("lastName").value = "Patient";
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
  setText($("currentUserName"), getDisplayName(user) || "Signed in user");

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
  elements.downloadReportBtn?.addEventListener("click", () => {
    downloadLatestRiskReport(elements, user);
  });

  clearError();
}
