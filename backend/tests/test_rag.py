import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from conftest import auth_header  # noqa: E402

from app.rag.corpus import load_corpus, parse_document  # noqa: E402
from app.rag.retriever import HybridRetriever, tokenize  # noqa: E402
from app.rag.service import ClinicalContextService  # noqa: E402

CORPUS_DIR = Path(__file__).resolve().parents[1] / "app" / "rag" / "corpus"


@pytest.fixture(scope="module")
def retriever():
    return HybridRetriever.from_documents(load_corpus(CORPUS_DIR))


def test_corpus_documents_carry_citation_metadata():
    documents = load_corpus(CORPUS_DIR)
    assert len(documents) >= 12
    for doc in documents:
        assert doc.id and doc.title and doc.source and doc.url.startswith("http"), doc.id
        assert doc.passages, doc.id
        assert doc.features, doc.id


def test_parse_document_splits_paragraphs_into_passages():
    doc = parse_document(
        "---\nid: t\ntitle: T\nsource: S\nfeatures: [cp, thal]\nyear: 2020\n---\nFirst para.\n\nSecond para.",
        fallback_id="x",
    )
    assert [p.id for p in doc.passages] == ["t#1", "t#2"]
    assert doc.features == ["cp", "thal"] and doc.year == 2020


def test_tokenizer_normalises_plurals_and_stopwords():
    assert tokenize("The vessels and the vessel") == ["vessel", "vessel"]


@pytest.mark.parametrize(
    "query,feature,expected_doc",
    [
        ("resting blood pressure 156 mm Hg hypertension stage", "trestbps", "acc-aha-2017-hypertension"),
        ("thallium reversible defect perfusion", "thal", "myocardial-perfusion-imaging"),
        ("maximum heart rate chronotropic incompetence", "thalach", "maximum-heart-rate-chronotropic"),
        ("exercise induced ST depression Duke treadmill score", "oldpeak", "exercise-ecg-st-depression"),
        ("number of major vessels fluoroscopy multivessel", "ca", "coronary-angiography-vessel-count"),
        ("fasting blood sugar diabetes", "fbs", "ada-standards-glucose-diabetes"),
        ("HEART score troponin emergency triage", "triage", "ed-chest-pain-triage-heart-score"),
    ],
)
def test_hybrid_retriever_finds_the_right_guideline(retriever, query, feature, expected_doc):
    results = retriever.search(query, top_k=3, boost_features=[feature])
    assert results and results[0].passage.doc_id == expected_doc
    assert results[0].boosted


def test_retriever_scores_are_fused_from_multiple_channels(retriever):
    results = retriever.search("hypertension", top_k=1)
    assert results[0].lexical_score > 0 and results[0].semantic_score > 0
    assert retriever.search("", top_k=3) == []


def test_template_narrative_is_grounded_and_leaves_model_output_untouched(retriever):
    service = ClinicalContextService(retriever, llm=None, use_llm=False, top_k=6)
    payload = dict(
        age=58,
        sex=1,
        cp=4,
        trestbps=156,
        chol=286,
        fbs=1,
        restecg=1,
        thalach=118,
        exang=1,
        oldpeak=2.8,
        slope=2,
        ca=2,
        thal=7,
    )
    top = [
        {"feature": "ca", "direction": "increases risk", "impact": 0.2},
        {"feature": "trestbps", "direction": "increases risk", "impact": 0.1},
    ]
    out = service.build(payload, 0.873, "High", "Immediate physician evaluation recommended", top)
    assert out["mode"] == "template"
    assert out["model_output"] == {
        "risk_probability": 0.873,
        "risk_percent": 87,
        "risk_level": "High",
        "triage_recommendation": "Immediate physician evaluation recommended",
    }
    assert [e["feature"] for e in out["evidence"]] == ["ca", "trestbps"]
    assert "87%" in out["narrative"] and "[S1]" in out["narrative"]
    assert any(c["doc_id"] == "acc-aha-2017-hypertension" for c in out["citations"])
    assert any(c["doc_id"] == "meditrust-model-methods-limitations" for c in out["citations"])


class _FakeLLM:
    available = True
    model = "fake"

    def __init__(self, text):
        self.text = text

    def generate(self, prompt, **kwargs):
        self.prompt = prompt
        return self.text


def test_llm_narrative_is_accepted_when_it_cites_and_keeps_the_score(retriever):
    llm = _FakeLLM(
        "The 87% estimate reflects two-vessel disease on fluoroscopy [S1]. Stage 2 hypertension adds risk [S2]."
    )
    service = ClinicalContextService(retriever, llm=llm, use_llm=True, top_k=6)
    out = service.build(
        dict(
            age=58,
            sex=1,
            cp=4,
            trestbps=156,
            chol=286,
            fbs=1,
            restecg=1,
            thalach=118,
            exang=1,
            oldpeak=2.8,
            slope=2,
            ca=2,
            thal=7,
        ),
        0.873,
        "High",
        "Immediate physician evaluation recommended",
        [
            {"feature": "ca", "direction": "increases risk", "impact": 0.2},
            {"feature": "trestbps", "direction": "increases risk", "impact": 0.1},
        ],
    )
    assert out["mode"] == "llm" and out["guardrails"]["passed"]
    assert "MODEL OUTPUT (fixed" in llm.prompt and "[S1]" in llm.prompt


@pytest.mark.parametrize(
    "bad_text,failed_check",
    [
        ("Risk is high because of vessel disease.", "has_citation"),
        ("Risk is high [S42].", "citations_known"),
        ("The estimate of 40% is high [S1].", "risk_percent_consistent"),
        ("The patient has coronary artery disease [S1].", "no_diagnosis_claim"),
        ("- vessel disease [S1]\n- hypertension [S2]", "no_markdown"),
    ],
)
def test_llm_guardrails_reject_ungrounded_or_altered_output(retriever, bad_text, failed_check):
    service = ClinicalContextService(retriever, llm=_FakeLLM(bad_text), use_llm=True, top_k=6)
    out = service.build(
        dict(
            age=58,
            sex=1,
            cp=4,
            trestbps=156,
            chol=286,
            fbs=1,
            restecg=1,
            thalach=118,
            exang=1,
            oldpeak=2.8,
            slope=2,
            ca=2,
            thal=7,
        ),
        0.873,
        "High",
        "Immediate physician evaluation recommended",
        [{"feature": "ca", "direction": "increases risk", "impact": 0.2}],
    )
    assert out["mode"] == "template"
    assert failed_check in out["guardrails"]["failed_checks"]
    assert "87%" in out["narrative"]


def test_rag_endpoints_require_auth_and_expose_sources(client, doctor_token):
    assert client.get("/rag/sources").status_code == 401
    sources = client.get("/rag/sources", headers=auth_header(doctor_token)).json()
    assert sources["count"] >= 12
    status = client.get("/rag/status", headers=auth_header(doctor_token)).json()
    assert status["enabled"] and status["passages"] > 30 and status["llm_enabled"] is False
    search = client.get("/rag/search?q=left+ventricular+hypertrophy&k=2", headers=auth_header(doctor_token)).json()
    assert search["results"][0]["doc_id"] == "resting-ecg-lvh-st-t"
