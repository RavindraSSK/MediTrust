"""
Grounded clinical context generation.

Pipeline
--------
1. ``build_queries`` turns the SHAP drivers, the risk band and a methods query
   into retrieval queries.
2. The hybrid retriever returns the best passages per query; passages are
   de-duplicated and numbered S1..Sn so they can be cited.
3. If an LLM is configured, it writes a short narrative that may only use the
   provided passages and must cite them. Guardrails reject any narrative that
   lacks citations, cites unknown sources, restates a different risk
   percentage, or looks like a diagnosis, in which case the deterministic
   template narrative is used instead.

The model output (probability, band, triage recommendation) is passed in as
read-only context and echoed back unchanged; nothing in this module can alter
it.
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime

from ..observability import LLM_FAILURES, RAG_GENERATIONS
from .query import RetrievalQuery, build_queries
from .retriever import HybridRetriever, RetrievalResult

logger = logging.getLogger(__name__)

DISCLAIMER = (
    "This clinical context is retrieved from curated guideline and literature summaries to help "
    "interpret the model output. It does not change the model's risk estimate, is not a diagnosis, "
    "and must be weighed against the clinical examination, ECG, vital signs and laboratory results."
)

SYSTEM_INSTRUCTION = (
    "You are a clinical decision-support writing assistant for MediTrust, a cardiovascular risk "
    "screening tool used by doctors and nurses. You explain a machine-learning risk estimate using ONLY "
    "the numbered evidence passages supplied in the prompt.\n"
    "Rules:\n"
    "1. Never change, recompute, round differently or dispute the model's risk probability or risk band; "
    "if you mention them, quote them exactly as given.\n"
    "2. Every clinical statement must end with a citation such as [S1] or [S2][S4] referring only to the "
    "supplied passages. Do not cite anything else and do not invent facts.\n"
    "3. Do not diagnose the patient, do not prescribe or name specific medications, and do not tell the "
    "clinician what decision to make.\n"
    "4. Write three to five sentences of plain professional prose: no bullet points, no headings, no markdown.\n"
    "5. If the evidence does not cover a point, say that the supplied evidence does not address it."
)

CITATION_RE = re.compile(r"\[S(\d+)\]")
PERCENT_RE = re.compile(r"(\d{1,3}(?:\.\d+)?)\s?%")
DIAGNOSIS_RE = re.compile(
    r"\b(?:the patient|this patient|he|she|they)\s+(?:has|have|is suffering from|is diagnosed with)\s+"
    r"(?:coronary|heart disease|a heart attack|myocardial infarction)",
    re.IGNORECASE,
)
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
MAX_NARRATIVE_CHARS = 1600


def first_sentences(text: str, count: int = 1) -> str:
    sentences = SENTENCE_SPLIT_RE.split(text.strip())
    return " ".join(sentences[:count]).strip()


class ClinicalContextService:
    def __init__(self, retriever: HybridRetriever, llm=None, use_llm: bool = True, top_k: int = 6):
        self.retriever = retriever
        self.llm = llm
        self.use_llm = use_llm
        self.top_k = max(3, top_k)

    # ----------------------------------------------------------------- public
    @property
    def llm_enabled(self) -> bool:
        return bool(self.use_llm and self.llm is not None and getattr(self.llm, "available", False))

    def status(self) -> dict:
        return {
            "documents": len(getattr(self.retriever, "documents", [])),
            "passages": len(self.retriever.passages),
            "retrieval_backend": self.retriever.backend_name,
            "llm_enabled": self.llm_enabled,
            "llm_model": getattr(self.llm, "model", None) if self.llm_enabled else None,
            "top_k": self.top_k,
        }

    def search(self, query: str, top_k: int = 5, features: list[str] | None = None) -> list[dict]:
        return [r.to_dict() for r in self.retriever.search(query, top_k=top_k, boost_features=features)]

    def build(
        self,
        payload: dict,
        risk_probability: float,
        risk_level: str,
        triage_recommendation: str,
        top_features: list[dict],
    ) -> dict:
        queries = build_queries(payload, risk_level, top_features)
        citations, evidence = self._retrieve(queries)

        model_output = {
            "risk_probability": float(risk_probability),
            "risk_percent": int(round(float(risk_probability) * 100)),
            "risk_level": risk_level,
            "triage_recommendation": triage_recommendation,
        }

        narrative = None
        mode = "template"
        guardrails: dict | None = None
        if self.llm_enabled and citations:
            candidate = self.llm.generate(
                self._prompt(payload, model_output, evidence, citations),
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.2,
                max_output_tokens=450,
            )
            guardrails = self._check_guardrails(candidate, citations, model_output["risk_percent"])
            if guardrails["passed"]:
                narrative = self._normalise_narrative(candidate)
                mode = "llm"
            else:
                LLM_FAILURES.labels("guardrail").inc()
                logger.info("RAG narrative rejected by guardrails: %s", guardrails["failed_checks"])

        if narrative is None:
            narrative = self._template_narrative(model_output, evidence, citations)

        RAG_GENERATIONS.labels(mode).inc()
        return {
            "narrative": narrative,
            "mode": mode,
            "model_output": model_output,
            "evidence": evidence,
            "citations": citations,
            "queries": [q.to_dict() for q in queries],
            "retrieval": {
                "backend": self.retriever.backend_name,
                "passages_indexed": len(self.retriever.passages),
                "top_k": self.top_k,
            },
            "guardrails": guardrails,
            "disclaimer": DISCLAIMER,
            "generated_at": datetime.now(UTC).isoformat(),
        }

    # -------------------------------------------------------------- retrieval
    def _retrieve(self, queries: list[RetrievalQuery]) -> tuple[list[dict], list[dict]]:
        citations: list[dict] = []
        citation_by_passage: dict[str, str] = {}
        evidence: list[dict] = []

        def register(result: RetrievalResult) -> str:
            passage = result.passage
            if passage.id in citation_by_passage:
                return citation_by_passage[passage.id]
            cid = f"S{len(citations) + 1}"
            citation_by_passage[passage.id] = cid
            citations.append(
                {
                    "id": cid,
                    **passage.to_dict(include_text=False),
                    "excerpt": passage.text,
                    "citation": passage.citation,
                    "score": round(result.score, 6),
                }
            )
            return cid

        feature_queries = [q for q in queries if q.kind == "feature"]
        other_queries = [q for q in queries if q.kind != "feature"]
        remaining = self.top_k

        for query in feature_queries:
            if remaining <= 0:
                break
            results = self.retriever.search(query.text, top_k=2, boost_features=query.boost_features)
            if not results:
                continue
            best = results[0]
            was_new = best.passage.id not in citation_by_passage
            cid = register(best)
            if was_new:
                remaining -= 1
            evidence.append(
                {
                    "feature": query.feature,
                    "label": query.label,
                    "value_text": query.value_text,
                    "direction": query.direction,
                    "impact": round(float(query.impact), 6) if query.impact is not None else None,
                    "citation_ids": [cid],
                    "summary": first_sentences(best.passage.text, 1),
                    "source": best.passage.citation,
                }
            )

        for query in other_queries:
            results = self.retriever.search(
                query.text, top_k=1, boost_features=query.boost_features, exclude_ids=set(citation_by_passage)
            )
            if results:
                register(results[0])

        return citations, evidence

    # ----------------------------------------------------------------- prompt
    @staticmethod
    def _patient_lines(payload: dict) -> str:
        from ..clinical_encoding import FEATURE_ORDER, value_text

        return "; ".join(value_text(feature, payload[feature]) for feature in FEATURE_ORDER if feature in payload)

    def _prompt(self, payload: dict, model_output: dict, evidence: list[dict], citations: list[dict]) -> str:
        drivers = (
            "; ".join(
                f"{item['value_text']} ({item['direction'] or 'influences risk'}) -> see [{item['citation_ids'][0]}]"
                for item in evidence
            )
            or "not available"
        )
        passages = "\n".join(f"[{c['id']}] ({c['citation']}) {c['excerpt']}" for c in citations)
        return (
            "MODEL OUTPUT (fixed; quote exactly, never recompute): "
            f"predicted probability of coronary artery disease {model_output['risk_percent']}%, "
            f"risk band {model_output['risk_level']}, triage recommendation: {model_output['triage_recommendation']}.\n\n"
            f"PATIENT INPUTS: {self._patient_lines(payload)}.\n\n"
            f"LEADING SHAP CONTRIBUTORS: {drivers}.\n\n"
            f"EVIDENCE PASSAGES:\n{passages}\n\n"
            "TASK: Write the grounded clinical context paragraph for the clinician following the rules."
        )

    # ------------------------------------------------------------- guardrails
    @staticmethod
    def _check_guardrails(candidate: str | None, citations: list[dict], risk_percent: int) -> dict:
        checks: dict[str, bool] = {}
        if not candidate or not candidate.strip():
            return {"passed": False, "checks": {"non_empty": False}, "failed_checks": ["non_empty"]}

        text = candidate.strip()
        checks["non_empty"] = True
        checks["length_ok"] = len(text) <= MAX_NARRATIVE_CHARS

        cited = {f"S{m}" for m in CITATION_RE.findall(text)}
        known = {c["id"] for c in citations}
        checks["has_citation"] = bool(cited)
        checks["citations_known"] = cited <= known

        percents = [float(p) for p in PERCENT_RE.findall(text)]
        checks["risk_percent_consistent"] = all(abs(p - risk_percent) <= 1.0 for p in percents)

        checks["no_diagnosis_claim"] = DIAGNOSIS_RE.search(text) is None
        checks["no_markdown"] = not re.search(r"^\s*(?:[-*#]|\d+\.)\s", text, re.MULTILINE)

        failed = [name for name, ok in checks.items() if not ok]
        return {"passed": not failed, "checks": checks, "failed_checks": failed}

    @staticmethod
    def _normalise_narrative(text: str) -> str:
        text = re.sub(r"\s+", " ", text.strip())
        return text

    # --------------------------------------------------------------- template
    @staticmethod
    def _template_narrative(model_output: dict, evidence: list[dict], citations: list[dict]) -> str:
        sentences = [
            (
                f"The model estimates a {model_output['risk_percent']}% probability of coronary artery disease, "
                f"which falls in the {model_output['risk_level']} risk band "
                f"({model_output['triage_recommendation'].rstrip('.').lower()}); this section does not modify that estimate."
            )
        ]
        for item in evidence:
            direction = item.get("direction") or "influences the estimate"
            summary = item.get("summary") or ""
            cid = item["citation_ids"][0]
            sentences.append(f"{item['value_text']} ({direction}): {summary} [{cid}]")

        feature_ids = {cid for item in evidence for cid in item["citation_ids"]}
        for citation in citations:
            if citation["id"] in feature_ids:
                continue
            sentences.append(f"{first_sentences(citation['excerpt'], 1)} [{citation['id']}]")

        return " ".join(sentences)
