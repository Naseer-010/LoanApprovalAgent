"""
Web Researcher — multi-source research for company intelligence.

Integrates GNews, Serper API, NewsAPI, and DuckDuckGo (fallback).
Searches for company news, promoter litigation, fraud, bankruptcy,
NCLT cases, and regulatory violations.

Produces structured risk signals: litigation_risk, reputation_risk,
sector_risk, regulatory_risk.
"""

import json
import logging
from typing import Optional

import requests
from langchain_community.tools import DuckDuckGoSearchResults

from app.config import settings
from app.schemas.research import NewsItem, WebSearchRequest

logger = logging.getLogger(__name__)

# Risk signal keywords
NEGATIVE_KEYWORDS = [
    "fraud", "scam", "default", "bankruptcy", "insolvency", "nclt",
    "litigation", "lawsuit", "arrest", "penalty", "violation", "ban",
    "suspension", "blacklist", "money laundering", "wilful defaulter",
    "npa", "non-performing", "regulatory action", "sebi order",
    "rbi penalty", "enforcement directorate", "cbi", "ed raid",
]

LITIGATION_KEYWORDS = [
    "court", "litigation", "lawsuit", "nclt", "drt", "nclat",
    "tribunal", "case filed", "legal dispute", "winding up",
    "insolvency", "ibc", "legal proceedings",
]

REGULATORY_KEYWORDS = [
    "rbi", "sebi", "mca", "regulatory", "compliance", "penalty",
    "fine", "order", "circular", "notification", "guideline",
]


def run_web_research(
    request: WebSearchRequest,
) -> list[NewsItem]:
    """
    Run multi-source research on a company.

    Sources (in order of priority):
    1. GNews API (if key configured)
    2. Serper API (if key configured)
    3. NewsAPI (if key configured)
    4. DuckDuckGo (always available fallback)
    """
    queries = _build_search_queries(request)
    all_findings: list[NewsItem] = []

    for query, category in queries:
        findings = _search_all_sources(query, category)
        all_findings.extend(findings)

    # Classify sentiment based on keywords
    for item in all_findings:
        if item.sentiment == "neutral":
            item.sentiment = _classify_sentiment(
                f"{item.title} {item.snippet}"
            )

    return all_findings


def _build_search_queries(
    request: WebSearchRequest,
) -> list[tuple[str, str]]:
    """Generate targeted search queries for research."""
    company = request.company_name
    sector = request.sector or "corporate"
    queries: list[tuple[str, str]] = []

    # Company news
    queries.append((
        f"{company} India latest news financial performance",
        "general",
    ))

    # Promoter background + litigation
    for promoter in request.promoter_names[:3]:
        queries.append((
            f"{promoter} {company} promoter background India",
            "promoter",
        ))
        queries.append((
            f"{promoter} court case litigation India NCLT DRT",
            "litigation",
        ))

    # Sector + RBI regulatory
    queries.append((
        f"{sector} India sector outlook RBI regulatory impact 2024 2025",
        "sector",
    ))

    # Fraud/negative news
    queries.append((
        f"{company} fraud allegation default NPA India",
        "litigation",
    ))

    # MCA filings
    queries.append((
        f"{company} MCA filing Ministry Corporate Affairs India",
        "regulatory",
    ))

    # RBI regulatory impact
    queries.append((
        f"RBI {sector} sector NPA circular regulatory action India",
        "regulatory",
    ))

    # Litigation — company level
    queries.append((
        f"{company} litigation legal dispute court case NCLT IBC India",
        "litigation",
    ))

    # Credit rating
    queries.append((
        f"{company} credit rating CRISIL ICRA CARE credit history India",
        "general",
    ))

    # Additional keywords
    for keyword in request.additional_keywords[:2]:
        queries.append((
            f"{company} {keyword}", "general",
        ))

    return queries


def _search_all_sources(
    query: str,
    category: str,
) -> list[NewsItem]:
    """Search across all configured sources."""
    results: list[NewsItem] = []

    # Try GNews API
    if settings.GNEWS_API_KEY:
        results.extend(_search_gnews(query, category))

    # Try Serper API
    if settings.SERPER_API_KEY:
        results.extend(_search_serper(query, category))

    # Try NewsAPI
    if settings.NEWSAPI_KEY:
        results.extend(_search_newsapi(query, category))

    # Fallback: DuckDuckGo (always available)
    if not results:
        results.extend(_search_duckduckgo(query, category))

    return results


def _search_gnews(query: str, category: str) -> list[NewsItem]:
    """Search using GNews API."""
    try:
        from gnews import GNews

        google_news = GNews(
            language="en",
            country="IN",
            max_results=5,
        )
        articles = google_news.get_news(query)

        items = []
        for article in articles[:5]:
            items.append(NewsItem(
                title=article.get("title", ""),
                source=article.get("publisher", {}).get("title", "GNews"),
                snippet=article.get("description", "")[:500],
                url=article.get("url", ""),
                category=category,
                sentiment="neutral",
            ))
        return items

    except Exception as e:
        logger.warning("GNews search failed: %s", e)
        return []


