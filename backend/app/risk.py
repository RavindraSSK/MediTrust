def risk_level_from_probability(p: float):
    """
    ED triage-style risk stratification using probability bands.
    """
    if p < 0.30:
        return "Low", "Standard evaluation recommended"
    elif p < 0.65:
        return "Medium", "Priority review recommended"
    else:
        return "High", "Immediate physician evaluation recommended"