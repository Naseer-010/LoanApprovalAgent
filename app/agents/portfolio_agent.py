"""
Portfolio Performance Agent — computes portfolio risk score
from extracted portfolio metrics.

Influences the final credit decision for NBFCs and lenders.
"""
import logging

logger = logging.getLogger(__name__)


def run_portfolio_analysis(
    company_name: str,
    portfolio_data: dict | None = None,
) -> dict:
    """
    Analyze portfolio performance and compute risk score.

    Args:
        company_name: borrower name
        portfolio_data: dict with yield, NPA, default
                        rate, recovery rate, etc.

    Returns:
        {
            "company_name": str,
            "portfolio_risk_score": float (0-100),
            "risk_level": str,
            "metrics": dict,
            "risk_signals": [dict],
            "summary": str,
        }
    """
    data = portfolio_data or {}

    if not data or all(v is None for v in data.values()):
        return {
            "company_name": company_name,
            "portfolio_risk_score": 0.0,
            "risk_level": "NOT_APPLICABLE",
            "metrics": {},
            "risk_signals": [],
            "summary": (
                "No portfolio data available. "
                "Not applicable for non-NBFC entities."
            ),
        }

    score = 50.0  # neutral baseline
    signals: list[dict] = []

    # ── Gross NPA Ratio ──
    gnpa = data.get("gross_npa_ratio")
    if gnpa is not None:
        if gnpa < 2:
            score += 20
            signals.append({
                "signal": "Strong Asset Quality",
                "detail": f"GNPA at {gnpa:.1f}% — "
                          f"well below 2% threshold",
                "severity": "low",
                "impact": "+20",
            })
        elif gnpa < 5:
            score += 5
            signals.append({
                "signal": "Moderate Asset Quality",
                "detail": f"GNPA at {gnpa:.1f}%",
                "severity": "medium",
                "impact": "+5",
            })
        elif gnpa < 10:
            score -= 15
            signals.append({
                "signal": "Elevated NPA",
                "detail": f"GNPA at {gnpa:.1f}% — "
                          f"approaching stress zone",
                "severity": "high",
                "impact": "-15",
            })
        else:
            score -= 30
            signals.append({
                "signal": "Critical NPA Levels",
                "detail": f"GNPA at {gnpa:.1f}% — "
                          f"severe asset quality issues",
                "severity": "critical",
                "impact": "-30",
            })

    # ── Default Rate ──
    default_rate = data.get("default_rate")
    if default_rate is not None:
        if default_rate < 1:
            score += 10
        elif default_rate < 3:
            score += 0
        elif default_rate < 8:
            score -= 10
            signals.append({
                "signal": "Elevated Default Rate",
                "detail": f"Default rate at {default_rate:.1f}%",
                "severity": "high",
                "impact": "-10",
            })
        else:
            score -= 20
            signals.append({
                "signal": "High Default Rate",
                "detail": f"Default rate at "
                          f"{default_rate:.1f}% — critical",
                "severity": "critical",
                "impact": "-20",
            })

    # ── Recovery Rate ──
    recovery = data.get("recovery_rate")
    if recovery is not None:
        if recovery > 70:
            score += 10
            signals.append({
                "signal": "Strong Recovery",
                "detail": f"Recovery rate at "
                          f"{recovery:.0f}%",
                "severity": "low",
                "impact": "+10",
            })
        elif recovery < 30:
            score -= 15
            signals.append({
                "signal": "Poor Recovery Rate",
                "detail": f"Recovery at {recovery:.0f}% — "
                          f"weak collections",
                "severity": "high",
                "impact": "-15",
            })

    # ── Portfolio Yield ──
    pyield = data.get("portfolio_yield")
    if pyield is not None:
        if pyield > 15:
            score += 5
        elif pyield < 8:
            score -= 5

    # ── Provision Coverage ──
    pcr = data.get("provision_coverage")
    if pcr is not None:
        if pcr > 70:
            score += 10
            signals.append({
                "signal": "Adequate Provisioning",
                "detail": f"PCR at {pcr:.0f}%",
                "severity": "low",
                "impact": "+10",
            })
        elif pcr < 40:
            score -= 10
            signals.append({
                "signal": "Under-Provisioned",
                "detail": f"PCR at {pcr:.0f}% — "
                          f"needs bolstering",
                "severity": "high",
                "impact": "-10",
            })

    score = max(0, min(100, score))

    # Risk level
    if score >= 70:
        risk_level = "LOW"
    elif score >= 50:
        risk_level = "MODERATE"
    elif score >= 30:
        risk_level = "HIGH"
    else:
        risk_level = "CRITICAL"

    summary = (
        f"Portfolio analysis for {company_name}: "
        f"risk score {score:.0f}/100 ({risk_level}). "
        f"{len(signals)} signal(s) identified."
    )

    return {
        "company_name": company_name,
        "portfolio_risk_score": round(score, 2),
        "risk_level": risk_level,
        "metrics": {
            "gross_npa_ratio": gnpa,
            "net_npa_ratio": data.get("net_npa_ratio"),
            "default_rate": default_rate,
            "recovery_rate": recovery,
            "portfolio_yield": pyield,
            "provision_coverage": pcr,
            "total_portfolio_size": data.get(
                "total_portfolio_size",
            ),
        },
        "risk_signals": signals,
        "summary": summary,
    }
