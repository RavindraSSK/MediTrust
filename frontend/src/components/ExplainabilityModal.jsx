import ClinicalContextPanel from "./ClinicalContextPanel.jsx";
import { formatNumber, formatRiskPercent } from "../lib/format.js";

function FactorList({ items, emptyText }) {
  if (!items?.length) return <div className="empty-clinical-note">{emptyText}</div>;
  return (
    <div className="factor-list">
      {items.map((item) => (
        <article className="factor-item" key={item.feature || item.label}>
          <strong>{item.label || item.feature || "Clinical feature"}</strong>
          <p>{item.explanation || "This feature contributed to the model prediction."}</p>
        </article>
      ))}
    </div>
  );
}

export default function ExplainabilityModal({ open, data, loading, onClose }) {
  if (!open) return null;
  const patient = data?.patient || {};
  return (
    <div id="explainabilityModal" className="clinical-modal">
      <div className="clinical-modal-backdrop" onClick={onClose} />
      <section className="clinical-modal-panel" role="dialog" aria-modal="true" aria-labelledby="explainabilityTitle">
        <header className="clinical-modal-header">
          <div>
            <h2 id="explainabilityTitle">Explainability Insights</h2>
            <p>Clinical model reasoning for the selected case</p>
          </div>
          <button className="mini-btn" type="button" onClick={onClose}>
            Close
          </button>
        </header>
        <div id="explainabilityModalBody" className="clinical-modal-body">
          {loading || !data ? (
            <div className="empty-clinical-note">Loading insights...</div>
          ) : (
            <>
              <div className="clinical-summary-grid">
                <div className="clinical-summary-card">
                  <h4>Patient / Case</h4>
                  <p>{patient.name || `Patient #${patient.id || data.case?.id || ""}`}</p>
                  <span>
                    Case #{patient.id || data.case?.id || ""} | Age {formatNumber(patient.age ?? data.case?.age)}
                    {data.legacy_model ? <span className="legacy-chip">legacy model</span> : null}
                  </span>
                </div>
                <div className="clinical-summary-card">
                  <h4>Risk Probability</h4>
                  <p>{formatRiskPercent(data.risk_probability)}</p>
                  <span>{data.risk_level || "Unknown"} predicted risk</span>
                </div>
                <div className="clinical-summary-card">
                  <h4>Model Confidence</h4>
                  <p>{data.risk_level || "Clinical"} signal</p>
                  <span>{data.confidence_note || "Final decision must be made by clinician."}</span>
                </div>
              </div>

              {data.gemini_summary ? (
                <section className="insight-section ai-section">
                  <h3>Gemini / AI Summary</h3>
                  <p>{data.gemini_summary}</p>
                </section>
              ) : null}

              <section className="insight-section">
                <h3>Risk-Increasing Factors</h3>
                <FactorList items={data.risk_increasing_factors} emptyText="No strong risk-increasing factors were identified." />
              </section>
              <section className="insight-section">
                <h3>Risk-Reducing Factors</h3>
                <FactorList items={data.risk_reducing_factors} emptyText="No strong risk-reducing factors were identified." />
              </section>
              <section className="insight-section">
                <h3>Clinical Interpretation</h3>
                <p>{data.clinical_interpretation || data.fallback_summary || "The model generated a prediction, but a detailed explanation is not available."}</p>
              </section>
              <section className="insight-section">
                <h3>Suggested Next Action</h3>
                <p>{data.suggested_next_action || data.triage_recommendation || "Review the case using clinical judgment."}</p>
              </section>

              <ClinicalContextPanel context={data.clinical_context} compact />
            </>
          )}
        </div>
      </section>
    </div>
  );
}
