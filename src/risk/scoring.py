"""Risk = Likelihood × Impact × Exposure × Data Sensitivity (all normalized 0–1 scale)."""

from __future__ import annotations


def compute_risk(
    likelihood: float,
    impact: float,
    exposure: float,
    data_sensitivity: float,
) -> float:
    """Returns a 0–100 style score for dashboarding."""
    for v in (likelihood, impact, exposure, data_sensitivity):
        if v < 0 or v > 1:
            raise ValueError("All factors must be in [0, 1]")
    raw = likelihood * impact * exposure * data_sensitivity
    return round(raw * 100, 2)


def severity_from_risk(score: float) -> str:
    if score >= 70:
        return "critical"
    if score >= 45:
        return "high"
    if score >= 25:
        return "medium"
    return "low"
