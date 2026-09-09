import { useCallback, useEffect, useState } from "react";

import { fetchDashboardSummary, fetchDoctorEscalations, fetchExplainability, fetchUrgentCases, saveDoctorDecision } from "../api/endpoints.js";
import { useAuth } from "../auth/AuthContext.jsx";
import DashboardShell from "../components/DashboardShell.jsx";
import ExplainabilityModal from "../components/ExplainabilityModal.jsx";
import StatsGrid from "../components/StatsGrid.jsx";
import { buildDoctorAlertMessage, errorMessage, formatDateTime, formatNumber, formatRiskPercent } from "../lib/format.js";

const DECISIONS = [
  ["Immediate physician review", "Immediate Review"],
  ["Priority monitoring", "Priority Monitoring"],
  ["Routine follow-up", "Routine Follow-up"],
];

function CaseList({ items, emptyText, selectedId, onSelect, loading }) {
  if (loading) return <ul className="alert-list"><li><span>Loading...</span></li></ul>;
  if (!items.length) return <ul className="alert-list"><li><span>{emptyText}</span></li></ul>;
  return (
    <ul className="alert-list">
      {items.map((item) => (
        <li
          key={`${item.escalation_id || "case"}-${item.id}`}
          className={`doctor-alert-item${Number(item.id) === Number(selectedId) ? " is-selected" : ""}`}
          onClick={() => onSelect(item)}
        >
          <strong>
            {item.patient_name || item.full_name || `Prediction #${item.id}`} - {item.risk_level}
            {item.legacy_model ? <span className="legacy-chip">legacy</span> : null}
          </strong>
          <span>
            Risk: {formatRiskPercent(item.risk_probability)} - Age: {formatNumber(item.age)} -{" "}
            {item.status === "Reviewed" ? item.doctor_decision || "Reviewed" : buildDoctorAlertMessage(item)}
          </span>
        </li>
      ))}
    </ul>
  );
}

