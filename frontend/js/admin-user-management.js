import {
  getCurrentUser,
  attachLogout,
  fetchAdminUsers,
  updateAdminUserRole,
  updateAdminUserRoleStatus,
  deleteAdminUser,
  fetchDoctorNurseAssignments,
  createDoctorNurseAssignment,
  deleteDoctorNurseAssignment,
  formatDateTime
} from "./dashboard.js";

const roles = ["Doctor", "Nurse", "Admin"];
let currentUser = null;
let users = [];
let assignments = [];

function setupAdminPage() {
  currentUser = getCurrentUser("Admin");
  if (!currentUser) throw new Error("Unauthorized");

  const name = [currentUser.first_name, currentUser.last_name].filter(Boolean).join(" ").trim()
    || currentUser.full_name
    || "Admin";
  const userNameNode = document.getElementById("adminUserName");
  if (userNameNode) userNameNode.textContent = name;

  attachLogout();
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;"
  }[char]));
}

function setMessage(message, isError = false) {
  const node = document.getElementById("adminManagementMessage");
  if (!node) return;
  node.textContent = message || "";
  node.classList.toggle("admin-message-error", Boolean(isError));
}

function getName(row) {
  return row.full_name || [row.first_name, row.last_name].filter(Boolean).join(" ") || "Unknown";
}

function isSelf(row) {
  return row.email === currentUser.email || row.id === currentUser.id;
}

function sortUsersNewestFirst(rows) {
  return [...rows].sort((a, b) => (Number(b.id) || 0) - (Number(a.id) || 0));
}

function sortAssignmentsNewestFirst(rows) {
  return [...rows].sort((a, b) => {
    const bTime = b.created_at ? new Date(b.created_at).getTime() : 0;
    const aTime = a.created_at ? new Date(a.created_at).getTime() : 0;
    return bTime - aTime || (Number(b.id) || 0) - (Number(a.id) || 0);
  });
}

function matchesUser(row, query) {
  if (!query) return true;
  const haystack = `${getName(row)} ${row.email} ${row.role} ${row.role_status}`.toLowerCase();
  return haystack.includes(query.toLowerCase());
}

function matchesAssignment(row, query) {
  if (!query) return true;
  const haystack = `${row.doctor_name} ${row.doctor_email} ${row.nurse_name} ${row.nurse_email}`.toLowerCase();
  return haystack.includes(query.toLowerCase());
}

function renderRoleSelect(row) {
  return `
    <select class="admin-select role-change-select" data-user-id="${row.id}" ${isSelf(row) ? "disabled" : ""}>
      ${roles.map(role => `
        <option value="${role}" ${row.role === role ? "selected" : ""}>${role}</option>
      `).join("")}
    </select>
  `;
}

function renderPendingRows(rows, emptyText) {
  const table = document.getElementById("pendingUsersTable");
  if (!rows.length) {
    table.innerHTML = `<tr><td colspan="5">${emptyText}</td></tr>`;
    return;
  }

  table.innerHTML = rows.map(row => `
    <tr>
      <td>${escapeHtml(getName(row))}</td>
      <td>${escapeHtml(row.email)}</td>
      <td>${escapeHtml(row.role)}</td>
      <td><span class="status-pill status-${escapeHtml(row.role_status || "approved")}">${escapeHtml(row.role_status || "approved")}</span></td>
      <td>
        <div class="admin-action-row">
          <button class="mini-btn admin-row-btn approve-user-btn" data-user-id="${row.id}" ${isSelf(row) ? "disabled" : ""}>Approve</button>
          <button class="mini-btn admin-row-btn reject-user-btn" data-user-id="${row.id}" ${isSelf(row) ? "disabled" : ""}>Reject</button>
        </div>
      </td>
    </tr>
  `).join("");
}

function renderPendingError(message) {
  const table = document.getElementById("pendingUsersTable");
  if (table) table.innerHTML = `<tr><td colspan="5">${escapeHtml(message)}</td></tr>`;
}

