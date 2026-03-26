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

function getClinicalNarrative(item) {
  const feature = item.feature;
  const value = item.value;
  const direction = item.direction;

  if (feature === "chol") {
    if (value >= 240) {
      return `Total cholesterol is ${value} mg/dL, which falls in the high range and is clinically associated with increased cardiovascular risk.`;
    }
    if (value >= 200) {
      return `Total cholesterol is ${value} mg/dL, which falls in the borderline-high range and may contribute to increased cardiovascular risk.`;
    }
    return `Total cholesterol is ${value} mg/dL, which is within the desirable range and is less likely to be contributing substantially to risk.`;
  }

  if (feature === "trestbps") {
    if (value >= 140) {
      return `Resting blood pressure is ${value} mmHg, which is in the stage 2 hypertension range and is an important cardiovascular risk factor.`;
    }
    if (value >= 130) {
      return `Resting blood pressure is ${value} mmHg, which is in the stage 1 hypertension range and may contribute to cardiovascular risk.`;
    }
    if (value >= 120) {
      return `Resting blood pressure is ${value} mmHg, which is elevated above the normal range and may modestly affect cardiovascular risk.`;
    }
    return `Resting blood pressure is ${value} mmHg, which is within the normal adult range.`;
  }

  if (feature === "oldpeak") {
    if (value >= 1) {
      return `Exercise-induced ST depression is ${value}, which is above the commonly used abnormal threshold in stress testing and may suggest ischemic change.`;
    }
    return `Exercise-induced ST depression is ${value}, which is not markedly abnormal by common exercise ECG thresholds.`;
  }

  if (feature === "exang") {
    return Number(value) === 1
      ? "Exercise-induced angina is present, which is a clinically important indicator of exertional cardiac stress."
      : "Exercise-induced angina is not present, which reduces concern from this specific indicator.";
  }

  if (feature === "ca") {
    return Number(value) > 0
      ? `Major vessel involvement is recorded as ${value}, and higher values generally support greater coronary disease burden in the model context.`
      : "No major vessel involvement is recorded in this field, which is favorable in the model context.";
  }

  if (feature === "thal") {
    return `The thallium stress test result is recorded as ${value}, and this feature is being used by the model as a meaningful indicator in the current prediction.`;
  }

  if (feature === "cp") {
    return `The chest pain category is recorded as ${value}, and chest pain pattern is one of the clinically relevant inputs for cardiovascular risk interpretation.`;
  }

  if (feature === "restecg") {
    return `The resting ECG category is recorded as ${value}, and resting ECG findings are contributing to the model's assessment.`;
  }

  if (feature === "thalach") {
    return direction === "decreases risk"
      ? `Maximum heart rate achieved is ${value}, and in this prediction it is acting as a risk-lowering signal within the model.`
      : `Maximum heart rate achieved is ${value}, and in this prediction it is acting as a risk-increasing signal within the model.`;
  }

  if (feature === "age") {
    return `Age is ${value}, and age is being considered by the model as part of the overall cardiovascular risk profile.`;
  }

  if (feature === "fbs") {
    return Number(value) === 1
      ? "Fasting blood sugar is flagged as elevated in this input, which may contribute additional metabolic risk."
      : "Fasting blood sugar is not flagged as elevated in this input.";
  }

  if (feature === "slope") {
    return `The ST-segment slope category is recorded as ${value}, and this parameter is contributing to the model's interpretation of exercise ECG behavior.`;
  }

  if (feature === "sex") {
    return `Sex is included as one of the model inputs for cardiovascular risk estimation.`;
  }

  return `${getClinicalFeatureLabel(feature)} is contributing to the current prediction.`;
}

function buildMainNarrative(riskLevel, topFeatures) {
  if (!topFeatures.length) {
    return "The prediction is based on the combination of the submitted clinical indicators. No specific feature-level explanation is available for this result.";
  }

  const increasing = topFeatures.filter(
    (item) => item.direction === "increases risk"
  );
  const decreasing = topFeatures.filter(
    (item) => item.direction === "decreases risk"
  );

  const incLabels = increasing.map((item) => getClinicalFeatureLabel(item.feature));
  const decLabels = decreasing.map((item) => getClinicalFeatureLabel(item.feature));

  const joinLabels = (items) => {
    if (items.length === 0) return "";
    if (items.length === 1) return items[0];
    if (items.length === 2) return `${items[0]} and ${items[1]}`;
    return `${items.slice(0, -1).join(", ")}, and ${items[items.length - 1]}`;
  };

  if (incLabels.length && decLabels.length) {
    return `The model indicates that ${joinLabels(incLabels)} are the primary factors increasing the estimated cardiovascular risk, while ${joinLabels(decLabels)} appear to offset the prediction to some extent.`;
  }

  if (incLabels.length) {
    return `The model indicates that ${joinLabels(incLabels)} are the primary factors increasing the estimated cardiovascular risk.`;
  }

  return `The model indicates that ${joinLabels(decLabels)} are the primary factors associated with a lower estimated cardiovascular risk.`;
}

function buildClinicalSummary(riskLevel) {
  const normalized = (riskLevel || "current").toLowerCase();

  return `Clinical Summary: Overall, the current pattern is most consistent with a ${normalized} predicted risk profile. This explanation is intended as decision support and should be interpreted together with symptoms, examination findings, and clinician judgement.`;
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
    const topFeatures = (data.top_features || []).slice(0, 3);

    const factorListHtml = topFeatures
      .map((item) => {
        const toneClass =
          item.direction === "increases risk" ? "risk-up" : "risk-down";

        return `
          <li class="${toneClass}">
            <strong>${getClinicalFeatureLabel(item.feature)}</strong>
            <div class="clinical-factor-text">${getClinicalNarrative(item)}</div>
          </li>
        `;
      })
      .join("");

    const mainNarrative = buildMainNarrative(riskLevel, topFeatures);
    const summarySentence = buildClinicalSummary(riskLevel);

    explanationSec.innerHTML = `
      <div class="risk-fluid">
        <div class="explain-box professional-clinical-box">
          <h3>AI Clinical Explanation</h3>
          <p class="clinical-summary-text">${mainNarrative}</p>
          ${
            factorListHtml
              ? `<ul class="clinical-factor-list">${factorListHtml}</ul>`
              : `<p class="hint">Detailed feature contributions are not available for this prediction.</p>`
          }
          <p class="clinical-conclusion">${summarySentence}</p>
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