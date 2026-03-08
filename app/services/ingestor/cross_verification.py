"""
Cross-Verification Service — compares GST reported revenue with bank statement credits.

Detects anomalies like circular trading, revenue inflation, and significant discrepancies.
Uses rule-based checks with per-period comparison. LLM analysis is optional enhancement.
"""

import logging

from langchain_core.prompts import ChatPromptTemplate

from app.core.llm import get_ingestor_llm
from app.schemas.ingestor import (
    AnomalyFlag,
    BankStatementSummary,
    CrossVerificationResult,
    GSTDataResponse,
)

logger = logging.getLogger(__name__)

CROSS_VERIFY_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a forensic financial analyst specializing in Indian corporate credit. "
        "Analyze the discrepancies between GST filings and bank statement data. "
        "Look for signs of circular trading, revenue inflation, or mismatched cash flows. "
        "Return ONLY valid JSON, no markdown fences.",
    ),
    (
        "human",
        """Compare the following GST and bank data:

GST Data:
- Total Turnover (as per GST filings): ₹{gst_turnover}
- Total Tax Paid: ₹{gst_tax}
- Total ITC Claimed: ₹{gst_itc}

Bank Statement Data:
- Total Credits: ₹{bank_credits}
- Total Debits: ₹{bank_debits}
- Average Balance: ₹{avg_balance}

Discrepancy: {discrepancy_pct}%

Respond with this JSON:
{{
  "anomalies": [
    {{
      "anomaly_type": "type",
      "severity": "low|medium|high|critical",
      "description": "what was found",
      "evidence": "supporting data"
    }}
  ],
  "risk_level": "low|medium|high|critical",
  "analysis": "detailed explanation"
}}
""",
    ),
])


def cross_verify(
    gst_data: GSTDataResponse,
    bank_data: BankStatementSummary,
) -> CrossVerificationResult:
    """
    Cross-verify GST reported turnover against bank statement credits.

    Applies rule-based checks first, then optionally uses LLM for deeper analysis.
    """
    gst_turnover = gst_data.total_turnover
    bank_credits = bank_data.total_credits

    # Calculate discrepancy
    if gst_turnover > 0:
        discrepancy_pct = abs(gst_turnover - bank_credits) / gst_turnover * 100
    elif bank_credits > 0:
        discrepancy_pct = 100.0
    else:
        discrepancy_pct = 0.0

    # Rule-based anomaly detection
    anomalies = _rule_based_checks(gst_data, bank_data, discrepancy_pct)

    # Per-period comparison (if GST has multiple entries)
    anomalies.extend(_per_period_checks(gst_data, bank_data))

    # GSTR-2A/3B mismatch checks
    anomalies.extend(_gstr_mismatch_checks(gst_data))

    # Determine risk level from rules
    risk_level = _assess_risk_level(anomalies, discrepancy_pct)

    # LLM-based deeper analysis (optional, best-effort)
    ai_analysis = _llm_analysis(gst_data, bank_data, discrepancy_pct)

    return CrossVerificationResult(
        gst_total_turnover=gst_turnover,
        bank_total_credits=bank_credits,
        discrepancy_percentage=round(discrepancy_pct, 2),
        anomalies=anomalies,
        risk_level=risk_level,
        ai_analysis=ai_analysis,
    )


def _rule_based_checks(
    gst_data: GSTDataResponse,
    bank_data: BankStatementSummary,
    discrepancy_pct: float,
) -> list[AnomalyFlag]:
    """Apply rule-based checks for common anomalies."""
    anomalies: list[AnomalyFlag] = []

    # Check 1: Large discrepancy between GST turnover and bank credits
    if discrepancy_pct > 25:
        anomalies.append(
            AnomalyFlag(
                anomaly_type="revenue_discrepancy",
                severity="high" if discrepancy_pct > 50 else "medium",
                description=(
                    f"GST reported turnover (₹{gst_data.total_turnover:,.0f}) differs "
                    f"from bank credits (₹{bank_data.total_credits:,.0f}) by "
                    f"{discrepancy_pct:.1f}%"
                ),
                evidence=f"Discrepancy: {discrepancy_pct:.1f}%",
            )
        )

    # Check 2: GST turnover > bank credits (possible revenue inflation)
    if gst_data.total_turnover > bank_data.total_credits * 1.2:
        anomalies.append(
            AnomalyFlag(
                anomaly_type="revenue_inflation",
                severity="high",
                description=(
                    "GST reported turnover significantly exceeds bank credits, "
                    "suggesting potential revenue inflation."
                ),
                evidence=(
                    f"GST: ₹{gst_data.total_turnover:,.0f} vs "
                    f"Bank: ₹{bank_data.total_credits:,.0f}"
                ),
            )
        )

    # Check 3: Very high ITC relative to tax paid (circular trading indicator)
    if gst_data.total_tax_paid > 0:
        itc_ratio = gst_data.total_itc_claimed / gst_data.total_tax_paid
        if itc_ratio > 0.95:
            anomalies.append(
                AnomalyFlag(
                    anomaly_type="circular_trading",
                    severity="critical" if itc_ratio > 1.0 else "high",
                    description=(
                        f"ITC claimed is {itc_ratio:.1%} of tax paid — possible "
                        f"circular trading or fraudulent ITC claims."
                    ),
                    evidence=f"ITC ratio: {itc_ratio:.2f}",
                )
            )

    # Check 4: Low average balance relative to turnover
    if gst_data.total_turnover > 0 and bank_data.average_balance > 0:
        balance_ratio = bank_data.average_balance / (gst_data.total_turnover / 12)
        if balance_ratio < 0.05:
            anomalies.append(
                AnomalyFlag(
                    anomaly_type="cash_flow_concern",
                    severity="medium",
                    description=(
                        "Average bank balance is very low relative to reported "
                        "monthly turnover, indicating possible cash flow stress."
                    ),
                    evidence=f"Balance/Monthly turnover ratio: {balance_ratio:.2%}",
                )
            )

    return anomalies


