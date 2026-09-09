import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from risk_stratification import risk_level_from_probability  # noqa: E402


def test_bands_with_explicit_thresholds():
    assert risk_level_from_probability(0.10, (0.3, 0.65))[0] == "Low"
    assert risk_level_from_probability(0.30, (0.3, 0.65))[0] == "Medium"
    assert risk_level_from_probability(0.64, (0.3, 0.65))[0] == "Medium"
    assert risk_level_from_probability(0.65, (0.3, 0.65))[0] == "High"


def test_messages_are_triage_oriented():
    level, message = risk_level_from_probability(0.9, (0.3, 0.65))
    assert level == "High"
    assert "physician" in message.lower()
