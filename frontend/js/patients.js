import { PAGE_LOGIN } from "./config.js?v=20260701a";
import { API_BASE } from "./services/api.js?v=20260701a";
import { $, go, setText } from "./utils.js?v=20260701a";
import { isLoggedIn, getCurrentUser, logout } from "./auth/session.js?v=20260701a";

function getDisplayName(user) {
  if (!user) return "";
  return [user.first_name, user.last_name].filter(Boolean).join(" ").trim() || user.full_name || user.email || "";
}

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return await response.json();
}

function formatRiskPercent(probability) {
  return `${Math.round((probability || 0) * 100)}%`;
}

function formatDateTime(value) {
  if (!value) return "N/A";
  return new Date(value).toLocaleString();
}

function renderPatientList(items, listEl, onSelect) {
  if (!items.length) {
    listEl.innerHTML = `<div class="patient-empty-state">No patient records found yet.</div>`;
    return;
  }

  listEl.innerHTML = items.map((item, index) => `
    <button
      type="button"
      class="patient-item"
      data-first-name="${item.first_name || ""}"
      data-last-name="${item.last_name || ""}"
      data-index="${index}"
    >
      <div class="patient-item-head">
        <strong>${item.full_name || "Unknown patient"}</strong>
        <span class="patient-risk-chip ${String(item.risk_level || "").toLowerCase()}">${item.risk_level || "Unknown"}</span>
      </div>
      <div class="patient-item-meta">
        <span>Risk ${formatRiskPercent(item.risk_probability)}</span>
        <span>Age ${item.age ?? "N/A"}</span>
        <span>${formatDateTime(item.created_at)}</span>
      </div>
    </button>
  `).join("");

  listEl.querySelectorAll(".patient-item").forEach((node) => {
    node.addEventListener("click", () => {
      onSelect(node.dataset.firstName || "", node.dataset.lastName || "");
    });
  });
}

function renderPatientDetails(records, detailEl) {
  if (!records.length) {
    detailEl.innerHTML = `<div class="patient-detail-empty">No risk assessment data found for this patient.</div>`;
    return;
  }

  const latest = records[0];
  const historyHtml = records.map((record) => `
    <div class="history-item">
      <strong>${formatDateTime(record.created_at)}</strong>
      <span>${record.risk_level} risk • ${formatRiskPercent(record.risk_probability)}</span>
    </div>
  `).join("");

  detailEl.innerHTML = `
    <div class="patient-detail-header">
      <div>
        <h3>${latest.full_name || "Patient Record"}</h3>
        <p>Latest saved cardiovascular risk assessment data.</p>
      </div>
      <div class="patient-risk-chip ${String(latest.risk_level || "").toLowerCase()}">${latest.risk_level || "Unknown"}</div>
    </div>

    <div class="patient-detail-grid">
      <div class="patient-detail-card">
        <small>Risk Probability</small>
        <strong>${formatRiskPercent(latest.risk_probability)}</strong>
      </div>
      <div class="patient-detail-card">
        <small>Triage Recommendation</small>
        <strong>${latest.triage_message || "N/A"}</strong>
      </div>
      <div class="patient-detail-card">
        <small>Age</small>
        <strong>${latest.age ?? "N/A"}</strong>
      </div>
      <div class="patient-detail-card">
        <small>Saved On</small>
        <strong>${formatDateTime(latest.created_at)}</strong>
      </div>
    </div>

    <div class="patient-metric-grid">
      <div class="field-card"><label>Resting Blood Pressure</label><div class="patient-metric-value">${latest.trestbps ?? "N/A"} mmHg</div></div>
      <div class="field-card"><label>Cholesterol</label><div class="patient-metric-value">${latest.chol ?? "N/A"} mg/dL</div></div>
      <div class="field-card"><label>Max Heart Rate</label><div class="patient-metric-value">${latest.thalach ?? "N/A"}</div></div>
      <div class="field-card"><label>ST Depression</label><div class="patient-metric-value">${latest.oldpeak ?? "N/A"}</div></div>
      <div class="field-card"><label>Chest Pain Type</label><div class="patient-metric-value">${latest.cp ?? "N/A"}</div></div>
      <div class="field-card"><label>Vessel Count</label><div class="patient-metric-value">${latest.ca ?? "N/A"}</div></div>
    </div>

    <div class="patient-history-box">
      <h4>Previous Records</h4>
      <div class="history-list">${historyHtml}</div>
    </div>
  `;
}

async function loadPatientRecords(firstName, lastName) {
  const url = `${API_BASE}/patients/records?first_name=${encodeURIComponent(firstName)}&last_name=${encodeURIComponent(lastName)}`;
  return await fetchJson(url);
}

export function initPatientsPage() {
  if (!isLoggedIn()) {
    go(PAGE_LOGIN);
    return;
  }

  const user = getCurrentUser();
  setText($("currentUserRole"), user?.role || "Clinician");
  setText($("currentUserName"), getDisplayName(user) || "Signed in user");
  $("logoutBtn")?.addEventListener("click", logout);

  const listEl = $("patientList");
  const detailEl = $("patientDetail");
  const searchInput = $("patientSearchInput");
  const searchBtn = $("patientSearchBtn");

  const selectPatient = async (firstName, lastName) => {
    detailEl.innerHTML = `<div class="patient-detail-empty">Loading patient record...</div>`;
    try {
      const records = await loadPatientRecords(firstName, lastName);
      renderPatientDetails(records, detailEl);
    } catch {
      detailEl.innerHTML = `<div class="patient-detail-empty">Unable to load patient record right now.</div>`;
    }
  };

  const loadRecentPatients = async () => {
    try {
      const items = await fetchJson(`${API_BASE}/patients/recent?limit=5`);
      renderPatientList(items, listEl, selectPatient);
      if (items.length) {
        await selectPatient(items[0].first_name || "", items[0].last_name || "");
      }
    } catch {
      listEl.innerHTML = `<div class="patient-empty-state">Unable to load recent patients.</div>`;
    }
  };

  const runSearch = async () => {
    const query = (searchInput?.value || "").trim();
    if (!query) {
      await loadRecentPatients();
      return;
    }

    listEl.innerHTML = `<div class="patient-empty-state">Searching patients...</div>`;
    try {
      const items = await fetchJson(`${API_BASE}/patients/search?q=${encodeURIComponent(query)}`);
      renderPatientList(items, listEl, selectPatient);
      if (items.length) {
        await selectPatient(items[0].first_name || "", items[0].last_name || "");
      } else {
        detailEl.innerHTML = `<div class="patient-detail-empty">No matching patient record found.</div>`;
      }
    } catch {
      listEl.innerHTML = `<div class="patient-empty-state">Search failed. Please try again.</div>`;
    }
  };

  searchBtn?.addEventListener("click", runSearch);
  searchInput?.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      runSearch();
    }
  });

  loadRecentPatients();
}
