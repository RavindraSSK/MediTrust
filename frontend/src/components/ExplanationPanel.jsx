import { buildClinicalExplanation, buildFeatureExplanation, getClinicalFeatureLabel, getRiskDirectionText } from "../lib/clinical.js";
import { safeNumber } from "../lib/format.js";

function ContributionBars({ features }) {
  if (!features.length) return null;
  const maxAbs = Math.max(...features.map((item) => Math.abs(item.impact)), 0.0001);
  return (
    <div className="contrib-section">
      <h4>Model Contribution Bars</h4>
      <div className="contrib-list">
        {features.map((item) => {
          const pct = Math.max(8, Math.round((Math.abs(item.impact) / maxAbs) * 100));
          const cls = item.direction === "increases risk" ? "contrib-up" : "contrib-down";
          return (
            <div className="contrib-row" key={item.feature}>
              <div className="contrib-label">{getClinicalFeatureLabel(item.feature)}</div>
              <div className="contrib-bar-wrap">
                <div className={`contrib-bar ${cls}`} style={{ width: `${pct}%` }} />
              </div>
              <div className="contrib-value">{item.impact.toFixed(3)}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function Waterfall({ baseValue, finalProbability, features }) {
  if (!features.length) return null;
  const rows = features.reduce((accumulated, item) => {
    const before = accumulated.length ? accumulated[accumulated.length - 1].after : baseValue;
    accumulated.push({ ...item, before, after: before + item.impact });
    return accumulated;
  }, []);
  return (
    <div className="waterfall-section">
      <h4>SHAP Waterfall View</h4>
      <div className="waterfall-base">
        <strong>Base value:</strong> {baseValue.toFixed(3)}
      </div>
      <div className="waterfall-list">
        {rows.map((item) => (
          <div className="waterfall-row" key={item.feature}>
            <div className="waterfall-feature">{getClinicalFeatureLabel(item.feature)}</div>
            <div className={`waterfall-shift ${item.direction === "increases risk" ? "wf-up" : "wf-down"}`}>
              {item.impact >= 0 ? "+" : ""}
              {item.impact.toFixed(3)}
            </div>
            <div className="waterfall-range">
              {item.before.toFixed(3)} -&gt; {item.after.toFixed(3)}
            </div>
          </div>
        ))}
      </div>
      <div className="waterfall-final">
        <strong>Final predicted probability:</strong> {finalProbability.toFixed(3)}
      </div>
    </div>
  );
}

export default function ExplanationPanel({ result }) {
  const riskLevel = result.risk_level || "-";
  const topFeatures = (result.top_features || []).slice(0, 4);
  const allFeatures = result.all_features || [];
  const baseValue = safeNumber(result.base_value) ?? 0;
  const score = safeNumber(result.risk_probability) ?? 0;
  const summaryText = buildClinicalExplanation(riskLevel, topFeatures);

  return (
    <div id="explanationSection" className="result show visible" aria-live="polite">
      <div className="risk-fluid">
        <div className="explain-box professional-clinical-box">
          <h3>AI Clinical Explanation</h3>
          <p className="clinical-summary-text">{summaryText}</p>
          {result.explanation_summary ? <p className="hint">{result.explanation_summary}</p> : null}
          {topFeatures.length ? (
            <ul className="clinical-factor-list">
              {topFeatures.map((item) => {
                const directionText = getRiskDirectionText(item.direction);
                const toneClass = directionText === "Increases risk" ? "risk-up" : directionText === "Decreases risk" ? "risk-down" : "";
                return (
                  <li className={toneClass} key={item.feature}>
                    <strong>{getClinicalFeatureLabel(item.feature)}</strong>
                    <div className="clinical-factor-text">{buildFeatureExplanation(item)}</div>
                  </li>
                );
              })}
            </ul>
          ) : (
            <p className="hint">Detailed feature contributions are not available for this prediction.</p>
          )}
          <p className="clinical-conclusion">This result should be interpreted along with clinical examination and symptoms.</p>
          <ContributionBars features={allFeatures.slice(0, 8)} />
          <Waterfall baseValue={baseValue} finalProbability={score} features={allFeatures.slice(0, 8)} />
          <p className="hint">
            Clinical reference ranges are based on commonly accepted guidelines from organizations such as the American
            Heart Association (AHA) and standard clinical practice. Cited sources appear in the evidence panel below.
          </p>
        </div>
      </div>
    </div>
  );
}
