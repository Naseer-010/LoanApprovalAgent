"""
Historical Borrower Trust Agent — analyses previous credit evaluations.

Queries the borrower_history database for past applications,
computes a Historical Trust Score, and detects trends in:
- risk scores
- fraud signals
- financial stability

The historical trust score is blended with the current risk model
(0.75 current + 0.25 historical) and never overrides current risk.
"""

import logging
from datetime import datetime

from app.services.database.borrower_db import get_history

logger = logging.getLogger(__name__)


def run_historical_trust_analysis(
    company_name: str,
) -> dict:
    """
    Analyse the historical credit behaviour of a company.

    Returns:
        dict matching HistoricalTrustReport schema.
    """
    records = get_history(company_name)

    if not records:
        return {
            "company_name": company_name,
            "number_of_previous_applications": 0,
            "historical_trust_score": 0.0,
            "risk_score_trend": "no_history",
            "fraud_risk_trend": "no_history",
            "financial_stability_trend": "no_history",
            "trend_summary": (
                "No previous loan applications found for this company. "
                "Historical trust analysis unavailable."
            ),
            "previous_applications": [],
        }

    # ── Compute Historical Trust Score ──
    # Weighted average: more recent applications carry more weight
    risk_scores = [r.get("risk_score", 0.0) for r in records]
    trust_score = _weighted_average(risk_scores)

    # ── Trend Detection ──
    risk_trend = _detect_trend(
        [r.get("risk_score", 0.0) for r in records],
    )
    fraud_trend = _detect_trend(
        [r.get("fraud_risk_score", 0.0) for r in records],
    )
    five_cs_scores = [r.get("five_cs_score", 0.0) for r in records]
    # For financial stability, higher 5Cs = better, so invert trend
    financial_trend = _detect_trend(five_cs_scores, higher_is_worse=False)

    # ── Summarise Previous Applications ──
    previous_apps = []
    for r in records:
        date_str = r.get("application_date", "")
        try:
            date_fmt = datetime.fromisoformat(date_str).strftime(
                "%d %b %Y",
            )
        except (ValueError, TypeError):
            date_fmt = date_str

        previous_apps.append({
            "date": date_fmt,
            "decision": r.get("decision", "REFER"),
            "risk_score": round(r.get("risk_score", 0.0), 2),
            "amount_requested": r.get("loan_amount_requested", 0.0),
            "amount_approved": r.get("loan_amount_approved", 0.0),
            "fraud_risk": round(r.get("fraud_risk_score", 0.0), 2),
            "five_cs": round(r.get("five_cs_score", 0.0), 2),
        })

    # ── Build Trend Summary ──
    trend_summary = _build_trend_summary(
        company_name,
        len(records),
        trust_score,
        risk_trend,
        fraud_trend,
        financial_trend,
    )

    return {
        "company_name": company_name,
        "number_of_previous_applications": len(records),
        "historical_trust_score": round(trust_score, 2),
        "risk_score_trend": risk_trend,
        "fraud_risk_trend": fraud_trend,
        "financial_stability_trend": financial_trend,
        "trend_summary": trend_summary,
        "previous_applications": previous_apps,
    }


def _weighted_average(values: list[float]) -> float:
    """
    Compute time-weighted average. More recent entries have higher weight.

    Weight scheme: linear from 1 (oldest) to N (newest).
    Returns the score inverted: high trust = 100 - risk_score.
    """
    if not values:
        return 0.0

    n = len(values)
    weights = list(range(1, n + 1))
    total_weight = sum(weights)

    weighted_sum = sum(v * w for v, w in zip(values, weights))
    avg_risk = weighted_sum / total_weight if total_weight > 0 else 0.0

    # Convert risk score (0-100, higher=riskier) to trust score
    # (0-100, higher=more trustworthy)
    trust = max(0.0, min(100.0, 100.0 - avg_risk))
    return trust


def _detect_trend(
    values: list[float],
    higher_is_worse: bool = True,
) -> str:
    """
    Detect trend direction from a series of values.

    Returns: 'improving', 'stable', 'worsening', or 'insufficient_data'
    """
    if len(values) < 2:
        return "insufficient_data"

    # Use simple linear regression slope
    n = len(values)
    x_mean = (n - 1) / 2.0
    y_mean = sum(values) / n

    numerator = sum(
        (i - x_mean) * (v - y_mean) for i, v in enumerate(values)
    )
    denominator = sum((i - x_mean) ** 2 for i in range(n))

    if denominator == 0:
        return "stable"

    slope = numerator / denominator

    # Normalize slope against the mean to get relative change
    if y_mean > 0:
        relative_change = abs(slope) / y_mean
    else:
        relative_change = abs(slope)

    # Threshold: < 5% per period = stable
    if relative_change < 0.05:
        return "stable"

    if higher_is_worse:
        return "worsening" if slope > 0 else "improving"
    else:
        return "improving" if slope > 0 else "worsening"


def _build_trend_summary(
    company: str,
    num_apps: int,
    trust_score: float,
    risk_trend: str,
    fraud_trend: str,
    fin_trend: str,
) -> str:
    """Build a human-readable trend summary for CAM report."""
    parts = [
        f"Company '{company}' has {num_apps} previous loan "
        f"application(s) on record.",
    ]

    if trust_score >= 70:
        parts.append(
            f"Historical Trust Score is {trust_score:.0f}/100 "
            f"(strong), indicating reliable credit behaviour."
        )
    elif trust_score >= 50:
        parts.append(
            f"Historical Trust Score is {trust_score:.0f}/100 "
            f"(moderate), indicating acceptable credit behaviour."
        )
    elif trust_score > 0:
        parts.append(
            f"Historical Trust Score is {trust_score:.0f}/100 "
            f"(weak), indicating elevated historical credit risk."
        )

    trend_map = {
        "improving": "improving",
        "stable": "stable",
        "worsening": "deteriorating",
    }

    risk_desc = trend_map.get(risk_trend, risk_trend)
    fraud_desc = trend_map.get(fraud_trend, fraud_trend)
    fin_desc = trend_map.get(fin_trend, fin_trend)

    if num_apps >= 2:
        parts.append(
            f"Risk scores have been {risk_desc} across applications. "
            f"Fraud signals are {fraud_desc}. "
            f"Financial stability is {fin_desc}."
        )

    return " ".join(parts)
