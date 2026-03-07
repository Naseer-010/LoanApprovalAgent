"""
Primary Insights Service — processes qualitative notes from credit officers.

Accepts observations from factory visits, management interviews, and other
due diligence activities. Uses LLM to interpret notes and generate risk adjustments.
"""

import json
import logging

from langchain_core.prompts import ChatPromptTemplate

from app.core.llm import get_research_llm
from app.schemas.research import (
    PrimaryInsight,
    PrimaryInsightsRequest,
    PrimaryInsightsResponse,
    RiskAdjustment,
)

logger = logging.getLogger(__name__)

INSIGHTS_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a senior credit analyst. Analyze qualitative observations from field "
        "visits and management interviews. Determine how each observation should adjust "
        "the company's credit risk score. "
        "Return ONLY valid JSON, no markdown fences.",
    ),
    (
        "human",
        """Company: {company_name}

Qualitative observations from the credit officer:
{observations}

For each observation, determine a risk adjustment factor between -1.0 (significantly increases risk)
and +1.0 (significantly reduces risk), with reasoning.

Respond with this JSON:
{{
  "adjustments": [
    {{
      "factor": "name of the risk factor",
      "adjustment": 0.0,
      "reasoning": "explanation"
    }}
  ],
  "overall_risk_delta": 0.0,
  "interpretation": "overall interpretation of the qualitative insights"
}}
""",
    ),
])


# In-memory store for primary insights (per company)
_insights_store: dict[str, list[PrimaryInsight]] = {}


def store_insights(request: PrimaryInsightsRequest) -> None:
    """Store primary insights for a company."""
    company = request.company_name.lower()
    if company not in _insights_store:
        _insights_store[company] = []
    _insights_store[company].extend(request.insights)


def get_stored_insights(company_name: str) -> list[PrimaryInsight]:
    """Retrieve stored insights for a company."""
    return _insights_store.get(company_name.lower(), [])


def process_primary_insights(
    request: PrimaryInsightsRequest,
) -> PrimaryInsightsResponse:
    """
    Process qualitative insights using LLM and generate risk adjustments.
    Also stores the insights for later retrieval.
    """
    # Store insights
    store_insights(request)

    # Format observations for LLM
    observations_text = "\n".join(
        f"- [{insight.insight_type}] ({insight.severity}) {insight.observation}"
        for insight in request.insights
    )

    # Get LLM analysis
    adjustments, overall_delta, interpretation = _analyze_with_llm(
        request.company_name, observations_text
    )

    return PrimaryInsightsResponse(
        company_name=request.company_name,
        insights_processed=len(request.insights),
        risk_adjustments=adjustments,
        overall_risk_delta=overall_delta,
        ai_interpretation=interpretation,
    )


def _analyze_with_llm(
    company_name: str,
    observations: str,
) -> tuple[list[RiskAdjustment], float, str]:
    """Use LLM to analyze observations and generate risk adjustments."""
    try:
        llm = get_research_llm()
        chain = INSIGHTS_PROMPT | llm

        result = chain.invoke({
            "company_name": company_name,
            "observations": observations,
        })

        content = result.content if hasattr(result, "content") else str(result)
        parsed = _parse_json(content)

        adjustments = [
            RiskAdjustment(**adj) for adj in parsed.get("adjustments", [])
        ]
        overall_delta = float(parsed.get("overall_risk_delta", 0.0))
        interpretation = parsed.get("interpretation", "")

        return adjustments, overall_delta, interpretation

    except Exception as e:
        logger.error("Primary insights LLM analysis failed: %s", e)
        return [], 0.0, f"AI analysis unavailable: {e}"


def _parse_json(text: str) -> dict:
    """Parse JSON from LLM response."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = [line for line in lines if not line.strip().startswith("```")]
        cleaned = "\n".join(lines)

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1:
        cleaned = cleaned[start : end + 1]

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {}
