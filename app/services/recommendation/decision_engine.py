"""
Decision Engine — real financial modeling with deep explainability.

Uses DSCR, ICR, Leverage Ratio, and other banking metrics alongside
Five Cs scores, fraud data, and regulatory checks to produce a
transparent, explainable lending recommendation with cited evidence.
"""

import logging

from app.schemas.recommendation import (
    FinancialRatio,
    FinancialRatioReport,
    FiveCsScoreResponse,
    LoanDecision,
    LoanDecisionRequest,
)

logger = logging.getLogger(__name__)

# Base interest rates by risk grade (Indian market context)
BASE_RATES = {
    "AAA": 8.5, "AA": 9.0, "A": 10.0, "BBB": 11.5,
    "BB": 13.0, "B": 15.0, "C": 18.0, "D": 0.0,
}

MAX_LTV = {
    "AAA": 0.80, "AA": 0.75, "A": 0.70, "BBB": 0.60,
    "BB": 0.50, "B": 0.40, "C": 0.25, "D": 0.0,
}

# Banking benchmarks
DSCR_MIN = 1.25
ICR_MIN = 1.5
LEVERAGE_MAX = 4.0
CURRENT_RATIO_MIN = 1.2
DTE_MAX = 2.5


def make_decision(request: LoanDecisionRequest) -> LoanDecision:
    """
    Generate loan decision with financial ratios and deep
    explainability. Each factor is cited with evidence.
    """
    five_cs = request.five_cs_scores
    if five_cs is None:
        return LoanDecision(
            company_name=request.company_name,
            decision="REFER",
            explanation=(
                "Five Cs scores not available. "
                "Cannot make automated decision."
            ),
        )

    weighted_score = five_cs.weighted_total

    # ── Financial Ratio Analysis ──
    ratios = _compute_financial_ratios(request.financial_data)

    # ── Collect all rejection/concern reasons ──
    reasons: list[str] = []
    key_factors: list[str] = []

    # Ratio-based reasons
    _evaluate_ratios(ratios, reasons, key_factors)

    # Five Cs-based reasons
    _evaluate_five_cs(five_cs, reasons, key_factors)

    # Fraud-based reasons
    _evaluate_fraud(request.fraud_data, reasons, key_factors)

    # Regulatory-based reasons
    _evaluate_regulatory(
        request.regulatory_data, reasons, key_factors,
    )

    # Promoter-based reasons
    _evaluate_promoter(
        request.promoter_data, reasons, key_factors,
    )

    # Risk adjustments from primary insights
    adjusted_score = _apply_risk_adjustments(
        weighted_score, request.risk_adjustments,
    )

    # ── Final Decision ──
    adjusted_grade = _grade_from_score(adjusted_score)

    # Ratio penalty: each failed ratio reduces score
    ratio_penalty = _ratio_penalty(ratios)
    final_score = max(0, adjusted_score - ratio_penalty)
    final_grade = _grade_from_score(final_score)

    # Critical overrides
    critical_reject = _check_critical_overrides(
        request, reasons,
    )

    if critical_reject:
        decision = "REJECT"
    elif final_grade == "D" or final_score < 25:
        decision = "REJECT"
    elif final_grade in ("C", "B") or final_score < 45:
        decision = "REFER"
    else:
        decision = "APPROVE"

    # Build explanation
    explanation = _build_explanation(
        decision, final_score, final_grade, reasons,
    )

    # Calculate amounts and rates
    recommended_amount = _calculate_amount(
        request.requested_amount, final_grade,
        request.financial_data,
    )
    interest_rate, risk_premium = _calculate_rate(
        final_grade, final_score,
    )
    conditions = _generate_conditions(
        final_grade, five_cs, request, ratios,
    )

    return LoanDecision(
        company_name=request.company_name,
        decision=decision,
        recommended_amount=recommended_amount,
        interest_rate=interest_rate,
        risk_premium=risk_premium,
        risk_grade=final_grade,
        confidence_score=min(final_score / 100, 1.0),
        explanation=explanation,
        rejection_reasons=reasons,
        key_factors=key_factors,
        conditions=conditions,
        financial_ratios=ratios,
    )


