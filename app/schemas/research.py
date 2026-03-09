"""Pydantic schemas for Research Agent (Pillar 2)."""

from pydantic import BaseModel, Field


# --- Risk Signals ---

class RiskSignals(BaseModel):
    """Structured risk signals derived from research."""
    litigation_risk: float = 0.0  # 0.0 - 1.0
    reputation_risk: float = 0.0  # 0.0 - 1.0
    sector_risk: float = 0.0  # 0.0 - 1.0
    regulatory_risk: float = 0.0  # 0.0 - 1.0


# --- Web Search ---

class WebSearchRequest(BaseModel):
    """Request to run secondary research on a company."""
    company_name: str
    sector: str = ""
    promoter_names: list[str] = Field(default_factory=list)
    additional_keywords: list[str] = Field(default_factory=list)


class NewsItem(BaseModel):
    """A single news or research finding."""
    title: str
    source: str = ""
    snippet: str = ""
    url: str = ""
    category: str = "general"  # promoter, sector, regulatory, litigation, general
    sentiment: str = "neutral"  # positive, neutral, negative
    relevance_score: float = 0.5


class ResearchReport(BaseModel):
    """Full secondary research report for a company."""
    company_name: str
    news_items: list[NewsItem] = Field(default_factory=list)
    promoter_findings: list[str] = Field(default_factory=list)
    sector_analysis: str = ""
    regulatory_findings: list[str] = Field(default_factory=list)
    litigation_findings: list[str] = Field(default_factory=list)
    overall_sentiment: str = "neutral"
    risk_flags: list[str] = Field(default_factory=list)
    risk_signals: RiskSignals = Field(default_factory=RiskSignals)
    ai_summary: str = ""


# --- Primary Insights ---

class PrimaryInsight(BaseModel):
    """Qualitative observation from credit officer."""
    insight_type: str = "general"  # factory_visit, management_interview, general
    observation: str
    severity: str = "neutral"  # positive, neutral, concerning, critical
    tags: list[str] = Field(default_factory=list)


class PrimaryInsightsRequest(BaseModel):
    """Request to process primary qualitative insights."""
    company_name: str
    insights: list[PrimaryInsight]


class RiskAdjustment(BaseModel):
    """Risk score adjustment based on primary insights."""
    factor: str
    adjustment: float = 0.0  # -1.0 to +1.0 (negative = risk increase)
    reasoning: str = ""


class PrimaryInsightsResponse(BaseModel):
    """Processed primary insights with risk adjustments."""
    company_name: str
    insights_processed: int = 0
    risk_adjustments: list[RiskAdjustment] = Field(default_factory=list)
    overall_risk_delta: float = 0.0  # aggregate shift
    ai_interpretation: str = ""
