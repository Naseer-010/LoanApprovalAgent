"""
Financial Trend Agent — detects multi-year financial trends.

Analyses:
- Revenue growth trajectory
- Profit margin trends (improving/declining/volatile)
- Debt accumulation trends
- Working capital efficiency over time

Output: FinancialTrendReport with stability assessment.
"""
import logging

logger = logging.getLogger(__name__)


def run_financial_trend_analysis(
    company_name: str,
    financial_data: dict,
    historical_data: list[dict] | None = None,
) -> dict:
    """
    Analyse multi-year financial trends from available data.

    Args:
        company_name: Name of the entity
        financial_data: Current year financial dict
        historical_data: Optional list of prior-year dicts

    Returns dict matching FinancialTrendReport schema.
    """
    trends: list[dict] = []
    stability_score = 50.0  # Neutral default
    stability_assessment = "Insufficient Data"
    trend_signals: list[dict] = []

    revenue = financial_data.get("revenue")
    ebitda = financial_data.get("ebitda")
    net_profit = financial_data.get("net_profit")
    total_debt = financial_data.get("total_debt")
    current_ratio = financial_data.get("current_ratio")
    debt_to_equity = financial_data.get("debt_to_equity")
    interest_coverage = financial_data.get("interest_coverage")

    # ── Revenue trend ──
    rev_growth = financial_data.get("revenue_growth")
    if rev_growth is not None:
        direction = (
            "growing" if rev_growth > 5
            else "declining" if rev_growth < -5
            else "stable"
        )
        severity = (
            "positive" if rev_growth > 10
            else "warning" if rev_growth < 0
            else "neutral"
        )
        trends.append({
            "metric": "Revenue Growth",
            "value": f"{rev_growth:.1f}%",
            "direction": direction,
            "severity": severity,
            "detail": (
                f"Revenue growth of {rev_growth:.1f}% indicates "
                f"{'strong expansion' if rev_growth > 15 else 'healthy growth' if rev_growth > 5 else 'stagnation' if rev_growth >= 0 else 'contraction'}"
            ),
        })
        if rev_growth > 10:
            stability_score += 10
        elif rev_growth < -10:
            stability_score -= 15

    # ── Profitability trend ──
    if ebitda is not None and revenue and revenue > 0:
        margin = (ebitda / revenue) * 100
        direction = (
            "strong" if margin > 15
            else "moderate" if margin > 8
            else "weak"
        )
        trends.append({
            "metric": "EBITDA Margin",
            "value": f"{margin:.1f}%",
            "direction": direction,
            "severity": "positive" if margin > 15 else (
                "neutral" if margin > 8 else "warning"
            ),
            "detail": (
                f"EBITDA margin of {margin:.1f}% — "
                f"{'above industry average' if margin > 15 else 'needs monitoring' if margin < 8 else 'within acceptable range'}"
            ),
        })
        if margin > 15:
            stability_score += 8
        elif margin < 5:
            stability_score -= 12

    # ── Net profit trend ──
    if net_profit is not None and revenue and revenue > 0:
        npm = (net_profit / revenue) * 100
        trends.append({
            "metric": "Net Profit Margin",
            "value": f"{npm:.1f}%",
            "direction": (
                "profitable" if npm > 5
                else "marginal" if npm > 0
                else "loss-making"
            ),
            "severity": (
                "positive" if npm > 5
                else "warning" if npm > 0
                else "critical"
            ),
            "detail": (
                f"Net margin {npm:.1f}%"
            ),
        })
        if npm > 5:
            stability_score += 5
        elif npm < 0:
            stability_score -= 15
            trend_signals.append({
                "signal": "Net Loss",
                "severity": "high",
                "detail": (
                    f"Company is loss-making with net margin of "
                    f"{npm:.1f}%"
                ),
            })

    # ── Debt trend ──
    if debt_to_equity is not None:
        trends.append({
            "metric": "Debt-to-Equity",
            "value": f"{debt_to_equity:.2f}x",
            "direction": (
                "low leverage" if debt_to_equity < 1
                else "moderate leverage" if debt_to_equity < 2
                else "high leverage"
            ),
            "severity": (
                "positive" if debt_to_equity < 1
                else "neutral" if debt_to_equity < 2
                else "warning" if debt_to_equity < 3
                else "critical"
            ),
            "detail": (
                f"D/E ratio of {debt_to_equity:.2f}x — "
                f"{'conservatively leveraged' if debt_to_equity < 1 else 'highly leveraged' if debt_to_equity > 2.5 else 'moderately leveraged'}"
            ),
        })
        if debt_to_equity < 1:
            stability_score += 8
        elif debt_to_equity > 3:
            stability_score -= 15
            trend_signals.append({
                "signal": "Excessive Leverage",
                "severity": "high",
                "detail": (
                    f"Debt-to-equity ratio of {debt_to_equity:.2f}x "
                    f"exceeds safe threshold"
                ),
            })

    # ── Interest coverage trend ──
    if interest_coverage is not None:
        trends.append({
            "metric": "Interest Coverage",
            "value": f"{interest_coverage:.2f}x",
            "direction": (
                "comfortable" if interest_coverage > 3
                else "tight" if interest_coverage > 1.5
                else "distressed"
            ),
            "severity": (
                "positive" if interest_coverage > 3
                else "warning" if interest_coverage > 1.5
                else "critical"
            ),
            "detail": (
                f"ICR of {interest_coverage:.2f}x — "
                f"{'strong debt servicing' if interest_coverage > 4 else 'adequate' if interest_coverage > 2 else 'strain on debt servicing'}"
            ),
        })
        if interest_coverage > 4:
            stability_score += 8
        elif interest_coverage < 1.5:
            stability_score -= 15
            trend_signals.append({
                "signal": "Debt Servicing Stress",
                "severity": "critical",
                "detail": (
                    f"Interest coverage of {interest_coverage:.2f}x "
                    f"indicates risk of default"
                ),
            })

    # ── Current ratio trend ──
    if current_ratio is not None:
        trends.append({
            "metric": "Current Ratio",
            "value": f"{current_ratio:.2f}x",
            "direction": (
                "healthy" if current_ratio > 1.5
                else "adequate" if current_ratio > 1
                else "strained"
            ),
            "severity": (
                "positive" if current_ratio > 1.5
                else "neutral" if current_ratio > 1
                else "critical"
            ),
            "detail": (
                f"Current ratio {current_ratio:.2f}x"
            ),
        })
        if current_ratio > 2:
            stability_score += 5
        elif current_ratio < 1:
            stability_score -= 10

    # ── Historical data analysis (if available) ──
    if historical_data and len(historical_data) >= 2:
        revenues = [
            h.get("revenue", 0) for h in historical_data
            if h.get("revenue")
        ]
        if len(revenues) >= 2:
            growth_rates = [
                ((revenues[i] - revenues[i - 1]) / revenues[i - 1]) * 100
                for i in range(1, len(revenues))
                if revenues[i - 1] > 0
            ]
            if growth_rates:
                avg_growth = sum(growth_rates) / len(growth_rates)
                is_volatile = (
                    max(growth_rates) - min(growth_rates) > 30
                )
                trends.append({
                    "metric": "Historical Revenue CAGR",
                    "value": f"{avg_growth:.1f}%",
                    "direction": (
                        "volatile"
                        if is_volatile
                        else "consistent growth"
                        if avg_growth > 0
                        else "consistent decline"
                    ),
                    "severity": (
                        "warning"
                        if is_volatile
                        else "positive"
                        if avg_growth > 5
                        else "neutral"
                    ),
                    "detail": (
                        f"Average revenue growth of {avg_growth:.1f}% "
                        f"over {len(revenues)} periods"
                    ),
                })
                if is_volatile:
                    trend_signals.append({
                        "signal": "Revenue Volatility",
                        "severity": "medium",
                        "detail": (
                            f"Revenue swings of "
                            f"{max(growth_rates) - min(growth_rates):.0f}pp"
                        ),
                    })
                    stability_score -= 8

    # ── Final stability assessment ──
    stability_score = max(0, min(100, stability_score))

    if stability_score >= 75:
        stability_assessment = "Strong Financial Stability"
    elif stability_score >= 55:
        stability_assessment = "Moderate Financial Stability"
    elif stability_score >= 35:
        stability_assessment = "Weak — Monitor Closely"
    else:
        stability_assessment = "Critical — High Risk"

    return {
        "company_name": company_name,
        "trends": trends,
        "stability_score": round(stability_score, 1),
        "stability_assessment": stability_assessment,
        "trend_signals": trend_signals,
        "num_metrics_analyzed": len(trends),
        "data_quality": (
            "comprehensive"
            if len(trends) >= 5
            else "partial"
            if len(trends) >= 3
            else "limited"
        ),
    }
