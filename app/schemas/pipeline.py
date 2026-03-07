"""Pydantic schemas for the unified pipeline endpoint."""

from pydantic import BaseModel, Field

from app.schemas.ingestor import (
    BankStatementSummary,
    CrossVerificationResult,
    DocumentAnalysisResponse,
    FraudReport,
    GSTDataResponse,
    RegulatoryCheckResult,
)
from app.schemas.recommendation import (
    CreditAppraisalMemo,
    FiveCsScoreResponse,
    LoanDecision,
)
from app.schemas.research import (
    PrimaryInsightsResponse,
    ResearchReport,
)


class PromoterRiskReport(BaseModel):
    """Promoter risk analysis output for pipeline."""
    promoters_analyzed: int = 0
    risk_flags: list[str] = Field(default_factory=list)
    linked_companies: list[dict] = Field(default_factory=list)
    litigation_flags: list[str] = Field(default_factory=list)
    overall_promoter_risk: str = "low"
    details: list[dict] = Field(default_factory=list)


class FullAnalysisResponse(BaseModel):
    """Unified response combining all pillar outputs."""

    company_name: str
    status: str = "completed"

    # Pillar 1 — Data Ingestor
    document_analysis: DocumentAnalysisResponse | None = None
    gst_data: GSTDataResponse | None = None
    bank_statement: BankStatementSummary | None = None
    cross_verification: CrossVerificationResult | None = None
    fraud_report: FraudReport | None = None
    regulatory_checks: RegulatoryCheckResult | None = None

    # Pillar 2 — Research Agent
    research_report: ResearchReport | None = None
    primary_insights: PrimaryInsightsResponse | None = None
    promoter_risk: PromoterRiskReport | None = None

    # Pillar 3 — Recommendation Engine
    five_cs_scores: FiveCsScoreResponse | None = None
    loan_decision: LoanDecision | None = None
    credit_memo: CreditAppraisalMemo | None = None

    # Processing metadata
    steps_completed: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
