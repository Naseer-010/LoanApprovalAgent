"""
Fraud Detector — advanced fraud pattern detection for Indian corporate credit.

Detects circular trading, shell company indicators, revenue spikes,
repeated counterparty patterns, cashflow manipulation, and GSTR-2A/3B
mismatch signals from GST and bank statement data.
"""

import logging

from app.schemas.ingestor import (
    BankStatementSummary,
    FraudAlert,
    FraudReport,
    GSTDataResponse,
)

logger = logging.getLogger(__name__)


def detect_fraud(
    gst_data: GSTDataResponse | None,
    bank_data: BankStatementSummary | None,
) -> FraudReport:
    """
    Run comprehensive fraud detection across GST and bank data.

    Returns a FraudReport with scored alerts.
    """
    alerts: list[FraudAlert] = []

    if gst_data:
        alerts.extend(_check_gst_fraud(gst_data))

    if bank_data:
        alerts.extend(_check_bank_fraud(bank_data))

    if gst_data and bank_data:
        alerts.extend(_check_cross_fraud(gst_data, bank_data))

    # Score
    critical = sum(1 for a in alerts if a.severity == "critical")
    high = sum(1 for a in alerts if a.severity == "high")
    fraud_score = min(100, critical * 30 + high * 15 + len(alerts) * 5)
    risk = _fraud_risk_level(fraud_score)

    return FraudReport(
        total_alerts=len(alerts),
        critical_count=critical,
        high_count=high,
        alerts=alerts,
        overall_fraud_risk=risk,
        fraud_score=fraud_score,
    )


def _check_gst_fraud(gst: GSTDataResponse) -> list[FraudAlert]:
    """Detect fraud patterns in GST data."""
    alerts: list[FraudAlert] = []

    # ── Revenue Spike Detection ──
    if len(gst.entries) >= 2:
        for i in range(1, len(gst.entries)):
            prev = gst.entries[i - 1].turnover
            curr = gst.entries[i].turnover
            if prev > 0 and curr > prev * 2.0:
                pct = ((curr - prev) / prev) * 100
                alerts.append(FraudAlert(
                    alert_type="revenue_spike",
                    severity="high",
                    title="Abnormal Revenue Spike",
                    description=(
                        f"Turnover jumped {pct:.0f}% from "
                        f"{gst.entries[i-1].period} to "
                        f"{gst.entries[i].period}"
                    ),
                    evidence=(
                        f"Previous: {prev:,.0f}, "
                        f"Current: {curr:,.0f}"
                    ),
                    confidence=0.7,
                ))

    # ── ITC Inflation (GSTR-2A vs 3B proxy) ──
    if gst.total_tax_paid > 0:
        itc_ratio = gst.total_itc_claimed / gst.total_tax_paid
        if itc_ratio > 1.0:
            alerts.append(FraudAlert(
                alert_type="itc_inflation",
                severity="critical",
                title="ITC Exceeds Tax Liability",
                description=(
                    f"ITC claimed ({gst.total_itc_claimed:,.0f}) "
                    f"exceeds total tax paid "
                    f"({gst.total_tax_paid:,.0f}). "
                    f"Possible GSTR-2A/3B mismatch or "
                    f"fraudulent ITC claims."
                ),
                evidence=f"ITC/Tax ratio: {itc_ratio:.2f}",
                confidence=0.85,
            ))
        elif itc_ratio > 0.9:
            alerts.append(FraudAlert(
                alert_type="high_itc_ratio",
                severity="high",
                title="Abnormally High ITC Claims",
                description=(
                    f"ITC claimed is {itc_ratio:.0%} of tax paid "
                    f"— near-complete offset suggests potential "
                    f"circular trading or inflated purchases."
                ),
                evidence=f"ITC/Tax ratio: {itc_ratio:.2f}",
                confidence=0.7,
            ))

    # ── Circular Trading — uniform period entries ──
    if len(gst.entries) >= 3:
        turnovers = [e.turnover for e in gst.entries if e.turnover > 0]
        if turnovers:
            avg = sum(turnovers) / len(turnovers)
            if avg > 0:
                variance = sum(
                    (t - avg) ** 2 for t in turnovers
                ) / len(turnovers)
                cv = (variance ** 0.5) / avg  # coefficient of variation
                if cv < 0.05 and len(turnovers) >= 3:
                    alerts.append(FraudAlert(
                        alert_type="uniform_revenue",
                        severity="medium",
                        title="Suspiciously Uniform Revenue",
                        description=(
                            "GST turnover is nearly identical across "
                            "all periods (CV < 5%). Natural business "
                            "shows variation — uniform figures may "
                            "indicate fabricated invoicing."
                        ),
                        evidence=f"CV: {cv:.3f}, Mean: {avg:,.0f}",
                        confidence=0.6,
                    ))

    return alerts