# ─── Financial Ratio Computation ─────────────────

def _compute_financial_ratios(
    fin: dict,
) -> FinancialRatioReport:
    """Compute DSCR, ICR, Leverage, and other banking ratios."""
    ebitda = fin.get("ebitda") or 0
    total_debt = fin.get("total_debt") or 0
    revenue = fin.get("revenue") or 0
    interest = fin.get("interest_expense") or 0
    debt_payments = fin.get("annual_debt_payments") or 0

    # DSCR = EBITDA / Annual Debt Payments
    dscr_val = None
    dscr_assess = "N/A"
    dscr_detail = "Insufficient data to compute DSCR"
    if ebitda and debt_payments:
        dscr_val = round(ebitda / debt_payments, 2)
        if dscr_val >= 2.0:
            dscr_assess = "Pass"
            dscr_detail = f"DSCR of {dscr_val}x is strong (>2.0x)"
        elif dscr_val >= DSCR_MIN:
            dscr_assess = "Pass"
            dscr_detail = (
                f"DSCR of {dscr_val}x meets minimum "
                f"threshold of {DSCR_MIN}x"
            )
        elif dscr_val >= 1.0:
            dscr_assess = "Watch"
            dscr_detail = (
                f"DSCR of {dscr_val}x below {DSCR_MIN}x "
                f"benchmark but above breakeven"
            )
        else:
            dscr_assess = "Fail"
            dscr_detail = (
                f"DSCR of {dscr_val}x below 1.0x — "
                f"cashflow insufficient for debt service"
            )
    elif ebitda and total_debt:
        # Estimate annual payments as ~20% of total debt
        est_payments = total_debt * 0.2
        if est_payments > 0:
            dscr_val = round(ebitda / est_payments, 2)
            dscr_assess = (
                "Pass" if dscr_val >= DSCR_MIN
                else "Watch" if dscr_val >= 1.0
                else "Fail"
            )
            dscr_detail = (
                f"Estimated DSCR of {dscr_val}x "
                f"(debt payments estimated at 20% of "
                f"total debt)"
            )

    # ICR = EBITDA / Interest Expense
    icr_val = fin.get("interest_coverage")
    icr_assess = "N/A"
    icr_detail = "Insufficient data to compute ICR"
    if icr_val is None and ebitda and interest:
        icr_val = round(ebitda / interest, 2)
    if icr_val is not None:
        if icr_val >= 3.0:
            icr_assess = "Pass"
            icr_detail = f"ICR of {icr_val}x is strong (>3.0x)"
        elif icr_val >= ICR_MIN:
            icr_assess = "Pass"
            icr_detail = (
                f"ICR of {icr_val}x meets minimum "
                f"threshold of {ICR_MIN}x"
            )
        elif icr_val >= 1.0:
            icr_assess = "Watch"
            icr_detail = (
                f"ICR of {icr_val}x is weak — limited "
                f"interest coverage"
            )
        else:
            icr_assess = "Fail"
            icr_detail = (
                f"ICR of {icr_val}x below 1.0x — "
                f"earnings insufficient to cover interest"
            )

    # Leverage = Total Debt / EBITDA
    lev_val = None
    lev_assess = "N/A"
    lev_detail = "Insufficient data"
    if total_debt and ebitda:
        lev_val = round(total_debt / ebitda, 2)
        if lev_val <= 2.0:
            lev_assess = "Pass"
            lev_detail = f"Leverage of {lev_val}x is conservative"
        elif lev_val <= LEVERAGE_MAX:
            lev_assess = "Watch"
            lev_detail = (
                f"Leverage of {lev_val}x is elevated but "
                f"within {LEVERAGE_MAX}x limit"
            )
        else:
            lev_assess = "Fail"
            lev_detail = (
                f"Leverage of {lev_val}x exceeds "
                f"{LEVERAGE_MAX}x threshold — overleveraged"
            )

    # Current Ratio
    cr_val = fin.get("current_ratio")
    cr_assess = "N/A"
    cr_detail = "Insufficient data"
    if cr_val is not None:
        if cr_val >= 1.5:
            cr_assess = "Pass"
            cr_detail = f"Current ratio of {cr_val}x is healthy"
        elif cr_val >= CURRENT_RATIO_MIN:
            cr_assess = "Pass"
            cr_detail = (
                f"Current ratio of {cr_val}x is adequate"
            )
        elif cr_val >= 1.0:
            cr_assess = "Watch"
            cr_detail = (
                f"Current ratio of {cr_val}x is tight — "
                f"limited short-term liquidity"
            )
        else:
            cr_assess = "Fail"
            cr_detail = (
                f"Current ratio of {cr_val}x below 1.0 — "
                f"short-term liabilities exceed assets"
            )

    # Debt/Equity
    dte_val = fin.get("debt_to_equity")
    dte_assess = "N/A"
    dte_detail = "Insufficient data"
    if dte_val is not None:
        if dte_val <= 1.0:
            dte_assess = "Pass"
            dte_detail = f"D/E of {dte_val}x is conservative"
        elif dte_val <= DTE_MAX:
            dte_assess = "Watch"
            dte_detail = f"D/E of {dte_val}x is moderate"
        else:
            dte_assess = "Fail"
            dte_detail = (
                f"D/E of {dte_val}x exceeds {DTE_MAX}x — "
                f"high equity risk"
            )

    # EBITDA Margin
    margin_val = None
    margin_assess = "N/A"
    margin_detail = "Insufficient data"
    if ebitda and revenue:
        margin_val = round((ebitda / revenue) * 100, 1)
        if margin_val >= 20:
            margin_assess = "Pass"
            margin_detail = f"EBITDA margin of {margin_val}% is strong"
        elif margin_val >= 10:
            margin_assess = "Watch"
            margin_detail = (
                f"EBITDA margin of {margin_val}% is moderate"
            )
        else:
            margin_assess = "Fail"
            margin_detail = (
                f"EBITDA margin of {margin_val}% is thin — "
                f"limited buffer for debt service"
            )

    # Overall health
    assessments = [
        dscr_assess, icr_assess, lev_assess,
        cr_assess, dte_assess, margin_assess,
    ]
    fail_count = assessments.count("Fail")
    watch_count = assessments.count("Watch")
    if fail_count >= 2:
        overall = "Critical"
    elif fail_count >= 1:
        overall = "Weak"
    elif watch_count >= 2:
        overall = "Moderate"
    else:
        overall = "Strong"

    return FinancialRatioReport(
        dscr=FinancialRatio(
            name="DSCR", value=dscr_val,
            benchmark=f">{DSCR_MIN}x",
            assessment=dscr_assess, detail=dscr_detail,
        ),
        icr=FinancialRatio(
            name="ICR", value=icr_val,
            benchmark=f">{ICR_MIN}x",
            assessment=icr_assess, detail=icr_detail,
        ),
        leverage=FinancialRatio(
            name="Leverage", value=lev_val,
            benchmark=f"<{LEVERAGE_MAX}x",
            assessment=lev_assess, detail=lev_detail,
        ),
        current_ratio=FinancialRatio(
            name="Current Ratio", value=cr_val,
            benchmark=f">{CURRENT_RATIO_MIN}x",
            assessment=cr_assess, detail=cr_detail,
        ),
        debt_to_equity=FinancialRatio(
            name="Debt/Equity", value=dte_val,
            benchmark=f"<{DTE_MAX}x",
            assessment=dte_assess, detail=dte_detail,
        ),
        ebitda_margin=FinancialRatio(
            name="EBITDA Margin", value=margin_val,
            benchmark=">10%",
            assessment=margin_assess, detail=margin_detail,
        ),
        overall_health=overall,
    )


