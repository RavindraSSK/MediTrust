import { Link } from "react-router-dom";

import { useBodyClass } from "../hooks/useBodyClass.js";

export default function DemoPreviewPage() {
  useBodyClass("dashboard-page");
  return (
    <>
      <div className="page-bg" />
      <div className="page-overlay" />
      <main className="dashboard-shell">
        <section className="dashboard-card assessment-page">
          <div className="topbar">
            <div>
              <h1>MediTrust</h1>
              <div className="subtitle">
                Explore a realistic clinician-facing preview of the MediTrust cardiovascular risk result screen using static sample data.
              </div>
              <div className="actions">
                <Link to="/" className="btn-secondary result-link-btn">Back to Login</Link>
                <Link to="/assessment?demo=true" className="mini-btn">Open Assessment</Link>
              </div>
            </div>
            <div className="pill">Demo Preview</div>
          </div>

          <div className="quick-overview">
            <div className="overview-card">
              <small>Sample Scenario</small>
              <strong>Demo patient snapshot: age 67, total cholesterol 286 mg/dL, resting blood pressure 156 mmHg, and exercise-related symptoms indicating elevated cardiovascular concern.</strong>
            </div>
          </div>

          <section className="section-box">
            <div className="section-header">
              <div>
                <div className="section-title">Assessment Result</div>
                <div className="section-subtitle">Static product preview of a completed MediTrust risk assessment.</div>
              </div>
              <span className="demo-chip">Demo Preview – Sample Output</span>
            </div>
            <div className="result show visible" aria-live="polite">
              <div className="risk-fluid">
                <div className="result-title">Assessment Result</div>
                <div className="risk-score-big">78%</div>
                <div className="risk-inline">
                  <div className="risk-level-text">High Risk</div>
                  <div className="risk-status-badge high">Needs attention</div>
                </div>
                <div className="risk-meter">
                  <div className="meter-labels"><span>Lower</span><span>Higher</span></div>
                  <div className="meter-track"><div className="meter-fill high" style={{ width: "78%" }} /></div>
                </div>
                <div className="risk-note">
                  Sample clinical summary: Elevated cholesterol, high resting blood pressure, and older age combine to suggest a clinically significant cardiovascular risk profile in this demo case.
                </div>
                <div className="workflow-notice">
                  <div className="workflow-banner workflow-high"><strong>Recommended Action:</strong> Immediate physician evaluation recommended.</div>
                </div>
              </div>
            </div>
          </section>

          <section className="section-box">
            <div className="section-header">
              <div>
                <div className="section-title">Top 3 Contributing Factors</div>
                <div className="section-subtitle">Key drivers of the sample high-risk result shown above.</div>
              </div>
            </div>
            <div className="professional-clinical-box">
              <p className="clinical-summary-text">
                This static preview reflects a patient pattern with several reinforcing cardiovascular risk markers. The combined effect of lipid burden, uncontrolled blood pressure, and age pushes the sample assessment into a high-risk range.
              </p>
              <ul className="clinical-factor-list">
                <li className="risk-up"><strong>Cholesterol</strong><div className="clinical-factor-text">Total cholesterol is elevated, suggesting a greater likelihood of atherosclerotic burden and increased cardiovascular event risk.</div></li>
                <li className="risk-up"><strong>Blood Pressure</strong><div className="clinical-factor-text">A resting blood pressure of 156 mmHg indicates hypertension that meaningfully increases the overall risk estimate.</div></li>
                <li className="risk-up"><strong>Age</strong><div className="clinical-factor-text">Older age raises baseline cardiovascular vulnerability and amplifies the significance of the other abnormal findings.</div></li>
              </ul>
              <p className="clinical-conclusion">
                Clinical Summary: This preview demonstrates how MediTrust can present a clinician-friendly interpretation of model output while keeping the final care decision with the physician.
              </p>
            </div>
          </section>

          <div className="footer">
            <div>© 2026 MediTrust</div>
            <div>Static demo assessment preview</div>
          </div>
        </section>
      </main>
    </>
  );
}
