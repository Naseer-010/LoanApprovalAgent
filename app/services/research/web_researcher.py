"""
Web Researcher — LangChain agent with DuckDuckGo for secondary research.

Searches for company news, promoter litigation, MCA filings, eCourts
cases, RBI regulatory impact, and sector analysis.
"""

import json
import logging

from langchain_classic.agents import AgentExecutor, create_react_agent
from langchain_community.tools import DuckDuckGoSearchResults
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import Tool

from app.core.llm import get_research_llm
from app.schemas.research import NewsItem, WebSearchRequest

logger = logging.getLogger(__name__)

RESEARCH_AGENT_PROMPT = PromptTemplate.from_template(
    """You are a credit research analyst for Indian corporate lending.
Research the company for credit appraisal purposes.

You have access to the following tools:
{tools}

Use the following format:

Question: the research question you must answer
Thought: think about what to search for
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (repeat Thought/Action/Action Input/Observation as needed)
Thought: I now have enough information
Final Answer: a JSON array of findings, each with keys: \
title, source, snippet, category \
(promoter|sector|regulatory|litigation|general), \
sentiment (positive|neutral|negative)

Begin!

Question: {input}
{agent_scratchpad}
"""
)


def run_web_research(
    request: WebSearchRequest,
) -> list[NewsItem]:
    """
    Run secondary research on a company using web search.

    Searches: company news, promoter background, sector,
    regulatory, litigation, eCourts, MCA, RBI.
    """
    search_tool = DuckDuckGoSearchResults(
        name="web_search",
        description=(
            "Search the web for news, regulatory filings, "
            "and litigation. Input: search query string."
        ),
        max_results=5,
    )

    tools = [search_tool]
    queries = _build_search_queries(request)
    all_findings: list[NewsItem] = []

    for query, category in queries:
        findings = _search_and_parse(query, category, tools)
        all_findings.extend(findings)

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
        # eCourts targeted search
        queries.append((
            f"{promoter} court case litigation India "
            f"eCourts NCLT DRT",
            "litigation",
        ))

    # Sector + RBI regulatory
    queries.append((
        f"{sector} India sector outlook RBI regulatory "
        f"impact 2024 2025",
        "sector",
    ))

    # MCA filings
    queries.append((
        f"{company} MCA filing Ministry Corporate Affairs "
        f"annual return ROC India",
        "regulatory",
    ))

    # RBI regulatory impact
    queries.append((
        f"RBI {sector} sector NPA circular regulatory "
        f"action India",
        "regulatory",
    ))

    # Litigation — company level
    queries.append((
        f"{company} litigation legal dispute court case "
        f"NCLT IBC India",
        "litigation",
    ))

    # CIBIL / credit history
    queries.append((
        f"{company} credit rating CRISIL ICRA CARE "
        f"credit history India",
        "general",
    ))

    # Additional keywords
    for keyword in request.additional_keywords[:2]:
        queries.append((
            f"{company} {keyword}", "general",
        ))

    return queries


def _search_and_parse(
    query: str,
    category: str,
    tools: list[Tool],
) -> list[NewsItem]:
    """Run a single search query and parse results."""
    try:
        llm = get_research_llm()
        agent = create_react_agent(
            llm, tools, RESEARCH_AGENT_PROMPT,
        )
        executor = AgentExecutor(
            agent=agent,
            tools=tools,
            max_iterations=3,
            handle_parsing_errors=True,
            verbose=False,
        )

        result = executor.invoke({"input": query})
        output = result.get("output", "")
        return _parse_findings(output, category)

    except Exception as e:
        logger.error(
            "Web research failed for '%s': %s", query, e,
        )
        return [
            NewsItem(
                title=f"Search: {query[:80]}",
                snippet=f"Search failed: {e}",
                category=category,
                sentiment="neutral",
            )
        ]


def _parse_findings(
    output: str, default_category: str,
) -> list[NewsItem]:
    """Parse agent output into NewsItem objects."""
    items: list[NewsItem] = []

    try:
        start = output.find("[")
        end = output.rfind("]")
        if start != -1 and end != -1:
            parsed = json.loads(output[start: end + 1])
            for item in parsed:
                items.append(
                    NewsItem(
                        title=item.get("title", ""),
                        source=item.get("source", ""),
                        snippet=item.get("snippet", ""),
                        category=item.get(
                            "category", default_category,
                        ),
                        sentiment=item.get(
                            "sentiment", "neutral",
                        ),
                    )
                )
            return items
    except (json.JSONDecodeError, TypeError):
        pass

    if output.strip():
        items.append(
            NewsItem(
                title="Research Finding",
                snippet=output[:500],
                category=default_category,
                sentiment="neutral",
            )
        )

    return items