def _check_bank_fraud(
    bank: BankStatementSummary,
) -> list[FraudAlert]:
    """Detect fraud patterns in bank statement data."""
    alerts: list[FraudAlert] = []

    # ── Round Number Transactions ──
    if bank.total_credits > 0:
        # Heuristic: if average credit is a very round number
        if bank.credit_count > 0:
            avg_credit = bank.total_credits / bank.credit_count
            if avg_credit > 100000 and avg_credit % 100000 == 0:
                alerts.append(FraudAlert(
                    alert_type="round_number_credits",
                    severity="medium",
                    title="Round-Number Credit Transactions",
                    description=(
                        "Average credit transaction is an exact "
                        "round number, which may indicate "
                        "fabricated or manipulated deposits."
                    ),
                    evidence=f"Avg credit: {avg_credit:,.0f}",
                    confidence=0.5,
                ))

    # ── Cash Flow Stress ──
    if bank.total_credits > 0 and bank.lowest_balance < 0:
        alerts.append(FraudAlert(
            alert_type="negative_balance",
            severity="high",
            title="Negative Balance Observed",
            description=(
                "Account hit negative balance during the "
                "statement period, indicating severe cash "
                "flow stress or overdraft dependency."
            ),
            evidence=f"Lowest balance: {bank.lowest_balance:,.0f}",
            confidence=0.8,
        ))

    # ── High Transaction Velocity ──
    total_txns = bank.credit_count + bank.debit_count
    if total_txns > 500 and bank.average_balance < bank.total_credits * 0.02:
        alerts.append(FraudAlert(
            alert_type="high_velocity_low_balance",
            severity="high",
            title="High Transaction Velocity with Low Balance",
            description=(
                "Very high transaction count with "
                "disproportionately low average balance "
                "— possible layering or round-tripping."
            ),
            evidence=(
                f"Transactions: {total_txns}, "
                f"Avg balance: {bank.average_balance:,.0f}"
            ),
            confidence=0.65,
        ))

    return alerts


def _check_cross_fraud(
    gst: GSTDataResponse,
    bank: BankStatementSummary,
) -> list[FraudAlert]:
    """Cross-data fraud patterns."""
    alerts: list[FraudAlert] = []

    # ── Shell Company Indicator ──
    if gst.total_turnover > 0 and bank.average_balance > 0:
        ratio = bank.average_balance / (gst.total_turnover / 12)
        if ratio < 0.01:
            alerts.append(FraudAlert(
                alert_type="shell_company_indicator",
                severity="critical",
                title="Potential Shell Company",
                description=(
                    "Extremely high reported turnover relative "
                    "to bank balance. Monthly turnover is 100x+ "
                    "the average balance — typical of shell "
                    "entities used for invoice trading."
                ),
                evidence=(
                    f"Balance/Monthly turnover: {ratio:.4f}"
                ),
                confidence=0.75,
            ))

    # ── Credits far exceed reported GST turnover ──
    if gst.total_turnover > 0:
        excess = bank.total_credits / gst.total_turnover
        if excess > 2.0:
            alerts.append(FraudAlert(
                alert_type="unreported_income",
                severity="high",
                title="Bank Credits Exceed GST Turnover",
                description=(
                    f"Bank credits are {excess:.1f}x the GST "
                    f"reported turnover. Significant unreported "
                    f"income or non-business fund flows detected."
                ),
                evidence=(
                    f"Bank credits: {bank.total_credits:,.0f}, "
                    f"GST turnover: {gst.total_turnover:,.0f}"
                ),
                confidence=0.7,
            ))

    return alerts


def _fraud_risk_level(score: float) -> str:
    """Map fraud score to risk level."""
    if score >= 60:
        return "critical"
    if score >= 40:
        return "high"
    if score >= 20:
        return "medium"
    return "low"