function renderRegisteredRows(rows, emptyText) {
  const table = document.getElementById("registeredUsersTable");
  if (!rows.length) {
    table.innerHTML = `<tr><td colspan="5">${emptyText}</td></tr>`;
    return;
  }

  table.innerHTML = rows.map(row => `
    <tr>
      <td>${escapeHtml(getName(row))}</td>
      <td>${escapeHtml(row.email)}</td>
      <td>${escapeHtml(row.role)}</td>
      <td><span class="status-pill status-${escapeHtml(row.role_status || "approved")}">${escapeHtml(row.role_status || "approved")}</span></td>
      <td>
        <div class="admin-action-row">
          ${renderRoleSelect(row)}
          <button class="mini-btn admin-row-btn delete-user-btn" data-user-id="${row.id}" ${isSelf(row) ? "disabled" : ""}>Delete</button>
        </div>
      </td>
    </tr>
  `).join("");
}

function renderRegisteredError(message) {
  const table = document.getElementById("registeredUsersTable");
  if (table) table.innerHTML = `<tr><td colspan="5">${escapeHtml(message)}</td></tr>`;
}

function renderAssignmentOptions() {
  const doctorSelect = document.getElementById("doctorSelect");
  const nurseSelect = document.getElementById("nurseSelect");
  const approvedDoctors = users.filter(row => row.role === "Doctor" && row.role_status === "approved");
  const approvedNurses = users.filter(row => row.role === "Nurse" && row.role_status === "approved");

  doctorSelect.innerHTML = `
    <option value="">Select doctor</option>
    ${sortUsersNewestFirst(approvedDoctors).map(row => `<option value="${row.id}">${escapeHtml(getName(row))}</option>`).join("")}
  `;
  nurseSelect.innerHTML = `
    <option value="">Select nurse</option>
    ${sortUsersNewestFirst(approvedNurses).map(row => `<option value="${row.id}">${escapeHtml(getName(row))}</option>`).join("")}
  `;
}

function renderAssignmentRows(rows, emptyText) {
  const table = document.getElementById("assignmentsTable");
  if (!rows.length) {
    table.innerHTML = `<tr><td colspan="4">${emptyText}</td></tr>`;
    return;
  }

  table.innerHTML = rows.map(row => `
    <tr>
      <td>${escapeHtml(row.doctor_name)}<br><span>${escapeHtml(row.doctor_email)}</span></td>
      <td>${escapeHtml(row.nurse_name)}<br><span>${escapeHtml(row.nurse_email)}</span></td>
      <td>${formatDateTime(row.created_at)}</td>
      <td><button class="mini-btn admin-row-btn unassign-btn" data-assignment-id="${row.id}">Unassign</button></td>
    </tr>
  `).join("");
}

function renderAssignmentError(message) {
  const table = document.getElementById("assignmentsTable");
  if (table) table.innerHTML = `<tr><td colspan="4">${escapeHtml(message)}</td></tr>`;
}

function filterInputValue() {
  return document.getElementById("adminSearchInput")?.value.trim() || "";
}

function renderPendingPage() {
  const query = filterInputValue();
  const rows = sortUsersNewestFirst(users)
    .filter(row => row.role_status === "pending")
    .filter(row => matchesUser(row, query));
  renderPendingRows(rows, query ? "No matching users found." : "No pending role requests.");
}

function renderRegisteredPage() {
  const query = filterInputValue();
  const rows = sortUsersNewestFirst(users).filter(row => matchesUser(row, query));
  renderRegisteredRows(rows, query ? "No matching users found." : "No registered users found.");
}

function renderAssignmentsPage() {
  const query = filterInputValue();
  renderAssignmentOptions();
  const rows = sortAssignmentsNewestFirst(assignments).filter(row => matchesAssignment(row, query));
  renderAssignmentRows(rows, query ? "No matching users found." : "No doctor-nurse assignments yet.");
}

async function loadUsers(render, successMessage = "Loaded.") {
  setMessage("Loading...");
  try {
    users = await fetchAdminUsers();
    render();
    setMessage(successMessage);
  } catch (error) {
    const message = error.message || "Unable to load users.";
    setMessage(message, true);
    renderPendingError(message);
    renderRegisteredError(message);
  }
}

async function loadAssignments(successMessage = "Loaded.") {
  setMessage("Loading...");
  try {
    const [userRows, assignmentRows] = await Promise.all([
      fetchAdminUsers(),
      fetchDoctorNurseAssignments()
    ]);
    users = userRows;
    assignments = assignmentRows;
    renderAssignmentsPage();
    setMessage(successMessage);
  } catch (error) {
    const message = error.message || "Unable to load assignments.";
    setMessage(message, true);
    renderAssignmentError(message);
  }
}

