"""Pydantic schemas for Recommendation Engine (Pillar 3)."""

from pydantic import BaseModel, Field


# --- Five Cs Scoring ---

class CreditCScore(BaseModel):
    """Score for a single C of the Five Cs of Credit."""
    category: str  # Character, Capacity, Capital, Collateral, Conditions
    score: float = 0.0  # 0–100
    weight: float = 0.2  # default equal weight
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
    weighted_total: float = 0.0  # 0–100
    risk_grade: str = ""  # AAA, AA, A, BBB, BB, B, C, D
    ai_commentary: str = ""


# --- Loan Decision ---

class LoanDecisionRequest(BaseModel):
    """Input for loan decision engine."""
    company_name: str
    requested_amount: float = 0.0
    five_cs_scores: FiveCsScoreResponse | None = None
    financial_data: dict = Field(default_factory=dict)
    research_data: dict = Field(default_factory=dict)
    risk_adjustments: list[dict] = Field(default_factory=list)


class LoanDecision(BaseModel):
    """Final loan decision output."""
    company_name: str
    decision: str = "REFER"  # APPROVE, REJECT, REFER
    recommended_amount: float = 0.0
    interest_rate: float = 0.0  # suggested rate in %
    risk_premium: float = 0.0  # additional premium in bps
    risk_grade: str = ""
    confidence_score: float = 0.0  # 0–1
    explanation: str = ""
    key_factors: list[str] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)


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
