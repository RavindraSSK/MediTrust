import { pickId, setText, show, safeNumber } from "../utils.js";

function getClinicalFeatureLabel(feature) {
  const labels = {
    age: "age",
    chol: "total cholesterol",
    trestbps: "resting blood pressure",
    oldpeak: "exercise-induced ST depression",
    exang: "exercise-induced angina",
    thalach: "maximum heart rate achieved",
    ca: "major vessel involvement",
    thal: "thallium stress test result",
    cp: "chest pain pattern",
    restecg: "resting ECG findings",
    fbs: "fasting blood sugar",
    slope: "ST-segment slope",
    sex: "sex"
  };
  return labels[feature] || feature;
}

function renderContributionBars(features) {
  if (!features || !features.length) return "";

  const maxAbs = Math.max(...features.map((item) => Math.abs(item.impact)), 0.0001);

  return `
    <div class="contrib-section">
      <h4>Model Contribution Bars</h4>
      <div class="contrib-list">
        ${features
          .map((item) => {
            const pct = Math.max(8, Math.round((Math.abs(item.impact) / maxAbs) * 100));
            const cls = item.direction === "increases risk" ? "contrib-up" : "contrib-down";

            return `
              <div class="contrib-row">
                <div class="contrib-label">${getClinicalFeatureLabel(item.feature)}</div>
                <div class="contrib-bar-wrap">
                  <div class="contrib-bar ${cls}" style="width:${pct}%"></div>
                </div>
                <div class="contrib-value">${item.impact.toFixed(3)}</div>
              </div>
            `;
          })
          .join("")}
      </div>
    </div>
  `;
}

function renderWaterfall(baseValue, finalProbability, features) {
  if (!features || !features.length) return "";

  let running = baseValue;

  const rows = features.map((item) => {
    const before = running;
    running += item.impact;
    const after = running;

    return `
      <div class="waterfall-row">
        <div class="waterfall-feature">${getClinicalFeatureLabel(item.feature)}</div>
        <div class="waterfall-shift ${item.direction === "increases risk" ? "wf-up" : "wf-down"}">
          ${item.impact >= 0 ? "+" : ""}${item.impact.toFixed(3)}
        </div>
        <div class="waterfall-range">
          ${before.toFixed(3)} → ${after.toFixed(3)}
        </div>
      </div>
    `;
  });

  return `
    <div class="waterfall-section">
      <h4>SHAP Waterfall View</h4>
      <div class="waterfall-base">
        <strong>Base value:</strong> ${baseValue.toFixed(3)}
      </div>
      <div class="waterfall-list">
        ${rows.join("")}
      </div>
      <div class="waterfall-final">
        <strong>Final predicted probability:</strong> ${finalProbability.toFixed(3)}
      </div>
    </div>
  `;
}

export function renderRiskResult(data) {
  const riskLevelEl = pickId("riskLevel");
  const riskScoreEl = pickId("riskScore");

  const badgeEl = pickId("riskBadge", "badge");
  const adviceEl = pickId("riskAdvice", "note");
  const barEl = pickId("riskBarFill", "bar");
  const resultSec = pickId("resultSection", "result");
  const explanationSec = pickId("explanationSection");

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

  if (explanationSec) {
    const topFeatures = data.top_features || [];
    const allFeatures = data.all_features || [];
    const baseValue = safeNumber(data.base_value) ?? 0;

    const factorListHtml = topFeatures
      .map((item) => {
        const toneClass =
          item.direction === "increases risk" ? "risk-up" : "risk-down";

        return `
          <li class="${toneClass}">
            <strong>${getClinicalFeatureLabel(item.feature)}</strong>
            <div class="clinical-factor-text">
              ${getClinicalFeatureLabel(item.feature)} contributed ${item.direction === "increases risk" ? "to a higher" : "to a lower"} estimated risk
              (observed value: ${item.value}, SHAP impact: ${item.impact.toFixed(3)})
            </div>
          </li>
        `;
      })
      .join("");

    const barsHtml = renderContributionBars(allFeatures.slice(0, 8));
    const waterfallHtml = renderWaterfall(baseValue, score || 0, allFeatures.slice(0, 8));

    explanationSec.innerHTML = `
      <div class="risk-fluid">
        <div class="explain-box professional-clinical-box">
          <h3>AI Clinical Explanation</h3>
          <p class="clinical-summary-text">
            ${data.explanation_summary || "No detailed explanation is available for this prediction."}
          </p>

          ${
            factorListHtml
              ? `<ul class="clinical-factor-list">${factorListHtml}</ul>`
              : `<p class="hint">Detailed feature contributions are not available for this prediction.</p>`
          }

          <p class="clinical-conclusion">
            Clinical Summary: Overall, the current pattern should be interpreted together with symptoms, examination findings, and clinician judgement.
          </p>

          ${barsHtml}
          ${waterfallHtml}
        </div>
      </div>
    `;

    show(explanationSec, true);
    explanationSec.classList.add("show");
    requestAnimationFrame(() => explanationSec.classList.add("visible"));
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