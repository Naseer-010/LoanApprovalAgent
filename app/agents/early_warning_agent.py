"""
Early Warning Signal Agent — predicts future borrower distress.

Monitors: revenue decline, EBITDA margin decline, sudden debt increase,
fraud signal increase, negative news. Computes early_warning_score (0-1)
with risk level (LOW/MODERATE/HIGH) and trigger descriptions.
"""

import logging

logger = logging.getLogger(__name__)


def run_early_warning_analysis(
    company_name: str,
    financial_data: dict,
    fraud_data: dict | None = None,
    research_data: dict | None = None,
    sector_risk: dict | None = None,
    historical_financials: dict | None = None,
) -> dict:
    """
    Run early warning signal detection.

    Returns:
    - early_warning_score (0.0-1.0)
    - risk_level: LOW / MODERATE / HIGH
    - triggers: list of warning descriptions
    - signal_details: breakdown by category
    """
    triggers: list[dict] = []
    signal_scores: dict[str, float] = {}

    # Signal 1: Revenue Decline
    rev_signal = _check_revenue_decline(financial_data, historical_financials)
    signal_scores["revenue_decline"] = rev_signal["score"]
    triggers.extend(rev_signal["triggers"])

    # Signal 2: EBITDA Margin Decline
    margin_signal = _check_margin_decline(financial_data, historical_financials)
    signal_scores["ebitda_margin_decline"] = margin_signal["score"]
    triggers.extend(margin_signal["triggers"])

    # Signal 3: Sudden Debt Increase
    debt_signal = _check_debt_increase(financial_data, historical_financials)
    signal_scores["debt_increase"] = debt_signal["score"]
    triggers.extend(debt_signal["triggers"])

    # Signal 4: Fraud Signal Increase
    fraud_signal = _check_fraud_signals(fraud_data)
    signal_scores["fraud_risk"] = fraud_signal["score"]
    triggers.extend(fraud_signal["triggers"])

    # Signal 5: Negative News
    news_signal = _check_negative_news(research_data)
    signal_scores["negative_news"] = news_signal["score"]
    triggers.extend(news_signal["triggers"])

    # Signal 6: Sector Stress
    sector_signal = _check_sector_stress(sector_risk)
    signal_scores["sector_stress"] = sector_signal["score"]
    triggers.extend(sector_signal["triggers"])

    # Signal 7: Weak Liquidity
    liquidity_signal = _check_liquidity(financial_data)
    signal_scores["liquidity_stress"] = liquidity_signal["score"]
    triggers.extend(liquidity_signal["triggers"])

    # Compute aggregate early warning score (0-1)
    weights = {
        "revenue_decline": 0.20,
        "ebitda_margin_decline": 0.15,
        "debt_increase": 0.15,
        "fraud_risk": 0.15,
        "negative_news": 0.10,
        "sector_stress": 0.10,
        "liquidity_stress": 0.15,
    }

    early_warning_score = sum(
        signal_scores.get(k, 0) * w
        for k, w in weights.items()
    )
    early_warning_score = round(min(1.0, max(0.0, early_warning_score)), 3)

    risk_level = _ews_risk_level(early_warning_score)

    # Sort triggers by severity
    triggers.sort(key=lambda t: {"HIGH": 0, "MODERATE": 1, "LOW": 2}.get(
        t.get("severity", "LOW"), 3,
    ))

    return {
        "company_name": company_name,
        "early_warning_score": early_warning_score,
        "risk_level": risk_level,
        "triggers": triggers,
        "signal_details": signal_scores,
        "signals_monitored": len(signal_scores),
        "active_warnings": len(triggers),
    }


def _check_revenue_decline(
    financial_data: dict,
    historical: dict | None,
) -> dict:
    """Check for revenue decline signals."""
    triggers = []
    score = 0.0

    revenue = financial_data.get("revenue")
    growth = financial_data.get("revenue_growth")

    if growth is not None:
        if growth < -0.25:
            score = 1.0
            triggers.append({
                "signal": "Revenue Decline",
                "description": f"Revenue dropped {abs(growth):.0%} — severe decline",
                "severity": "HIGH",
                "metric": f"growth: {growth:.1%}",
            })
        elif growth < -0.10:
            score = 0.6
            triggers.append({
                "signal": "Revenue Decline",
                "description": f"Revenue declined {abs(growth):.0%}",
                "severity": "MODERATE",
                "metric": f"growth: {growth:.1%}",
            })
        elif growth < -0.05:
            score = 0.3
            triggers.append({
                "signal": "Revenue Softening",
                "description": f"Revenue slightly declining ({growth:.1%})",
                "severity": "LOW",
                "metric": f"growth: {growth:.1%}",
            })

    # Check historical trend if available
    if historical:
        prev_revenue = historical.get("previous_revenue")
        if prev_revenue and revenue and prev_revenue > 0:
            change = (revenue - prev_revenue) / prev_revenue
            if change < -0.25 and score < 1.0:
                score = max(score, 0.8)
                triggers.append({
                    "signal": "Historical Revenue Drop",
                    "description": (
                        f"Revenue dropped from ₹{prev_revenue:,.0f} "
                        f"to ₹{revenue:,.0f} ({change:.0%})"
                    ),
                    "severity": "HIGH",
                    "metric": f"change: {change:.1%}",
                })

    return {"score": score, "triggers": triggers}