# ─── Evaluation Functions ────────────────────────

def _evaluate_ratios(
    ratios: FinancialRatioReport,
    reasons: list[str],
    factors: list[str],
) -> None:
    """Evaluate financial ratios and populate reasons."""
    for ratio in [
        ratios.dscr, ratios.icr, ratios.leverage,
        ratios.current_ratio, ratios.debt_to_equity,
        ratios.ebitda_margin,
    ]:
        if ratio.assessment == "Fail":
            reasons.append(ratio.detail)
        if ratio.assessment == "Pass" and ratio.value is not None:
            factors.append(
                f"{ratio.name}: {ratio.value} ({ratio.assessment})"
            )


def _evaluate_five_cs(
    five_cs: FiveCsScoreResponse,
    reasons: list[str],
    factors: list[str],
) -> None:
    """Evaluate Five Cs scores."""
    for cs in five_cs.scores:
        if cs.score < 35:
            reasons.append(
                f"Weak {cs.category} score ({cs.score:.0f}/100)"
                f": {cs.explanation[:120]}"
            )
        elif cs.score >= 70:
            factors.append(
                f"Strong {cs.category} ({cs.score:.0f}/100)"
            )


def _evaluate_fraud(
    fraud: dict, reasons: list[str], factors: list[str],
) -> None:
    """Evaluate fraud detection results."""
    if not fraud:
        return
    score = fraud.get("fraud_score", 0)
    if score >= 60:
        reasons.append(
            f"Fraud risk score of {score}/100 — "
            f"critical fraud indicators detected"
        )
    alerts = fraud.get("alerts", [])
    for a in alerts:
        if a.get("severity") == "critical":
            reasons.append(
                f"Fraud alert: {a.get('title', 'Unknown')}"
            )


