import { fetchModelInfo, fetchRagSources } from "../api/endpoints.js";
import { useAsync } from "../hooks/useAsync.js";
import { errorMessage, formatDecimal } from "../lib/format.js";

function pct(value, digits = 1) {
  const num = Number(value);
  return Number.isFinite(num) ? `${(num * 100).toFixed(digits)}%` : "N/A";
}

export function GlobalImportance({ importance }) {
  const features = importance?.features || [];
  if (!features.length) return <p className="hint">Global feature importance is not available.</p>;
  const max = Math.max(...features.map((item) => item.mean_abs_shap), 0.0001);
  return (
    <div className="importance-list">
      {features.map((item) => (
        <div className="importance-row" key={item.feature}>
          <span>{item.label || item.feature}</span>
          <div className="importance-track">
            <div className="importance-bar" style={{ width: `${Math.max(4, (item.mean_abs_shap / max) * 100)}%` }} />
          </div>
          <span className="importance-value">{pct(item.share, 1)}</span>
        </div>
      ))}
    </div>
  );
}

export default function ModelCard({ withSources = true }) {
  const { data: info, error, loading } = useAsync(fetchModelInfo, []);
  const sources = useAsync(() => (withSources ? fetchRagSources() : Promise.resolve(null)), [withSources]);

  if (loading) return <div className="page-loading">Loading model card...</div>;
  if (error || !info || info.status !== "ready") {
    return <div className="inline-error">{errorMessage(error, info?.error || "Model information is unavailable.")}</div>;
  }

  const cv = info.cross_validation || {};
  const test = info.test_metrics?.["at_0.5"] || {};
  const thresholds = info.active_thresholds || {};
  const ruleOut = info.thresholds?.rule_out_metrics || {};
  const ruleIn = info.thresholds?.rule_in_metrics || {};
  const leaderboard = info.leaderboard || [];

  return (
    <div className="model-card">
      <div className="metric-tiles">
        <div className="metric-tile">
          <small>Selected model</small>
          <strong>{info.model_name}</strong>
          <span className="hint">v{info.model_version}</span>
        </div>
        <div className="metric-tile">
          <small>CV ROC-AUC (5x3 stratified)</small>
          <strong>{formatDecimal(cv.roc_auc_mean, 3)}</strong>
          <span className="hint">± {formatDecimal(cv.roc_auc_std, 3)}</span>
        </div>
        <div className="metric-tile">
          <small>Held-out ROC-AUC</small>
          <strong>{formatDecimal(test.roc_auc, 3)}</strong>
          <span className="hint">PR-AUC {formatDecimal(test.pr_auc, 3)} · Brier {formatDecimal(test.brier, 3)}</span>
        </div>
        <div className="metric-tile">
          <small>Rule-out threshold</small>
          <strong>{formatDecimal(thresholds.rule_out, 2)}</strong>
          <span className="hint">Sensitivity {pct(ruleOut.sensitivity)} (OOF)</span>
        </div>
        <div className="metric-tile">
          <small>Rule-in threshold</small>
          <strong>{formatDecimal(thresholds.rule_in, 2)}</strong>
          <span className="hint">Specificity {pct(ruleIn.specificity)} (OOF)</span>
        </div>
      </div>

      <div className="band-row">
        <span className="band-chip low">Low: p &lt; {formatDecimal(thresholds.rule_out, 2)}</span>
        <span className="band-chip medium">Medium: in between</span>
        <span className="band-chip high">High: p &ge; {formatDecimal(thresholds.rule_in, 2)}</span>
      </div>

      <div>
        <h4 style={{ margin: "6px 0 10px" }}>Global feature importance (mean |SHAP|, held-out set)</h4>
        <GlobalImportance importance={info.global_feature_importance} />
      </div>

      {leaderboard.length ? (
        <div style={{ overflowX: "auto" }}>
          <h4 style={{ margin: "6px 0 10px" }}>Model benchmark</h4>
          <table className="leaderboard-table">
            <thead>
              <tr>
                <th>Model</th>
                <th>CV ROC-AUC</th>
                <th>Test ROC-AUC</th>
                <th>Test PR-AUC</th>
                <th>Brier</th>
                <th>Candidates</th>
              </tr>
            </thead>
            <tbody>
              {leaderboard.map((row) => (
                <tr key={row.model} className={row.model === info.model_name ? "selected" : ""}>
                  <td>{row.model}</td>
                  <td>
                    {formatDecimal(row.cv_roc_auc_mean, 3)} ± {formatDecimal(row.cv_roc_auc_std, 3)}
                  </td>
                  <td>{formatDecimal(row.test_roc_auc, 3)}</td>
                  <td>{formatDecimal(row.test_pr_auc, 3)}</td>
                  <td>{formatDecimal(row.test_brier, 3)}</td>
                  <td>{row.n_candidates}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      <p className="hint">
        {info.label_definition}. Training data: {info.dataset?.rows_clean || "—"} patients (
        {info.dataset?.train_rows || "—"} train / {info.dataset?.test_rows || "—"} test), encoding{" "}
        {info.encoding_version}. Explainer: {info.explainer}. Libraries: scikit-learn{" "}
        {info.library_versions?.["scikit-learn"]}, xgboost {info.library_versions?.xgboost}.
      </p>

      {withSources && sources.data?.documents?.length ? (
        <div>
          <h4 style={{ margin: "6px 0 10px" }}>Curated clinical sources ({sources.data.count})</h4>
          <div className="source-list">
            {sources.data.documents.map((doc) => (
              <div className="source-item" key={doc.id}>
                <strong>{doc.title}</strong>
                <span>
                  {doc.source}
                  {doc.year ? ` (${doc.year})` : ""} · {doc.evidence_type} · {doc.passages} passages
                </span>
                {doc.url ? (
                  <a href={doc.url} target="_blank" rel="noreferrer">
                    {doc.url}
                  </a>
                ) : null}
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}
