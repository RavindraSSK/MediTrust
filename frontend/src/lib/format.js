export function formatRiskPercent(probability) {
  return `${Math.round((Number(probability) || 0) * 100)}%`;
}

export function formatPercent1(value) {
  const num = Number(value);
  return Number.isFinite(num) ? `${(num * 100).toFixed(1)}%` : "N/A";
}

export function formatDateTime(value) {
  if (!value) return "N/A";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "N/A" : date.toLocaleString();
}

export function formatNumber(value, fallback = "N/A") {
  if (value === null || value === undefined || value === "") return fallback;
  const number = Number(value);
  return Number.isFinite(number) ? String(Math.round(number)) : fallback;
}

export function formatDecimal(value, digits = 3) {
  const number = Number(value);
  return Number.isFinite(number) ? number.toFixed(digits) : "N/A";
}

export function safeNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

export function riskClass(riskLevel) {
  const level = String(riskLevel || "").toLowerCase();
  if (level === "high") return "badge-risk-high";
  if (level === "medium") return "badge-risk-medium";
  if (level === "low") return "badge-risk-low";
  return "badge-neutral";
}

export function priorityClass(priority) {
  const value = String(priority || "").toLowerCase();
  if (value === "urgent") return "badge-risk-high";
  if (value === "monitor") return "badge-risk-medium";
  return "badge-risk-low";
}

export function statusClass(status) {
  const value = String(status || "").toLowerCase();
  if (value === "escalated") return "badge-escalated";
  if (value === "reviewed") return "badge-reviewed";
  return "badge-pending";
}

export function buildDoctorAlertMessage(item) {
  if (!item) return "Urgent physician evaluation recommended.";
  const risk = Math.round((item.risk_probability || 0) * 100);
  if (risk >= 85) return "Immediate physician evaluation recommended.";
  if (risk >= 70) return "Priority physician review recommended.";
  return "Clinical review recommended.";
}

export function errorMessage(error, fallback = "Something went wrong.") {
  if (!error) return fallback;
  if (typeof error === "string") return error;
  const parts = [error.message || fallback];
  if (Array.isArray(error.errors) && error.errors.length) {
    parts.push(error.errors.join(" "));
  }
  return parts.join(" ");
}
