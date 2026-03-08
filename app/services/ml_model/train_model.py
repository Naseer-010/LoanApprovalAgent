"""
Train Credit Risk Model — generates synthetic training data and trains model.

This script generates realistic synthetic corporate loan data for demo purposes.
In production, replace with real labeled loan data.

Usage:
    python -m app.services.ml_model.train_model
"""

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score
import joblib

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from app.config import ML_MODEL_DIR
from app.services.ml_model.credit_risk_model import MODEL_FEATURES

logger = logging.getLogger(__name__)


def generate_synthetic_data(n_samples: int = 2000) -> pd.DataFrame:
    """
    Generate realistic synthetic corporate loan application data.

    This simulates the distribution of real Indian corporate loan data
    for demo/training. Replace with real labeled data for production.
    """
    rng = np.random.default_rng(42)

    data = {
        "dscr": rng.lognormal(mean=0.4, sigma=0.5, size=n_samples).clip(0.3, 5.0),
        "icr": rng.lognormal(mean=0.5, sigma=0.6, size=n_samples).clip(0.2, 10.0),
        "debt_to_equity": rng.lognormal(mean=0.3, sigma=0.7, size=n_samples).clip(0.1, 8.0),
        "revenue_growth": rng.normal(loc=0.08, scale=0.15, size=n_samples).clip(-0.5, 1.0),
        "current_ratio": rng.lognormal(mean=0.3, sigma=0.4, size=n_samples).clip(0.3, 5.0),
        "fraud_risk_score": rng.beta(2, 8, size=n_samples) * 100,  # mostly low
        "litigation_risk": rng.beta(2, 5, size=n_samples),  # 0-1
        "promoter_risk": rng.beta(2, 5, size=n_samples),  # 0-1
    }

    df = pd.DataFrame(data)

    # Generate target variable based on realistic rules
    # Higher risk of default when:
    #   - DSCR < 1.25 (can't service debt)
    #   - ICR < 1.5 (can't cover interest)
    #   - D/E > 3.0 (overleveraged)
    #   - Fraud score > 50 (high fraud risk)
    #   - Litigation risk > 0.6

    risk_score = (
        (df["dscr"] < 1.0).astype(float) * 0.25
        + (df["dscr"] < 1.25).astype(float) * 0.1
        + (df["icr"] < 1.0).astype(float) * 0.2
        + (df["icr"] < 1.5).astype(float) * 0.05
        + (df["debt_to_equity"] > 3.0).astype(float) * 0.15
        + (df["debt_to_equity"] > 5.0).astype(float) * 0.1
        + (df["current_ratio"] < 1.0).astype(float) * 0.1
        + (df["fraud_risk_score"] > 50).astype(float) * 0.15
        + (df["fraud_risk_score"] > 70).astype(float) * 0.1
        + (df["litigation_risk"] > 0.6).astype(float) * 0.1
        + (df["promoter_risk"] > 0.6).astype(float) * 0.1
        + (df["revenue_growth"] < -0.1).astype(float) * 0.1
    )

    # Add noise
    risk_score += rng.normal(0, 0.05, size=n_samples)

    # Binary target: default (1) or no-default (0)
    threshold = np.percentile(risk_score, 70)  # ~30% default rate
    df["default"] = (risk_score > threshold).astype(int)

    return df


def train_model():
    """Train the credit risk model and save to disk."""
    print("=" * 60)
    print("Credit Risk Model Training")
    print("=" * 60)

    # Generate data
    print("\n1. Generating synthetic training data...")
    df = generate_synthetic_data(2000)
    print(f"   Generated {len(df)} samples")
    print(f"   Default rate: {df['default'].mean():.1%}")

    # Split features and target
    X = df[MODEL_FEATURES]
    y = df["default"]

    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y,
    )
    print(f"   Train: {len(X_train)}, Test: {len(X_test)}")

    # Train RandomForest
    print("\n2. Training RandomForest classifier...")
    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=8,
        min_samples_split=10,
        min_samples_leaf=5,
        random_state=42,
        class_weight="balanced",
    )
    model.fit(X_train, y_train)

    # Evaluate
    print("\n3. Model Evaluation:")
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    print(classification_report(y_test, y_pred, target_names=["No Default", "Default"]))
    auc = roc_auc_score(y_test, y_proba)
    print(f"   ROC AUC: {auc:.4f}")

    # Feature importances
    print("\n4. Feature Importances:")
    for feat, imp in sorted(
        zip(MODEL_FEATURES, model.feature_importances_),
        key=lambda x: x[1],
        reverse=True,
    ):
        print(f"   {feat:20s}: {imp:.4f}")

    # Save model
    ML_MODEL_DIR.mkdir(parents=True, exist_ok=True)
    model_path = ML_MODEL_DIR / "credit_risk_model.joblib"
    joblib.dump(model, model_path)
    print(f"\n5. Model saved to: {model_path}")
    print("=" * 60)

    return model


if __name__ == "__main__":
    train_model()
