"""API routes for the Research Agent (Pillar 2)."""

from fastapi import APIRouter

from app.schemas.research import (
    PrimaryInsightsRequest,
    PrimaryInsightsResponse,
    ResearchReport,
    WebSearchRequest,
)
from app.services.research.news_aggregator import build_research_report
from app.services.research.primary_insights import (
    get_stored_insights,
    process_primary_insights,
)
from app.services.research.web_researcher import run_web_research

router = APIRouter(prefix="/research", tags=["Research Agent"])


@router.post("/web-search")
def web_search(request: WebSearchRequest) -> ResearchReport:
    """Run secondary research: web search for news, regulatory, litigation."""
    news_items = run_web_research(request)
    report = build_research_report(request, news_items)
    return report


@router.post("/primary-insights")
def submit_primary_insights(request: PrimaryInsightsRequest) -> PrimaryInsightsResponse:
    """Submit qualitative observations from field visits / management interviews."""
    return process_primary_insights(request)


@router.get("/report/{company_name}")
def get_research_report(company_name: str) -> dict:
    """Get stored research data for a company."""
    insights = get_stored_insights(company_name)
    return {
        "company_name": company_name,
        "stored_insights_count": len(insights),
        "insights": [i.model_dump() for i in insights],
    }
