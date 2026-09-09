import { formatDateTime, formatNumber, formatRiskPercent, priorityClass, riskClass, statusClass } from "../lib/format.js";

export default function TriageQueueTable({ items, selectedCaseId, onView, onEscalate, canEscalate = true, busyCaseId = null }) {
  const rows = Array.isArray(items) ? items : [];
  if (!rows.length) {
    return <div id="triageQueueEmpty" className="empty-clinical-note">No cases in the triage queue yet.</div>;
  }
  return (
    <div className="clinical-table-wrap">
      <table className="clinical-table">
        <thead>
          <tr>
            <th>Patient</th>
            <th>Age</th>
            <th>Risk</th>
            <th>Probability</th>
            <th>Priority</th>
            <th>Status</th>
            <th>Created</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody id="triageQueueBody">
          {rows.map((item) => (
            <tr key={item.id} className={Number(item.id) === Number(selectedCaseId) ? "is-selected" : ""}>
              <td>
                <strong>{item.patient_name || `Patient #${item.id}`}</strong>
                <span>
                  #{item.patient_id || item.id}
                  {item.legacy_model ? <span className="legacy-chip">legacy</span> : null}
                </span>
              </td>
              <td>{formatNumber(item.age)}</td>
              <td>
                <span className={`clinical-badge ${riskClass(item.risk_level)}`}>{item.risk_level || "Unknown"}</span>
              </td>
              <td>{formatRiskPercent(item.risk_probability)}</td>
              <td>
                <span className={`clinical-badge ${priorityClass(item.priority)}`}>{item.priority || "Routine"}</span>
              </td>
              <td>
                <span className={`clinical-badge ${statusClass(item.status)}`}>{item.status || "Pending"}</span>
              </td>
              <td>{formatDateTime(item.created_at)}</td>
              <td className="table-actions">
                <div className="triage-actions">
                  <button className="mini-btn table-btn" type="button" onClick={() => onView?.(item)}>
                    View case
                  </button>
                  {canEscalate ? (
                    <button
                      className="mini-btn table-btn"
                      type="button"
                      disabled={item.escalated || !["High", "Medium"].includes(item.risk_level) || busyCaseId === item.id}
                      onClick={() => onEscalate?.(item)}
                    >
                      {item.escalated ? "Escalated" : busyCaseId === item.id ? "Escalating..." : "Escalate to doctor"}
                    </button>
                  ) : null}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
