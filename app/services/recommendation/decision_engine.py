"""
Decision Engine — determines loan approval, amount, and interest rate.

Uses Five Cs scores, risk adjustments, and financial data to produce
a transparent, explainable lending recommendation.
"""

import logging

from app.schemas.recommendation import FiveCsScoreResponse, LoanDecision, LoanDecisionRequest

logger = logging.getLogger(__name__)

# Base interest rates by risk grade (Indian market context)
BASE_RATES = {
    "AAA": 8.5,
    "AA": 9.0,
    "A": 10.0,
    "BBB": 11.5,
    "BB": 13.0,
    "B": 15.0,
    "C": 18.0,
    "D": 0.0,  # reject
}

# Maximum LTV (Loan-to-Value) by risk grade
MAX_LTV = {
    "AAA": 0.80,
    "AA": 0.75,
    "A": 0.70,
    "BBB": 0.60,
    "BB": 0.50,
    "B": 0.40,
    "C": 0.25,
    "D": 0.0,
}


def make_decision(request: LoanDecisionRequest) -> LoanDecision:
    """
    Generate a loan decision with recommended amount, rate, and explanation.

    Decision logic is transparent and explainable.
    """
    five_cs = request.five_cs_scores
    if five_cs is None:
        return LoanDecision(
            company_name=request.company_name,
            decision="REFER",
            explanation="Five Cs scores not available. Cannot make automated decision.",
        )

    risk_grade = five_cs.risk_grade
    weighted_score = five_cs.weighted_total

    # Apply risk adjustments from primary insights
    adjusted_score = _apply_risk_adjustments(weighted_score, request.risk_adjustments)

    # Re-evaluate grade after adjustments
    adjusted_grade = _grade_from_score(adjusted_score)

    # Determine decision
    decision, explanation, key_factors = _determine_decision(
        adjusted_score, adjusted_grade, five_cs, request
    )

    # Calculate recommended amount
    recommended_amount = _calculate_amount(
        request.requested_amount, adjusted_grade, request.financial_data
    )

    # Calculate interest rate
    interest_rate, risk_premium = _calculate_rate(adjusted_grade, adjusted_score)

    # Build conditions
    conditions = _generate_conditions(adjusted_grade, five_cs, request)

    return LoanDecision(
        company_name=request.company_name,
        decision=decision,
        recommended_amount=recommended_amount,
        interest_rate=interest_rate,
        risk_premium=risk_premium,
        risk_grade=adjusted_grade,
        confidence_score=min(adjusted_score / 100, 1.0),
        explanation=explanation,
        key_factors=key_factors,
        conditions=conditions,
    )


def _apply_risk_adjustments(
    score: float,
    adjustments: list[dict],
) -> float:
    """Apply risk adjustment deltas from primary insights."""
    total_delta = 0.0
    for adj in adjustments:
        delta = adj.get("adjustment", adj.get("overall_risk_delta", 0.0))
        if isinstance(delta, (int, float)):
            total_delta += delta

    # Scale: each 1.0 of delta = 10 points adjustment
    adjusted = score + (total_delta * 10)
    return max(0, min(100, adjusted))


def _grade_from_score(score: float) -> str:
    """Map score to risk grade."""
    if score >= 85:
        return "AAA"
    if score >= 75:
        return "AA"
    if score >= 65:
        return "A"
    if score >= 55:
        return "BBB"
    if score >= 45:
        return "BB"
    if score >= 35:
        return "B"
    if score >= 25:
        return "C"
    return "D"


def _determine_decision(
    score: float,
    grade: str,
    five_cs: FiveCsScoreResponse,
    request: LoanDecisionRequest,
) -> tuple[str, str, list[str]]:
    """Determine APPROVE/REJECT/REFER with explanation."""
    key_factors: list[str] = []

    # Check each C for red flags
    for cs in five_cs.scores:
        if cs.score >= 70:
            key_factors.append(f"Strong {cs.category} ({cs.score:.0f}/100): {cs.explanation[:100]}")
        elif cs.score < 40:
            key_factors.append(f"Weak {cs.category} ({cs.score:.0f}/100): {cs.explanation[:100]}")

    # Decision logic
    if grade == "D" or score < 25:
        decision = "REJECT"
        explanation = (
            f"Rejected — overall credit score {score:.1f}/100 (Grade: {grade}). "
            f"Multiple critical weaknesses identified across the Five Cs assessment."
        )
    elif grade in ("C", "B") or score < 45:
        decision = "REFER"
        explanation = (
            f"Referred for manual review — credit score {score:.1f}/100 (Grade: {grade}). "
            f"Some risk factors require human judgment before approval."
        )
    elif grade in ("AAA", "AA", "A", "BBB", "BB"):
        decision = "APPROVE"
        explanation = (
            f"Approved — credit score {score:.1f}/100 (Grade: {grade}). "
            f"Company demonstrates adequate creditworthiness "
            f"across the Five Cs assessment."
        )
    else:
        decision = "REFER"
        explanation = f"Score: {score:.1f}/100, Grade: {grade}. Requires further review."

    return decision, explanation, key_factors


def _calculate_amount(
    requested: float,
    grade: str,
    financial_data: dict,
) -> float:
    """Calculate recommended loan amount based on risk grade and financials."""
    if grade == "D":
        return 0.0

    ltv = MAX_LTV.get(grade, 0.5)

    # Use revenue as a proxy for maximum exposure if available
    revenue = financial_data.get("revenue", 0)
    ebitda = financial_data.get("ebitda", 0)

    # Max exposure: 3x EBITDA or 0.5x revenue (whichever is lower)
    max_by_ebitda = ebitda * 3 if ebitda else float("inf")
    max_by_revenue = revenue * 0.5 if revenue else float("inf")
    max_exposure = min(max_by_ebitda, max_by_revenue)

    if max_exposure == float("inf"):
        # No financial data — use requested amount with LTV haircut
        return round(requested * ltv, 2)

    recommended = min(requested, max_exposure) * ltv
    return round(recommended, 2)


def _calculate_rate(grade: str, score: float) -> tuple[float, float]:
    """Calculate interest rate and risk premium."""
    base_rate = BASE_RATES.get(grade, 15.0)

    # Additional premium based on score granularity (0-200 bps)
    if score < 30:
        premium_bps = 200
    elif score < 50:
        premium_bps = 150
    elif score < 60:
        premium_bps = 100
    elif score < 70:
        premium_bps = 50
    else:
        premium_bps = 0

    total_rate = base_rate + (premium_bps / 100)
    return round(total_rate, 2), premium_bps


def _generate_conditions(
    grade: str,
    five_cs: FiveCsScoreResponse,
    request: LoanDecisionRequest,
) -> list[str]:
    """Generate lending conditions based on risk assessment."""
    conditions: list[str] = []

    if grade in ("BB", "B", "C"):
        conditions.append("Quarterly financial reporting required")
        conditions.append("Enhanced monitoring with monthly review calls")

    if grade in ("B", "C"):
        conditions.append("Personal guarantee of promoters required")
        conditions.append("Additional collateral security to be provided")

    # Check for specific weaknesses
    for cs in five_cs.scores:
        if cs.category == "Collateral" and cs.score < 50:
            conditions.append("Adequate collateral coverage to be ensured before disbursement")
        if cs.category == "Character" and cs.score < 50:
            conditions.append("Enhanced due diligence on promoter background required")
        if cs.category == "Conditions" and cs.score < 50:
            conditions.append("Sector-specific risk covenants to be included")

    if not conditions:
        conditions.append("Standard lending terms and conditions apply")

    return conditions
