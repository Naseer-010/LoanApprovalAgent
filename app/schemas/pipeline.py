"""Pydantic schemas for the unified pipeline endpoint."""

from pydantic import BaseModel, Field

from app.schemas.ingestor import (
    BankStatementSummary,
    CrossVerificationResult,
    DocumentAnalysisResponse,
    GSTDataResponse,
)
from app.schemas.recommendation import (
    CreditAppraisalMemo,
    FiveCsScoreResponse,
    LoanDecision,
)
from app.schemas.research import PrimaryInsightsResponse, ResearchReport


class FullAnalysisResponse(BaseModel):
    """Unified response combining all three pillar outputs."""

    company_name: str
    status: str = "completed"

    # Pillar 1 — Data Ingestor
    document_analysis: DocumentAnalysisResponse | None = None
    gst_data: GSTDataResponse | None = None
    bank_statement: BankStatementSummary | None = None
    cross_verification: CrossVerificationResult | None = None

    # Pillar 2 — Research Agent
    research_report: ResearchReport | None = None
    primary_insights: PrimaryInsightsResponse | None = None

    # Pillar 3 — Recommendation Engine
    five_cs_scores: FiveCsScoreResponse | None = None
    loan_decision: LoanDecision | None = None
    credit_memo: CreditAppraisalMemo | None = None

    # Processing metadata
    steps_completed: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
