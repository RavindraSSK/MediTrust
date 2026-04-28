import { getLatestRiskResult } from "./render.js";

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

function formatFeatureRows(features = []) {
  if (!Array.isArray(features) || !features.length) {
    return `
      <tr>
        <td colspan="4">No feature explanation details available for this report.</td>
      </tr>
    `;
  }

  return features
    .map(
      (feature) => `
        <tr>
          <td>${escapeHtml(feature.feature)}</td>
          <td>${escapeHtml(feature.value)}</td>
          <td>${escapeHtml(feature.direction)}</td>
          <td>${escapeHtml(Number(feature.impact).toFixed(4))}</td>
        </tr>
      `
    )
    .join("");
}

function buildReportMarkup(result, user) {
  const generatedAt = new Date().toLocaleString();
  const clinician = user?.full_name || user?.email || "Clinician";
  const role = user?.role || result.current_role || "Clinician";
  const summaryText =
    result.gemini_summary || result.explanation_summary || "No explanation summary available.";

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>MediTrust Risk Report</title>
  <style>
    body {
      font-family: Arial, Helvetica, sans-serif;
      margin: 32px;
      color: #0f172a;
      line-height: 1.45;
    }

    h1, h2, h3, p {
      margin: 0 0 12px;
    }

    .top {
      margin-bottom: 24px;
      padding-bottom: 16px;
      border-bottom: 2px solid #cbd5e1;
    }

    .meta,
    .summary-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
      margin: 18px 0 24px;
    }

    .card {
      background: #f8fafc;
      border: 1px solid #dbe4f0;
      border-radius: 12px;
      padding: 14px;
    }

    .label {
      font-size: 12px;
      text-transform: uppercase;
      color: #475569;
      letter-spacing: 0.04em;
    }

    .value {
      font-size: 18px;
      font-weight: 700;
      margin-top: 6px;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 12px;
    }

    th,
    td {
      border: 1px solid #cbd5e1;
      padding: 10px;
      text-align: left;
      vertical-align: top;
    }

    th {
      background: #e2e8f0;
    }

    .note {
      margin-top: 20px;
      padding: 14px;
      border-radius: 12px;
      background: #eff6ff;
      border: 1px solid #bfdbfe;
    }

    @media print {
      body {
        margin: 18px;
      }
    }
  </style>
</head>
<body>
  <section class="top">
    <h1>MediTrust Cardiovascular Risk Report</h1>
    <p>Generated: ${escapeHtml(generatedAt)}</p>
    <p>Prepared for: ${escapeHtml(clinician)} (${escapeHtml(role)})</p>
  </section>

  <section class="summary-grid">
    <div class="card">
      <div class="label">Patient Name</div>
      <div class="value">${escapeHtml(result.patient_name || "Not provided")}</div>
    </div>
    <div class="card">
      <div class="label">Risk Level</div>
      <div class="value">${escapeHtml(result.risk_level || "N/A")}</div>
    </div>
    <div class="card">
      <div class="label">Risk Probability</div>
      <div class="value">${escapeHtml(formatPercent(result.risk_probability))}</div>
    </div>
    <div class="card">
      <div class="label">Recommendation</div>
      <div class="value">${escapeHtml(result.triage_recommendation || "No recommendation available")}</div>
    </div>
  </section>

  <section>
    <h2>Clinical Summary</h2>
    <p>${escapeHtml(summaryText)}</p>
  </section>

  <section>
    <h2>Top Feature Contributions</h2>
    <table>
      <thead>
        <tr>
          <th>Feature</th>
          <th>Value</th>
          <th>Direction</th>
          <th>Impact</th>
        </tr>
      </thead>
      <tbody>
        ${formatFeatureRows(result.top_features)}
      </tbody>
    </table>
  </section>

  <section class="note">
    <h3>Prototype Notice</h3>
    <p>This report is generated from the current MediTrust prototype workflow and should support, not replace, clinical judgment.</p>
  </section>
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
    const reportWindow = window.open("", "_blank", "noopener,noreferrer");

    if (!reportWindow) {
      window.alert("Enable pop-ups to open the printable report window.");
      return;
    }

    reportWindow.document.open();
    reportWindow.document.write(buildReportMarkup(result, user));
    reportWindow.document.close();
    reportWindow.focus();
    reportWindow.print();
  } finally {
    if (triggerButton) {
      triggerButton.disabled = false;
      triggerButton.textContent = "Download PDF Report";
    }
  }
}
