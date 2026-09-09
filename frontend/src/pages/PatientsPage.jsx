import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { fetchPatientRecords, fetchRecentPatients, searchPatients } from "../api/endpoints.js";
import { useAuth } from "../auth/AuthContext.jsx";
import { useBodyClass } from "../hooks/useBodyClass.js";
import { formatDateTime, formatRiskPercent } from "../lib/format.js";

function PatientDetail({ records, state }) {
  if (state === "loading") return <div className="patient-detail-empty">Loading patient record...</div>;
  if (state === "error") return <div className="patient-detail-empty">Unable to load patient record right now.</div>;
  if (!records) return <div className="patient-detail-empty">Select a patient record to view saved assessment data.</div>;
  if (!records.length) return <div className="patient-detail-empty">No risk assessment data found for this patient.</div>;

  const latest = records[0];
  return (
    <>
      <div className="patient-detail-header">
        <div>
          <h3>{latest.full_name || "Patient Record"}</h3>
          <p>Latest saved cardiovascular risk assessment data.</p>
        </div>
        <div className={`patient-risk-chip ${String(latest.risk_level || "").toLowerCase()}`}>{latest.risk_level || "Unknown"}</div>
      </div>
      <div className="patient-detail-grid">
        <div className="patient-detail-card">
          <small>Risk Probability</small>
          <strong>{formatRiskPercent(latest.risk_probability)}</strong>
        </div>
        <div className="patient-detail-card">
          <small>Triage Recommendation</small>
          <strong>{latest.triage_message || "N/A"}</strong>
        </div>
        <div className="patient-detail-card">
          <small>Age</small>
          <strong>{latest.age ?? "N/A"}</strong>
        </div>
        <div className="patient-detail-card">
          <small>Saved On</small>
          <strong>{formatDateTime(latest.created_at)}</strong>
        </div>
      </div>
      <div className="patient-metric-grid">
        <div className="field-card"><label>Resting Blood Pressure</label><div className="patient-metric-value">{latest.trestbps ?? "N/A"} mmHg</div></div>
        <div className="field-card"><label>Cholesterol</label><div className="patient-metric-value">{latest.chol ?? "N/A"} mg/dL</div></div>
        <div className="field-card"><label>Max Heart Rate</label><div className="patient-metric-value">{latest.thalach ?? "N/A"}</div></div>
        <div className="field-card"><label>ST Depression</label><div className="patient-metric-value">{latest.oldpeak ?? "N/A"}</div></div>
        <div className="field-card"><label>Chest Pain Type</label><div className="patient-metric-value">{latest.cp ?? "N/A"}</div></div>
        <div className="field-card"><label>Vessel Count</label><div className="patient-metric-value">{latest.ca ?? "N/A"}</div></div>
      </div>
      <div className="patient-history-box">
        <h4>Previous Records</h4>
        <div className="history-list">
          {records.map((record) => (
            <div className="history-item" key={record.id}>
              <strong>{formatDateTime(record.created_at)}</strong>
              <span>
                {record.risk_level} risk • {formatRiskPercent(record.risk_probability)}
                {record.legacy_model ? <span className="legacy-chip">legacy model</span> : null}
              </span>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}

export default function PatientsPage() {
  useBodyClass("assessment-page");
  const { user, displayName, dashboardPath, logout } = useAuth();
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [patients, setPatients] = useState([]);
  const [listState, setListState] = useState("loading");
  const [listMessage, setListMessage] = useState("");
  const [records, setRecords] = useState(null);
  const [recordState, setRecordState] = useState("idle");
  const [selected, setSelected] = useState(null);

  const selectPatient = useCallback(async (firstName, lastName) => {
    setSelected(`${firstName}|${lastName}`);
    setRecordState("loading");
    try {
      const rows = await fetchPatientRecords(firstName || "", lastName || "");
      setRecords(rows);
      setRecordState("ready");
    } catch {
      setRecordState("error");
    }
  }, []);

  const loadList = useCallback(
    async (searchTerm) => {
      setListState("loading");
      setListMessage(searchTerm ? "Searching patients..." : "");
      try {
        const items = searchTerm ? await searchPatients(searchTerm) : await fetchRecentPatients(5);
        setPatients(items);
        setListState("ready");
        if (items.length) {
          await selectPatient(items[0].first_name || "", items[0].last_name || "");
        } else {
          setRecords([]);
          setRecordState(searchTerm ? "ready" : "idle");
        }
      } catch {
        setListState("error");
        setListMessage(searchTerm ? "Search failed. Please try again." : "Unable to load recent patients.");
      }
    },
    [selectPatient]
  );

  useEffect(() => {
    loadList("");
  }, [loadList]);

  const runSearch = () => loadList(query.trim());

  return (
    <div className="wrapper">
      <div className="card">
        <div className="topbar">
          <div>
            <h1>MediTrust</h1>
            <div className="subtitle">Review recent patients, search prior records, and inspect previous cardiovascular risk assessments.</div>
            <div className="session-strip">
              <span id="currentUserRole" className="session-pill">{user?.role || "Clinician"}</span>
              <span id="currentUserName" className="session-user">{displayName || "Signed in user"}</span>
            </div>
            <div className="actions nav-links">
              <Link to="/assessment" className="btn-secondary result-link-btn">New Assessment</Link>
              <Link to={dashboardPath} className="btn-secondary result-link-btn">Dashboard</Link>
              <button id="logoutBtn" className="btn-secondary" type="button" onClick={() => { logout(); navigate("/", { replace: true }); }}>Logout</button>
            </div>
          </div>
          <div className="pill">Patient Records</div>
        </div>

        <div className="quick-overview">
          <div className="overview-card">
            <small>Records View</small>
            <strong>Open one of the five most recent patients or search by patient name to review prior risk assessment results.</strong>
          </div>
        </div>

        <div className="section-box">
          <div className="section-header">
            <div>
              <div className="section-title">Search Patients</div>
              <div className="section-subtitle">Search by first name, last name, or full patient name.</div>
            </div>
          </div>
          <div className="patient-search-row">
            <input id="patientSearchInput" type="text" placeholder="Search patient name" value={query} onChange={(event) => setQuery(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") { event.preventDefault(); runSearch(); } }} />
            <button id="patientSearchBtn" className="btn-secondary" type="button" onClick={runSearch}>Search</button>
          </div>
        </div>

        <div className="patient-layout">
          <div className="section-box patient-list-box">
            <div className="section-header">
              <div>
                <div className="section-title">Recent Patients</div>
                <div className="section-subtitle">The five latest patients with saved risk assessment records.</div>
              </div>
            </div>
            <div id="patientList" className="patient-list">
              {listState === "loading" ? <div className="patient-empty-state">{listMessage || "Loading patients..."}</div> : null}
              {listState === "error" ? <div className="patient-empty-state">{listMessage}</div> : null}
              {listState === "ready" && !patients.length ? <div className="patient-empty-state">No patient records found yet.</div> : null}
              {listState === "ready"
                ? patients.map((item) => (
                    <button
                      type="button"
                      className={`patient-item${selected === `${item.first_name || ""}|${item.last_name || ""}` ? " is-selected" : ""}`}
                      key={item.id}
                      onClick={() => selectPatient(item.first_name || "", item.last_name || "")}
                    >
                      <div className="patient-item-head">
                        <strong>{item.full_name || "Unknown patient"}</strong>
                        <span className={`patient-risk-chip ${String(item.risk_level || "").toLowerCase()}`}>{item.risk_level || "Unknown"}</span>
                      </div>
                      <div className="patient-item-meta">
                        <span>Risk {formatRiskPercent(item.risk_probability)}</span>
                        <span>Age {item.age ?? "N/A"}</span>
                        <span>{formatDateTime(item.created_at)}</span>
                      </div>
                    </button>
                  ))
                : null}
            </div>
          </div>

          <div className="section-box patient-detail-box">
            <div className="section-header">
              <div>
                <div className="section-title">Patient Risk Assessment Data</div>
                <div className="section-subtitle">Click a patient on the left to inspect their latest record and previous assessments.</div>
              </div>
            </div>
            <div id="patientDetail">
              <PatientDetail records={records} state={recordState} />
            </div>
          </div>
        </div>

        <div className="footer">
          <div>© 2026 MediTrust</div>
          <div>Historical patient record review</div>
        </div>
      </div>
    </div>
  );
}
