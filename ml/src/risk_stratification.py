def risk_level_from_probability(p: float):
    """
    Convert disease probability into ED triage risk category.
    Tuned for triage: high-risk should be more sensitive.
    """
    if p < 0.30:
        return "Low", "Standard evaluation recommended"
    elif p < 0.65:
        return "Medium", "Priority review recommended"
    else:
        return "High", "Immediate physician evaluation recommended"