async function performAction(action, reload, successMessage) {
  setMessage("Saving changes...");
  try {
    await action();
    await reload(successMessage);
  } catch (error) {
    setMessage(error.message || "Unable to save changes.", true);
  }
}

export function initUserManagementHub() {
  try {
    setupAdminPage();
    document.getElementById("pendingRequestsBtn").addEventListener("click", () => {
      window.location.href = "pending-requests/";
    });
    document.getElementById("registeredUsersBtn").addEventListener("click", () => {
      window.location.href = "registered-users/";
    });
    document.getElementById("doctorNurseAssignmentsBtn").addEventListener("click", () => {
      window.location.href = "doctor-nurse-assignments/";
    });
  } catch (error) {
    const node = document.getElementById("adminUserName");
    if (node) node.textContent = "Admin session required";
    console.error(error);
  }
}

export function initPendingRequestsPage() {
  setupAdminPage();
  document.getElementById("adminSearchInput").addEventListener("input", renderPendingPage);
  document.getElementById("refreshAdminUsersBtn").addEventListener("click", () => loadUsers(renderPendingPage, "Pending requests refreshed."));
  document.getElementById("adminManagementPanel").addEventListener("click", (event) => {
    const target = event.target;
    if (target.classList.contains("approve-user-btn")) {
      performAction(
        () => updateAdminUserRoleStatus(target.dataset.userId, "approved"),
        (message) => loadUsers(renderPendingPage, message),
        "Role request approved."
      );
    }
    if (target.classList.contains("reject-user-btn")) {
      performAction(
        () => updateAdminUserRoleStatus(target.dataset.userId, "rejected"),
        (message) => loadUsers(renderPendingPage, message),
        "Role request rejected."
      );
    }
  });
  loadUsers(renderPendingPage, "Pending requests loaded.");
}

export function initRegisteredUsersPage() {
  setupAdminPage();
  document.getElementById("adminSearchInput").addEventListener("input", renderRegisteredPage);
  document.getElementById("refreshAdminUsersBtn").addEventListener("click", () => loadUsers(renderRegisteredPage, "Registered users refreshed."));
  document.getElementById("adminManagementPanel").addEventListener("change", (event) => {
    const target = event.target;
    if (!target.classList.contains("role-change-select")) return;
    performAction(
      () => updateAdminUserRole(target.dataset.userId, target.value),
      (message) => loadUsers(renderRegisteredPage, message),
      "User role updated."
    );
  });
  document.getElementById("adminManagementPanel").addEventListener("click", (event) => {
    const target = event.target;
    if (!target.classList.contains("delete-user-btn")) return;
    const selected = users.find(row => String(row.id) === String(target.dataset.userId));
    const label = selected?.email || "this user";
    if (!confirm(`Delete ${label}? This cannot be undone.`)) return;
    performAction(
      () => deleteAdminUser(target.dataset.userId),
      (message) => loadUsers(renderRegisteredPage, message),
      "User account deleted."
    );
  });
  loadUsers(renderRegisteredPage, "Registered users loaded.");
}

export function initDoctorNurseAssignmentsPage() {
  setupAdminPage();
  document.getElementById("adminSearchInput").addEventListener("input", renderAssignmentsPage);
  document.getElementById("refreshAdminUsersBtn").addEventListener("click", () => loadAssignments("Assignments refreshed."));
  document.getElementById("adminManagementPanel").addEventListener("click", (event) => {
    const target = event.target;
    if (!target.classList.contains("unassign-btn")) return;
    performAction(
      () => deleteDoctorNurseAssignment(target.dataset.assignmentId),
      loadAssignments,
      "Nurse unassigned from doctor."
    );
  });
  document.getElementById("assignmentForm").addEventListener("submit", (event) => {
    event.preventDefault();
    const doctorId = document.getElementById("doctorSelect").value;
    const nurseId = document.getElementById("nurseSelect").value;
    if (!doctorId || !nurseId) {
      setMessage("Select both a doctor and a nurse.", true);
      return;
    }
    performAction(
      () => createDoctorNurseAssignment(doctorId, nurseId),
      loadAssignments,
      "Nurse assigned to doctor."
    );
  });
  loadAssignments("Assignments loaded.");
}
