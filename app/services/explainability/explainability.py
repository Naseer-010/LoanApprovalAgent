"""
Explainability Engine — structured reasoning for every recommendation.

Explains: why approved/rejected, risks detected, financial ratios that
influenced the decision, research signals that affected the score.
Integrates SHAP values from the ML model.
"""

import logging

logger = logging.getLogger(__name__)


def build_explainability_report(
    decision: dict,
    financial_ratios: dict | None = None,
    five_cs: dict | None = None,
    fraud_data: dict | None = None,
    research_data: dict | None = None,
    ml_prediction: dict | None = None,
) -> dict:
    """
    Build structured explainability report for a loan decision.

    Returns a dict with categorized reasoning:
    - structured_reasons: rigidly formatted [Financial Reason, Risk Signal, Metric]
    - risk_factors: detected risks and their severity
    - financial_drivers: ratios that influenced the decision
    - research_signals: external signals that affected scoring
    - ml_explanation: SHAP-based ML model explanation
    """
    report = {
        "decision": decision.get("decision", "REFER"),
        "structured_reasons": [],
        "risk_factors": [],
        "financial_drivers": [],
        "research_signals": [],
        "ml_explanation": None,
        "confidence_basis": [],
    }

    # Rigid Structured Reasoning
    report["structured_reasons"] = _build_structured_reasons(
        decision, financial_ratios, five_cs,
    )

    # Financial ratio drivers
    if financial_ratios:
        report["financial_drivers"] = _explain_financials(financial_ratios)

    # Risk factors from fraud, research, promoter
    report["risk_factors"] = _explain_risks(
        fraud_data, research_data, decision,
    )

    # Research signals
    if research_data:
        report["research_signals"] = _explain_research(research_data)

    # ML model explanation
    if ml_prediction:
        report["ml_explanation"] = _explain_ml(ml_prediction)

    # Confidence basis
    report["confidence_basis"] = _explain_confidence(
        decision, financial_ratios, five_cs,
    )

    return report


def _build_structured_reasons(
    decision: dict, ratios: dict | None, five_cs: dict | None,
) -> list[dict]:
    """Strictly format reasons into [Financial Reason, Risk Signal, Supporting Metric]."""
    structured = []
    verdict = decision.get("decision", "REFER")
    reasons = decision.get("rejection_reasons", [])

    if verdict == "APPROVE":
        structured.append({
            "financial_reason": "Financial metrics exceed minimum banking thresholds.",
            "risk_signal": "Low Default Risk",
            "supporting_metric": f"Risk Grade {decision.get('risk_grade', 'A')}",
        })
        return structured

    for r in reasons[:5]:
        signal = "High Risk" if "Critical" in r or "High" in r else "Moderate Risk"
        metric = "Derived from Ratio Analysis / Five Cs"

        # Try to extract the metric dynamically
        if "DSCR" in r:
            metric = "DSCR below benchmark"
        elif "ICR" in r:
            metric = "ICR below benchmark"
        elif "Leverage" in r:
            metric = "Elevated Leverage Ratio"
        elif "Fraud" in r:
            metric = "Fraud Score"
        elif "Working capital" in r:
            metric = "Cash Conversion Cycle"

        structured.append({
            "financial_reason": r,
            "risk_signal": signal,
            "supporting_metric": metric,
        })

    if not structured:
        structured.append({
            "financial_reason": "Mixed signals across financial and qualitative data.",
            "risk_signal": "Ambiguous Risk",
            "supporting_metric": "Overall Confidence < 70%",
        })

    return structured


def _explain_financials(ratios: dict) -> list[dict]:
    """Explain which financial ratios influenced the decision."""
    drivers = []

    ratio_fields = [
        "dscr", "icr", "leverage", "current_ratio",
        "debt_to_equity", "ebitda_margin",
    ]

    for field in ratio_fields:
        ratio = ratios.get(field, {})
        if isinstance(ratio, dict) and ratio.get("value") is not None:
            assessment = ratio.get("assessment", "N/A")
            direction = "positive" if assessment == "Pass" else (
                "negative" if assessment == "Fail" else "neutral"
            )
            drivers.append({
                "metric": ratio.get("name", field),
                "value": ratio.get("value"),
                "benchmark": ratio.get("benchmark", ""),
                "assessment": assessment,
                "direction": direction,
                "detail": ratio.get("detail", ""),
            })

    return drivers


def _explain_risks(
    fraud_data: dict | None,
    research_data: dict | None,
    decision: dict,
) -> list[dict]:
    """Explain detected risk factors."""
    risks = []

    # Fraud risks
    if fraud_data:
        fraud_score = fraud_data.get("fraud_score", 0)
        if fraud_score > 0:
            risks.append({
                "category": "Fraud Risk",
                "severity": fraud_data.get("overall_fraud_risk", "low"),
                "score": fraud_score,
                "detail": f"Fraud risk score of {fraud_score}/100",
            })
        for alert in fraud_data.get("alerts", [])[:3]:
            if isinstance(alert, dict):
                risks.append({
                    "category": "Fraud Alert",
                    "severity": alert.get("severity", "medium"),
                    "detail": alert.get("description", alert.get("title", "")),
                })

    # Research-based risks
    if research_data:
        risk_signals = research_data.get("risk_signals", {})
        if isinstance(risk_signals, dict):
            for signal, value in risk_signals.items():
                if isinstance(value, (int, float)) and value > 0.3:
                    risks.append({
                        "category": "Research Signal",
                        "severity": "high" if value > 0.6 else "medium",
                        "detail": f"{signal}: {value:.1%} risk level",
                    })

    return risks


def _explain_research(research_data: dict) -> list[dict]:
    """Explain research signals that affected scoring."""
    signals = []

    sentiment = research_data.get("overall_sentiment", "neutral")
    signals.append({
        "signal": "Overall Research Sentiment",
        "value": sentiment,
        "impact": (
            "Negative sentiment reduces score" if sentiment == "negative"
            else "Positive sentiment improves score" if sentiment == "positive"
            else "Neutral — no significant impact"
        ),
    })

    for flag in research_data.get("risk_flags", [])[:5]:
        signals.append({
            "signal": "Risk Flag",
            "value": flag[:200],
            "impact": "Negative impact on credit assessment",
        })

    return signals


def _explain_ml(ml_prediction: dict) -> dict:
    """Explain ML model prediction with SHAP values."""
    explanation = {
        "risk_probability": ml_prediction.get("credit_risk_probability", 0),
        "risk_label": ml_prediction.get("risk_label", "unknown"),
        "model_explanation": ml_prediction.get("explanation", ""),
        "top_factors": [],
    }

    shap = ml_prediction.get("shap_values", {})
    if shap:
        sorted_shap = sorted(
            shap.items(),
            key=lambda x: abs(x[1]),
            reverse=True,
        )
        for feat, val in sorted_shap[:5]:
            explanation["top_factors"].append({
                "feature": feat,
                "shap_value": val,
                "direction": "increases risk" if val > 0 else "decreases risk",
            })

    return explanation


def _explain_confidence(
    decision: dict,
    financial_ratios: dict | None,
    five_cs: dict | None,
) -> list[str]:
    """Explain the basis for the confidence score."""
    basis = []

    key_factors = decision.get("key_factors", [])
    for factor in key_factors[:5]:
        basis.append(f"Positive: {factor}")

    conditions = decision.get("conditions", [])
    if conditions:
        basis.append(
            f"Conditions imposed: {len(conditions)} lending conditions"
        )

    return basis
