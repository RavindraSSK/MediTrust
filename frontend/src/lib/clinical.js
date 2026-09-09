/**
 * Clinical vocabulary shared by the assessment form, SHAP explanation panel,
 * dashboards and the printable report. Codes follow the canonical UCI
 * Cleveland encoding exposed by the API (/model/encoding).
 */
import { safeNumber } from "./format.js";

export const FEATURE_LABELS = {
  age: "Age",
  sex: "Sex",
  cp: "Chest pain type",
  trestbps: "Resting blood pressure",
  chol: "Total cholesterol",
  fbs: "Fasting blood sugar > 120 mg/dL",
  restecg: "Resting ECG result",
  thalach: "Maximum heart rate achieved",
  exang: "Exercise-induced angina",
  oldpeak: "ST depression during exercise",
  slope: "ST segment slope",
  ca: "Major vessels count",
  thal: "Thallium stress test result",
};

const CLINICAL_LABELS = {
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
  sex: "sex",
};

export const VALUE_LABELS = {
  sex: { 0: "Female", 1: "Male" },
  cp: { 1: "Typical angina", 2: "Atypical angina", 3: "Non-anginal pain", 4: "Asymptomatic" },
  fbs: { 0: "No", 1: "Yes" },
  restecg: { 0: "Normal", 1: "ST-T abnormality", 2: "Left ventricular hypertrophy pattern" },
  exang: { 0: "No", 1: "Yes" },
  slope: { 1: "Upsloping", 2: "Flat", 3: "Downsloping" },
  thal: { 3: "Normal", 6: "Fixed defect", 7: "Reversible defect" },
};

export const DEMO_PATIENT = {
  first_name: "Demo",
  last_name: "Patient",
  age: 58,
  sex: 1,
  cp: 4,
  trestbps: 156,
  chol: 286,
  fbs: 1,
  restecg: 1,
  thalach: 118,
  exang: 1,
  oldpeak: 2.8,
  slope: 2,
  ca: 2,
  thal: 7,
};

/** Field definitions for the assessment form (order, defaults, hints). */
export const CLINICAL_FIELDS = [
  { id: "sex", label: "Sex", type: "select", options: [[1, "Male"], [0, "Female"]], default: 1, hint: "Biological sex of the patient." },
  {
    id: "cp",
    label: "Chest pain type",
    type: "select",
    options: [[1, "Typical angina"], [2, "Atypical angina"], [3, "Non-anginal pain"], [4, "Asymptomatic"]],
    default: 3,
    hint: "Type of chest discomfort reported by the patient.",
  },
  { id: "trestbps", label: "Resting blood pressure", type: "number", min: 50, max: 260, default: 140, hint: "Resting blood pressure in mmHg." },
  { id: "chol", label: "Cholesterol level", type: "number", min: 50, max: 800, default: 250, hint: "Serum cholesterol level in mg/dL." },
  { id: "fbs", label: "High fasting blood sugar", type: "select", options: [[0, "No"], [1, "Yes"]], default: 0, hint: "Whether fasting blood sugar is above 120 mg/dL." },
  {
    id: "restecg",
    label: "Resting ECG result",
    type: "select",
    options: [[0, "Normal"], [1, "ST-T abnormality"], [2, "LV hypertrophy"]],
    default: 1,
    hint: "Electrocardiogram result at rest.",
  },
  { id: "thalach", label: "Maximum heart rate", type: "number", min: 30, max: 250, default: 150, hint: "Maximum heart rate achieved during exercise test." },
  { id: "exang", label: "Exercise-induced angina", type: "select", options: [[0, "No"], [1, "Yes"]], default: 0, hint: "Indicates chest pain triggered by exercise." },
  { id: "oldpeak", label: "ST depression (oldpeak)", type: "number", min: 0, max: 10, step: 0.1, default: 1.2, hint: "ST depression induced by exercise relative to rest." },
  { id: "slope", label: "ST segment slope", type: "select", options: [[1, "Upsloping"], [2, "Flat"], [3, "Downsloping"]], default: 2, hint: "Slope of the peak exercise ST segment." },
  { id: "ca", label: "Major vessels count", type: "select", options: [[0, "0"], [1, "1"], [2, "2"], [3, "3"]], default: 0, hint: "Number of major vessels observed by fluoroscopy." },
  {
    id: "thal",
    label: "Thallium test result",
    type: "select",
    options: [[3, "Normal"], [6, "Fixed defect"], [7, "Reversible defect"]],
    default: 3,
    hint: "Thallium stress test result category.",
  },
];

