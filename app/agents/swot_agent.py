"""
SWOT Generator Agent — produces AI-powered SWOT analysis
from financial data, sector research, fraud signals, and
market sentiment.
"""
import logging

logger = logging.getLogger(__name__)


def run_swot_analysis(
    company_name: str,
    financial_data: dict | None = None,
    research_data: dict | None = None,
    fraud_data: dict | None = None,
    sector_data: dict | None = None,
    working_capital_data: dict | None = None,
    portfolio_data: dict | None = None,
) -> dict:
    """
    Generate SWOT analysis from all available analysis signals.

    Returns:
        {
            "company_name": str,
            "strengths": [str],
            "weaknesses": [str],
            "opportunities": [str],
            "threats": [str],
            "summary": str,
        }
    """
    fin = financial_data or {}
    res = research_data or {}
    fraud = fraud_data or {}
    sec = sector_data or {}
    wc = working_capital_data or {}
    pf = portfolio_data or {}

    strengths: list[str] = []
    weaknesses: list[str] = []
    opportunities: list[str] = []
    threats: list[str] = []

    # ── STRENGTHS ──
    revenue = fin.get("revenue")
    net_profit = fin.get("net_profit")
    cur_ratio = fin.get("current_ratio")
    icr = fin.get("interest_coverage")
    ebitda = fin.get("ebitda")

    if revenue and net_profit and revenue > 0:
        margin = (net_profit / revenue) * 100
        if margin > 10:
            strengths.append(
                f"Healthy net profit margin of {margin:.1f}%"
            )
        elif margin > 5:
            strengths.append(
                f"Moderate net profit margin of {margin:.1f}%"
            )

    if ebitda and revenue and revenue > 0:
        em = (ebitda / revenue) * 100
        if em > 20:
            strengths.append(
                f"Strong EBITDA margin of {em:.1f}% "
                f"indicating operational efficiency"
            )

    if cur_ratio and cur_ratio > 1.5:
        strengths.append(
            f"Strong current ratio of {cur_ratio:.2f}x "
            f"ensures short-term liquidity"
        )

    if icr and icr > 3.0:
        strengths.append(
            f"Comfortable interest coverage ratio "
            f"of {icr:.2f}x"
        )

    dte = fin.get("debt_to_equity")
    if dte and dte < 1.0:
        strengths.append(
            f"Low leverage with debt-to-equity "
            f"of {dte:.2f}x"
        )

    fraud_score = fraud.get("fraud_score", 0)
    if fraud_score < 20:
        strengths.append(
            "Low fraud risk profile — "
            "clean compliance record"
        )

    # Portfolio strengths
    gnpa = pf.get("gross_npa_ratio")
    if gnpa is not None and gnpa < 2:
        strengths.append(
            f"Strong asset quality with GNPA "
            f"at {gnpa:.1f}%"
        )

    if not strengths:
        strengths.append(
            "Established market presence in sector"
        )

    # ── WEAKNESSES ──
    if dte and dte > 2.0:
        weaknesses.append(
            f"High leverage — debt-to-equity "
            f"of {dte:.2f}x above comfortable levels"
        )

    if cur_ratio and cur_ratio < 1.0:
        weaknesses.append(
            f"Weak current ratio of {cur_ratio:.2f}x "
            f"raises liquidity concerns"
        )

    if icr and icr < 1.5:
        weaknesses.append(
            f"Low interest coverage of {icr:.2f}x — "
            f"debt servicing stress"
        )

    ccc = wc.get("cash_conversion_cycle")
    if ccc and ccc > 120:
        weaknesses.append(
            f"Extended cash conversion cycle of "
            f"{ccc:.0f} days — working capital stress"
        )

    rec_days = wc.get("receivable_days")
    if rec_days and rec_days > 90:
        weaknesses.append(
            f"High receivable days ({rec_days:.0f}) "
            f"indicating collection inefficiency"
        )

    if gnpa is not None and gnpa > 5:
        weaknesses.append(
            f"Elevated GNPA ratio of {gnpa:.1f}% "
            f"signals asset quality deterioration"
        )

    if fraud_score > 50:
        weaknesses.append(
            f"Elevated fraud risk score ({fraud_score:.0f}/100)"
        )

    if not weaknesses:
        weaknesses.append(
            "Limited diversification in revenue streams"
        )

    # ── OPPORTUNITIES ──
    sector_summary = sec.get("sector_summary", "")
    risk_level = sec.get("risk_level", "")

    if risk_level.lower() in ("low", "moderate"):
        opportunities.append(
            f"Favorable sector outlook — "
            f"{risk_level} risk environment"
        )

    sentiment = res.get("overall_sentiment", "")
    if sentiment.lower() in ("positive", "mixed_positive"):
        opportunities.append(
            "Positive market sentiment supports growth"
        )

    if sector_summary:
        opportunities.append(
            f"Sector insight: {sector_summary[:150]}"
        )

    if not opportunities:
        opportunities.append(
            "Potential for market expansion "
            "with credit facility support"
        )

    # ── THREATS ──
    sector_risk_score = sec.get("sector_risk_score", 0)
    if sector_risk_score > 60:
        threats.append(
            f"High sector risk score ({sector_risk_score:.0f}/100) — "
            f"macro headwinds"
        )

    headwinds = sec.get("sector_headwinds", [])
    for hw in headwinds[:2]:
        if isinstance(hw, dict):
            threats.append(
                f"Sector headwind: "
                f"{hw.get('risk_factor', 'Unknown')}"
            )

    reg_changes = sec.get("regulatory_changes", [])
    if reg_changes:
        threats.append(
            "Regulatory policy changes affecting industry"
        )

    risk_flags = res.get("risk_flags", [])
    for flag in risk_flags[:2]:
        threats.append(f"Research risk flag: {flag[:100]}")

    if fraud_score > 30:
        threats.append(
            "Fraud/compliance risk signals "
            "require ongoing monitoring"
        )

    if not threats:
        threats.append(
            "Macroeconomic volatility may "
            "impact business performance"
        )

    # ── Summary ──
    s_count = len(strengths)
    w_count = len(weaknesses)
    balance = "balanced"
    if s_count > w_count + 1:
        balance = "strength-dominated"
    elif w_count > s_count + 1:
        balance = "weakness-dominated"

    summary = (
        f"SWOT analysis for {company_name} reveals a "
        f"{balance} profile with {s_count} strength(s), "
        f"{w_count} weakness(es), "
        f"{len(opportunities)} opportunity(ies), "
        f"and {len(threats)} threat(s)."
    )

    return {
        "company_name": company_name,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "opportunities": opportunities,
        "threats": threats,
        "summary": summary,
    }
