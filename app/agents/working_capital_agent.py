"""
Working Capital Stress Analyzer — evaluates liquidity health using
working capital metrics derived from extracted financial data.

Computes:
- Receivable Days = (AR / Revenue) × 365
- Inventory Days  = (Inventory / COGS) × 365
- Payable Days    = (AP / COGS) × 365
- Cash Conversion Cycle (CCC) = Receivable + Inventory − Payable
- Working Capital Score (0–100)
- Liquidity Risk Level (LOW / MODERATE / HIGH / CRITICAL)

Companies often default due to liquidity stress even when
profits appear strong — this module catches those patterns.
"""

import logging

logger = logging.getLogger(__name__)


def run_working_capital_analysis(
    company_name: str,
    financial_data: dict,
) -> dict:
    """
    Analyse working capital health from extracted financial metrics.

    Args:
        company_name: Name of the company
        financial_data: Dict with keys like revenue, cogs,
            accounts_receivable, accounts_payable, inventory

    Returns:
        Dict matching WorkingCapitalReport schema.
    """
    revenue = financial_data.get("revenue")
    cogs = financial_data.get("cogs")
    ar = financial_data.get("accounts_receivable")
    ap = financial_data.get("accounts_payable")
    inventory = financial_data.get("inventory")

    # Check data availability
    available_metrics = {
        "revenue": revenue,
        "cogs": cogs,
        "accounts_receivable": ar,
        "accounts_payable": ap,
        "inventory": inventory,
    }
    missing = [k for k, v in available_metrics.items() if v is None]

    if revenue is None or revenue <= 0:
        return _no_data_result(company_name, missing)

    # Use revenue as fallback for COGS if not available
    cogs_effective = cogs if (cogs and cogs > 0) else revenue * 0.7

    # ── Receivable Days ──
    receivable_days = None
    if ar is not None and ar >= 0:
        receivable_days = (ar / revenue) * 365

    # ── Inventory Days ──
    inventory_days = None
    if inventory is not None and inventory >= 0 and cogs_effective > 0:
        inventory_days = (inventory / cogs_effective) * 365

    # ── Payable Days ──
    payable_days = None
    if ap is not None and ap >= 0 and cogs_effective > 0:
        payable_days = (ap / cogs_effective) * 365

    # ── Cash Conversion Cycle ──
    ccc = None
    ccc_components_available = 0
    rec_d = receivable_days or 0
    inv_d = inventory_days or 0
    pay_d = payable_days or 0

    if receivable_days is not None:
        ccc_components_available += 1
    if inventory_days is not None:
        ccc_components_available += 1
    if payable_days is not None:
        ccc_components_available += 1

    if ccc_components_available >= 2:
        ccc = rec_d + inv_d - pay_d

    # ── Working Capital Score (0-100, higher=healthier) ──
    wc_score = _compute_wc_score(
        receivable_days, inventory_days, payable_days, ccc,
    )

    # ── Liquidity Risk Level ──
    risk_level = _assess_risk(ccc, wc_score)

    # ── Stress Indicators ──
    stress_indicators = _detect_stress(
        receivable_days, inventory_days, payable_days, ccc,
    )

    # ── Explanation ──
    explanation = _build_explanation(
        company_name, receivable_days, inventory_days,
        payable_days, ccc, risk_level, stress_indicators,
    )

    return {
        "company_name": company_name,
        "receivable_days": _round_or_none(receivable_days),
        "inventory_days": _round_or_none(inventory_days),
        "payable_days": _round_or_none(payable_days),
        "cash_conversion_cycle": _round_or_none(ccc),
        "working_capital_score": round(wc_score, 1),
        "liquidity_risk_level": risk_level,
        "stress_indicators": stress_indicators,
        "data_completeness": f"{3 - len([m for m in ['accounts_receivable', 'inventory', 'accounts_payable'] if m in missing])}/3 key metrics available",
        "explanation": explanation,
        "missing_data": missing,
    }


def _no_data_result(company_name: str, missing: list) -> dict:
    """Return result when insufficient data is available."""
    return {
        "company_name": company_name,
        "receivable_days": None,
        "inventory_days": None,
        "payable_days": None,
        "cash_conversion_cycle": None,
        "working_capital_score": 50.0,  # Neutral when unknown
        "liquidity_risk_level": "UNKNOWN",
        "stress_indicators": [],
        "data_completeness": "Insufficient financial data",
        "explanation": (
            "Working capital analysis unavailable — revenue data "
            "is required at minimum. Consider uploading detailed "
            "financial statements."
        ),
        "missing_data": missing,
    }


