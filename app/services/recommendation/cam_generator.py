"""
CAM Generator — generates a structured Credit Appraisal Memo.

Produces a comprehensive memo covering Company Overview, Financial Analysis,
Five Cs Assessment, Research Findings, Risk Factors, and Recommendation.
"""

import logging
from datetime import datetime

from langchain_core.prompts import ChatPromptTemplate

from app.core.llm import get_recommendation_llm
from app.schemas.recommendation import (
    CAMRequest,
    CAMSection,
    CreditAppraisalMemo,
)

logger = logging.getLogger(__name__)

CAM_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a senior credit officer at an Indian bank. Write a professional, "
        "concise narrative for a Credit Appraisal Memo section. Use formal banking "
        "language. Be specific with numbers and findings. "
        "Indian regulatory context (RBI, SEBI, MCA) is important.",
    ),
    (
        "human",
        """Write the "{section_title}" section for the Credit Appraisal Memo of {company_name}.

Available data:
{section_data}

Write 3-5 concise paragraphs. Be factual and analytical. Include specific numbers where available.
""",
    ),
])


def generate_cam(request: CAMRequest) -> CreditAppraisalMemo:
    """
    Generate a full Credit Appraisal Memo from all available data.

    Sections:
    1. Executive Summary
    2. Company Overview
    3. Financial Analysis
    4. Five Cs Assessment
    5. Secondary Research Findings
    6. Primary Due Diligence
    7. Cross-Verification Results
    8. Risk Factors
    9. Recommendation
    """
    sections: list[CAMSection] = []

    # Section definitions with their data sources
    section_configs = [
        ("Company Overview", {
            "financial_data": request.financial_data,
            "research_report": request.research_report,
        }),
        ("Financial Analysis", {
            "financial_data": request.financial_data,
            "cross_verification": request.cross_verification,
        }),
        ("Five Cs of Credit Assessment", {
            "five_cs_scores": request.five_cs_scores,
        }),
        ("Secondary Research Findings", {
            "research_report": request.research_report,
        }),
        ("Primary Due Diligence", {
            "primary_insights": request.primary_insights,
        }),
        ("Cross-Verification & Anomaly Analysis", {
            "cross_verification": request.cross_verification,
        }),
        ("Risk Factors & Mitigants", {
            "five_cs_scores": request.five_cs_scores,
            "research_report": request.research_report,
            "cross_verification": request.cross_verification,
        }),
        ("Recommendation", {
            "loan_decision": request.loan_decision,
            "five_cs_scores": request.five_cs_scores,
        }),
    ]

    for title, data in section_configs:
        content = _generate_section(request.company_name, title, data)
        sections.append(CAMSection(title=title, content=content))

    # Generate executive summary from all sections
    executive_summary = _generate_executive_summary(request, sections)

    # Extract recommendation details
    decision = request.loan_decision
    recommendation = decision.get("decision", "REFER")
    recommended_amount = decision.get("recommended_amount", 0.0)
    interest_rate = decision.get("interest_rate", 0.0)
    risk_grade = decision.get("risk_grade", "")

    return CreditAppraisalMemo(
        company_name=request.company_name,
        generated_at=datetime.now().isoformat(),
        sections=sections,
        executive_summary=executive_summary,
        recommendation=recommendation,
        risk_grade=risk_grade,
        recommended_amount=recommended_amount,
        interest_rate=interest_rate,
    )


def _generate_section(company_name: str, title: str, data: dict) -> str:
    """Generate a single CAM section using LLM."""
    try:
        llm = get_recommendation_llm()
        chain = CAM_PROMPT | llm

        import json
        section_data = json.dumps(data, indent=2, default=str)[:3000]

        result = chain.invoke({
            "company_name": company_name,
            "section_title": title,
            "section_data": section_data,
        })

        return result.content if hasattr(result, "content") else str(result)

    except Exception as e:
        logger.error("CAM section '%s' generation failed: %s", title, e)
        return f"Section generation failed: {e}. Data available: {list(data.keys())}"


def _generate_executive_summary(
    request: CAMRequest,
    sections: list[CAMSection],
) -> str:
    """Generate an executive summary from all CAM sections."""
    try:
        llm = get_recommendation_llm()

        summary_prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are a senior credit officer. Write a concise executive summary "
                "(3-4 paragraphs) for a Credit Appraisal Memo. Highlight key findings, "
                "risk assessment, and recommendation.",
            ),
            (
                "human",
                """Company: {company_name}

CAM sections:
{sections_summary}

Decision: {decision}

Write the executive summary.
""",
            ),
        ])

        sections_text = "\n\n".join(
            f"### {s.title}\n{s.content[:300]}..." for s in sections
        )

        import json
        decision_text = json.dumps(request.loan_decision, default=str)[:500]

        chain = summary_prompt | llm
        result = chain.invoke({
            "company_name": request.company_name,
            "sections_summary": sections_text[:3000],
            "decision": decision_text,
        })

        return result.content if hasattr(result, "content") else str(result)

    except Exception as e:
        logger.error("Executive summary generation failed: %s", e)
        return f"Executive summary generation failed: {e}"
