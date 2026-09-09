import { Link } from "react-router-dom";

import { formatRiskPercent } from "../lib/format.js";

function WorkflowNotice({ role, riskLevel }) {
  if (role === "Nurse" && riskLevel === "High") {
    return (
      <div className="workflow-banner workflow-high">
        <strong>High Risk Detected:</strong> This case is ready for nurse escalation to a doctor. Use the nurse dashboard
        to escalate high-risk cases.
      </div>
    );
  }
  if (role === "Nurse" && riskLevel === "Medium") {
    return (
      <div className="workflow-banner workflow-medium">
        <strong>Priority Review:</strong> This case should remain in the clinical review queue for timely physician
        assessment.
      </div>
    );
  }
  if (role === "Doctor") {
    return (
      <div className="workflow-banner workflow-doctor">
        <strong>Doctor Review Mode:</strong> Use this prediction together with clinical examination, symptoms, and
        professional judgment before final action.
      </div>
    );
  }
  if (role === "Admin") {
    return (
      <div className="workflow-banner workflow-admin">
        <strong>Administrative View:</strong> Prediction results are visible for workflow monitoring and system
        oversight.
      </div>
    );
  }
  return (
    <div className="workflow-banner">
      <strong>Clinical Workflow:</strong> This result should be interpreted within the care workflow and does not replace
      clinician judgment.
    </div>
  );
}

export default function RiskResultCard({ result, role, dashboardPath, onDownload, downloading }) {
  const riskLevel = result.risk_level || "-";
  const score = Number(result.risk_probability);
  const pct = Number.isFinite(score) ? Math.min(100, Math.max(0, Math.round(score * 100))) : 0;
  const barClass = riskLevel === "High" ? "high" : riskLevel === "Medium" ? "medium" : "low";
  const badgeText = riskLevel === "High" ? "Needs attention" : riskLevel === "Medium" ? "Priority review" : "Low concern";

  return (
    <div id="result" className="result show visible" aria-live="polite">
      <div className="risk-fluid">
        <div className="result-title">Assessment Result</div>
        <div id="riskScore" className="risk-score-big">
          {Number.isFinite(score) ? formatRiskPercent(score) : "-"}
        </div>
        <div className="risk-inline">
          <div id="riskLevel" className="risk-level-text">
            {riskLevel}
          </div>
          <div id="badge" className={`risk-status-badge ${barClass}`}>
            {badgeText}
          </div>
        </div>
        <div className="risk-meter">
          <div className="meter-labels">
            <span>Lower</span>
            <span>Higher</span>
          </div>
          <div className="meter-track">
            <div id="bar" className={`meter-fill ${barClass}`} style={{ width: `${pct}%` }} />
          </div>
        </div>
        <div id="note" className="risk-note">
          {result.triage_recommendation || "Maintain healthy habits and follow routine checkups as recommended."}
          {result.thresholds ? (
            <span className="hint" style={{ display: "block", marginTop: 6 }}>
              Probability of coronary artery disease. Bands: Low &lt; {Math.round(result.thresholds.rule_out * 100)}%, High
              &ge; {Math.round(result.thresholds.rule_in * 100)}% ({result.model_name || "model"}
              {result.model_version ? ` v${result.model_version}` : ""}).
            </span>
          ) : null}
        </div>
        <div id="workflowNotice" className="workflow-notice">
          <WorkflowNotice role={role} riskLevel={riskLevel} />
        </div>
        <div className="result-actions">
          <Link id="returnDashboardBtn" className="btn-secondary result-link-btn" to={dashboardPath}>
            Return to Dashboard
          </Link>
          <button id="downloadReportBtn" className="btn-secondary result-link-btn" type="button" onClick={onDownload} disabled={downloading}>
            {downloading ? "Preparing Report..." : "Download PDF Report"}
          </button>
        </div>
      </div>
    </div>
  );
}
