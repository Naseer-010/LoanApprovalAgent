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
    promoter_risk_score: float = 0.0  # 0-100, derived from graph + research
    details: list[dict] = Field(default_factory=list)
    graph_structure: dict | None = None
    graph_risk_signals: dict | None = None


class SectorRiskReport(BaseModel):
    """Sector risk intelligence output."""
    company_name: str
    sector: str
    sector_risk_score: float = 0.0
    risk_level: str = "unknown"
    sector_headwinds: list[dict] = Field(default_factory=list)
    regulatory_changes: list[dict] = Field(default_factory=list)
    macro_risks: list[dict] = Field(default_factory=list)
    sector_summary: str = ""
    findings_analyzed: int = 0
    negative_signal_ratio: float = 0.0


class EarlyWarningReport(BaseModel):
    """Early warning system output."""
    company_name: str
    early_warning_score: float = 0.0
    risk_level: str = "LOW"
    triggers: list[dict] = Field(default_factory=list)
    signal_details: dict = Field(default_factory=dict)
    signals_monitored: int = 0
    active_warnings: int = 0


class WorkingCapitalReport(BaseModel):
    """Working capital stress analysis output."""
    company_name: str
    receivable_days: float | None = None
    inventory_days: float | None = None
    payable_days: float | None = None
    cash_conversion_cycle: float | None = None
    working_capital_score: float = 50.0
    liquidity_risk_level: str = "UNKNOWN"
    stress_indicators: list[dict] = Field(default_factory=list)
    data_completeness: str = ""
    explanation: str = ""
    missing_data: list[str] = Field(default_factory=list)


class HistoricalTrustReport(BaseModel):
    """Historical borrower trust analysis output."""
    company_name: str
    number_of_previous_applications: int = 0
    historical_trust_score: float = 0.0
    risk_score_trend: str = "no_history"
    fraud_risk_trend: str = "no_history"
    financial_stability_trend: str = "no_history"
    trend_summary: str = ""
    previous_applications: list[dict] = Field(default_factory=list)


class SwotReport(BaseModel):
    """SWOT analysis output."""
    company_name: str
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)
    threats: list[str] = Field(default_factory=list)
    summary: str = ""


class PortfolioRiskReport(BaseModel):
    """Portfolio performance risk output."""
    company_name: str
    portfolio_risk_score: float = 0.0
    risk_level: str = "NOT_APPLICABLE"
    metrics: dict = Field(default_factory=dict)
    risk_signals: list[dict] = Field(default_factory=list)
    summary: str = ""


class FinancialTrendReport(BaseModel):
    """Multi-year financial trend analysis output."""
    company_name: str
    trends: list[dict] = Field(default_factory=list)
    stability_score: float = 50.0
    stability_assessment: str = "Insufficient Data"
    trend_signals: list[dict] = Field(default_factory=list)
    num_metrics_analyzed: int = 0
    data_quality: str = "limited"


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
    sector_risk: SectorRiskReport | None = None
    early_warning: EarlyWarningReport | None = None

    # Pillar 3 — Recommendation Engine
    five_cs_scores: FiveCsScoreResponse | None = None
    loan_decision: LoanDecision | None = None
    credit_memo: CreditAppraisalMemo | None = None

    # Phase 4 — Financial Intelligence
    working_capital: WorkingCapitalReport | None = None
    historical_trust: HistoricalTrustReport | None = None

    # Phase 5 — Hackathon Extensions
    swot_analysis: SwotReport | None = None
    portfolio_risk: PortfolioRiskReport | None = None
    financial_trends: FinancialTrendReport | None = None

    # Processing metadata
    steps_completed: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
