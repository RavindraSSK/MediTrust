import { getLatestRiskResult } from "./render.js?v=20260609a";

const FEATURE_LABELS = {
  age: "Age",
  sex: "Sex",
  cp: "Chest pain type",
  trestbps: "Resting blood pressure",
  chol: "Serum cholesterol",
  fbs: "Fasting blood sugar > 120 mg/dL",
  restecg: "Resting ECG result",
  thalach: "Maximum heart rate achieved",
  exang: "Exercise-induced angina",
  oldpeak: "ST depression during exercise",
  slope: "ST segment slope",
  ca: "Major vessels count",
  thal: "Thallium stress test result",
};

const VALUE_LABELS = {
  sex: { 0: "Female", 1: "Male" },
  cp: { 1: "Typical angina", 2: "Atypical angina", 3: "Non-anginal pain", 4: "Asymptomatic" },
  fbs: { 0: "No", 1: "Yes" },
  restecg: { 0: "Normal", 1: "ST-T abnormality", 2: "Left ventricular hypertrophy pattern" },
  exang: { 0: "No", 1: "Yes" },
  slope: { 1: "Upsloping", 2: "Flat", 3: "Downsloping" },
  thal: { 3: "Normal", 6: "Fixed defect", 7: "Reversible defect" },
};

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function formatPercent(value) {
  const num = Number(value);
  return Number.isFinite(num) ? `${(num * 100).toFixed(1)}%` : "N/A";
}

function formatNumber(value, digits = 1) {
  const num = Number(value);
  if (!Number.isFinite(num)) return "N/A";
  return Number.isInteger(num) ? String(num) : num.toFixed(digits).replace(/\.0$/, "");
}

function formatSigned(value) {
  const num = Number(value);
  if (!Number.isFinite(num)) return "N/A";
  return `${num >= 0 ? "+" : ""}${num.toFixed(4)}`;
}

function formatFeatureValue(feature, value) {
  const rounded = Math.round(Number(value));
  if (VALUE_LABELS[feature]?.[rounded]) return VALUE_LABELS[feature][rounded];
  if (feature === "trestbps") return `${formatNumber(value, 0)} mmHg`;
  if (feature === "chol") return `${formatNumber(value, 0)} mg/dL`;
  if (feature === "thalach") return `${formatNumber(value, 0)} bpm`;
  if (feature === "oldpeak") return formatNumber(value, 1);
  return formatNumber(value, 0);
}

function formatDateTime(value = new Date()) {
  return new Date(value).toLocaleString();
}

function buildReportId(result) {
  const timestamp = new Date().toISOString().replace(/[-:TZ.]/g, "").slice(0, 14);
  const namePart = String(result.patient_name || "patient")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 18);
  return `MT-${timestamp}-${namePart || "case"}`.toUpperCase();
}

function riskClass(riskLevel) {
  const level = String(riskLevel || "").toLowerCase();
  if (level === "high") return "risk-high";
  if (level === "medium") return "risk-medium";
  if (level === "low") return "risk-low";
  return "risk-neutral";
}

function buildClinicalInputsRows(inputs = {}) {
  const orderedKeys = [
    "age",
    "sex",
    "cp",
    "trestbps",
    "chol",
    "fbs",
    "restecg",
    "thalach",
    "exang",
    "oldpeak",
    "slope",
    "ca",
    "thal",
  ];

  return orderedKeys
    .filter((key) => inputs[key] !== undefined && inputs[key] !== null && inputs[key] !== "")
    .map((key) => `
      <tr>
        <td>${escapeHtml(FEATURE_LABELS[key] || key)}</td>
        <td>${escapeHtml(formatFeatureValue(key, inputs[key]))}</td>
        <td>${escapeHtml(getReferenceText(key))}</td>
      </tr>
    `)
    .join("");
}