def _search_serper(query: str, category: str) -> list[NewsItem]:
    """Search using Serper API."""
    try:
        resp = requests.post(
            "https://google.serper.dev/search",
            headers={
                "X-API-KEY": settings.SERPER_API_KEY,
                "Content-Type": "application/json",
            },
            json={"q": query, "gl": "in", "num": 5},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

        items = []
        for result in data.get("organic", [])[:5]:
            items.append(NewsItem(
                title=result.get("title", ""),
                source="Serper",
                snippet=result.get("snippet", "")[:500],
                url=result.get("link", ""),
                category=category,
                sentiment="neutral",
            ))

        # Also check news results
        for result in data.get("news", [])[:3]:
            items.append(NewsItem(
                title=result.get("title", ""),
                source=result.get("source", "Serper News"),
                snippet=result.get("snippet", "")[:500],
                url=result.get("link", ""),
                category=category,
                sentiment="neutral",
            ))

        return items

    except Exception as e:
        logger.warning("Serper search failed: %s", e)
        return []


def _search_newsapi(query: str, category: str) -> list[NewsItem]:
    """Search using NewsAPI."""
    try:
        resp = requests.get(
            "https://newsapi.org/v2/everything",
            params={
                "q": query,
                "language": "en",
                "sortBy": "relevancy",
                "pageSize": 5,
                "apiKey": settings.NEWSAPI_KEY,
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

        items = []
        for article in data.get("articles", [])[:5]:
            items.append(NewsItem(
                title=article.get("title", ""),
                source=article.get("source", {}).get("name", "NewsAPI"),
                snippet=article.get("description", "")[:500],
                url=article.get("url", ""),
                category=category,
                sentiment="neutral",
            ))
        return items

    except Exception as e:
        logger.warning("NewsAPI search failed: %s", e)
        return []


def _search_duckduckgo(query: str, category: str) -> list[NewsItem]:
    """Search using DuckDuckGo (always available fallback)."""
    try:
        search_tool = DuckDuckGoSearchResults(max_results=5)
        raw_results = search_tool.invoke(query)

        items = []
        if isinstance(raw_results, str):
            # Parse the string format
            items.append(NewsItem(
                title=f"Search: {query[:80]}",
                source="DuckDuckGo",
                snippet=raw_results[:500],
                category=category,
                sentiment="neutral",
            ))
        elif isinstance(raw_results, list):
            for r in raw_results[:5]:
                if isinstance(r, dict):
                    items.append(NewsItem(
                        title=r.get("title", query[:80]),
                        source="DuckDuckGo",
                        snippet=r.get("snippet", r.get("body", ""))[:500],
                        url=r.get("link", r.get("href", "")),
                        category=category,
                        sentiment="neutral",
                    ))

        return items

    except Exception as e:
        logger.warning("DuckDuckGo search failed: %s", e)
        return [
            NewsItem(
                title=f"Search: {query[:80]}",
                snippet=f"All search sources failed: {e}",
                category=category,
                sentiment="neutral",
            )
        ]


def _classify_sentiment(text: str) -> str:
    """Classify text sentiment based on keyword analysis."""
    text_lower = text.lower()

    negative_hits = sum(
        1 for kw in NEGATIVE_KEYWORDS if kw in text_lower
    )
    positive_keywords = [
        "growth", "profit", "award", "expansion", "upgrade",
        "strong", "positive", "success", "achievement",
    ]
    positive_hits = sum(
        1 for kw in positive_keywords if kw in text_lower
    )

    if negative_hits >= 2:
        return "negative"
    if negative_hits > positive_hits:
        return "negative"
    if positive_hits > negative_hits:
        return "positive"
    return "neutral"


def compute_risk_signals(
    news_items: list[NewsItem],
) -> dict[str, float]:
    """
    Compute structured risk signals from research findings.

    Returns dict with:
    - litigation_risk (0.0-1.0)
    - reputation_risk (0.0-1.0)
    - sector_risk (0.0-1.0)
    - regulatory_risk (0.0-1.0)
    """
    if not news_items:
        return {
            "litigation_risk": 0.0,
            "reputation_risk": 0.0,
            "sector_risk": 0.0,
            "regulatory_risk": 0.0,
        }

    litigation_count = 0
    negative_count = 0
    sector_negative = 0
    regulatory_negative = 0

    for item in news_items:
        text = f"{item.title} {item.snippet}".lower()

        # Litigation risk
        if any(kw in text for kw in LITIGATION_KEYWORDS):
            litigation_count += 1

        # Reputation risk
        if item.sentiment == "negative":
            negative_count += 1

        # Sector risk
        if item.category == "sector" and item.sentiment == "negative":
            sector_negative += 1

        # Regulatory risk
        if any(kw in text for kw in REGULATORY_KEYWORDS):
            if item.sentiment == "negative":
                regulatory_negative += 1

    total = max(len(news_items), 1)

    return {
        "litigation_risk": min(1.0, litigation_count / max(total * 0.3, 1)),
        "reputation_risk": min(1.0, negative_count / max(total * 0.5, 1)),
        "sector_risk": min(1.0, sector_negative / max(total * 0.2, 1)),
        "regulatory_risk": min(1.0, regulatory_negative / max(total * 0.2, 1)),
    }
