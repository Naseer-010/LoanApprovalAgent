"""
Five Cs of Credit Scorer — scores Character, Capacity, Capital, Collateral, Conditions.

Uses a combination of financial ratios, research findings, and LLM reasoning
to produce explainable scores for each C (0-100).
"""

import json
import logging

from langchain_core.prompts import ChatPromptTemplate

from app.core.llm import get_recommendation_llm
from app.schemas.recommendation import CreditCScore, FiveCsScoreRequest, FiveCsScoreResponse

logger = logging.getLogger(__name__)

SCORING_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a senior credit risk analyst for an Indian corporate bank. "
        "Score each of the Five Cs of Credit (Character, Capacity, Capital, Collateral, "
        "Conditions) on a scale of 0-100 based on the provided data. "
        "Provide clear explanations and supporting evidence for each score. "
        "Return ONLY valid JSON, no markdown fences.",
    ),
    (
        "human",
        """Score the Five Cs for: {company_name}

Financial Data:
{financial_data}

Research Findings:
{research_data}

Primary Insights (field observations):
{primary_insights}

Cross-Verification Results:
{cross_verification}

Score each C (0-100) and provide explanation + evidence.

Respond with this JSON:
{{
  "scores": [
    {{
      "category": "Character",
      "score": 0,
      "explanation": "",
      "supporting_evidence": []
    }},
    {{
      "category": "Capacity",
      "score": 0,
      "explanation": "",
      "supporting_evidence": []
    }},
    {{
      "category": "Capital",
      "score": 0,
      "explanation": "",
      "supporting_evidence": []
    }},
    {{
      "category": "Collateral",
      "score": 0,
      "explanation": "",
      "supporting_evidence": []
    }},
    {{
      "category": "Conditions",
      "score": 0,
      "explanation": "",
      "supporting_evidence": []
    }}
  ],
  "commentary": "overall assessment"
}}
""",
    ),
])

# Default weights for the Five Cs
FIVE_CS_WEIGHTS = {
    "Character": 0.20,
    "Capacity": 0.30,
    "Capital": 0.20,
    "Collateral": 0.15,
    "Conditions": 0.15,
}


def score_five_cs(request: FiveCsScoreRequest) -> FiveCsScoreResponse:
    """
    Score a company on the Five Cs of Credit.

    Combines LLM reasoning with rule-based baseline scoring.
    """
    # Generate baseline scores from financial data
    baseline_scores = _compute_baseline_scores(request.financial_data)

    # Get LLM-generated scores
    llm_scores, commentary = _llm_score(request)

    # Merge: use LLM scores if available, fall back to baseline
    final_scores = _merge_scores(baseline_scores, llm_scores)

    # Calculate weighted total
    weighted_total = sum(
        score.score * FIVE_CS_WEIGHTS.get(score.category, 0.2)
        for score in final_scores
    )

    # Determine risk grade
    risk_grade = _risk_grade_from_score(weighted_total)

    return FiveCsScoreResponse(
        company_name=request.company_name,
        scores=final_scores,
        weighted_total=round(weighted_total, 2),
        risk_grade=risk_grade,
        ai_commentary=commentary,
    )


def _compute_baseline_scores(financial_data: dict) -> dict[str, float]:
    """Compute baseline scores from financial ratios."""
    scores: dict[str, float] = {}

    # Capacity — based on debt-to-equity and interest coverage
    dte = financial_data.get("debt_to_equity")
    icr = financial_data.get("interest_coverage")
    capacity = 50.0
    if dte is not None:
        if dte < 1.0:
            capacity += 20
        elif dte < 2.0:
            capacity += 10
        elif dte > 3.0:
            capacity -= 15
    if icr is not None:
        if icr > 3.0:
            capacity += 15
        elif icr > 1.5:
            capacity += 5
        elif icr < 1.0:
            capacity -= 20
    scores["Capacity"] = max(0, min(100, capacity))

    # Capital — based on revenue and EBITDA
    revenue = financial_data.get("revenue")
    ebitda = financial_data.get("ebitda")
    capital = 50.0
    if revenue and ebitda and revenue > 0:
        margin = ebitda / revenue
        if margin > 0.2:
            capital += 20
        elif margin > 0.1:
            capital += 10
        elif margin < 0.05:
            capital -= 15
    scores["Capital"] = max(0, min(100, capital))

    # Default scores for others (LLM fills these in)
    scores.setdefault("Character", 50.0)
    scores.setdefault("Collateral", 50.0)
    scores.setdefault("Conditions", 50.0)

    return scores


def _llm_score(
    request: FiveCsScoreRequest,
) -> tuple[list[CreditCScore], str]:
    """Use LLM to score the Five Cs with explanations."""
    try:
        llm = get_recommendation_llm()
        chain = SCORING_PROMPT | llm

        result = chain.invoke({
            "company_name": request.company_name,
            "financial_data": json.dumps(request.financial_data, indent=2)[:1500],
            "research_data": json.dumps(request.research_data, indent=2)[:1500],
            "primary_insights": json.dumps(request.primary_insights, indent=2)[:1000],
            "cross_verification": json.dumps(request.cross_verification, indent=2)[:1000],
        })

        content = result.content if hasattr(result, "content") else str(result)
        parsed = _parse_json(content)

        scores = []
        for s in parsed.get("scores", []):
            scores.append(
                CreditCScore(
                    category=s.get("category", ""),
                    score=float(s.get("score", 0)),
                    weight=FIVE_CS_WEIGHTS.get(s.get("category", ""), 0.2),
                    explanation=s.get("explanation", ""),
                    supporting_evidence=s.get("supporting_evidence", []),
                )
            )

        commentary = parsed.get("commentary", "")
        return scores, commentary

    except Exception as e:
        logger.error("Five Cs LLM scoring failed: %s", e)
        return [], f"AI scoring unavailable: {e}"


def _merge_scores(
    baseline: dict[str, float],
    llm_scores: list[CreditCScore],
) -> list[CreditCScore]:
    """Merge LLM scores with baseline, preferring LLM where available."""
    if llm_scores:
        return llm_scores

    # Fall back to baseline
    return [
        CreditCScore(
            category=cat,
            score=score,
            weight=FIVE_CS_WEIGHTS.get(cat, 0.2),
            explanation="Computed from financial ratios (AI unavailable).",
        )
        for cat, score in baseline.items()
    ]


def _risk_grade_from_score(score: float) -> str:
    """Map weighted score to a risk grade."""
    if score >= 85:
        return "AAA"
    if score >= 75:
        return "AA"
    if score >= 65:
        return "A"
    if score >= 55:
        return "BBB"
    if score >= 45:
        return "BB"
    if score >= 35:
        return "B"
    if score >= 25:
        return "C"
    return "D"


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