def _check_margin_decline(
    financial_data: dict,
    historical: dict | None,
) -> dict:
    """Check for EBITDA margin deterioration."""
    triggers = []
    score = 0.0

    ebitda = financial_data.get("ebitda")
    revenue = financial_data.get("revenue")

    if ebitda and revenue and revenue > 0:
        margin = ebitda / revenue
        if margin < 0.05:
            score = 0.9
            triggers.append({
                "signal": "Critical EBITDA Margin",
                "description": (
                    f"EBITDA margin at {margin:.1%} — dangerously thin"
                ),
                "severity": "HIGH",
                "metric": f"margin: {margin:.1%}",
            })
        elif margin < 0.10:
            score = 0.5
            triggers.append({
                "signal": "Low EBITDA Margin",
                "description": f"EBITDA margin at {margin:.1%} — below healthy levels",
                "severity": "MODERATE",
                "metric": f"margin: {margin:.1%}",
            })

    # Historical comparison
    if historical:
        prev_margin = historical.get("previous_ebitda_margin")
        if prev_margin and ebitda and revenue and revenue > 0:
            current_margin = ebitda / revenue
            margin_change = current_margin - prev_margin
            if margin_change < -0.05:
                score = max(score, 0.7)
                triggers.append({
                    "signal": "Margin Compression",
                    "description": (
                        f"EBITDA margin declined from "
                        f"{prev_margin:.1%} to {current_margin:.1%}"
                    ),
                    "severity": "MODERATE",
                    "metric": f"change: {margin_change:.1%}",
                })

    return {"score": score, "triggers": triggers}


def _check_debt_increase(
    financial_data: dict,
    historical: dict | None,
) -> dict:
    """Check for sudden debt increase."""
    triggers = []
    score = 0.0

    total_debt = financial_data.get("total_debt")
    equity = financial_data.get("equity") or financial_data.get("net_worth")
    dte = financial_data.get("debt_to_equity")

    if dte is not None:
        if dte > 5.0:
            score = 0.9
            triggers.append({
                "signal": "Extreme Leverage",
                "description": f"D/E ratio at {dte:.1f}x — overleveraged",
                "severity": "HIGH",
                "metric": f"D/E: {dte:.1f}",
            })
        elif dte > 3.0:
            score = 0.5
            triggers.append({
                "signal": "High Leverage",
                "description": f"D/E ratio at {dte:.1f}x — elevated",
                "severity": "MODERATE",
                "metric": f"D/E: {dte:.1f}",
            })

    if historical:
        prev_debt = historical.get("previous_total_debt")
        if prev_debt and total_debt and prev_debt > 0:
            change = (total_debt - prev_debt) / prev_debt
            if change > 0.50:
                score = max(score, 0.8)
                triggers.append({
                    "signal": "Sudden Debt Increase",
                    "description": (
                        f"Total debt increased {change:.0%} "
                        f"— significant new borrowing"
                    ),
                    "severity": "HIGH",
                    "metric": f"debt increase: {change:.0%}",
                })

    return {"score": score, "triggers": triggers}


def _check_fraud_signals(fraud_data: dict | None) -> dict:
    """Check for elevated fraud risk."""
    triggers = []
    score = 0.0

    if not fraud_data:
        return {"score": 0.0, "triggers": []}

    fraud_score = fraud_data.get("fraud_score", 0)
    if fraud_score >= 60:
        score = 0.9
        triggers.append({
            "signal": "Critical Fraud Risk",
            "description": f"Fraud risk score at {fraud_score}/100",
            "severity": "HIGH",
            "metric": f"fraud_score: {fraud_score}",
        })
    elif fraud_score >= 40:
        score = 0.5
        triggers.append({
            "signal": "Elevated Fraud Risk",
            "description": f"Fraud risk score at {fraud_score}/100",
            "severity": "MODERATE",
            "metric": f"fraud_score: {fraud_score}",
        })
    elif fraud_score >= 20:
        score = 0.2
        triggers.append({
            "signal": "Moderate Fraud Indicators",
            "description": f"Fraud risk score at {fraud_score}/100",
            "severity": "LOW",
            "metric": f"fraud_score: {fraud_score}",
        })

    critical = fraud_data.get("critical_count", 0)
    if critical > 0:
        score = max(score, 0.8)
        triggers.append({
            "signal": "Critical Fraud Alerts",
            "description": f"{critical} critical fraud alert(s) detected",
            "severity": "HIGH",
            "metric": f"critical_alerts: {critical}",
        })

    return {"score": score, "triggers": triggers}


