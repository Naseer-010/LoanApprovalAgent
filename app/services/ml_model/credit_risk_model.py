"""
Credit Risk Model — ML-based credit risk prediction with SHAP explainability.

Uses RandomForestClassifier to predict credit risk probability.
Features: DSCR, ICR, Debt/Equity, Revenue Growth, Current Ratio,
Fraud Risk Score, Litigation Risk, Promoter Risk.

Explanations via SHAP values.
"""

import logging
from pathlib import Path

import numpy as np
import joblib

logger = logging.getLogger(__name__)

MODEL_FEATURES = [
    "dscr",
    "icr",
    "debt_to_equity",
    "revenue_growth",
    "current_ratio",
    "fraud_risk_score",
    "litigation_risk",
    "promoter_risk",
]

# Default feature values when data is missing
FEATURE_DEFAULTS = {
    "dscr": 1.25,
    "icr": 1.5,
    "debt_to_equity": 2.0,
    "revenue_growth": 0.0,
    "current_ratio": 1.0,
    "fraud_risk_score": 50.0,
    "litigation_risk": 0.5,
    "promoter_risk": 0.5,
}


def _get_model_path() -> Path:
    """Get the model file path."""
    from app.config import ML_MODEL_DIR
    return ML_MODEL_DIR / "credit_risk_model.joblib"


def _load_model():
    """Load trained model from disk."""
    model_path = _get_model_path()
    if model_path.exists():
        return joblib.load(model_path)
    return None


def _prepare_features(data: dict) -> np.ndarray:
    """
    Prepare feature vector from input data.
    Uses defaults for missing features.
    """
    features = []
    for feat in MODEL_FEATURES:
        value = data.get(feat, FEATURE_DEFAULTS.get(feat, 0.0))
        if value is None:
            value = FEATURE_DEFAULTS.get(feat, 0.0)
        features.append(float(value))
    return np.array([features])


def predict_credit_risk(data: dict) -> dict:
    """
    Predict credit risk probability and explain with SHAP.

    Args:
        data: dict with feature values (dscr, icr, debt_to_equity, etc.)

    Returns:
        dict with:
        - credit_risk_probability (0-1)
        - risk_label (low/medium/high)
        - feature_importances: dict of feature -> importance
        - shap_values: dict of feature -> SHAP contribution
        - explanation: human-readable explanation
    """
    model = _load_model()

    X = _prepare_features(data)

    if model is None:
        # No trained model — use heuristic scoring
        return _heuristic_prediction(data, X)

    try:
        # Predict probability
        proba = model.predict_proba(X)
        # Class 1 = high risk
        risk_prob = float(proba[0][1]) if proba.shape[1] > 1 else float(proba[0][0])

        # Feature importances from model
        importances = {}
        if hasattr(model, "feature_importances_"):
            for feat, imp in zip(MODEL_FEATURES, model.feature_importances_):
                importances[feat] = round(float(imp), 4)

        # SHAP values
        shap_values = _compute_shap(model, X)

        # Risk label
        risk_label = _risk_label(risk_prob)

        # Build explanation
        explanation = _build_explanation(
            risk_prob, risk_label, importances, shap_values, data,
        )

        return {
            "credit_risk_probability": round(risk_prob, 4),
            "risk_label": risk_label,
            "feature_importances": importances,
            "shap_values": shap_values,
            "explanation": explanation,
        }

    except Exception as e:
        logger.error("ML prediction failed: %s", e)
        return _heuristic_prediction(data, X)


def _compute_shap(model, X: np.ndarray) -> dict:
    """Compute SHAP values for the prediction."""
    try:
        import shap

        explainer = shap.TreeExplainer(model)
        shap_vals = explainer.shap_values(X)

        # For binary classification, use class 1 (high risk) SHAP values
        if isinstance(shap_vals, list):
            vals = shap_vals[1][0]  # class 1, first sample
        else:
            vals = shap_vals[0]

        result = {}
        for feat, val in zip(MODEL_FEATURES, vals):
            result[feat] = round(float(val), 4)

        return result

    except ImportError:
        logger.warning("SHAP not available — skipping SHAP explanation")
        return {}
    except Exception as e:
        logger.warning("SHAP computation failed: %s", e)
        return {}


def _heuristic_prediction(data: dict, X: np.ndarray) -> dict:
    """
    Fallback heuristic prediction when no ML model is available.
    Based on financial ratio analysis.
    """
    features = X[0]
    feat_dict = dict(zip(MODEL_FEATURES, features))

    # Simple scoring heuristic
    score = 0.5  # Start neutral

    dscr = feat_dict.get("dscr", 1.25)
    if dscr >= 2.0:
        score -= 0.15
    elif dscr >= 1.25:
        score -= 0.05
    elif dscr < 1.0:
        score += 0.2

    icr = feat_dict.get("icr", 1.5)
    if icr >= 3.0:
        score -= 0.1
    elif icr < 1.0:
        score += 0.15

    dte = feat_dict.get("debt_to_equity", 2.0)
    if dte <= 1.0:
        score -= 0.1
    elif dte > 3.0:
        score += 0.15

    fraud = feat_dict.get("fraud_risk_score", 50.0)
    score += (fraud / 100) * 0.2

    lit = feat_dict.get("litigation_risk", 0.5)
    score += lit * 0.1

    promoter = feat_dict.get("promoter_risk", 0.5)
    score += promoter * 0.1

    risk_prob = max(0.0, min(1.0, score))
    risk_label = _risk_label(risk_prob)

    return {
        "credit_risk_probability": round(risk_prob, 4),
        "risk_label": risk_label,
        "feature_importances": {},
        "shap_values": {},
        "explanation": (
            f"Heuristic risk assessment (ML model not trained): "
            f"Risk probability {risk_prob:.1%}. "
            f"Key factors: DSCR={dscr:.2f}, ICR={icr:.2f}, "
            f"D/E={dte:.2f}, Fraud score={fraud:.0f}. "
            f"Run train_model.py to train the ML model for better predictions."
        ),
    }


def _risk_label(probability: float) -> str:
    """Map risk probability to label."""
    if probability >= 0.7:
        return "high"
    if probability >= 0.4:
        return "medium"
    return "low"


def _build_explanation(
    risk_prob: float,
    risk_label: str,
    importances: dict,
    shap_values: dict,
    data: dict,
) -> str:
    """Build human-readable explanation of the ML prediction."""
    parts = [
        f"ML Model Credit Risk Assessment: {risk_label.upper()} "
        f"(probability: {risk_prob:.1%})",
    ]

    # Top contributing features from SHAP
    if shap_values:
        sorted_shap = sorted(
            shap_values.items(),
            key=lambda x: abs(x[1]),
            reverse=True,
        )
        parts.append("\nKey factors influencing the decision:")
        for feat, val in sorted_shap[:5]:
            direction = "increases" if val > 0 else "decreases"
            feat_val = data.get(feat, "N/A")
            parts.append(
                f"  - {feat} = {feat_val}: {direction} risk "
                f"(SHAP: {val:+.4f})"
            )
    elif importances:
        sorted_imp = sorted(
            importances.items(),
            key=lambda x: x[1],
            reverse=True,
        )
        parts.append("\nMost important features:")
        for feat, imp in sorted_imp[:5]:
            feat_val = data.get(feat, "N/A")
            parts.append(
                f"  - {feat} = {feat_val} (importance: {imp:.4f})"
            )

    return "\n".join(parts)
