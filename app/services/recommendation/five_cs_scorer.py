"""
Five Cs of Credit Scorer — computed from real financial inputs.

Character → promoter risk + litigation risk (from research)
Capacity → DSCR + ICR (from financial ratios)
Capital → net worth + leverage ratio (from financials)
Collateral → asset coverage ratio (from financials)
Conditions → sector risk + macro signals (from research)

LLM is optional enhancement for explanations, not the primary scorer.
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
        "Review the Five Cs scores computed below and provide explanations and "
        "supporting evidence for each. The scores have already been computed — "
        "your role is to explain them and add context. "
        "Return ONLY valid JSON, no markdown fences.",
    ),
    (
        "human",
        """Review and explain the Five Cs scores for: {company_name}

Computed Scores:
{computed_scores}

Financial Data: {financial_data}
Research Data: {research_data}

For each C, provide an explanation and supporting evidence.
Respond with:
{{
  "explanations": {{
    "Character": {{"explanation": "", "evidence": []}},
    "Capacity": {{"explanation": "", "evidence": []}},
    "Capital": {{"explanation": "", "evidence": []}},
    "Collateral": {{"explanation": "", "evidence": []}},
    "Conditions": {{"explanation": "", "evidence": []}}
  }},
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

    Primary scoring is from real inputs (financial ratios, research signals).
    LLM provides explanations (optional enhancement).
    """
    # Compute scores from real data
    baseline_scores = _compute_real_scores(
        request.financial_data,
        request.research_data,
        request.primary_insights,
        request.cross_verification,
    )

    # Get LLM explanations (optional)
    explanations, commentary = _get_explanations(request, baseline_scores)

    # Build final scores with explanations
    final_scores = []
    for category, score in baseline_scores.items():
        exp_data = explanations.get(category, {})
        final_scores.append(
            CreditCScore(
                category=category,
                score=score,
                weight=FIVE_CS_WEIGHTS.get(category, 0.2),
                explanation=exp_data.get(
                    "explanation",
                    _default_explanation(category, score, request.financial_data),
                ),
                supporting_evidence=exp_data.get("evidence", []),
            )
        )

    # Calculate weighted total
    weighted_total = sum(
        score.score * score.weight for score in final_scores
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


def _compute_real_scores(
    financial_data: dict,
    research_data: dict,
    primary_insights: dict,
    cross_verification: dict,
) -> dict[str, float]:
    """
    Compute Five Cs scores from real inputs.

    Character → promoter risk + litigation risk
    Capacity → DSCR + ICR
    Capital → net worth + leverage
    Collateral → asset coverage
    Conditions → sector + macro signals
    """
    scores: dict[str, float] = {}

    # ── CHARACTER: Promoter + Litigation Risk ──
    character = 60.0  # neutral baseline

    # Research-based signals
    risk_signals = research_data.get("risk_signals", {})
    lit_risk = risk_signals.get("litigation_risk", 0.0)
    rep_risk = risk_signals.get("reputation_risk", 0.0)

    character -= lit_risk * 30  # high litigation reduces character
    character -= rep_risk * 20  # bad reputation reduces character

    # Promoter data
    promoter_findings = research_data.get("promoter_findings", [])
    if promoter_findings:
        neg_count = sum(
            1 for f in promoter_findings
            if any(w in f.lower() for w in ["fraud", "default", "arrest", "litigation"])
        )
        character -= neg_count * 10

    # Primary insights about management
    insights = primary_insights.get("risk_adjustments", [])
    for adj in insights:
        if isinstance(adj, dict):
            delta = adj.get("adjustment", 0)
            if isinstance(delta, (int, float)):
                character += delta * 10

    scores["Character"] = max(0, min(100, character))

    # ── CAPACITY: DSCR + ICR ──
    capacity = 50.0

    dscr = financial_data.get("dscr")
    icr = financial_data.get("interest_coverage") or financial_data.get("icr")
    dte = financial_data.get("debt_to_equity")

    if dscr is not None:
        if dscr >= 2.0:
            capacity += 25
        elif dscr >= 1.5:
            capacity += 15
        elif dscr >= 1.25:
            capacity += 5
        elif dscr >= 1.0:
            capacity -= 5
        else:
            capacity -= 25

    if icr is not None:
        if icr >= 3.0:
            capacity += 20
        elif icr >= 2.0:
            capacity += 10
        elif icr >= 1.5:
            capacity += 5
        elif icr < 1.0:
            capacity -= 20

    if dte is not None:
        if dte < 1.0:
            capacity += 5
        elif dte > 3.0:
            capacity -= 10
        elif dte > 5.0:
            capacity -= 20

    scores["Capacity"] = max(0, min(100, capacity))

    # ── CAPITAL: Net Worth + Leverage ──
    capital = 50.0

    revenue = financial_data.get("revenue")
    ebitda = financial_data.get("ebitda")
    net_worth = financial_data.get("net_worth") or financial_data.get("equity")
    total_debt = financial_data.get("total_debt")

    if revenue and ebitda and revenue > 0:
        margin = ebitda / revenue
        if margin > 0.25:
            capital += 25
        elif margin > 0.15:
            capital += 15
        elif margin > 0.10:
            capital += 5
        elif margin < 0.05:
            capital -= 15

    if net_worth and total_debt:
        if net_worth > total_debt:
            capital += 15
        elif net_worth > total_debt * 0.5:
            capital += 5
        else:
            capital -= 10

    revenue_growth = financial_data.get("revenue_growth")
    if revenue_growth is not None:
        if revenue_growth > 0.15:
            capital += 10
        elif revenue_growth > 0.05:
            capital += 5
        elif revenue_growth < -0.1:
            capital -= 15

    scores["Capital"] = max(0, min(100, capital))

    # ── COLLATERAL: Asset Coverage ──
    collateral = 50.0

    current_assets = financial_data.get("current_assets")
    current_liabilities = financial_data.get("current_liabilities")
    total_assets = financial_data.get("total_assets")

    current_ratio = financial_data.get("current_ratio")
    if current_ratio is None and current_assets and current_liabilities:
        current_ratio = current_assets / current_liabilities if current_liabilities > 0 else None

    if current_ratio is not None:
        if current_ratio >= 2.0:
            collateral += 25
        elif current_ratio >= 1.5:
            collateral += 15
        elif current_ratio >= 1.2:
            collateral += 5
        elif current_ratio < 1.0:
            collateral -= 20

    if total_assets and total_debt and total_debt > 0:
        asset_coverage = total_assets / total_debt
        if asset_coverage >= 3.0:
            collateral += 15
        elif asset_coverage >= 2.0:
            collateral += 5
        elif asset_coverage < 1.0:
            collateral -= 15

    scores["Collateral"] = max(0, min(100, collateral))

    # ── CONDITIONS: Sector + Macro ──
    conditions = 55.0  # slightly positive neutral

    sector_risk = risk_signals.get("sector_risk", 0.0)
    reg_risk = risk_signals.get("regulatory_risk", 0.0)

    conditions -= sector_risk * 25
    conditions -= reg_risk * 20

    # Cross-verification risk
    cv_risk = cross_verification.get("risk_level", "low")
    if cv_risk == "critical":
        conditions -= 20
    elif cv_risk == "high":
        conditions -= 10
    elif cv_risk == "medium":
        conditions -= 5

    # Overall research sentiment
    sentiment = research_data.get("overall_sentiment", "neutral")
    if sentiment == "negative":
        conditions -= 10
    elif sentiment == "positive":
        conditions += 10

    scores["Conditions"] = max(0, min(100, conditions))

    return scores


def _default_explanation(category: str, score: float, fin: dict) -> str:
    """Generate a default explanation when LLM is unavailable."""
    explanations = {
        "Character": f"Promoter and management character score of {score:.0f}/100, derived from litigation, reputation, and research signals.",
        "Capacity": f"Debt servicing capacity score of {score:.0f}/100, based on DSCR ({fin.get('dscr', 'N/A')}), ICR ({fin.get('interest_coverage', 'N/A')}), and leverage.",
        "Capital": f"Capital adequacy score of {score:.0f}/100, based on EBITDA margins, net worth, and revenue trends.",
        "Collateral": f"Collateral coverage score of {score:.0f}/100, based on current ratio ({fin.get('current_ratio', 'N/A')}) and asset coverage.",
        "Conditions": f"Market and sector conditions score of {score:.0f}/100, based on sector outlook and regulatory environment.",
    }
    return explanations.get(category, f"Score: {score:.0f}/100")


def _get_explanations(
    request: FiveCsScoreRequest,
    scores: dict[str, float],
) -> tuple[dict, str]:
    """Get LLM-generated explanations for the computed scores."""
    try:
        llm = get_recommendation_llm()
        chain = SCORING_PROMPT | llm

        result = chain.invoke({
            "company_name": request.company_name,
            "computed_scores": json.dumps(scores, indent=2),
            "financial_data": json.dumps(request.financial_data, indent=2)[:1500],
            "research_data": json.dumps(request.research_data, indent=2)[:1500],
        })

        content = result.content if hasattr(result, "content") else str(result)
        parsed = _parse_json(content)

        explanations = parsed.get("explanations", {})
        commentary = parsed.get("commentary", "")
        return explanations, commentary

    except Exception as e:
        logger.error("Five Cs LLM explanations failed: %s", e)
        return {}, f"AI explanations unavailable: {e}"


def _risk_grade_from_score(score: float) -> str:
    """Map weighted score to a risk grade."""
    if score >= 85: return "AAA"
    if score >= 75: return "AA"
    if score >= 65: return "A"
    if score >= 55: return "BBB"
    if score >= 45: return "BB"
    if score >= 35: return "B"
    if score >= 25: return "C"
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
