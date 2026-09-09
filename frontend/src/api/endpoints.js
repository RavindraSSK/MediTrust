import { api } from "./client.js";

// ---------------------------------------------------------------- auth
export const registerUser = (payload) => api.post("/auth/register", payload, { auth: false });
export const loginUser = (email, password) => api.post("/auth/login", { email, password }, { auth: false });
export const fetchMe = () => api.get("/auth/me");
export const requestPasswordReset = (email) => api.post("/auth/request-reset", { email }, { auth: false });
export const verifyResetCode = (email, code) => api.post("/auth/verify-reset-code", { email, code }, { auth: false });
export const resetPassword = (email, newPassword) =>
  api.post("/auth/reset-password", { email, new_password: newPassword }, { auth: false });
export const changePassword = (currentPassword, newPassword) =>
  api.post("/auth/change-password", { current_password: currentPassword, new_password: newPassword });

// ---------------------------------------------------------------- prediction + workflow
export const predictRisk = (payload) => api.post("/predict", payload);
export const fetchRecentPredictions = () => api.get("/predictions/recent");
export const fetchUrgentCases = () => api.get("/predictions/urgent");
export const fetchDashboardSummary = () => api.get("/dashboard/summary");
export const fetchTriageQueue = () => api.get("/cases/triage-queue");
export const escalateCase = (caseId) => api.post(`/cases/${caseId}/escalate`);
export const fetchDoctorEscalations = () => api.get("/doctor/escalations");
export const saveDoctorDecision = (escalationId, decision, note = "") =>
  api.post(`/doctor/escalations/${escalationId}/decision`, { decision, note });
export const fetchExplainability = (caseId) => api.get(`/cases/${caseId}/explainability`);

// ---------------------------------------------------------------- patients
export const fetchRecentPatients = (limit = 5) => api.get(`/patients/recent?limit=${limit}`);
export const searchPatients = (query) => api.get(`/patients/search?q=${encodeURIComponent(query)}`);
export const fetchPatientRecords = (firstName, lastName) =>
  api.get(`/patients/records?first_name=${encodeURIComponent(firstName)}&last_name=${encodeURIComponent(lastName)}`);

// ---------------------------------------------------------------- admin
export const fetchAdminUsers = () => api.get("/admin/users");
export const updateAdminUserRole = (userId, role) => api.patch(`/admin/users/${userId}/role`, { role });
export const updateAdminUserRoleStatus = (userId, roleStatus) =>
  api.patch(`/admin/users/${userId}/role-status`, { role_status: roleStatus });
export const deleteAdminUser = (userId) => api.delete(`/admin/users/${userId}`);
export const fetchDoctorNurseAssignments = () => api.get("/admin/doctor-nurse-assignments");
export const createDoctorNurseAssignment = (doctorId, nurseId) =>
  api.post("/admin/doctor-nurse-assignments", { doctor_id: Number(doctorId), nurse_id: Number(nurseId) });
export const deleteDoctorNurseAssignment = (assignmentId) => api.delete(`/admin/doctor-nurse-assignments/${assignmentId}`);
export const fetchAdminCases = () => api.get("/admin/cases");
export const fetchAdminAuditLog = () => api.get("/admin/audit-log");

// ---------------------------------------------------------------- model + RAG
export const fetchModelInfo = () => api.get("/model/info", { auth: false });
export const fetchRagStatus = () => api.get("/rag/status");
export const fetchRagSources = () => api.get("/rag/sources");
export const searchRag = (query, k = 5) => api.get(`/rag/search?q=${encodeURIComponent(query)}&k=${k}`);
export const fetchHealth = () => api.get("/health/ready", { auth: false });
