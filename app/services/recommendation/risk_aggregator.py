"""
Risk Aggregation Engine — computes the final credit risk score.

Combines multiple risk dimensions into a single unified score:
- Financial Risk (from Five Cs)
- Fraud Risk
- Promoter Network Risk
- Sector Risk
- Early Warning Signals (EWS)
"""

import logging

logger = logging.getLogger(__name__)

# Default weights for the final score
RISK_WEIGHTS = {
    "financial_risk": 0.30,
    "fraud_risk": 0.20,
    "promoter_risk": 0.15,
    "sector_risk": 0.15,
    "early_warning": 0.20,
}


def compute_final_credit_risk(
    five_cs_score: float,
    fraud_score: float,
    promoter_risk_score: float,
    sector_risk_score: float,
    early_warning_score: float,  # 0 to 1
) -> dict:
    """
    Compute the aggregated final credit risk score.

    Note: financial_risk is derived inversely from the five_cs_score 
    (higher 5C score = lower financial risk).
    All scores inside the function are 0-100 where higher is MORE risky.

    Returns:
    - final_credit_risk_score: 0-100 (higher = riskier)
    - risk_grade: AAA to D
    - factor_contributions: breakdown of risk by component
    """
    # Convert five_cs_score (100 is best) to financial risk (100 is worst)
    financial_risk = max(0.0, 100.0 - five_cs_score)

    # Scale early warning from 0-1 to 0-100
    ews_scaled = early_warning_score * 100.0

    # Apply weights
    components = {
        "financial_risk": financial_risk * RISK_WEIGHTS["financial_risk"],
        "fraud_risk": fraud_score * RISK_WEIGHTS["fraud_risk"],
        "promoter_risk": promoter_risk_score * RISK_WEIGHTS["promoter_risk"],
        "sector_risk": sector_risk_score * RISK_WEIGHTS["sector_risk"],
        "early_warning": ews_scaled * RISK_WEIGHTS["early_warning"],
    }

    final_score = sum(components.values())
    final_score = round(min(100.0, max(0.0, final_score)), 2)

    return {
        "final_credit_risk_score": final_score,
        "risk_grade": _grade_from_risk_score(final_score),
        "factor_contributions": {
            k: round(v, 2) for k, v in components.items()
        },
        "raw_scores": {
            "financial_risk_raw": round(financial_risk, 2),
            "fraud_risk_raw": round(fraud_score, 2),
            "promoter_risk_raw": round(promoter_risk_score, 2),
            "sector_risk_raw": round(sector_risk_score, 2),
            "early_warning_raw": round(ews_scaled, 2),
        }
    }


def _grade_from_risk_score(risk_score: float) -> str:
    """
    Map risk score (100 is worst) to a risk grade.
    Inverse of the original decision engine grading.
    """
    if risk_score <= 15: return "AAA"
    if risk_score <= 25: return "AA"
    if risk_score <= 35: return "A"
    if risk_score <= 45: return "BBB"
    if risk_score <= 55: return "BB"
    if risk_score <= 65: return "B"
    if risk_score <= 75: return "C"
    return "D"