def _evaluate_regulatory(
    reg: dict, reasons: list[str], factors: list[str],
) -> None:
    """Evaluate regulatory check results."""
    if not reg:
        return
    cibil = reg.get("cibil", {})
    score = cibil.get("score", 0)
    if score and score < 650:
        reasons.append(
            f"CIBIL commercial score of {score} "
            f"below 650 threshold"
        )
    elif score and score >= 750:
        factors.append(f"CIBIL score: {score} (Strong)")

    flags = reg.get("flags", [])
    for f in flags:
        if f not in reasons:
            reasons.append(f)


def _evaluate_promoter(
    promo: dict, reasons: list[str], factors: list[str],
) -> None:
    """Evaluate promoter risk data."""
    if not promo:
        return
    lit = promo.get("litigation_flags", [])
    for l in lit[:3]:
        reasons.append(f"Promoter litigation: {l}")

    risk = promo.get("overall_promoter_risk", "low")
    if risk == "high":
        reasons.append("Overall promoter risk rated HIGH")


# ─── Helper Functions ────────────────────────────

def _apply_risk_adjustments(
    score: float, adjustments: list[dict],
) -> float:
    """Apply risk adjustment deltas."""
    total_delta = 0.0
    for adj in adjustments:
        delta = adj.get(
            "adjustment", adj.get("overall_risk_delta", 0.0),
        )
        if isinstance(delta, (int, float)):
            total_delta += delta
    adjusted = score + (total_delta * 10)
    return max(0, min(100, adjusted))


def _grade_from_score(score: float) -> str:
    """Map score to risk grade."""
    if score >= 85: return "AAA"
    if score >= 75: return "AA"
    if score >= 65: return "A"
    if score >= 55: return "BBB"
    if score >= 45: return "BB"
    if score >= 35: return "B"
    if score >= 25: return "C"
    return "D"


def _ratio_penalty(ratios: FinancialRatioReport) -> float:
    """Calculate score penalty from failed ratios."""
    penalty = 0
    for r in [
        ratios.dscr, ratios.icr, ratios.leverage,
        ratios.current_ratio, ratios.debt_to_equity,
    ]:
        if r.assessment == "Fail":
            penalty += 8
        elif r.assessment == "Watch":
            penalty += 3
    return penalty