function getReferenceText(feature) {
  const references = {
    age: "Completed years",
    sex: "Recorded demographic input",
    cp: "Assessment category",
    trestbps: "Systolic resting BP",
    chol: "Serum cholesterol",
    fbs: "Binary flag",
    restecg: "Resting ECG category",
    thalach: "Exercise test value",
    exang: "Exercise symptom flag",
    oldpeak: "ST depression value",
    slope: "Exercise ST segment",
    ca: "0-3 vessels",
    thal: "Stress test category",
  };
  return references[feature] || "Model input";
}

function buildFeatureRows(features = []) {
  if (!Array.isArray(features) || !features.length) {
    return `
      <tr>
        <td colspan="5">No SHAP feature explanation details were returned for this prediction.</td>
      </tr>
    `;
  }

  return features
    .map((feature, index) => `
      <tr>
        <td>${index + 1}</td>
        <td>${escapeHtml(FEATURE_LABELS[feature.feature] || feature.feature || "Clinical feature")}</td>
        <td>${escapeHtml(formatFeatureValue(feature.feature, feature.value))}</td>
        <td>${escapeHtml(feature.direction || "Influences risk")}</td>
        <td>${escapeHtml(formatSigned(feature.impact))}</td>
      </tr>
    `)
    .join("");
}

function buildFactorSummary(features = []) {
  const increasing = features
    .filter((item) => String(item.direction || "").toLowerCase().includes("increase"))
    .slice(0, 3)
    .map((item) => FEATURE_LABELS[item.feature] || item.feature);
  const reducing = features
    .filter((item) => String(item.direction || "").toLowerCase().includes("decrease"))
    .slice(0, 3)
    .map((item) => FEATURE_LABELS[item.feature] || item.feature);

  return `
    <div class="factor-columns">
      <div>
        <h3>Risk-Increasing Signals</h3>
        <ul>
          ${(increasing.length ? increasing : ["No dominant increasing signal returned"]).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}
        </ul>
      </div>
      <div>
        <h3>Risk-Reducing Signals</h3>
        <ul>
          ${(reducing.length ? reducing : ["No dominant reducing signal returned"]).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}
        </ul>
      </div>
    </div>
  `;
}

