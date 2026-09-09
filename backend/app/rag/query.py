"""
Build retrieval queries from a patient's inputs and the SHAP drivers.

Each query combines the clinical meaning of a feature value with the vocabulary
used in guideline text so lexical retrieval lands on the right passage even
without dense embeddings.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..clinical_encoding import CATEGORY_LABELS, describe_value, feature_label

FEATURE_QUERY_TEMPLATES: dict[str, str] = {
    "trestbps": "resting systolic blood pressure {value} mm Hg hypertension category stage cardiovascular risk",
    "chol": "total cholesterol {value} mg/dL lipid category borderline high atherosclerosis statin",
    "fbs": "fasting blood sugar glucose above 120 mg/dL diabetes prediabetes cardiovascular risk enhancer",
    "cp": "chest pain type {label} angina classification typical atypical non-anginal asymptomatic",
    "exang": "exercise-induced angina exertional chest pain during exercise test prognosis",
    "oldpeak": "exercise-induced ST depression {value} mm ischaemia exercise ECG Duke treadmill score",
    "slope": "peak exercise ST segment slope {label} upsloping flat downsloping ischaemia",
    "thalach": "maximum heart rate achieved {value} bpm age-predicted chronotropic incompetence heart rate recovery",
    "restecg": "resting ECG {label} left ventricular hypertrophy ST-T wave abnormality",
    "ca": "number of major coronary vessels {label} fluoroscopy angiography multivessel disease prognosis",
    "thal": "thallium stress perfusion imaging {label} reversible fixed defect ischaemia scar",
    "age": "age {value} years cardiovascular risk increases with age pooled cohort equations",
    "sex": "{label} sex cardiovascular risk difference women men presentation",
}

CONTEXT_QUERIES: dict[str, str] = {
    "High": "emergency department chest pain triage high risk HEART score high-sensitivity troponin pathway immediate evaluation",
    "Medium": "intermediate risk chest pain evaluation HEART score priority review serial troponin clinical decision pathway",
    "Low": "low risk cardiovascular prevention follow-up modifiable risk factors Life's Essential 8",
}
METHODS_QUERY = "SHAP explainability model limitations decision support validation Cleveland data set thresholds"


@dataclass
class RetrievalQuery:
    kind: str  # "feature" | "context" | "methods"
    text: str
    feature: str | None = None
    label: str | None = None
    value_text: str | None = None
    direction: str | None = None
    impact: float | None = None
    boost_features: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "feature": self.feature,
            "label": self.label,
            "value_text": self.value_text,
            "direction": self.direction,
            "query": self.text,
        }


def feature_query(feature: str, value, direction: str | None = None, impact: float | None = None) -> RetrievalQuery:
    label = feature_label(feature)
    described = describe_value(feature, value)
    template = FEATURE_QUERY_TEMPLATES.get(feature, "{label} {value} cardiovascular risk")
    text = template.format(
        value=f"{float(value):g}" if feature not in CATEGORY_LABELS else described,
        label=described if feature in CATEGORY_LABELS else label.lower(),
    )
    value_text = f"{label}: {described}" if feature in CATEGORY_LABELS else f"{label} {described}"
    return RetrievalQuery(
        kind="feature",
        text=text,
        feature=feature,
        label=label,
        value_text=value_text,
        direction=direction,
        impact=impact,
        boost_features=[feature],
    )


def build_queries(
    payload: dict, risk_level: str, top_features: list[dict], max_features: int = 4
) -> list[RetrievalQuery]:
    queries: list[RetrievalQuery] = []
    seen: set[str] = set()

    for item in top_features:
        feature = str(item.get("feature") or "")
        if not feature or feature in seen or feature not in payload:
            continue
        seen.add(feature)
        queries.append(
            feature_query(
                feature,
                payload[feature],
                direction=item.get("direction"),
                impact=item.get("impact"),
            )
        )
        if len(queries) >= max_features:
            break

    level = risk_level if risk_level in CONTEXT_QUERIES else "Medium"
    queries.append(
        RetrievalQuery(
            kind="context",
            text=CONTEXT_QUERIES[level],
            boost_features=["triage"] if level != "Low" else ["prevention", "triage"],
        )
    )
    queries.append(RetrievalQuery(kind="methods", text=METHODS_QUERY, boost_features=["methods"]))
    return queries
