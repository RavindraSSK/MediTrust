import { useCallback, useEffect, useState } from "react";

import { escalateCase, fetchDashboardSummary, fetchExplainability, fetchRecentPredictions, fetchTriageQueue } from "../api/endpoints.js";
import { useAuth } from "../auth/AuthContext.jsx";
import DashboardShell from "../components/DashboardShell.jsx";
import ExplainabilityModal from "../components/ExplainabilityModal.jsx";
import StatsGrid from "../components/StatsGrid.jsx";
import TriageQueueTable from "../components/TriageQueueTable.jsx";
import { errorMessage, formatDateTime, formatRiskPercent } from "../lib/format.js";

export default function NurseDashboardPage() {
  const { displayName } = useAuth();
  const [summary, setSummary] = useState({});
  const [recent, setRecent] = useState([]);
  const [queue, setQueue] = useState([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState({ text: "", type: "info" });
  const [selectedCaseId, setSelectedCaseId] = useState(null);
  const [busyCaseId, setBusyCaseId] = useState(null);
  const [modal, setModal] = useState({ open: false, loading: false, data: null });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [summaryData, recentData, queueData] = await Promise.all([fetchDashboardSummary(), fetchRecentPredictions(), fetchTriageQueue()]);
      setSummary(summaryData);
      setRecent(recentData);
      setQueue(queueData);
    } catch (error) {
      setMessage({ text: errorMessage(error, "Unable to load triage queue."), type: "error" });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleEscalate = async (item) => {
    setBusyCaseId(item.id);
    setMessage({ text: `Escalating case #${item.id}...`, type: "info" });
    try {
      const data = await escalateCase(item.id);
      setMessage({ text: data.message || "Case escalated to doctor for review.", type: data.ok ? "success" : "warning" });
      await load();
    } catch (error) {
      setMessage({ text: errorMessage(error, "Unable to escalate case."), type: "error" });
    } finally {
      setBusyCaseId(null);
    }
  };

  const handleView = async (item) => {
    setSelectedCaseId(item.id);
    setModal({ open: true, loading: true, data: null });
    try {
      const data = await fetchExplainability(item.id);
      setModal({ open: true, loading: false, data });
    } catch (error) {
      setModal({ open: false, loading: false, data: null });
      setMessage({ text: errorMessage(error, "Unable to load explainability insights."), type: "error" });
    }
  };

  const scrollToQueue = () => document.getElementById("triageQueuePanel")?.scrollIntoView({ behavior: "smooth", block: "start" });

  return (
    <DashboardShell
      title="Nurse Dashboard"
      subtitle="Triage workflow and escalation support"
      userLabel={displayName || "Nurse"}
      links={[{ to: "/patients", label: "Patients" }, { to: "/model", label: "Model Card" }, { to: "/change-password", label: "Password" }]}
    >
      <StatsGrid
        stats={[
          { id: "nurseTotalPredictions", label: "Total Predictions", value: summary.total_predictions ?? 0 },
          { id: "nurseUrgentCount", label: "Urgent Escalations", value: summary.urgent_cases ?? 0 },
          { id: "nurseLowCount", label: "Low Risk Cases", value: summary.low_cases ?? 0 },
          { id: "nurseOpenEscalations", label: "Awaiting Doctor", value: summary.open_escalations ?? 0 },
        ]}
      />

      <section className="dashboard-grid">
        <div className="panel-box">
          <h2>Quick Actions</h2>
          <div className="action-list">
            <a href="/assessment" className="action-btn">Start New Patient Assessment</a>
            <button className="action-btn action-btn-secondary" type="button" onClick={scrollToQueue}>Review Triage Queue</button>
            <button
              className="action-btn action-btn-secondary"
              type="button"
              onClick={() => {
                const candidate = queue.find((item) => item.risk_level === "High" && !item.escalated);
                if (candidate) handleEscalate(candidate);
                else setMessage({ text: "No un-escalated high-risk cases in the queue.", type: "warning" });
              }}
            >
              Escalate High Risk Case
            </button>
          </div>
          <div className={`workflow-message workflow-${message.type}`} role="status">{message.text}</div>
        </div>
        <div className="panel-box">
          <h2>Recent Triage Queue</h2>
          <ul className="alert-list" id="nurseRecentList">
            {loading ? <li><span>Loading triage queue...</span></li> : null}
            {!loading && !recent.length ? <li><span>No triage results available yet.</span></li> : null}
            {!loading
              ? recent.map((item) => (
                  <li key={item.id}>
                    <strong>{item.patient_name || `Prediction #${item.id}`} • {item.risk_level}</strong>
                    <span>
                      Risk: {formatRiskPercent(item.risk_probability)} • Age: {item.age} • BP: {item.trestbps} • Chol: {item.chol} • {formatDateTime(item.created_at)}
                    </span>
                  </li>
                ))
              : null}
          </ul>
        </div>
      </section>

      <section id="triageQueuePanel" className="panel-box wide-panel">
        <div className="clinical-panel-header">
          <div>
            <h2>Triage Queue</h2>
            <p>Escalate high-risk (or selected medium-risk) cases to a doctor and review the model's explanation for any case.</p>
          </div>
          <button className="mini-btn" type="button" onClick={load}>Refresh</button>
        </div>
        {loading ? <div className="empty-clinical-note">Loading triage queue...</div> : (
          <TriageQueueTable items={queue} selectedCaseId={selectedCaseId} onView={handleView} onEscalate={handleEscalate} busyCaseId={busyCaseId} />
        )}
      </section>

      <ExplainabilityModal open={modal.open} loading={modal.loading} data={modal.data} onClose={() => setModal({ open: false, loading: false, data: null })} />
    </DashboardShell>
  );
}
