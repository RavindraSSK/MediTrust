const API_BASE = "http://127.0.0.1:8000";

function getLoginPagePath() {
  const frontendMarker = "/frontend/";
  const markerIndex = window.location.pathname.indexOf(frontendMarker);
  if (markerIndex >= 0) {
    return `${window.location.pathname.slice(0, markerIndex)}${frontendMarker}index.html`;
  }

  return "/index.html";
}

export function getCurrentUser(requiredRole) {
  let user = {};
  try {
    user = JSON.parse(localStorage.getItem("meditrust_user") || "{}");
  } catch {
    user = {};
  }
  const fallbackRole = localStorage.getItem("mt_user_role") || "";
  const normalized = {
    ...user,
    role: user.role || fallbackRole,
    full_name: user.full_name || localStorage.getItem("mt_user_name") || "",
  };

  if (!normalized.ok || normalized.role !== requiredRole) {
    window.location.href = getLoginPagePath();
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
    window.location.href = getLoginPagePath();
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

function getAdminHeaders() {
  let user = {};
  try {
    user = JSON.parse(localStorage.getItem("meditrust_user") || "{}");
  } catch {
    user = {};
  }
  return {
    "Content-Type": "application/json",
    "X-Admin-Email": user.email || localStorage.getItem("mt_user_email") || "",
  };
}

async function adminRequest(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      ...getAdminHeaders(),
      ...(options.headers || {}),
    },
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || data.message || "Admin request failed.");
  }

  return data;
}

export async function fetchAdminUsers() {
  return await adminRequest("/admin/users");
}

export async function updateAdminUserRole(userId, role) {
  return await adminRequest(`/admin/users/${userId}/role`, {
    method: "PATCH",
    body: JSON.stringify({ role }),
  });
}

export async function updateAdminUserRoleStatus(userId, roleStatus) {
  return await adminRequest(`/admin/users/${userId}/role-status`, {
    method: "PATCH",
    body: JSON.stringify({ role_status: roleStatus }),
  });
}

export async function deleteAdminUser(userId) {
  return await adminRequest(`/admin/users/${userId}`, {
    method: "DELETE",
  });
}

export async function fetchDoctorNurseAssignments() {
  return await adminRequest("/admin/doctor-nurse-assignments");
}

export async function createDoctorNurseAssignment(doctorId, nurseId) {
  return await adminRequest("/admin/doctor-nurse-assignments", {
    method: "POST",
    body: JSON.stringify({ doctor_id: Number(doctorId), nurse_id: Number(nurseId) }),
  });
}

export async function deleteDoctorNurseAssignment(assignmentId) {
  return await adminRequest(`/admin/doctor-nurse-assignments/${assignmentId}`, {
    method: "DELETE",
  });
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