export function getClinicalFeatureLabel(feature) {
  return CLINICAL_LABELS[feature] || feature;
}

export function getFeatureLabel(feature) {
  return FEATURE_LABELS[feature] || feature;
}

export function getRiskDirectionText(direction) {
  const normalized = String(direction || "").toLowerCase();
  if (normalized.includes("decrease")) return "Decreases risk";
  if (normalized.includes("increase")) return "Increases risk";
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

export function formatFeatureValue(feature, value) {
  const rounded = Math.round(Number(value));
  if (VALUE_LABELS[feature]?.[rounded]) return VALUE_LABELS[feature][rounded];
  if (feature === "trestbps") return `${formatClinicalNumber(value, 0)} mmHg`;
  if (feature === "chol") return `${formatClinicalNumber(value, 0)} mg/dL`;
  if (feature === "thalach") return `${formatClinicalNumber(value, 0)} bpm`;
  if (feature === "oldpeak") return `${formatClinicalNumber(value, 1)} mm`;
  if (feature === "age") return `${formatClinicalNumber(value, 0)} years`;
  return formatClinicalNumber(value, 1) ?? "N/A";
}

function getCategoricalValueLabel(feature, value) {
  const numeric = safeNumber(value);
  if (numeric === null) return null;
  const label = VALUE_LABELS[feature]?.[Math.round(numeric)];
  return label ? label.toLowerCase() : null;
}

function formatFeatureList(features) {
  const labels = [...new Set(features.map((item) => getClinicalFeatureLabel(item.feature)).filter(Boolean))];
  if (!labels.length) return "";
  if (labels.length === 1) return labels[0];
  if (labels.length === 2) return `${labels[0]} and ${labels[1]}`;
  return `${labels.slice(0, -1).join(", ")}, and ${labels[labels.length - 1]}`;
}

export function buildClinicalExplanation(riskLevel, features) {
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
  return [intro, factorSentence].filter(Boolean).join(" ");
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

// Reference ranges follow common U.S. clinical categories (ACC/AHA, NCEP ATP III) for plain-language
// explanation only; they do not replace medical judgment. See the evidence panel for cited sources.
export function buildFeatureExplanation(item) {
  const feature = item?.feature;
  const value = safeNumber(item?.value);
  const directionText = getRiskDirectionText(item?.direction);
  const label = getClinicalFeatureLabel(feature);

  if (feature === "trestbps" && value !== null) {
    const formatted = formatClinicalNumber(value, 0);
    if (value < 120) return `Resting blood pressure is ${formatted} mmHg, which is within the normal systolic range and may be less supportive of blood pressure-related cardiovascular strain.`;
    if (value <= 129) return `Resting blood pressure is ${formatted} mmHg, which is in the elevated range and can add to cardiovascular strain over time.`;
    if (value <= 139) return `Resting blood pressure is ${formatted} mmHg, which falls in the stage 1 hypertension range and can increase workload on the heart and blood vessels.`;
    return `Resting blood pressure is ${formatted} mmHg, which falls in the stage 2 hypertension range and can place extra strain on the heart and blood vessels.`;
  }
  if (feature === "chol" && value !== null) {
    const formatted = formatClinicalNumber(value, 0);
    if (value < 200) return `Cholesterol is ${formatted} mg/dL, which is within the desirable range and may be less supportive of plaque buildup in the arteries.`;
    if (value <= 239) return `Cholesterol is ${formatted} mg/dL, which is in the borderline high range and may contribute to cardiovascular strain over time.`;
    return `Cholesterol is ${formatted} mg/dL, which is in the high range and may contribute to plaque buildup in arteries.`;
  }
  if (feature === "fbs" && value !== null) {
    if (Math.round(value) === 1) return "Fasting blood sugar is flagged as elevated, which may reflect impaired glucose regulation and can add to cardiovascular risk.";
    return "Fasting blood sugar is not flagged as elevated, which is less supportive of glucose-related cardiovascular strain in this assessment.";
  }
  if (feature === "age" && value !== null) {
    const formatted = formatClinicalNumber(value, 0);
    if (value < 40) return `Age is ${formatted} years, which falls in a lower baseline risk group and may be associated with lower age-related cardiovascular risk.`;
    if (value <= 59) return `Age is ${formatted} years, which falls in a moderate age-related risk group and can contribute to cardiovascular risk in the right clinical context.`;
    return `Age is ${formatted} years, which falls in a higher age-related risk group and may contribute to greater cardiovascular vulnerability.`;
  }
  if (feature === "exang" && value !== null) {
    if (Math.round(value) === 1) return "Exercise-induced angina is present, which may suggest exertional cardiac stress and supports closer clinical review.";
    return "Exercise-induced angina is absent, which is less supportive of exercise-related ischemic symptoms in this assessment.";
  }
  if (feature === "ca" && value !== null) {
    const rounded = Math.round(value);
    if (rounded <= 0) return "Major vessel involvement is recorded as 0, which does not indicate major vessel involvement in this assessment.";
    if (rounded === 1) return "Major vessel involvement is recorded as 1, which may indicate some vessel involvement and is associated with higher cardiovascular concern.";
    return `Major vessel involvement is recorded as ${rounded}, which suggests greater vessel involvement and may support higher cardiovascular concern.`;
  }
  if (feature === "cp" && value !== null) {
    const cpLabel = getCategoricalValueLabel(feature, value);
    if (cpLabel) {
      if (directionText === "Decreases risk") return `Chest pain pattern is recorded as ${cpLabel}, which may be less suggestive of higher cardiovascular concern in this assessment.`;
      if (directionText === "Increases risk") return `Chest pain pattern is recorded as ${cpLabel}, which may be associated with higher cardiovascular concern in this assessment.`;
      return `Chest pain pattern is recorded as ${cpLabel}, which should be interpreted in the overall clinical context.`;
    }
  }
  if (feature === "restecg" && value !== null) {
    const ecgLabel = getCategoricalValueLabel(feature, value);
    if (ecgLabel) {
      if (ecgLabel === "normal") return "ECG result is recorded as normal, which is less supportive of ECG-related abnormality in this assessment.";
      return `ECG result is recorded as ${ecgLabel}, which may reflect cardiac electrical changes and supports closer cardiovascular review.`;
    }
  }
  if (feature === "slope" && value !== null) {
    const slopeLabel = getCategoricalValueLabel(feature, value);
    if (slopeLabel) {
      if (directionText === "Decreases risk") return `ST-segment slope is recorded as ${slopeLabel}, which may be less associated with higher cardiovascular concern in this assessment.`;
      if (directionText === "Increases risk") return `ST-segment slope is recorded as ${slopeLabel}, which can be associated with higher cardiovascular concern in this assessment.`;
      return `ST-segment slope is recorded as ${slopeLabel}, which should be interpreted in the overall clinical context.`;
    }
  }
  if (feature === "thal" && value !== null) {
    const thalLabel = getCategoricalValueLabel(feature, value);
    if (thalLabel) {
      if (thalLabel === "normal") return "Thallium stress test result is recorded as normal, which is less supportive of a perfusion-related concern in this assessment.";
      return `Thallium stress test result is recorded as ${thalLabel}, which may support closer evaluation of myocardial perfusion.`;
    }
  }
  if (feature === "thalach" && value !== null) {
    const formatted = formatClinicalNumber(value, 0);
    if (directionText === "Decreases risk") return `Maximum heart rate is ${formatted} bpm during exercise testing, which may be less suggestive of exercise-related limitation in this assessment.`;
    if (directionText === "Increases risk") return `Maximum heart rate is ${formatted} bpm during exercise testing, which may reflect reduced exercise tolerance in this assessment.`;
    return `Maximum heart rate is ${formatted} bpm during exercise testing and should be interpreted in the overall clinical context.`;
  }
  if (feature === "oldpeak" && value !== null) {
    const formatted = formatClinicalNumber(value, 1);
    if (directionText === "Decreases risk") return `ST depression is ${formatted}, which may be less suggestive of exercise-related cardiac stress in this assessment.`;
    if (directionText === "Increases risk") return `ST depression is ${formatted}, which may reflect more exercise-related cardiac stress in this assessment.`;
    return `ST depression is ${formatted} and should be interpreted in the overall clinical context.`;
  }
  if (feature === "sex" && value !== null) {
    const sexLabel = getCategoricalValueLabel(feature, value);
    if (sexLabel) return `Sex is recorded as ${sexLabel}, which is associated with a different baseline cardiovascular risk pattern in population studies.`;
  }
  if (value !== null) {
    const formatted = formatClinicalNumber(value, 1);
    if (formatted !== null) {
      if (directionText === "Increases risk") return `${capitalizeFirst(label)} is ${formatted}, which may be associated with higher cardiovascular concern in this assessment.`;
      if (directionText === "Decreases risk") return `${capitalizeFirst(label)} is ${formatted}, which may be associated with lower cardiovascular concern in this assessment.`;
    }
  }
  return buildDirectionFallback(label, directionText);
}
