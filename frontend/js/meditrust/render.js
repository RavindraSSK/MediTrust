import { pickId, setText, show, safeNumber } from "../utils.js";

function getClinicalFeatureLabel(feature) {
  const labels = {
    age: "age",
    chol: "cholesterol",
    trestbps: "resting blood pressure",
    oldpeak: "ST depression",
    exang: "exercise-induced angina",
    thalach: "maximum heart rate",
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

function getRiskDirectionText(direction) {
  const normalized = String(direction || "").toLowerCase();

  if (normalized.includes("decrease")) {
    return "Decreases risk";
  }

  if (normalized.includes("increase")) {
    return "Increases risk";
  }

  return "Affects risk";
}

function capitalizeFirst(text) {
  if (!text) return "";
  return text.charAt(0).toUpperCase() + text.slice(1);
}

function formatClinicalNumber(value, digits = 1) {
  const numeric = safeNumber(value);
  if (numeric === null) return null;
  if (Number.isInteger(numeric)) return String(numeric);
  return numeric.toFixed(digits).replace(/\.0$/, "");
}

function formatFeatureList(features) {
  const labels = [...new Set(features.map((item) => getClinicalFeatureLabel(item.feature)).filter(Boolean))];

  if (!labels.length) return "";
  if (labels.length === 1) return labels[0];
  if (labels.length === 2) return `${labels[0]} and ${labels[1]}`;

  return `${labels.slice(0, -1).join(", ")}, and ${labels[labels.length - 1]}`;
}

function buildClinicalExplanation(riskLevel, features) {
  const intro =
    riskLevel === "High"
      ? "This result indicates a high cardiovascular risk."
      : riskLevel === "Medium"
        ? "This result indicates a moderate cardiovascular risk."
        : riskLevel === "Low"
          ? "This result indicates a low cardiovascular risk."
          : "This result reflects the current cardiovascular risk assessment.";

  const increasing = features.filter((item) => getRiskDirectionText(item.direction) === "Increases risk").slice(0, 2);
  const decreasing = features.filter((item) => getRiskDirectionText(item.direction) === "Decreases risk").slice(0, 2);

  let factorSentence = "";

  if (increasing.length && decreasing.length) {
    factorSentence = `Key factors such as ${formatFeatureList(increasing)} increased the risk, while ${formatFeatureList(decreasing)} helped lower it.`;
  } else if (increasing.length) {
    factorSentence = `Key factors such as ${formatFeatureList(increasing)} increased the risk.`;
  } else if (decreasing.length) {
    factorSentence = `Key factors such as ${formatFeatureList(decreasing)} contributed to lowering the risk.`;
  } else if (features.length) {
    factorSentence = `Key factors included ${formatFeatureList(features.slice(0, 3))}.`;
  }

  return [
    intro,
    factorSentence,
  ]
    .filter(Boolean)
    .join(" ");
}

function getCategoricalValueLabel(feature, value) {
  const numeric = safeNumber(value);
  if (numeric === null) return null;

  const rounded = Math.round(numeric);
  const labelsByFeature = {
    cp: {
      1: "typical angina",
      2: "atypical angina",
      3: "non-anginal pain",
      4: "asymptomatic",
    },
    restecg: {
      0: "normal",
      1: "ST-T abnormality",
      2: "left ventricular hypertrophy pattern",
    },
    slope: {
      1: "upsloping",
      2: "flat",
      3: "downsloping",
    },
    thal: {
      3: "normal",
      6: "fixed defect",
      7: "reversible defect",
    },
    sex: {
      0: "female",
      1: "male",
    },
  };

  return labelsByFeature[feature]?.[rounded] || null;
}

function buildDirectionFallback(label, directionText) {
  if (directionText === "Increases risk") {
    return `${capitalizeFirst(label)} may be associated with higher cardiovascular concern in this assessment.`;
  }

  if (directionText === "Decreases risk") {
    return `${capitalizeFirst(label)} may be associated with lower cardiovascular concern in this assessment.`;
  }

  return `${capitalizeFirst(label)} should be interpreted in the overall clinical context.`;
}

// These ranges are based on common U.S. clinical reference categories for plain-language explanation
// and should not replace medical judgement or individualized clinical assessment.
function buildFeatureExplanation(item) {
  const feature = item?.feature;
  const value = safeNumber(item?.value);
  const directionText = getRiskDirectionText(item?.direction);
  const label = getClinicalFeatureLabel(feature);

  if (feature === "trestbps" && value !== null) {
    const formatted = formatClinicalNumber(value, 0);

    if (value < 120) {
      return `Resting blood pressure is ${formatted} mmHg, which is within the normal systolic range and may be less supportive of blood pressure-related cardiovascular strain.`;
    }
    if (value <= 129) {
      return `Resting blood pressure is ${formatted} mmHg, which is in the elevated range and can add to cardiovascular strain over time.`;
    }
    if (value <= 139) {
      return `Resting blood pressure is ${formatted} mmHg, which falls in the stage 1 hypertension range and can increase workload on the heart and blood vessels.`;
    }
    return `Resting blood pressure is ${formatted} mmHg, which falls in the stage 2 hypertension range and can place extra strain on the heart and blood vessels.`;
  }

  if (feature === "chol" && value !== null) {
    const formatted = formatClinicalNumber(value, 0);

    if (value < 200) {
      return `Cholesterol is ${formatted} mg/dL, which is within the desirable range and may be less supportive of plaque buildup in the arteries.`;
    }
    if (value <= 239) {
      return `Cholesterol is ${formatted} mg/dL, which is in the borderline high range and may contribute to cardiovascular strain over time.`;
    }
    return `Cholesterol is ${formatted} mg/dL, which is in the high range and may contribute to plaque buildup in arteries.`;
  }

  if (feature === "fbs" && value !== null) {
    if (Math.round(value) === 1) {
      return "Fasting blood sugar is flagged as elevated, which may reflect impaired glucose regulation and can add to cardiovascular risk.";
    }
    if (Math.round(value) === 0) {
      return "Fasting blood sugar is not flagged as elevated, which is less supportive of glucose-related cardiovascular strain in this assessment.";
    }
  }

  if (feature === "age" && value !== null) {
    const formatted = formatClinicalNumber(value, 0);

    if (value < 40) {
      return `Age is ${formatted} years, which falls in a lower baseline risk group and may be associated with lower age-related cardiovascular risk.`;
    }
    if (value <= 59) {
      return `Age is ${formatted} years, which falls in a moderate age-related risk group and can contribute to cardiovascular risk in the right clinical context.`;
    }
    return `Age is ${formatted} years, which falls in a higher age-related risk group and may contribute to greater cardiovascular vulnerability.`;
  }

  if (feature === "exang" && value !== null) {
    if (Math.round(value) === 1) {
      return "Exercise-induced angina is present, which may suggest exertional cardiac stress and supports closer clinical review.";
    }
    if (Math.round(value) === 0) {
      return "Exercise-induced angina is absent, which is less supportive of exercise-related ischemic symptoms in this assessment.";
    }
  }

  if (feature === "ca" && value !== null) {
    const rounded = Math.round(value);
    if (rounded <= 0) {
      return "Major vessel involvement is recorded as 0, which does not indicate major vessel involvement in this assessment.";
    }
    if (rounded === 1) {
      return "Major vessel involvement is recorded as 1, which may indicate some vessel involvement and is associated with higher cardiovascular concern.";
    }
    return `Major vessel involvement is recorded as ${rounded}, which suggests greater vessel involvement and may support higher cardiovascular concern.`;
  }

  if (feature === "cp" && value !== null) {
    const cpLabel = getCategoricalValueLabel(feature, value);
    if (cpLabel) {
      if (directionText === "Decreases risk") {
        return `Chest pain pattern is recorded as ${cpLabel}, which may be less suggestive of higher cardiovascular concern in this assessment.`;
      }
      if (directionText === "Increases risk") {
        return `Chest pain pattern is recorded as ${cpLabel}, which may be associated with higher cardiovascular concern in this assessment.`;
      }
      return `Chest pain pattern is recorded as ${cpLabel}, which should be interpreted in the overall clinical context.`;
    }
  }

  if (feature === "restecg" && value !== null) {
    const ecgLabel = getCategoricalValueLabel(feature, value);
    if (ecgLabel) {
      if (ecgLabel === "normal") {
        return "ECG result is recorded as normal, which is less supportive of ECG-related abnormality in this assessment.";
      }
      return `ECG result is recorded as ${ecgLabel}, which may reflect cardiac electrical changes and supports closer cardiovascular review.`;
    }
  }

  if (feature === "slope" && value !== null) {
    const slopeLabel = getCategoricalValueLabel(feature, value);
    if (slopeLabel) {
      if (directionText === "Decreases risk") {
        return `ST-segment slope is recorded as ${slopeLabel}, which may be less associated with higher cardiovascular concern in this assessment.`;
      }
      if (directionText === "Increases risk") {
        return `ST-segment slope is recorded as ${slopeLabel}, which can be associated with higher cardiovascular concern in this assessment.`;
      }
      return `ST-segment slope is recorded as ${slopeLabel}, which should be interpreted in the overall clinical context.`;
    }
  }

  if (feature === "thal" && value !== null) {
    const thalLabel = getCategoricalValueLabel(feature, value);
    if (thalLabel) {
      if (thalLabel === "normal") {
        return "Thallium stress test result is recorded as normal, which is less supportive of a perfusion-related concern in this assessment.";
      }
      return `Thallium stress test result is recorded as ${thalLabel}, which may support closer evaluation of myocardial perfusion.`;
    }
  }

  if (feature === "thalach" && value !== null) {
    const formatted = formatClinicalNumber(value, 0);
    if (directionText === "Decreases risk") {
      return `Maximum heart rate is ${formatted} bpm during exercise testing, which may be less suggestive of exercise-related limitation in this assessment.`;
    }
    if (directionText === "Increases risk") {
      return `Maximum heart rate is ${formatted} bpm during exercise testing, which may reflect reduced exercise tolerance in this assessment.`;
    }
    return `Maximum heart rate is ${formatted} bpm during exercise testing and should be interpreted in the overall clinical context.`;
  }

  if (feature === "oldpeak" && value !== null) {
    const formatted = formatClinicalNumber(value, 1);
    if (directionText === "Decreases risk") {
      return `ST depression is ${formatted}, which may be less suggestive of exercise-related cardiac stress in this assessment.`;
    }
    if (directionText === "Increases risk") {
      return `ST depression is ${formatted}, which may reflect more exercise-related cardiac stress in this assessment.`;
    }
    return `ST depression is ${formatted} and should be interpreted in the overall clinical context.`;
  }

  if (feature === "sex" && value !== null) {
    const sexLabel = getCategoricalValueLabel(feature, value);
    if (sexLabel) {
      return `Sex is recorded as ${sexLabel}, which is associated with a different baseline cardiovascular risk pattern in population studies.`;
    }
  }

  if (value !== null) {
    const formatted = formatClinicalNumber(value, 1);
    if (formatted !== null) {
      if (directionText === "Increases risk") {
        return `${capitalizeFirst(label)} is ${formatted}, which may be associated with higher cardiovascular concern in this assessment.`;
      }
      if (directionText === "Decreases risk") {
        return `${capitalizeFirst(label)} is ${formatted}, which may be associated with lower cardiovascular concern in this assessment.`;
      }
    }
  }

  return buildDirectionFallback(label, directionText);
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

function renderWorkflowNotice(data) {
  const workflowNoticeEl = pickId("workflowNotice");
  if (!workflowNoticeEl) return;

  const role = data.current_role || "Clinician";
  const riskLevel = data.risk_level || "-";

  let html = "";

  if (role === "Nurse" && riskLevel === "High") {
    html = `
      <div class="workflow-banner workflow-high">
        <strong>High Risk Detected:</strong>
        Doctor has been notified for immediate review. Prepare the patient for urgent physician evaluation.
      </div>
    `;
  } else if (role === "Nurse" && riskLevel === "Medium") {
    html = `
      <div class="workflow-banner workflow-medium">
        <strong>Priority Review:</strong>
        This case should remain in the clinical review queue for timely physician assessment.
      </div>
    `;
  } else if (role === "Doctor") {
    html = `
      <div class="workflow-banner workflow-doctor">
        <strong>Doctor Review Mode:</strong>
        Use this prediction together with clinical examination, symptoms, and professional judgement before final action.
      </div>
    `;
  } else if (role === "Admin") {
    html = `
      <div class="workflow-banner workflow-admin">
        <strong>Administrative View:</strong>
        Prediction results are visible for workflow monitoring and system oversight.
      </div>
    `;
  } else {
    html = `
      <div class="workflow-banner">
        <strong>Clinical Workflow:</strong>
        This result should be interpreted within the care workflow and does not replace clinician judgement.
      </div>
    `;
  }

  workflowNoticeEl.innerHTML = html;
  show(workflowNoticeEl, true);
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

    barEl.classList.remove("low", "medium", "high");

    if (riskLevel === "High") {
      barEl.classList.add("high");
    } else if (riskLevel === "Medium") {
      barEl.classList.add("medium");
    } else {
      barEl.classList.add("low");
    }
  }

  renderWorkflowNotice(data);

  if (explanationSec) {
    const topFeatures = (data.top_features || []).slice(0, 4);
    const allFeatures = data.all_features || [];
    const baseValue = safeNumber(data.base_value) ?? 0;
    const summaryText = buildClinicalExplanation(riskLevel, topFeatures);

    const factorListHtml = topFeatures
      .map((item) => {
        const directionText = getRiskDirectionText(item.direction);
        const toneClass = directionText === "Increases risk" ? "risk-up" : directionText === "Decreases risk" ? "risk-down" : "";

        return `
          <li class="${toneClass}">
            <strong>${getClinicalFeatureLabel(item.feature)}</strong>
            <div class="clinical-factor-text">
              ${buildFeatureExplanation(item)}
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
            ${summaryText}
          </p>

          ${
            factorListHtml
              ? `<ul class="clinical-factor-list">${factorListHtml}</ul>`
              : `<p class="hint">Detailed feature contributions are not available for this prediction.</p>`
          }

          <p class="clinical-conclusion">
            This result should be interpreted along with clinical examination and symptoms.
          </p>

          ${barsHtml}
          ${waterfallHtml}

          <p class="hint">
            Clinical reference ranges are based on commonly accepted guidelines from organizations such as the American Heart Association (AHA) and standard clinical practice.
          </p>
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

  const workflowNoticeEl = pickId("workflowNotice");
  if (workflowNoticeEl) {
    workflowNoticeEl.innerHTML = "";
    show(workflowNoticeEl, false);
  }
}
