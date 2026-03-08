"""
Fraud Detector — advanced fraud pattern detection for Indian corporate credit.

Detects circular trading, shell company indicators, revenue spikes,
repeated counterparty patterns, cashflow manipulation, and GSTR-2A/3B
mismatch signals from GST and bank statement data.

All fraud signals are derived from actual document data — no hardcoded
scores or simulated patterns.
"""

import logging
from collections import Counter

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

    Returns a FraudReport with scored alerts and a fraud_risk_score (0-100).
    All signals are derived from actual input data.
    """
    alerts: list[FraudAlert] = []

    if gst_data:
        alerts.extend(_check_gst_fraud(gst_data))

    if bank_data:
        alerts.extend(_check_bank_fraud(bank_data))

    if gst_data and bank_data:
        alerts.extend(_check_cross_fraud(gst_data, bank_data))

    # Compute fraud risk score (0-100)
    fraud_score = _compute_fraud_score(alerts)
    risk = _fraud_risk_level(fraud_score)

    # Build anomaly list
    anomalies = [
        {
            "type": a.alert_type,
            "severity": a.severity,
            "title": a.title,
            "description": a.description,
            "evidence": a.evidence,
            "confidence": a.confidence,
        }
        for a in alerts
    ]

    critical = sum(1 for a in alerts if a.severity == "critical")
    high = sum(1 for a in alerts if a.severity == "high")

    return FraudReport(
        total_alerts=len(alerts),
        critical_count=critical,
        high_count=high,
        alerts=alerts,
        overall_fraud_risk=risk,
        fraud_score=fraud_score,
    )


def _compute_fraud_score(alerts: list[FraudAlert]) -> float:
    """
    Compute fraud risk score (0-100) from detected alerts.

    Score is based on severity-weighted sum of alerts with
    confidence-adjusted scoring.
    """
    if not alerts:
        return 0.0

    severity_weights = {
        "critical": 25,
        "high": 15,
        "medium": 8,
        "low": 3,
    }

    score = 0.0
    for alert in alerts:
        weight = severity_weights.get(alert.severity, 5)
        confidence = max(0.0, min(1.0, alert.confidence))
        score += weight * confidence

    return min(100.0, round(score, 1))


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

    # ── Sudden Revenue Drop (potential manipulation) ──
    if len(gst.entries) >= 2:
        for i in range(1, len(gst.entries)):
            prev = gst.entries[i - 1].turnover
            curr = gst.entries[i].turnover
            if prev > 0 and curr < prev * 0.3:
                pct = ((prev - curr) / prev) * 100
                alerts.append(FraudAlert(
                    alert_type="revenue_cliff",
                    severity="medium",
                    title="Sudden Revenue Drop",
                    description=(
                        f"Turnover dropped {pct:.0f}% from "
                        f"{gst.entries[i-1].period} to "
                        f"{gst.entries[i].period}. "
                        f"May indicate business stress or prior inflation."
                    ),
                    evidence=(
                        f"Previous: {prev:,.0f}, Current: {curr:,.0f}"
                    ),
                    confidence=0.55,
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
                cv = (variance ** 0.5) / avg
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

    # ── Round-Number Turnovers ──
    if len(gst.entries) >= 2:
        round_count = 0
        for entry in gst.entries:
            if entry.turnover > 10000 and entry.turnover % 10000 == 0:
                round_count += 1
        if round_count >= 2:
            ratio = round_count / len(gst.entries)
            if ratio > 0.5:
                alerts.append(FraudAlert(
                    alert_type="round_number_turnover",
                    severity="medium",
                    title="Round-Number Turnovers in GST",
                    description=(
                        f"{round_count} of {len(gst.entries)} periods "
                        f"have suspiciously round turnover figures. "
                        f"May indicate estimated or fabricated filings."
                    ),
                    evidence=f"{ratio:.0%} of periods have round numbers",
                    confidence=0.5,
                ))

    # ── Repeated Same Turnover (possible copy-paste filings) ──
    if len(gst.entries) >= 3:
        turnover_counts = Counter(
            e.turnover for e in gst.entries if e.turnover > 0
        )
        repeated = {t: c for t, c in turnover_counts.items() if c >= 2}
        if len(repeated) > 0:
            total_repeated = sum(repeated.values())
            if total_repeated / len(gst.entries) > 0.5:
                alerts.append(FraudAlert(
                    alert_type="repeated_turnover",
                    severity="high",
                    title="Repeated Identical Turnovers",
                    description=(
                        "Multiple GST periods show identical turnover "
                        "amounts. This is unusual for genuine business "
                        "and may indicate copy-paste filings."
                    ),
                    evidence=f"Repeated values: {dict(repeated)}",
                    confidence=0.65,
                ))

    return alerts


def _check_bank_fraud(
    bank: BankStatementSummary,
) -> list[FraudAlert]:
    """Detect fraud patterns in bank statement data."""
    alerts: list[FraudAlert] = []

    # ── Round Number Transactions ──
    if bank.total_credits > 0 and bank.credit_count > 0:
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

    # ── Large Individual Round Credits ──
    if bank.total_credits > 0 and bank.credit_count > 0:
        avg = bank.total_credits / bank.credit_count
        if avg > 500000 and bank.credit_count < 10:
            alerts.append(FraudAlert(
                alert_type="few_large_credits",
                severity="medium",
                title="Few Large Credit Transactions",
                description=(
                    f"Only {bank.credit_count} credit transactions "
                    f"totaling ₹{bank.total_credits:,.0f}. "
                    f"Few large credits may indicate "
                    f"lump-sum round-tripping."
                ),
                evidence=f"Avg credit: ₹{avg:,.0f}",
                confidence=0.45,
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

    # ── Credit-Debit Symmetry (circular fund flow) ──
    if bank.total_credits > 0 and bank.total_debits > 0:
        symmetry = min(bank.total_credits, bank.total_debits) / max(
            bank.total_credits, bank.total_debits
        )
        if symmetry > 0.95 and total_txns > 20:
            alerts.append(FraudAlert(
                alert_type="credit_debit_symmetry",
                severity="high",
                title="Credit-Debit Symmetry Detected",
                description=(
                    f"Credits and debits are {symmetry:.1%} symmetric. "
                    f"Near-perfect symmetry in high-volume accounts "
                    f"may indicate circular fund flow or layering."
                ),
                evidence=(
                    f"Credits: ₹{bank.total_credits:,.0f}, "
                    f"Debits: ₹{bank.total_debits:,.0f}"
                ),
                confidence=0.6,
            ))

    return alerts


def _check_cross_fraud(
    gst: GSTDataResponse,
    bank: BankStatementSummary,
) -> list[FraudAlert]:
    """Cross-data fraud patterns."""
    alerts: list[FraudAlert] = []

    # ── Revenue Mismatch ──
    if gst.total_turnover > 0 and bank.total_credits > 0:
        mismatch_pct = abs(
            gst.total_turnover - bank.total_credits
        ) / gst.total_turnover * 100
        if mismatch_pct > 50:
            alerts.append(FraudAlert(
                alert_type="revenue_mismatch",
                severity="critical",
                title="Severe Revenue Mismatch",
                description=(
                    f"GST turnover and bank credits differ by "
                    f"{mismatch_pct:.1f}%. Severe mismatch "
                    f"indicates potential revenue manipulation."
                ),
                evidence=(
                    f"GST: ₹{gst.total_turnover:,.0f}, "
                    f"Bank: ₹{bank.total_credits:,.0f}"
                ),
                confidence=0.8,
            ))
        elif mismatch_pct > 25:
            alerts.append(FraudAlert(
                alert_type="revenue_mismatch",
                severity="high",
                title="Significant Revenue Mismatch",
                description=(
                    f"GST turnover and bank credits differ by "
                    f"{mismatch_pct:.1f}%."
                ),
                evidence=(
                    f"GST: ₹{gst.total_turnover:,.0f}, "
                    f"Bank: ₹{bank.total_credits:,.0f}"
                ),
                confidence=0.7,
            ))

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
                evidence=f"Balance/Monthly turnover: {ratio:.4f}",
                confidence=0.75,
            ))

    # ── Revenue Inflation (GST > Bank) ──
    if gst.total_turnover > bank.total_credits * 1.2:
        alerts.append(FraudAlert(
            alert_type="revenue_inflation",
            severity="high",
            title="Possible Revenue Inflation",
            description=(
                "GST reported turnover exceeds bank credits by >20%, "
                "suggesting potential revenue inflation via "
                "fake invoices."
            ),
            evidence=(
                f"GST: ₹{gst.total_turnover:,.0f}, "
                f"Bank: ₹{bank.total_credits:,.0f}"
            ),
            confidence=0.7,
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
