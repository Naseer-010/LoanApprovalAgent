"""
News Aggregator — processes and summarizes web research findings.

Categorizes, deduplicates, and generates an overall research report using LLM.
"""

import logging

from langchain_core.prompts import ChatPromptTemplate

from app.core.llm import get_research_llm
from app.schemas.research import NewsItem, ResearchReport, WebSearchRequest

logger = logging.getLogger(__name__)

SUMMARIZE_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a credit research analyst. Summarize the following research findings "
        "into a structured analysis for a corporate credit appraisal. Focus on material "
        "risks, positive indicators, and anything that affects creditworthiness. "
        "Be specific to the Indian corporate context.",
    ),
    (
        "human",
        """Company: {company_name}
Sector: {sector}

Research Findings:
{findings_text}

Provide a structured analysis covering:
1. Promoter assessment
2. Sector outlook
3. Regulatory environment
4. Litigation/legal risks
5. Overall sentiment and risk flags

Keep it concise and actionable for a credit officer.
""",
    ),
])


def build_research_report(
    request: WebSearchRequest,
    news_items: list[NewsItem],
) -> ResearchReport:
    """
    Aggregate news items into a structured research report with LLM summary.
    """
    # Categorize findings
    promoter_findings = [
        item.snippet for item in news_items if item.category == "promoter" and item.snippet
    ]
    regulatory_findings = [
        item.snippet for item in news_items if item.category == "regulatory" and item.snippet
    ]
    litigation_findings = [
        item.snippet for item in news_items if item.category == "litigation" and item.snippet
    ]
    risk_flags = [
        item.snippet
        for item in news_items
        if item.sentiment == "negative" and item.snippet
    ]

    # Determine overall sentiment
    sentiments = [item.sentiment for item in news_items]
    neg_count = sentiments.count("negative")
    pos_count = sentiments.count("positive")
    if neg_count > pos_count + 2:
        overall_sentiment = "negative"
    elif pos_count > neg_count + 2:
        overall_sentiment = "positive"
    else:
        overall_sentiment = "neutral"

    # Generate LLM summary
    ai_summary = _generate_summary(request, news_items)
    sector_analysis = _extract_sector_analysis(news_items)

    return ResearchReport(
        company_name=request.company_name,
        news_items=news_items,
        promoter_findings=promoter_findings[:5],
        sector_analysis=sector_analysis,
        regulatory_findings=regulatory_findings[:5],
        litigation_findings=litigation_findings[:5],
        overall_sentiment=overall_sentiment,
        risk_flags=risk_flags[:10],
        ai_summary=ai_summary,
    )


def _generate_summary(request: WebSearchRequest, items: list[NewsItem]) -> str:
    """Use LLM to generate a narrative research summary."""
    try:
        llm = get_research_llm()
        chain = SUMMARIZE_PROMPT | llm

        findings_text = "\n".join(
            f"- [{item.category}] {item.title}: {item.snippet}"
            for item in items
            if item.snippet
        )

        if not findings_text:
            return "No significant research findings available."

        result = chain.invoke({
            "company_name": request.company_name,
            "sector": request.sector or "N/A",
            "findings_text": findings_text[:3000],
        })

        return result.content if hasattr(result, "content") else str(result)

    except Exception as e:
        logger.error("Research summary generation failed: %s", e)
        return f"AI summary unavailable: {e}"


def _extract_sector_analysis(items: list[NewsItem]) -> str:
    """Extract sector-specific findings into a combined analysis string."""
    sector_items = [item for item in items if item.category == "sector"]
    if not sector_items:
        return "No sector-specific findings available."
    return " | ".join(item.snippet for item in sector_items if item.snippet)[:1000]
