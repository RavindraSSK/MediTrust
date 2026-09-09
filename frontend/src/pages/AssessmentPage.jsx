import { useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { predictRisk } from "../api/endpoints.js";
import { useAuth } from "../auth/AuthContext.jsx";
import ClinicalContextPanel from "../components/ClinicalContextPanel.jsx";
import ExplanationPanel from "../components/ExplanationPanel.jsx";
import RiskResultCard from "../components/RiskResultCard.jsx";
import { useBodyClass } from "../hooks/useBodyClass.js";
import { CLINICAL_FIELDS, DEMO_PATIENT } from "../lib/clinical.js";
import { errorMessage, safeNumber } from "../lib/format.js";
import { openPrintableReport } from "../lib/report.js";

function initialForm(isDemo) {
  const values = { first_name: "", last_name: "", age: "" };
  for (const field of CLINICAL_FIELDS) {
    values[field.id] = String(field.default);
  }
  if (isDemo) {
    for (const [key, value] of Object.entries(DEMO_PATIENT)) {
      values[key] = String(value);
    }
  }
  return values;
}

export default function AssessmentPage() {
  useBodyClass("assessment-page");
  const { user, displayName, dashboardPath, logout } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const isDemo = params.get("demo") === "true";
  const [form, setForm] = useState(() => initialForm(isDemo));
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);

  const update = (key) => (event) => setForm((current) => ({ ...current, [key]: event.target.value }));

  const payload = useMemo(() => {
    const values = { first_name: form.first_name.trim(), last_name: form.last_name.trim(), age: safeNumber(form.age) };
    for (const field of CLINICAL_FIELDS) {
      values[field.id] = safeNumber(form[field.id]);
    }
    return values;
  }, [form]);

  const handlePredict = async (event) => {
    event?.preventDefault();
    setError("");
    if (!payload.first_name || !payload.last_name) {
      setError("Please enter the patient's first and last name.");
      return;
    }
    if (payload.age === null || payload.age < 1 || payload.age > 120) {
      setError("Please enter a valid age (1-120).");
      return;
    }
    for (const field of CLINICAL_FIELDS) {
      if (!Number.isFinite(payload[field.id])) {
        setError(`Please enter a valid number for ${field.label.toLowerCase()}.`);
        return;
      }
    }
    setBusy(true);
    try {
      const data = await predictRisk(payload);
      setResult({
        ...data,
        clinical_inputs: payload,
        patient_name: `${payload.first_name} ${payload.last_name}`.trim(),
        current_role: user?.role || "Clinician",
      });
      setTimeout(() => document.getElementById("result")?.scrollIntoView({ behavior: "smooth", block: "start" }), 50);
    } catch (err) {
      setError(err?.status ? errorMessage(err) : errorMessage(err, "Unable to reach the MediTrust API."));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="wrapper">
      <div className="card">
        <div className="topbar">
          <div>
            <h1>MediTrust</h1>
            <div className="subtitle">
              Clinician decision-support prototype for cardiovascular risk screening. For decision support only, not a
              replacement for clinical judgment.
            </div>
            <div className="session-strip">
              <span id="currentUserRole" className="session-pill">
                {user?.role || "Clinician"}
              </span>
              <span id="currentUserName" className="session-user">
                {displayName || "Signed in user"}
              </span>
            </div>
            <div className="actions nav-links">
              <Link to={dashboardPath} className="btn-secondary result-link-btn">
                Dashboard
              </Link>
              <Link to="/patients" className="btn-secondary result-link-btn">
                Patients
              </Link>
              <Link to="/model" className="btn-secondary result-link-btn">
                Model Card
              </Link>
              <button
                id="logoutBtn"
                className="btn-secondary"
                type="button"
                onClick={() => {
                  logout();
                  navigate("/", { replace: true });
                }}
              >
                Logout
              </button>
            </div>
          </div>
          <div className="pill">Risk Assessment</div>
        </div>

        <div className="quick-overview">
          <div className="overview-card">
            <small>Assessment Type</small>
            <strong>Cardiovascular risk screening for early clinical support and triage-oriented evaluation.</strong>
          </div>
        </div>

        <form id="riskForm" noValidate onSubmit={handlePredict}>
          <div className="section-box">
            <div className="section-header">
              <div>
                <div className="section-title">Patient Information</div>
                <div className="section-subtitle">Enter the patient's basic profile before clinical assessment.</div>
              </div>
            </div>
            <div className="row">
              <div>
                <label htmlFor="patientFirstName">
                  Patient first name <span className="required-star">*</span>
                </label>
                <input id="patientFirstName" placeholder="e.g., Ravi" autoComplete="off" value={form.first_name} onChange={update("first_name")} />
                <span className="hint">Used for on-screen patient identification only.</span>
              </div>
              <div>
                <label htmlFor="patientLastName">
                  Patient last name <span className="required-star">*</span>
                </label>
                <input id="patientLastName" placeholder="e.g., Kumar" autoComplete="off" value={form.last_name} onChange={update("last_name")} />
                <span className="hint">Used for on-screen patient identification only.</span>
              </div>
              <div>
                <label htmlFor="age">
                  Age <span className="required-star">*</span>
                </label>
                <input id="age" type="number" min="1" max="120" placeholder="e.g., 27" value={form.age} onChange={update("age")} />
                <span className="hint">Enter age in completed years.</span>
              </div>
            </div>
          </div>

          <div className="section-box">
            <div className="section-header">
              <div>
                <div className="section-title">Clinical Parameters</div>
                <div className="section-subtitle">Provide the core cardiac indicators used by the prediction model.</div>
              </div>
            </div>
            <div className="grid3">
              {CLINICAL_FIELDS.map((field) => (
                <div className="field-card" key={field.id}>
                  <label htmlFor={field.id}>
                    {field.label} <span className="required-star">*</span>
                  </label>
                  {field.type === "select" ? (
                    <select id={field.id} value={form[field.id]} onChange={update(field.id)}>
                      {field.options.map(([value, label]) => (
                        <option key={value} value={value}>
                          {label}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <input id={field.id} type="number" min={field.min} max={field.max} step={field.step || 1} value={form[field.id]} onChange={update(field.id)} />
                  )}
                  <span className="hint">{field.hint}</span>
                </div>
              ))}
            </div>
            <div className="helper-box">
              <b>Tip:</b> Use clinically realistic values while testing. Extremely high or low values can strongly affect
              the risk score and move the output toward a high-risk prediction.
            </div>
          </div>

          <button id="btn" className="btn" type="submit" disabled={busy}>
            {busy ? "Predicting..." : "Predict Risk"}
          </button>
        </form>

        {error ? (
          <div id="alert" className="alert" aria-live="polite" style={{ display: "block" }}>
            {error}
          </div>
        ) : null}

        {result ? (
          <>
            <RiskResultCard result={result} role={user?.role} dashboardPath={dashboardPath} onDownload={() => openPrintableReport(result, user)} />
            <ExplanationPanel result={result} />
            <ClinicalContextPanel context={result.clinical_context} />
          </>
        ) : null}

        <div className="footer">
          <div>Copyright 2026 MediTrust</div>
          <div>AI-assisted screening prototype</div>
        </div>
      </div>
    </div>
  );
}