export default function DoctorDashboardPage() {
  const { user, displayName } = useAuth();
  const [summary, setSummary] = useState({});
  const [urgent, setUrgent] = useState([]);
  const [escalations, setEscalations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedCase, setSelectedCase] = useState(null);
  const [note, setNote] = useState("");
  const [message, setMessage] = useState({ text: "", type: "info" });
  const [modal, setModal] = useState({ open: false, loading: false, data: null });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [summaryData, urgentData, escalationData] = await Promise.all([fetchDashboardSummary(), fetchUrgentCases(), fetchDoctorEscalations()]);
      setSummary(summaryData);
      setUrgent(urgentData);
      setEscalations(escalationData);
      setSelectedCase((current) => {
        const pool = [...escalationData, ...urgentData];
        const refreshed = current ? pool.find((item) => item.id === current.id) : null;
        return refreshed || escalationData[0] || urgentData[0] || null;
      });
    } catch (error) {
      setMessage({ text: errorMessage(error, "Unable to load the doctor dashboard."), type: "error" });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    setNote(selectedCase?.doctor_note || "");
  }, [selectedCase]);

  const openExplainability = async () => {
    if (!selectedCase?.id) {
      setMessage({ text: "Select a case before viewing explainability insights.", type: "warning" });
      return;
    }
    setModal({ open: true, loading: true, data: null });
    try {
      const data = await fetchExplainability(selectedCase.id);
      setModal({ open: true, loading: false, data });
      setMessage({ text: "Explainability insights loaded.", type: "success" });
    } catch (error) {
      setModal({ open: false, loading: false, data: null });
      setMessage({ text: errorMessage(error, "Unable to load explainability insights."), type: "error" });
    }
  };

  const saveDecision = async (decision) => {
    if (!selectedCase?.escalation_id) {
      setMessage({ text: "Select a nurse-escalated case before saving a decision.", type: "warning" });
      return;
    }
    setMessage({ text: "Saving triage decision...", type: "info" });
    try {
      await saveDoctorDecision(selectedCase.escalation_id, decision, note.trim());
      setMessage({ text: "Doctor triage decision saved.", type: "success" });
      await load();
    } catch (error) {
      setMessage({ text: errorMessage(error, "Unable to save triage decision."), type: "error" });
    }
  };

  return (
    <DashboardShell
      title="Doctor Dashboard"
      subtitle="Full clinical review and urgent case visibility"
      userLabel={displayName ? `Dr. ${displayName}` : "Doctor"}
      links={[{ to: "/patients", label: "Patients" }, { to: "/model", label: "Model Card" }, { to: "/change-password", label: "Password" }]}
    >
      <StatsGrid
        stats={[
          { id: "doctorUrgentCount", label: "Urgent Cases", value: summary.urgent_cases ?? 0 },
          { id: "doctorTotalPredictions", label: "Total Predictions", value: summary.total_predictions ?? 0 },
          { id: "doctorMediumCount", label: "Medium Risk", value: summary.medium_cases ?? 0 },
          { id: "doctorOpenEscalations", label: "Open Escalations", value: summary.open_escalations ?? 0 },
        ]}
      />

      <section className="dashboard-grid dashboard-grid-three">
        <div className="panel-box">
          <h2>Quick Actions</h2>
          <div className="action-list">
            <a href="/assessment" className="action-btn">Open Patient Assessment</a>
            <button id="viewExplainabilityBtn" className="action-btn action-btn-secondary" type="button" onClick={openExplainability}>
              View Explainability Insights
            </button>
          </div>
          <div id="doctorWorkflowMessage" className={`workflow-message workflow-${message.type}`} role="status">{message.text}</div>
        </div>
        <div className="panel-box">
          <h2>Urgent Clinical Alerts</h2>
          <CaseList items={urgent} loading={loading} emptyText="No urgent high-risk cases right now." selectedId={selectedCase?.id} onSelect={setSelectedCase} />
        </div>
        <div className="panel-box">
          <h2>Nurse Escalations</h2>
          <CaseList items={escalations} loading={loading} emptyText="No nurse-escalated cases yet." selectedId={selectedCase?.id} onSelect={setSelectedCase} />
        </div>
      </section>

      <section className="panel-box wide-panel">
        <h2>Selected Case Details</h2>
        <div id="doctorCaseDetails" className="doctor-case-details">
          {!selectedCase ? (
            <div className="scope-item">Select a case from urgent alerts or nurse escalations.</div>
          ) : (
            <>
              <div className="case-detail-grid">
                <div className="case-detail-card"><h4>Prediction ID</h4><p>#{selectedCase.id}</p></div>
                <div className="case-detail-card"><h4>Patient</h4><p>{selectedCase.patient_name || selectedCase.full_name || `Patient #${selectedCase.id}`}</p></div>
                <div className="case-detail-card"><h4>Risk Level</h4><p>{selectedCase.risk_level}</p></div>
                <div className="case-detail-card"><h4>Risk Probability</h4><p>{formatRiskPercent(selectedCase.risk_probability)}</p></div>
                <div className="case-detail-card"><h4>Age</h4><p>{formatNumber(selectedCase.age)}</p></div>
                <div className="case-detail-card"><h4>Resting BP</h4><p>{formatNumber(selectedCase.trestbps)} mmHg</p></div>
                <div className="case-detail-card"><h4>Status</h4><p>{selectedCase.status || "Pending"}</p></div>
                <div className="case-detail-card"><h4>Decision</h4><p>{selectedCase.doctor_decision || "Not recorded"}</p></div>
              </div>
              <div className="doctor-note-box"><strong>Triage Message:</strong> {buildDoctorAlertMessage(selectedCase)}</div>
              {selectedCase.doctor_note ? <div className="doctor-note-box secondary-note"><strong>Doctor Note:</strong> {selectedCase.doctor_note}</div> : null}
              <div className="doctor-note-box secondary-note">
                <strong>Logged:</strong> {formatDateTime(selectedCase.created_at)}
                {selectedCase.model_version ? ` · model ${selectedCase.model_version}` : " · legacy model output"}
              </div>
            </>
          )}
        </div>
        {selectedCase?.escalation_id ? (
          <div id="doctorDecisionPanel" className="doctor-decision-panel">
            <h3>Triage Decision</h3>
            <p>Record a student-project-safe decision-support disposition for the escalated case.</p>
            <div className="decision-grid">
              {DECISIONS.map(([value, label]) => (
                <button key={value} className="mini-btn decision-btn" type="button" onClick={() => saveDecision(value)}>
                  {label}
                </button>
              ))}
            </div>
            <label className="decision-note-label" htmlFor="doctorDecisionNote">Review note</label>
            <textarea id="doctorDecisionNote" className="decision-note" rows={3} placeholder="Optional note for the demo workflow" value={note} onChange={(event) => setNote(event.target.value)} />
          </div>
        ) : null}
      </section>

      <ExplainabilityModal open={modal.open} loading={modal.loading} data={modal.data} onClose={() => setModal({ open: false, loading: false, data: null })} />
      {user?.role === "Admin" ? <p className="hint">Viewing as administrator.</p> : null}
    </DashboardShell>
  );
}