def _check_critical_overrides(
    request: LoanDecisionRequest,
    reasons: list[str],
) -> bool:
    """Check for automatic rejection triggers."""
    fraud = request.fraud_data
    if fraud and fraud.get("fraud_score", 0) >= 70:
        return True

    reg = request.regulatory_data
    if reg:
        cibil = reg.get("cibil", {})
        if cibil.get("score", 999) < 500:
            return True
        directors = reg.get("director_checks", [])
        if any(d.get("defaulter_flag") for d in directors):
            reasons.append(
                "Automatic rejection: promoter flagged as "
                "defaulter in MCA records"
            )
            return True

    return False


def _build_explanation(
    decision: str, score: float, grade: str,
    reasons: list[str],
) -> str:
    """Build structured explanation with cited evidence."""
    if decision == "REJECT" and reasons:
        bullets = "\n".join(f"  - {r}" for r in reasons[:8])
        return (
            f"REJECTED (Score: {score:.1f}/100, "
            f"Grade: {grade})\n\n"
            f"Reasons:\n{bullets}"
        )
    if decision == "REFER" and reasons:
        bullets = "\n".join(f"  - {r}" for r in reasons[:6])
        return (
            f"REFERRED for manual review "
            f"(Score: {score:.1f}/100, Grade: {grade})\n\n"
            f"Concerns:\n{bullets}"
        )
    if decision == "APPROVE":
        return (
            f"APPROVED (Score: {score:.1f}/100, "
            f"Grade: {grade}). Company demonstrates "
            f"adequate creditworthiness across financial "
            f"ratio analysis, Five Cs assessment, "
            f"and regulatory checks."
        )
    return f"Score: {score:.1f}/100, Grade: {grade}."


def _calculate_amount(
    requested: float, grade: str, fin: dict,
) -> float:
    """Calculate recommended loan amount."""
    if grade == "D":
        return 0.0
    ltv = MAX_LTV.get(grade, 0.5)
    revenue = fin.get("revenue", 0)
    ebitda = fin.get("ebitda", 0)
    max_ebitda = ebitda * 3 if ebitda else float("inf")
    max_rev = revenue * 0.5 if revenue else float("inf")
    max_exp = min(max_ebitda, max_rev)
    if max_exp == float("inf"):
        return round(requested * ltv, 2)
    return round(min(requested, max_exp) * ltv, 2)


def _calculate_rate(
    grade: str, score: float,
) -> tuple[float, float]:
    """Calculate interest rate and risk premium."""
    base = BASE_RATES.get(grade, 15.0)
    if score < 30: premium = 200
    elif score < 50: premium = 150
    elif score < 60: premium = 100
    elif score < 70: premium = 50
    else: premium = 0
    return round(base + premium / 100, 2), premium


def _generate_conditions(
    grade: str, five_cs: FiveCsScoreResponse,
    request: LoanDecisionRequest,
    ratios: FinancialRatioReport,
) -> list[str]:
    """Generate lending conditions."""
    conds: list[str] = []

    if grade in ("BB", "B", "C"):
        conds.append("Quarterly financial reporting required")
        conds.append("Monthly review calls with relationship manager")

    if grade in ("B", "C"):
        conds.append("Personal guarantee of promoters required")
        conds.append("Additional collateral security required")

    if ratios.dscr.assessment == "Watch":
        conds.append(
            "DSCR covenant: maintain minimum 1.25x DSCR"
        )

    if ratios.leverage.assessment in ("Watch", "Fail"):
        conds.append("Leverage covenant: reduce debt/EBITDA below 4.0x")

    for cs in five_cs.scores:
        if cs.category == "Collateral" and cs.score < 50:
            conds.append(
                "Adequate collateral coverage before disbursement"
            )
        if cs.category == "Character" and cs.score < 50:
            conds.append(
                "Enhanced promoter due diligence required"
            )

    fraud = request.fraud_data
    if fraud and fraud.get("fraud_score", 0) >= 30:
        conds.append(
            "Forensic audit of accounts required prior to "
            "disbursement"
        )

    if not conds:
        conds.append("Standard lending terms and conditions apply")

    return conds
