"""
Web Researcher — LangChain agent with DuckDuckGo search for secondary research.

Searches for news, regulatory filings, and litigation history related to
a company, its promoters, and sector.
"""

import logging

from langchain_classic.agents import AgentExecutor, create_react_agent
from langchain_community.tools import DuckDuckGoSearchResults
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import Tool

from app.core.llm import get_research_llm
from app.schemas.research import NewsItem, WebSearchRequest

logger = logging.getLogger(__name__)

RESEARCH_AGENT_PROMPT = PromptTemplate.from_template(
    """You are a credit research analyst specializing in Indian corporate lending.
Your job is to research a company for credit appraisal purposes.

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
Final Answer: a JSON array of findings, each with keys: title, source, snippet, category (promoter|sector|regulatory|litigation|general), sentiment (positive|neutral|negative)

Begin!

Question: {input}
{agent_scratchpad}
"""
)


def run_web_research(request: WebSearchRequest) -> list[NewsItem]:
    """
    Run secondary research on a company using web search.

    Searches for: company news, promoter background, sector analysis,
    regulatory updates, and litigation history.
    """
    search_tool = DuckDuckGoSearchResults(
        name="web_search",
        description="Search the web for news, regulatory filings, and litigation. Input should be a search query string.",
        max_results=5,
    )

    tools = [search_tool]

    # Build research queries
    queries = _build_search_queries(request)
    all_findings: list[NewsItem] = []

    for query, category in queries:
        findings = _search_and_parse(query, category, tools)
        all_findings.extend(findings)

    return all_findings


def _build_search_queries(request: WebSearchRequest) -> list[tuple[str, str]]:
    """Generate targeted search queries for different research dimensions."""
    company = request.company_name
    sector = request.sector or "corporate"
    queries: list[tuple[str, str]] = []

    # Company news
    queries.append((f"{company} India latest news financial", "general"))

    # Promoter background
    for promoter in request.promoter_names[:3]:  # limit to 3
        queries.append((f"{promoter} {company} promoter background India", "promoter"))

    # Sector analysis
    queries.append((f"{sector} India sector outlook regulatory RBI 2024 2025", "sector"))

    # Regulatory / MCA filings
    queries.append((f"{company} MCA filing regulatory compliance India", "regulatory"))

    # Litigation
    queries.append((f"{company} litigation legal dispute court case India", "litigation"))

    # Additional keywords
    for keyword in request.additional_keywords[:2]:
        queries.append((f"{company} {keyword}", "general"))

    return queries


def _search_and_parse(
    query: str,
    category: str,
    tools: list[Tool],
) -> list[NewsItem]:
    """Run a single search query and parse results into NewsItem objects."""
    try:
        llm = get_research_llm()
        agent = create_react_agent(llm, tools, RESEARCH_AGENT_PROMPT)
        executor = AgentExecutor(
            agent=agent,
            tools=tools,
            max_iterations=3,
            handle_parsing_errors=True,
            verbose=False,
        )

        result = executor.invoke({"input": query})
        output = result.get("output", "")

        # Parse the agent output into NewsItem objects
        return _parse_findings(output, category)

    except Exception as e:
        logger.error("Web research failed for query '%s': %s", query, e)
        return [
            NewsItem(
                title=f"Search: {query}",
                snippet=f"Search failed: {e}",
                category=category,
                sentiment="neutral",
            )
        ]


def _parse_findings(output: str, default_category: str) -> list[NewsItem]:
    """Parse agent output into NewsItem objects."""
    import json

    items: list[NewsItem] = []

    try:
        # Try JSON parsing first
        start = output.find("[")
        end = output.rfind("]")
        if start != -1 and end != -1:
            parsed = json.loads(output[start : end + 1])
            for item in parsed:
                items.append(
                    NewsItem(
                        title=item.get("title", ""),
                        source=item.get("source", ""),
                        snippet=item.get("snippet", ""),
                        category=item.get("category", default_category),
                        sentiment=item.get("sentiment", "neutral"),
                    )
                )
            return items
    except (json.JSONDecodeError, TypeError):
        pass

    # Fallback: treat the entire output as a single finding
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
