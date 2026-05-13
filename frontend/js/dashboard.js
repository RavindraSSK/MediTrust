import { API_BASE } from "./services/api.js?v=20260429c";

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

function getStoredUser() {
  try {
    return JSON.parse(localStorage.getItem("meditrust_user") || "{}");
  } catch {
    return {};
  }
}

async function readJsonResponse(response, fallbackMessage = "Request failed.") {
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || data.message || fallbackMessage);
  }
  return data;
}

export async function fetchTriageQueue() {
  const response = await fetch(`${API_BASE}/cases/triage-queue`);
  return await readJsonResponse(response, "Unable to load triage queue.");
}

export function renderTriageQueue(items, options = {}) {
  const tbody = document.getElementById(options.tableBodyId || "triageQueueBody");
  const empty = document.getElementById(options.emptyId || "triageQueueEmpty");
  if (!tbody) return;

  const rows = Array.isArray(items) ? items : [];
  if (!rows.length) {
    tbody.innerHTML = "";
    if (empty) empty.hidden = false;
    return;
  }

  if (empty) empty.hidden = true;
  tbody.innerHTML = rows.map((item) => `
    <tr class="${Number(item.id) === Number(options.selectedCaseId) ? "is-selected" : ""}" data-case-id="${safeText(item.id)}">
      <td>
        <strong>${safeText(item.patient_name || `Patient #${item.id}`)}</strong>
        <span>#${safeText(item.patient_id || item.id)}</span>
      </td>
      <td>${safeText(formatNumber(item.age))}</td>
      <td><span class="clinical-badge ${riskClass(item.risk_level)}">${safeText(item.risk_level || "Unknown")}</span></td>
      <td>${formatRiskPercent(item.risk_probability)}</td>
      <td><span class="clinical-badge ${priorityClass(item.priority)}">${safeText(item.priority || "Routine")}</span></td>
      <td><span class="clinical-badge ${statusClass(item.status)}">${safeText(item.status || "Pending")}</span></td>
      <td>${safeText(formatDateTime(item.created_at))}</td>
      <td class="table-actions">
        <button class="mini-btn table-btn" type="button" data-action="view" data-case-id="${safeText(item.id)}">View case</button>
        <button class="mini-btn table-btn" type="button" data-action="escalate" data-case-id="${safeText(item.id)}" ${item.escalated ? "disabled" : ""}>Escalate to doctor</button>
      </td>
    </tr>
  `).join("");
}

export async function escalateCase(caseId) {
  if (!caseId) {
    throw new Error("Select a case before escalating.");
  }

  const user = getStoredUser();
  const response = await fetch(`${API_BASE}/cases/${caseId}/escalate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Nurse-Id": user.id || "",
    },
  });
  return await readJsonResponse(response, "Unable to escalate case.");
}

export async function fetchDoctorEscalations() {
  const response = await fetch(`${API_BASE}/doctor/escalations`);
  return await readJsonResponse(response, "Unable to load doctor escalations.");
}

export async function fetchExplainability(caseId) {
  if (!caseId) {
    throw new Error("Select a case before viewing explainability insights.");
  }

  const response = await fetch(`${API_BASE}/cases/${caseId}/explainability`);
  return await readJsonResponse(response, "Unable to load explainability insights.");
}

export function renderExplainabilityModal(data) {
  const modal = document.getElementById("explainabilityModal");
  const body = document.getElementById("explainabilityModalBody");
  if (!modal || !body) return;

  const increasing = Array.isArray(data?.risk_increasing_factors) ? data.risk_increasing_factors : [];
  const reducing = Array.isArray(data?.risk_reducing_factors) ? data.risk_reducing_factors : [];
  const patient = data?.patient || {};

  body.innerHTML = `
    <div class="clinical-summary-grid">
      <div class="clinical-summary-card">
        <h4>Patient / Case</h4>
        <p>${safeText(patient.name || `Patient #${patient.id || data?.case?.id || ""}`)}</p>
        <span>Case #${safeText(patient.id || data?.case?.id || "")} · Age ${safeText(formatNumber(patient.age || data?.case?.age))}</span>
      </div>
      <div class="clinical-summary-card">
        <h4>Risk Probability</h4>
        <p>${formatRiskPercent(data?.risk_probability)}</p>
        <span>${safeText(data?.risk_level || "Unknown")} predicted risk</span>
      </div>
      <div class="clinical-summary-card">
        <h4>Model Confidence</h4>
        <p>${safeText(data?.risk_level || "Clinical")} signal</p>
        <span>${safeText(data?.confidence_note || "Final decision must be made by clinician.")}</span>
      </div>
    </div>

    ${data?.gemini_summary ? `
      <section class="insight-section ai-section">
        <h3>Gemini / AI Summary</h3>
        <p>${safeText(data.gemini_summary)}</p>
      </section>
    ` : ""}

    <section class="insight-section">
      <h3>Risk-Increasing Factors</h3>
      ${renderFactorList(increasing, "No strong risk-increasing factors were identified.")}
    </section>

    <section class="insight-section">
      <h3>Risk-Reducing Factors</h3>
      ${renderFactorList(reducing, "No strong risk-reducing factors were identified.")}
    </section>

    <section class="insight-section">
      <h3>Clinical Interpretation</h3>
      <p>${safeText(data?.clinical_interpretation || data?.fallback_summary || "The model generated a prediction, but a detailed explanation is not available.")}</p>
    </section>

    <section class="insight-section">
      <h3>Suggested Next Action</h3>
      <p>${safeText(data?.suggested_next_action || data?.triage_recommendation || "Review the case using clinical judgment.")}</p>
    </section>
  `;

  modal.hidden = false;
  document.body.classList.add("modal-open");
}

function getAdminHeaders() {
  const user = getStoredUser();
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

export function safeText(value, fallback = "N/A") {
  const text = value === null || value === undefined || value === "" ? fallback : String(value);
  return text
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

export function formatNumber(value, fallback = "N/A") {
  if (value === null || value === undefined || value === "") return fallback;
  const number = Number(value);
  return Number.isFinite(number) ? String(Math.round(number)) : fallback;
}

function riskClass(riskLevel) {
  const level = String(riskLevel || "").toLowerCase();
  if (level === "high") return "badge-risk-high";
  if (level === "medium") return "badge-risk-medium";
  if (level === "low") return "badge-risk-low";
  return "badge-neutral";
}

function priorityClass(priority) {
  const value = String(priority || "").toLowerCase();
  if (value === "urgent") return "badge-risk-high";
  if (value === "monitor") return "badge-risk-medium";
  return "badge-risk-low";
}

function statusClass(status) {
  const value = String(status || "").toLowerCase();
  if (value === "escalated") return "badge-escalated";
  if (value === "reviewed") return "badge-reviewed";
  return "badge-pending";
}

function renderFactorList(items, emptyText) {
  if (!items.length) {
    return `<div class="empty-clinical-note">${safeText(emptyText)}</div>`;
  }

  return `
    <div class="factor-list">
      ${items.map((item) => `
        <article class="factor-item">
          <strong>${safeText(item.label || item.feature || "Clinical feature")}</strong>
          <p>${safeText(item.explanation || "This feature contributed to the model prediction.")}</p>
        </article>
      `).join("")}
    </div>
  `;
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
