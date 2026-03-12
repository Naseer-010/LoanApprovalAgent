"""Pydantic schemas for Recommendation Engine (Pillar 3)."""

from pydantic import BaseModel, Field


# --- Financial Ratios ---

class FinancialRatio(BaseModel):
    """A single financial ratio with assessment."""
    name: str
    value: float | None = None
    benchmark: str = ""
    assessment: str = "N/A"  # Pass, Watch, Fail, N/A
    detail: str = ""


class FinancialRatioReport(BaseModel):
    """All computed financial ratios."""
    dscr: FinancialRatio = Field(
        default_factory=lambda: FinancialRatio(name="DSCR"),
    )
    icr: FinancialRatio = Field(
        default_factory=lambda: FinancialRatio(name="ICR"),
    )
    leverage: FinancialRatio = Field(
        default_factory=lambda: FinancialRatio(name="Leverage"),
    )
    current_ratio: FinancialRatio = Field(
        default_factory=lambda: FinancialRatio(name="Current Ratio"),
    )
    debt_to_equity: FinancialRatio = Field(
        default_factory=lambda: FinancialRatio(name="Debt/Equity"),
    )
    ebitda_margin: FinancialRatio = Field(
        default_factory=lambda: FinancialRatio(name="EBITDA Margin"),
    )
    overall_health: str = "Moderate"  # Strong, Moderate, Weak, Critical


# --- Five Cs Scoring ---

class CreditCScore(BaseModel):
    """Score for a single C of the Five Cs of Credit."""
    category: str
    score: float = 0.0
    weight: float = 0.2
    explanation: str = ""
    supporting_evidence: list[str] = Field(default_factory=list)


class FiveCsScoreRequest(BaseModel):
    """Input data for Five Cs scoring."""
    company_name: str
    financial_data: dict = Field(default_factory=dict)
    research_data: dict = Field(default_factory=dict)
    primary_insights: dict = Field(default_factory=dict)
    cross_verification: dict = Field(default_factory=dict)


class FiveCsScoreResponse(BaseModel):
    """Five Cs scoring result."""
    company_name: str
    scores: list[CreditCScore] = Field(default_factory=list)
    weighted_total: float = 0.0
    risk_grade: str = ""
    ai_commentary: str = ""


# --- Explainability ---

class StructuredReasoning(BaseModel):
    """Rigidly structured reasoning requirement."""
    financial_reason: str
    risk_signal: str
    supporting_metric: str


class ExplainabilityReport(BaseModel):
    """Structured explainability for a loan decision."""
    decision: str = "REFER"
    structured_reasons: list[StructuredReasoning] = Field(default_factory=list)
    risk_factors: list[dict] = Field(default_factory=list)
    financial_drivers: list[dict] = Field(default_factory=list)
    research_signals: list[dict] = Field(default_factory=list)
    ml_explanation: dict | None = None
    confidence_basis: list[str] = Field(default_factory=list)


# --- Loan Decision ---

class LoanDecisionRequest(BaseModel):
    """Input for loan decision engine."""
    company_name: str
    requested_amount: float = 0.0
    five_cs_scores: FiveCsScoreResponse | None = None
    financial_data: dict = Field(default_factory=dict)
    research_data: dict = Field(default_factory=dict)
    risk_adjustments: list[dict] = Field(default_factory=list)
    fraud_data: dict = Field(default_factory=dict)
    regulatory_data: dict = Field(default_factory=dict)
    promoter_data: dict = Field(default_factory=dict)
    sector_data: dict = Field(default_factory=dict)
    early_warning_data: dict = Field(default_factory=dict)
    working_capital_data: dict = Field(default_factory=dict)
    historical_trust_data: dict = Field(default_factory=dict)


class LoanDecision(BaseModel):
    """Final loan decision output."""
    company_name: str
    decision: str = "REFER"
    recommended_amount: float = 0.0
    interest_rate: float = 0.0
    risk_premium: float = 0.0
    risk_grade: str = ""
    final_credit_risk_score: float = 0.0
    confidence_score: float = 0.0
    explanation: str = ""
    rejection_reasons: list[str] = Field(default_factory=list)
    key_factors: list[str] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)
    financial_ratios: FinancialRatioReport = Field(
        default_factory=FinancialRatioReport,
    )
    ml_risk_prediction: dict = Field(default_factory=dict)
    explainability: ExplainabilityReport = Field(
        default_factory=ExplainabilityReport,
    )


# --- Credit Appraisal Memo (CAM) ---

class CAMSection(BaseModel):
    """A single section of the Credit Appraisal Memo."""
    title: str
    content: str
    subsections: list[dict] = Field(default_factory=list)


class CAMRequest(BaseModel):
    """Request to generate a full Credit Appraisal Memo."""
    company_name: str
    financial_data: dict = Field(default_factory=dict)
    research_report: dict = Field(default_factory=dict)
    five_cs_scores: dict = Field(default_factory=dict)
    loan_decision: dict = Field(default_factory=dict)
    primary_insights: list[dict] = Field(default_factory=list)
    cross_verification: dict = Field(default_factory=dict)
    promoter_network: dict = Field(default_factory=dict)
    sector_risk: dict = Field(default_factory=dict)
    early_warning: dict = Field(default_factory=dict)
    working_capital: dict = Field(default_factory=dict)
    historical_trust: dict = Field(default_factory=dict)


class CreditAppraisalMemo(BaseModel):
    """Full Credit Appraisal Memo."""
    company_name: str
    generated_at: str = ""
    sections: list[CAMSection] = Field(default_factory=list)
    executive_summary: str = ""
    recommendation: str = ""
    risk_grade: str = ""
    recommended_amount: float = 0.0
    interest_rate: float = 0.0
    docx_path: str = ""  # Path to downloadable DOCX
    pdf_path: str = ""  # Path to downloadable PDF