def _check_negative_news(research_data: dict | None) -> dict:
    """Check for negative news and research signals."""
    triggers = []
    score = 0.0

    if not research_data:
        return {"score": 0.0, "triggers": []}

    sentiment = research_data.get("overall_sentiment", "neutral")
    risk_signals = research_data.get("risk_signals", {})

    if isinstance(risk_signals, dict):
        lit_risk = risk_signals.get("litigation_risk", 0)
        rep_risk = risk_signals.get("reputation_risk", 0)

        if lit_risk > 0.6:
            score = max(score, 0.8)
            triggers.append({
                "signal": "Litigation Risk",
                "description": f"High litigation risk detected ({lit_risk:.0%})",
                "severity": "HIGH",
                "metric": f"litigation_risk: {lit_risk:.2f}",
            })
        elif lit_risk > 0.3:
            score = max(score, 0.4)
            triggers.append({
                "signal": "Litigation Concerns",
                "description": f"Moderate litigation risk ({lit_risk:.0%})",
                "severity": "MODERATE",
                "metric": f"litigation_risk: {lit_risk:.2f}",
            })

        if rep_risk > 0.5:
            score = max(score, 0.6)
            triggers.append({
                "signal": "Reputation Risk",
                "description": "Significant negative press detected",
                "severity": "MODERATE",
                "metric": f"reputation_risk: {rep_risk:.2f}",
            })

    if sentiment == "negative":
        score = max(score, 0.5)
        triggers.append({
            "signal": "Negative Research Sentiment",
            "description": "Overall research sentiment is negative",
            "severity": "MODERATE",
            "metric": "sentiment: negative",
        })

    return {"score": score, "triggers": triggers}


def _check_sector_stress(sector_risk: dict | None) -> dict:
    """Check for sector-level stress signals."""
    triggers = []
    score = 0.0

    if not sector_risk:
        return {"score": 0.0, "triggers": []}

    sector_score = sector_risk.get("sector_risk_score", 0)

    if sector_score >= 60:
        score = 0.8
        triggers.append({
            "signal": "Sector Under Stress",
            "description": (
                f"Sector risk score at {sector_score}/100 — "
                f"industry-level headwinds"
            ),
            "severity": "HIGH",
            "metric": f"sector_risk: {sector_score}",
        })
    elif sector_score >= 40:
        score = 0.4
        triggers.append({
            "signal": "Sector Caution",
            "description": f"Sector risk score at {sector_score}/100",
            "severity": "MODERATE",
            "metric": f"sector_risk: {sector_score}",
        })

    headwinds = sector_risk.get("sector_headwinds", [])
    if len(headwinds) >= 3:
        score = max(score, 0.5)
        triggers.append({
            "signal": "Multiple Sector Headwinds",
            "description": f"{len(headwinds)} sector headwinds identified",
            "severity": "MODERATE",
            "metric": f"headwinds: {len(headwinds)}",
        })

    return {"score": score, "triggers": triggers}


def _check_liquidity(financial_data: dict) -> dict:
    """Check for liquidity stress signals."""
    triggers = []
    score = 0.0

    current_ratio = financial_data.get("current_ratio")
    if current_ratio is not None:
        if current_ratio < 0.8:
            score = 0.9
            triggers.append({
                "signal": "Severe Liquidity Stress",
                "description": (
                    f"Current ratio at {current_ratio:.2f} — "
                    f"below critical threshold"
                ),
                "severity": "HIGH",
                "metric": f"current_ratio: {current_ratio:.2f}",
            })
        elif current_ratio < 1.0:
            score = 0.5
            triggers.append({
                "signal": "Liquidity Weakness",
                "description": (
                    f"Current ratio at {current_ratio:.2f} — "
                    f"below 1.0"
                ),
                "severity": "MODERATE",
                "metric": f"current_ratio: {current_ratio:.2f}",
            })

    icr = financial_data.get("interest_coverage")
    if icr is not None and icr < 1.0:
        score = max(score, 0.8)
        triggers.append({
            "signal": "Interest Coverage Breach",
            "description": (
                f"Interest coverage at {icr:.2f}x — "
                f"cannot cover interest payments"
            ),
            "severity": "HIGH",
            "metric": f"ICR: {icr:.2f}",
        })

    return {"score": score, "triggers": triggers}


def _ews_risk_level(score: float) -> str:
    if score >= 0.6:
        return "HIGH"
    if score >= 0.3:
        return "MODERATE"
    return "LOW"
