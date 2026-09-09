import { useState } from "react";

const CITATION_RE = /(\[S\d+\])/g;

function Narrative({ text }) {
  const parts = String(text || "").split(CITATION_RE);
  return (
    <p className="context-narrative">
      {parts.map((part, index) =>
        CITATION_RE.test(part) ? (
          <span className="cite" key={index}>
            {part}
          </span>
        ) : (
          <span key={index}>{part}</span>
        )
      )}
    </p>
  );
}

export default function ClinicalContextPanel({ context, compact = false }) {
  const [showSources, setShowSources] = useState(!compact);
  if (!context) return null;

  const modelOutput = context.model_output || {};
  const citations = context.citations || [];
  const evidence = context.evidence || [];
  const modeLabel = context.mode === "llm" ? "LLM narrative, citation-checked" : "Deterministic evidence template";

  return (
    <section className="context-panel" aria-label="Evidence-grounded clinical context">
      <div className="context-header">
        <div>
          <h3>Evidence-Grounded Clinical Context</h3>
          <p>Retrieved from curated guideline and literature summaries. Separate from the model score.</p>
        </div>
        <span className={`mode-badge ${context.mode === "llm" ? "llm" : "template"}`}>{modeLabel}</span>
      </div>

      {modelOutput.risk_level ? (
        <div className="model-output-echo">
          <span>
            Model output (read-only): <strong>{modelOutput.risk_percent}%</strong> probability of coronary artery disease
          </span>
          <span>
            Band: <strong>{modelOutput.risk_level}</strong>
          </span>
          {modelOutput.triage_recommendation ? <span>{modelOutput.triage_recommendation}</span> : null}
        </div>
      ) : null}

      <Narrative text={context.narrative} />

      {evidence.length ? (
        <div className="evidence-grid">
          {evidence.map((item) => {
            const up = String(item.direction || "").includes("increase");
            const down = String(item.direction || "").includes("decrease");
            return (
              <article className="evidence-item" key={item.feature}>
                <strong>{item.value_text}</strong>
                <div className={`evidence-direction ${up ? "up" : down ? "down" : ""}`}>
                  {item.direction || "influences risk"} &middot; {item.citation_ids?.join(", ")}
                </div>
                <p>{item.summary}</p>
              </article>
            );
          })}
        </div>
      ) : null}

      {citations.length ? (
        <>
          <button type="button" className="citation-toggle" onClick={() => setShowSources((value) => !value)}>
            {showSources ? "Hide sources" : `Show ${citations.length} cited sources`}
          </button>
          {showSources ? (
            <ol className="citation-list" style={{ marginTop: 10 }}>
              {citations.map((citation) => (
                <li key={citation.id}>
                  <span className="citation-id">{citation.id}</span>
                  {citation.url ? (
                    <a href={citation.url} target="_blank" rel="noreferrer">
                      {citation.title}
                    </a>
                  ) : (
                    citation.title
                  )}
                  <span className="citation-source">
                    {citation.citation || citation.source}
                    {citation.evidence_type ? ` · ${citation.evidence_type}` : ""}
                  </span>
                </li>
              ))}
            </ol>
          ) : null}
        </>
      ) : null}

      <p className="context-disclaimer">{context.disclaimer}</p>
    </section>
  );
}
