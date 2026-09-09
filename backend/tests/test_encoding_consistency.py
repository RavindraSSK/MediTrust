"""The API validation must agree with the training data dictionary."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "ml" / "src"))

import data_dictionary as dd  # noqa: E402

from app import clinical_encoding as ce  # noqa: E402


def test_backend_uses_the_ml_data_dictionary():
    assert ce.ENCODING_VERSION == dd.ENCODING_VERSION
    assert ce.FEATURE_ORDER == dd.FEATURE_ORDER
    assert ce.CATEGORY_CODES == dd.CATEGORY_CODES
    assert ce.CATEGORY_LABELS == dd.CATEGORY_LABELS


def test_model_card_encoding_matches_code():
    import json

    metadata = json.loads((ROOT / "ml" / "models" / "model_metadata.json").read_text())
    assert metadata["encoding_version"] == ce.ENCODING_VERSION
    assert metadata["features"] == ce.FEATURE_ORDER
