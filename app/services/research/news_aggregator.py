"""
News Aggregator — processes and summarizes multi-source research findings.

Deduplicates across sources, categorizes, computes risk signals,
and generates a structured research report with optional LLM summary.
"""

import logging

from langchain_core.prompts import ChatPromptTemplate

from app.core.llm import get_research_llm
from app.schemas.research import (
    NewsItem,
    ResearchReport,
    RiskSignals,
    WebSearchRequest,
)
from app.services.research.web_researcher import compute_risk_signals

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
    Aggregate news items into a structured research report.
    Deduplicates across sources, computes risk signals, and generates summary.
    """
    # Deduplicate by title similarity
    deduplicated = _deduplicate_items(news_items)

    # Categorize findings
    promoter_findings = [
        item.snippet for item in deduplicated
        if item.category == "promoter" and item.snippet
    ]
    regulatory_findings = [
        item.snippet for item in deduplicated
        if item.category == "regulatory" and item.snippet
    ]
    litigation_findings = [
        item.snippet for item in deduplicated
        if item.category == "litigation" and item.snippet
    ]
    risk_flags = [
        item.snippet
        for item in deduplicated
        if item.sentiment == "negative" and item.snippet
    ]

    # Determine overall sentiment
    sentiments = [item.sentiment for item in deduplicated]
    neg_count = sentiments.count("negative")
    pos_count = sentiments.count("positive")
    if neg_count > pos_count + 2:
        overall_sentiment = "negative"
    elif pos_count > neg_count + 2:
        overall_sentiment = "positive"
    else:
        overall_sentiment = "neutral"

    # Compute structured risk signals
    risk_signals_dict = compute_risk_signals(deduplicated)
    risk_signals = RiskSignals(**risk_signals_dict)

    # Generate LLM summary (optional/best-effort)
    ai_summary = _generate_summary(request, deduplicated)
    sector_analysis = _extract_sector_analysis(deduplicated)

    return ResearchReport(
        company_name=request.company_name,
        news_items=deduplicated,
        promoter_findings=promoter_findings[:5],
        sector_analysis=sector_analysis,
        regulatory_findings=regulatory_findings[:5],
        litigation_findings=litigation_findings[:5],
        overall_sentiment=overall_sentiment,
        risk_flags=risk_flags[:10],
        risk_signals=risk_signals,
        ai_summary=ai_summary,
    )


def _deduplicate_items(items: list[NewsItem]) -> list[NewsItem]:
    """Remove duplicate news items based on title similarity."""
    seen_titles: set[str] = set()
    unique: list[NewsItem] = []

    for item in items:
        # Normalize title for comparison
        normalized = item.title.lower().strip()
        # Simple dedup: check if title is substantially similar
        if normalized and normalized not in seen_titles:
            # Check for partial matches
            is_duplicate = False
            for seen in seen_titles:
                if len(normalized) > 20 and len(seen) > 20:
                    # Use first 30 chars as fingerprint
                    if normalized[:30] == seen[:30]:
                        is_duplicate = True
                        break
            if not is_duplicate:
                seen_titles.add(normalized)
                unique.append(item)

    return unique


def _generate_summary(request: WebSearchRequest, items: list[NewsItem]) -> str:
    """Use LLM to generate a narrative research summary."""
    try:
        llm = get_research_llm()
        chain = SUMMARIZE_PROMPT | llm

        findings_text = "\n".join(
            f"- [{item.category}] ({item.sentiment}) {item.title}: {item.snippet}"
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