function buildReportMarkup(result, user) {
  const generatedAt = formatDateTime();
  const clinician = user?.full_name || [user?.first_name, user?.last_name].filter(Boolean).join(" ") || user?.email || "Clinician";
  const role = user?.role || result.current_role || "Clinician";
  const inputs = result.clinical_inputs || {};
  const reportId = buildReportId(result);
  const summaryText =
    result.gemini_summary ||
    result.explanation_summary ||
    "The model returned a risk estimate, but no AI narrative summary was available for this report.";

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>MediTrust Hospital Risk Report</title>
  <style>
    * { box-sizing: border-box; }

    body {
      margin: 0;
      padding: 28px;
      color: #102033;
      font-family: Arial, Helvetica, sans-serif;
      line-height: 1.45;
      background: #eef3f8;
    }

    .page {
      max-width: 980px;
      margin: 0 auto;
      background: #ffffff;
      border: 1px solid #cfd9e6;
      box-shadow: 0 18px 48px rgba(16, 32, 51, 0.16);
    }

    .masthead {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 18px;
      padding: 24px 28px;
      color: #ffffff;
      background: #12355b;
      border-bottom: 5px solid #2f80ed;
    }

    .masthead h1 {
      margin: 0 0 6px;
      font-size: 28px;
      letter-spacing: 0;
    }

    .masthead p,
    .report-meta p,
    h2,
    h3 {
      margin: 0;
    }

    .hospital-tag {
      padding: 10px 14px;
      border: 1px solid rgba(255, 255, 255, 0.35);
      border-radius: 8px;
      text-align: right;
      font-weight: 700;
    }

    .report-meta {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
      padding: 18px 28px;
      border-bottom: 1px solid #d8e2ee;
      background: #f8fbff;
    }

    .meta-item,
    .result-card,
    .notice,
    .section {
      border: 1px solid #d8e2ee;
      border-radius: 8px;
      background: #ffffff;
    }

    .meta-item {
      padding: 11px 12px;
    }

    .label {
      display: block;
      margin-bottom: 5px;
      color: #5c7088;
      font-size: 11px;
      font-weight: 800;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }

    .value {
      color: #102033;
      font-size: 15px;
      font-weight: 800;
    }

    .content {
      padding: 24px 28px 28px;
    }

    .result-grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 18px;
    }

    .result-card {
      padding: 15px;
      min-height: 94px;
    }

    .result-card strong {
      display: block;
      margin-top: 7px;
      font-size: 22px;
    }

    .risk-high strong { color: #b42318; }
    .risk-medium strong { color: #b76e00; }
    .risk-low strong { color: #177245; }
    .risk-neutral strong { color: #586a7e; }

    .section {
      margin-top: 16px;
      padding: 18px;
    }

    .section h2 {
      color: #12355b;
      font-size: 18px;
      margin-bottom: 12px;
      padding-bottom: 8px;
      border-bottom: 1px solid #d8e2ee;
    }

    .section h3 {
      color: #234968;
      font-size: 14px;
      margin-bottom: 8px;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 8px;
      font-size: 13px;
    }

    th,
    td {
      padding: 10px;
      border: 1px solid #d0dbe8;
      text-align: left;
      vertical-align: top;
    }

    th {
      color: #12355b;
      background: #edf4fb;
      font-size: 12px;
      text-transform: uppercase;
    }

    .factor-columns {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
      margin-top: 12px;
    }

    ul {
      margin: 0;
      padding-left: 18px;
    }

    .notice {
      margin-top: 16px;
      padding: 14px 16px;
      color: #12355b;
      background: #eff6ff;
      border-color: #b9d7ff;
      font-weight: 700;
    }

    .signature-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 16px;
      margin-top: 22px;
    }

    .signature-box {
      min-height: 72px;
      padding-top: 42px;
      border-top: 1px solid #7f91a6;
      color: #4b5f72;
      font-size: 12px;
      font-weight: 700;
    }

    .footer {
      margin-top: 18px;
      padding-top: 12px;
      border-top: 1px solid #d8e2ee;
      color: #5c7088;
      font-size: 11px;
    }

    .print-actions {
      display: flex;
      justify-content: flex-end;
      gap: 10px;
      margin: 0 auto 14px;
      max-width: 980px;
    }

    .print-actions button {
      border: none;
      border-radius: 8px;
      padding: 10px 14px;
      color: #ffffff;
      background: #1d67c4;
      font-weight: 800;
      cursor: pointer;
    }

    @media print {
      body {
        padding: 0;
        background: #ffffff;
      }

      .page {
        border: none;
        box-shadow: none;
      }

      .print-actions {
        display: none;
      }

      .section {
        break-inside: avoid;
      }
    }
  </style>
</head>
<body>
  <div class="print-actions">
    <button type="button" onclick="window.print()">Save / Print PDF</button>
  </div>

  <main class="page">
    <header class="masthead">
      <div>
        <h1>MediTrust Hospital Risk Laboratory Report</h1>
        <p>Cardiovascular Risk Prediction Panel with Explainable AI Summary</p>
      </div>
      <div class="hospital-tag">
        Decision Support<br />
        Prototype Report
      </div>
    </header>

    <section class="report-meta">
      <div class="meta-item">
        <span class="label">Report ID</span>
        <span class="value">${escapeHtml(reportId)}</span>
      </div>
      <div class="meta-item">
        <span class="label">Generated</span>
        <span class="value">${escapeHtml(generatedAt)}</span>
      </div>
      <div class="meta-item">
        <span class="label">Ordering User</span>
        <span class="value">${escapeHtml(clinician)}</span>
      </div>
      <div class="meta-item">
        <span class="label">Role</span>
        <span class="value">${escapeHtml(role)}</span>
      </div>
    </section>

    <div class="content">
      <section class="result-grid">
        <div class="result-card">
          <span class="label">Patient</span>
          <strong>${escapeHtml(result.patient_name || "Not provided")}</strong>
        </div>
        <div class="result-card ${riskClass(result.risk_level)}">
          <span class="label">Predicted Risk</span>
          <strong>${escapeHtml(result.risk_level || "N/A")}</strong>
        </div>
        <div class="result-card">
          <span class="label">Probability</span>
          <strong>${escapeHtml(formatPercent(result.risk_probability ?? result.risk_score))}</strong>
        </div>
        <div class="result-card">
          <span class="label">Triage Recommendation</span>
          <strong>${escapeHtml(result.triage_recommendation || "Clinical review")}</strong>
        </div>
      </section>

      <div class="notice">
        For decision support only, not a replacement for clinical judgment. This report does not diagnose disease.
      </div>

      <section class="section">
        <h2>Clinical Summary</h2>
        <p>${escapeHtml(summaryText)}</p>
      </section>

      <section class="section">
        <h2>Submitted Cardiovascular Panel Values</h2>
        <table>
          <thead>
            <tr>
              <th>Test / Input</th>
              <th>Reported Value</th>
              <th>Reference / Unit</th>
            </tr>
          </thead>
          <tbody>
            ${buildClinicalInputsRows(inputs) || `<tr><td colspan="3">No detailed clinical inputs were available.</td></tr>`}
          </tbody>
        </table>
      </section>

      <section class="section">
        <h2>Explainable AI Findings</h2>
        ${buildFactorSummary(result.top_features || [])}
        <table>
          <thead>
            <tr>
              <th>Rank</th>
              <th>Feature</th>
              <th>Value</th>
              <th>Direction</th>
              <th>SHAP Impact</th>
            </tr>
          </thead>
          <tbody>
            ${buildFeatureRows(result.top_features || [])}
          </tbody>
        </table>
      </section>

      <section class="section">
        <h2>Model and Workflow Details</h2>
        <table>
          <tbody>
            <tr>
              <th>Model Type</th>
              <td>Logistic Regression cardiovascular risk model</td>
            </tr>
            <tr>
              <th>Explainability Method</th>
              <td>SHAP feature contribution analysis</td>
            </tr>
            <tr>
              <th>AI Narrative</th>
              <td>Gemini-assisted clinical-style summary when available; fallback model summary otherwise</td>
            </tr>
            <tr>
              <th>Recommended Workflow</th>
              <td>Nurse creates case, system predicts risk, SHAP explains factors, high-risk cases may be escalated to doctor for review.</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section class="section">
        <h2>Clinical Safety Notes</h2>
        <p>
          This student project report is intended for portfolio demonstration and simulated clinical workflow support.
          It should be interpreted alongside symptoms, examination findings, ECG, vitals, lab values, and clinician judgment.
          It must not be used as a standalone diagnosis, treatment order, or emergency decision system.
        </p>
      </section>

      <section class="signature-grid">
        <div class="signature-box">Clinician / Reviewer Signature</div>
        <div class="signature-box">Date / Time Reviewed</div>
      </section>

      <footer class="footer">
        MediTrust Explainable AI Healthcare Risk Prediction Platform. Generated by the web application for demo and documentation use.
      </footer>
    </div>
  </main>

  <script>
    window.addEventListener("load", () => {
      setTimeout(() => window.print(), 350);
    });
  </script>
</body>
</html>`;
}

export function downloadLatestRiskReport(elements, user = null) {
  const result = getLatestRiskResult();

  if (!result) {
    window.alert("Generate a patient risk result before downloading the report.");
    return;
  }

  const triggerButton = elements?.downloadReportBtn;
  if (triggerButton) {
    triggerButton.disabled = true;
    triggerButton.textContent = "Preparing Report...";
  }

  try {
    const reportWindow = window.open("", "_blank");

    if (!reportWindow) {
      window.alert("Enable pop-ups to open the printable PDF report window.");
      return;
    }

    reportWindow.document.open();
    reportWindow.document.write(buildReportMarkup(result, user));
    reportWindow.document.close();
    reportWindow.focus();
  } finally {
    if (triggerButton) {
      triggerButton.disabled = false;
      triggerButton.textContent = "Download PDF Report";
    }
  }
}
