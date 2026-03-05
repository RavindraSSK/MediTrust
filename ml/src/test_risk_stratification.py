print("test_risk_stratification started")

from risk_stratification import risk_level_from_probability

tests = [0.12, 0.45, 0.78]

for p in tests:
    level, msg = risk_level_from_probability(p)
    print(f"p={p:.2f} -> {level} | {msg}")