def _compute_wc_score(
    rec_days: float | None,
    inv_days: float | None,
    pay_days: float | None,
    ccc: float | None,
) -> float:
    """
    Compute working capital health score (0-100).

    Higher score = healthier working capital position.
    """
    score = 60.0  # Neutral baseline

    # CCC scoring (primary metric)
    if ccc is not None:
        if ccc < 30:
            score += 25  # Excellent
        elif ccc < 60:
            score += 15  # Good
        elif ccc < 90:
            score += 5   # Acceptable
        elif ccc < 120:
            score -= 10  # Moderate stress
        elif ccc < 180:
            score -= 25  # High stress
        else:
            score -= 40  # Critical stress

        # Negative CCC bonus (faster cash cycle)
        if ccc < 0:
            score += 10

    # Receivable days scoring
    if rec_days is not None:
        if rec_days < 30:
            score += 5
        elif rec_days < 60:
            score += 2
        elif rec_days > 120:
            score -= 10
        elif rec_days > 90:
            score -= 5

    # Inventory days scoring
    if inv_days is not None:
        if inv_days < 30:
            score += 5
        elif inv_days < 60:
            score += 2
        elif inv_days > 120:
            score -= 10
        elif inv_days > 90:
            score -= 5

    # Payable days scoring (longer = better cash position)
    if pay_days is not None:
        if pay_days > 60:
            score += 5
        elif pay_days > 45:
            score += 2
        elif pay_days < 15:
            score -= 5

    return max(0.0, min(100.0, score))


def _assess_risk(
    ccc: float | None,
    wc_score: float,
) -> str:
    """Determine liquidity risk level."""
    if ccc is not None:
        if ccc > 180:
            return "CRITICAL"
        if ccc > 120:
            return "HIGH"
        if ccc > 60:
            return "MODERATE"
        return "LOW"

    # Fallback to score-based assessment
    if wc_score >= 70:
        return "LOW"
    if wc_score >= 50:
        return "MODERATE"
    if wc_score >= 30:
        return "HIGH"
    return "CRITICAL"


def _detect_stress(
    rec_days: float | None,
    inv_days: float | None,
    pay_days: float | None,
    ccc: float | None,
) -> list[dict]:
    """Detect specific working capital stress indicators."""
    indicators: list[dict] = []

    if rec_days is not None and rec_days > 90:
        indicators.append({
            "signal": "Slow Receivable Collection",
            "severity": "high" if rec_days > 120 else "medium",
            "description": (
                f"Receivable days of {rec_days:.0f} indicate delayed "
                f"customer payments. Industry norm is 30-60 days."
            ),
            "metric": f"{rec_days:.0f} days",
        })

    if inv_days is not None and inv_days > 90:
        indicators.append({
            "signal": "Inventory Buildup",
            "severity": "high" if inv_days > 150 else "medium",
            "description": (
                f"Inventory days of {inv_days:.0f} suggest stock "
                f"piling up. May indicate demand slowdown or "
                f"obsolescence risk."
            ),
            "metric": f"{inv_days:.0f} days",
        })

    if pay_days is not None and pay_days < 15:
        indicators.append({
            "signal": "Weak Supplier Credit",
            "severity": "medium",
            "description": (
                f"Payable days of {pay_days:.0f} indicate very "
                f"short supplier credit terms. Company may lack "
                f"bargaining power or creditworthiness with suppliers."
            ),
            "metric": f"{pay_days:.0f} days",
        })

    if ccc is not None and ccc > 120:
        indicators.append({
            "signal": "Extended Cash Conversion Cycle",
            "severity": "critical" if ccc > 180 else "high",
            "description": (
                f"CCC of {ccc:.0f} days means cash is locked in "
                f"operations for {ccc:.0f} days. Company requires "
                f"significant working capital financing."
            ),
            "metric": f"{ccc:.0f} days",
        })

    if (rec_days and rec_days > 90) and (inv_days and inv_days > 90):
        indicators.append({
            "signal": "Dual Liquidity Pressure",
            "severity": "high",
            "description": (
                "Both receivable collection and inventory turnover "
                "are slow, creating compounded liquidity pressure."
            ),
            "metric": f"AR: {rec_days:.0f}d + Inv: {inv_days:.0f}d",
        })

    return indicators


def _build_explanation(
    company: str,
    rec_days: float | None,
    inv_days: float | None,
    pay_days: float | None,
    ccc: float | None,
    risk_level: str,
    stress: list[dict],
) -> str:
    """Build human-readable explanation for CAM report."""
    parts = []

    if ccc is not None:
        parts.append(
            f"Cash Conversion Cycle for {company} is {ccc:.0f} days."
        )
        if ccc < 60:
            parts.append(
                "This indicates healthy cash flow with efficient "
                "working capital management."
            )
        elif ccc < 120:
            parts.append(
                "This indicates moderate working capital stress. "
                "Cash is tied up for an extended period."
            )
        else:
            parts.append(
                "This represents significant liquidity stress. "
                "The company needs substantial working capital "
                "financing to sustain operations."
            )

    metrics = []
    if rec_days is not None:
        metrics.append(f"Receivable Days: {rec_days:.0f}")
    if inv_days is not None:
        metrics.append(f"Inventory Days: {inv_days:.0f}")
    if pay_days is not None:
        metrics.append(f"Payable Days: {pay_days:.0f}")

    if metrics:
        parts.append(f"Key metrics: {', '.join(metrics)}.")

    if stress:
        parts.append(
            f"Identified {len(stress)} stress indicator(s): "
            + "; ".join(s["signal"] for s in stress) + "."
        )

    if not parts:
        parts.append(
            "Insufficient data for working capital analysis. "
            "Consider providing detailed balance sheet data."
        )

    return " ".join(parts)


def _round_or_none(value: float | None) -> float | None:
    """Round a value to 1 decimal or return None."""
    return round(value, 1) if value is not None else None
