import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { fetchAdminAuditLog, fetchAdminCases, fetchDashboardSummary, fetchRecentPredictions } from "../api/endpoints.js";
import { useAuth } from "../auth/AuthContext.jsx";
import DashboardShell from "../components/DashboardShell.jsx";
import StatsGrid from "../components/StatsGrid.jsx";
import { errorMessage, formatDateTime, formatRiskPercent } from "../lib/format.js";

export default function AdminDashboardPage() {
  const { displayName } = useAuth();
  const navigate = useNavigate();
  const [summary, setSummary] = useState({});
  const [recent, setRecent] = useState([]);
  const [recentState, setRecentState] = useState("loading");
  const [panel, setPanel] = useState(null);
  const [cases, setCases] = useState([]);
  const [events, setEvents] = useState([]);
  const [message, setMessage] = useState({ text: "", type: "info" });

  const load = useCallback(async () => {
    try {
      const [summaryData, recentData] = await Promise.all([fetchDashboardSummary(), fetchRecentPredictions()]);
      setSummary(summaryData);
      setRecent(recentData);
      setRecentState("ready");
    } catch {
      setRecentState("error");
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const loadCases = async () => {
    setPanel("cases");
    setMessage({ text: "Loading prediction logs...", type: "info" });
    try {
      setCases(await fetchAdminCases());
      setMessage({ text: "Prediction logs loaded.", type: "success" });
    } catch (error) {
      setCases([]);
      setMessage({ text: errorMessage(error, "Unable to load prediction logs."), type: "error" });
    }
  };

  const loadActivity = async () => {
    setPanel("activity");
    setMessage({ text: "Loading activity monitor...", type: "info" });
    try {
      setEvents(await fetchAdminAuditLog());
      setMessage({ text: "Activity monitor loaded.", type: "success" });
    } catch (error) {
      setEvents([]);
      setMessage({ text: errorMessage(error, "Unable to load activity monitor."), type: "error" });
    }
  };

  return (
    <DashboardShell
      title="Admin Dashboard"
      subtitle="System monitoring and recent prediction activity"
      userLabel={displayName || "Admin"}
      links={[{ to: "/model", label: "Model Card" }, { to: "/change-password", label: "Password" }]}
    >
      <StatsGrid
        stats={[
          { id: "adminTotalUsers", label: "Total Users", value: summary.total_users ?? 0 },
          { id: "adminPendingUsers", label: "Pending Approvals", value: summary.pending_users ?? 0 },
          { id: "adminTotalPredictions", label: "Total Predictions", value: summary.total_predictions ?? 0 },
          { id: "adminUrgentCount", label: "Urgent Cases", value: summary.urgent_cases ?? 0 },
        ]}
      />

      <section className="dashboard-grid">
        <div className="panel-box">
          <h2>Admin Actions</h2>
          <div className="action-list">
            <button className="action-btn" id="manageUsersBtn" type="button" onClick={() => navigate("/admin/users")}>Manage Users</button>
            <button className="action-btn action-btn-secondary" id="viewPredictionLogsBtn" type="button" onClick={loadCases}>View Prediction Logs</button>
            <button className="action-btn action-btn-secondary" id="monitorActivityBtn" type="button" onClick={loadActivity}>Monitor Activity</button>
            <button className="action-btn action-btn-secondary" type="button" onClick={() => navigate("/assessment")}>Open Patient Assessment</button>
          </div>
          <div id="adminWorkflowMessage" className={`workflow-message workflow-${message.type}`} role="status">{message.text}</div>
        </div>
        <div className="panel-box">
          <h2>Recent Predictions</h2>
          <ul className="alert-list" id="adminRecentList">
            {recentState === "loading" ? <li><span>Loading recent predictions...</span></li> : null}
            {recentState === "error" ? <li><span>Unable to load recent predictions.</span></li> : null}
            {recentState === "ready" && !recent.length ? <li><span>No recent predictions available.</span></li> : null}
            {recentState === "ready"
              ? recent.map((item) => (
                  <li key={item.id}>
                    <strong>
                      {item.full_name || `Prediction #${item.id}`} | {item.risk_level}
                      {item.legacy_model ? <span className="legacy-chip">legacy</span> : null}
                    </strong>
                    <span>
                      Risk: {formatRiskPercent(item.risk_probability)} | Age: {item.age} | BP: {item.trestbps} | Chol: {item.chol} | {formatDateTime(item.created_at)}
                    </span>
                  </li>
                ))
              : null}
          </ul>
        </div>
      </section>

      {panel === "cases" ? (
        <section id="adminCasePanel" className="panel-box wide-panel admin-live-panel">
          <div className="clinical-panel-header">
            <div>
              <h2>Prediction Logs</h2>
              <p>Recent model runs, triage priority, escalation status, and doctor review outcomes.</p>
            </div>
          </div>
          {cases.length ? (
            <div className="clinical-table-wrap">
              <table className="clinical-table">
                <thead>
                  <tr><th>Case</th><th>Risk</th><th>Probability</th><th>Status</th><th>Decision</th><th>Model</th><th>Created</th></tr>
                </thead>
                <tbody id="adminCaseTableBody">
                  {cases.map((item) => (
                    <tr key={item.id}>
                      <td><strong>{item.patient_name || item.full_name || `Case #${item.id}`}</strong><span>#{item.id}</span></td>
                      <td>{item.risk_level || "Unknown"}</td>
                      <td>{formatRiskPercent(item.risk_probability)}</td>
                      <td>{item.status || "Pending"}</td>
                      <td>{item.doctor_decision || "Not reviewed"}</td>
                      <td>{item.model_version || "legacy"}</td>
                      <td>{formatDateTime(item.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div id="adminCaseEmpty" className="empty-clinical-note">No prediction logs are available yet.</div>
          )}
        </section>
      ) : null}

      {panel === "activity" ? (
        <section id="adminActivityPanel" className="panel-box wide-panel admin-live-panel">
          <div className="clinical-panel-header">
            <div>
              <h2>Activity Monitor</h2>
              <p>Audit-style view for demo oversight across users, predictions, escalations, and reviews.</p>
            </div>
          </div>
          <ul className="alert-list" id="adminActivityList">
            {!events.length ? <li><span>No activity events available yet.</span></li> : null}
            {events.map((item, index) => (
              <li key={`${item.type}-${index}`}>
                <strong>{item.type} | {item.title}</strong>
                <span>{item.description}{item.created_at ? ` | ${formatDateTime(item.created_at)}` : ""}</span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </DashboardShell>
  );
}