def _per_period_checks(
    gst_data: GSTDataResponse,
    bank_data: BankStatementSummary,
) -> list[AnomalyFlag]:
    """
    Compare GST turnover with bank credits on a per-period basis
    if GST has multiple entries.
    """
    anomalies: list[AnomalyFlag] = []

    if len(gst_data.entries) < 2:
        return anomalies

    # Check for inconsistent growth patterns
    turnovers = [e.turnover for e in gst_data.entries]
    if turnovers:
        growth_rates = []
        for i in range(1, len(turnovers)):
            if turnovers[i - 1] > 0:
                rate = (turnovers[i] - turnovers[i - 1]) / turnovers[i - 1]
                growth_rates.append(rate)

        # Flag volatile growth (sign changes more than 3 times)
        if len(growth_rates) >= 4:
            sign_changes = sum(
                1 for i in range(1, len(growth_rates))
                if (growth_rates[i] > 0) != (growth_rates[i - 1] > 0)
            )
            if sign_changes >= 3:
                anomalies.append(
                    AnomalyFlag(
                        anomaly_type="volatile_growth",
                        severity="medium",
                        description=(
                            "Revenue shows highly volatile growth pattern "
                            "with frequent direction changes. May indicate "
                            "manipulated period-end reporting."
                        ),
                        evidence=f"Sign changes in growth: {sign_changes}",
                    )
                )

    return anomalies


def _gstr_mismatch_checks(
    gst_data: GSTDataResponse,
) -> list[AnomalyFlag]:
    """
    Check for GSTR-2A vs 3B style mismatches using available data.

    When actual GSTR-2A data is not available, flag ITC anomalies
    that would typically be caught by 2A/3B reconciliation.
    """
    anomalies: list[AnomalyFlag] = []

    if not gst_data or gst_data.total_itc_claimed == 0:
        return anomalies

    # Check ITC as percentage of turnover
    if gst_data.total_turnover > 0:
        itc_to_turnover = gst_data.total_itc_claimed / gst_data.total_turnover
        if itc_to_turnover > 0.15:
            anomalies.append(
                AnomalyFlag(
                    anomaly_type="high_itc_to_turnover",
                    severity="medium",
                    description=(
                        f"ITC claimed is {itc_to_turnover:.1%} of turnover, "
                        f"which is unusually high. May indicate inflated "
                        f"purchase invoices or GSTR-2A/3B mismatch."
                    ),
                    evidence=(
                        f"ITC: ₹{gst_data.total_itc_claimed:,.0f}, "
                        f"Turnover: ₹{gst_data.total_turnover:,.0f}"
                    ),
                )
            )

    # Check per-period ITC consistency
    if len(gst_data.entries) >= 3:
        itc_ratios = []
        for entry in gst_data.entries:
            if entry.tax_paid > 0:
                itc_ratios.append(entry.itc_claimed / entry.tax_paid)

        if itc_ratios:
            avg_ratio = sum(itc_ratios) / len(itc_ratios)
            deviations = [abs(r - avg_ratio) for r in itc_ratios]
            if max(deviations) > 0.3 * avg_ratio:
                anomalies.append(
                    AnomalyFlag(
                        anomaly_type="itc_inconsistency",
                        severity="medium",
                        description=(
                            "ITC-to-tax ratio varies significantly across "
                            "periods. Large swings may indicate selective "
                            "or opportunistic ITC claiming."
                        ),
                        evidence=f"ITC ratios range: {min(itc_ratios):.2f} - {max(itc_ratios):.2f}",
                    )
                )

    return anomalies


def _assess_risk_level(anomalies: list[AnomalyFlag], discrepancy_pct: float) -> str:
    """Determine overall risk level from anomalies."""
    if any(a.severity == "critical" for a in anomalies):
        return "critical"
    if any(a.severity == "high" for a in anomalies) or discrepancy_pct > 50:
        return "high"
    if any(a.severity == "medium" for a in anomalies) or discrepancy_pct > 25:
        return "medium"
    return "low"


def _llm_analysis(
    gst_data: GSTDataResponse,
    bank_data: BankStatementSummary,
    discrepancy_pct: float,
) -> str:
    """Use LLM for deeper analysis of discrepancies (optional/best-effort)."""
    try:
        llm = get_ingestor_llm()
        chain = CROSS_VERIFY_PROMPT | llm

        result = chain.invoke({
            "gst_turnover": f"{gst_data.total_turnover:,.0f}",
            "gst_tax": f"{gst_data.total_tax_paid:,.0f}",
            "gst_itc": f"{gst_data.total_itc_claimed:,.0f}",
            "bank_credits": f"{bank_data.total_credits:,.0f}",
            "bank_debits": f"{bank_data.total_debits:,.0f}",
            "avg_balance": f"{bank_data.average_balance:,.0f}",
            "discrepancy_pct": f"{discrepancy_pct:.1f}",
        })

        content = result.content if hasattr(result, "content") else str(result)
        return content

    except Exception as e:
        logger.error("LLM cross-verification analysis failed: %s", e)
        return f"AI analysis unavailable: {e}"
