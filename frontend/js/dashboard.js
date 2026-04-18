const API_BASE = "http://127.0.0.1:8000";

export function getCurrentUser(requiredRole) {
  const user = JSON.parse(localStorage.getItem("meditrust_user") || "{}");
  const fallbackRole = localStorage.getItem("mt_user_role") || "";
  const normalized = {
    ...user,
    role: user.role || fallbackRole,
    full_name: user.full_name || localStorage.getItem("mt_user_name") || "",
  };

  if (!normalized.ok || normalized.role !== requiredRole) {
    window.location.href = "index.html";
    return null;
  }

  return normalized;
}

export function attachLogout(buttonId = "logoutBtn") {
  const btn = document.getElementById(buttonId);
  if (!btn) return;

  btn.addEventListener("click", () => {
    localStorage.removeItem("meditrust_user");
    localStorage.removeItem("mt_user_email");
    localStorage.removeItem("mt_user_role");
    localStorage.removeItem("mt_user_name");
    window.location.href = "index.html";
  });
}

export async function fetchUrgentCases() {
  const response = await fetch(`${API_BASE}/predictions/urgent`);
  return await response.json();
}

export async function fetchRecentPredictions() {
  const response = await fetch(`${API_BASE}/predictions/recent`);
  return await response.json();
}

export async function fetchDashboardSummary() {
  const response = await fetch(`${API_BASE}/dashboard/summary`);
  return await response.json();
}

export function formatRiskPercent(probability) {
  return `${Math.round((probability || 0) * 100)}%`;
}

export function formatDateTime(value) {
  if (!value) return "N/A";
  return new Date(value).toLocaleString();
}

export function buildDoctorAlertMessage(item) {
  if (!item) return "Urgent physician evaluation recommended.";

  const risk = Math.round((item.risk_probability || 0) * 100);

  if (risk >= 85) {
    return "Immediate physician evaluation recommended.";
  }

  if (risk >= 70) {
    return "Priority physician review recommended.";
  }

  return "Clinical review recommended.";
}
