import { pickId, setText, show, safeNumber } from "../utils.js";

export function renderRiskResult(data) {
  const riskLevelEl = pickId("riskLevel");
  const riskScoreEl = pickId("riskScore");

  const badgeEl = pickId("riskBadge", "badge");
  const adviceEl = pickId("riskAdvice", "note");
  const barEl = pickId("riskBarFill", "bar");
  const resultSec = pickId("resultSection", "result");

  const riskLevel = data.risk_level || "-";

  const score =
    safeNumber(data.risk_probability) !== null
      ? safeNumber(data.risk_probability)
      : safeNumber(data.risk_score);

  setText(riskLevelEl, riskLevel);
  setText(riskScoreEl, score !== null ? `${Math.round(score * 100)}%` : "-");

  if (badgeEl) {
    badgeEl.textContent =
      riskLevel === "High"
        ? "Needs attention"
        : riskLevel === "Medium"
        ? "Priority review"
        : "Low concern";
  }

  if (adviceEl) {
    if (data.triage_recommendation) {
      adviceEl.textContent = data.triage_recommendation;
    } else {
      adviceEl.textContent =
        riskLevel === "High"
          ? "Consider scheduling a checkup. If you have symptoms or concerns, seek medical guidance."
          : "Maintain healthy habits and follow routine checkups as recommended.";
    }
  }

  if (barEl && score !== null) {
    const pct = Math.min(100, Math.max(0, Math.round(score * 100)));
    barEl.style.width = `${pct}%`;
  }

  if (resultSec) {
    resultSec.classList.add("show");
    requestAnimationFrame(() => resultSec.classList.add("visible"));
  }
}

export function renderError(msg) {
  const errEl = pickId("errorBox", "alert");
  if (!errEl) {
    alert(msg);
    return;
  }
  errEl.textContent = msg;
  show(errEl, true);
}

export function clearError() {
  const errEl = pickId("errorBox", "alert");
  if (!errEl) return;
  errEl.textContent = "";
  show(errEl, false);
}