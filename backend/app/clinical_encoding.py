"""
Bridge to the canonical clinical encoding defined in ``ml/src/data_dictionary.py``.

The training pipeline and the API must agree on feature codes, labels and
validation ranges, so the backend loads the very same module instead of
keeping a second copy.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from .config import ML_DIR

_DATA_DICTIONARY_PATH = ML_DIR / "src" / "data_dictionary.py"


def _load_data_dictionary():
    module_name = "meditrust_data_dictionary"
    if module_name in sys.modules:
        return sys.modules[module_name]
    if not _DATA_DICTIONARY_PATH.exists():
        raise FileNotFoundError(
            f"Clinical data dictionary not found at {_DATA_DICTIONARY_PATH}. "
            "The backend must be deployed together with the ml/ directory."
        )
    spec = importlib.util.spec_from_file_location(module_name, _DATA_DICTIONARY_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


_dd = _load_data_dictionary()

ENCODING_VERSION: str = _dd.ENCODING_VERSION
FEATURE_ORDER: list[str] = list(_dd.FEATURE_ORDER)
NUMERIC_FEATURES: list[str] = list(_dd.NUMERIC_FEATURES)
CATEGORICAL_FEATURES: list[str] = list(_dd.CATEGORICAL_FEATURES)
CATEGORY_CODES: dict[str, list[int]] = dict(_dd.CATEGORY_CODES)
CATEGORY_LABELS: dict[str, dict[int, str]] = dict(_dd.CATEGORY_LABELS)
FEATURE_LABELS: dict[str, str] = dict(_dd.FEATURE_LABELS)
FEATURE_UNITS: dict[str, str] = dict(_dd.FEATURE_UNITS)
NUMERIC_RANGES: dict[str, tuple[float, float]] = dict(_dd.NUMERIC_RANGES)

validate_record = _dd.validate_record
describe_value = _dd.describe_value


def feature_label(feature: str) -> str:
    return FEATURE_LABELS.get(feature, feature.replace("_", " ").title())


def value_text(feature: str, value) -> str:
    """'Resting blood pressure 156 mmHg' / 'Chest pain type: asymptomatic'."""
    described = describe_value(feature, value)
    if feature in CATEGORY_LABELS:
        return f"{feature_label(feature)}: {described}"
    return f"{feature_label(feature)} {described}"


def data_dictionary_path() -> Path:
    return _DATA_DICTIONARY_PATH
