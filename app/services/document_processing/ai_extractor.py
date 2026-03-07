"""
AI-powered document extraction using LangChain + HuggingFace LLM.

Extracts structured financial data, risk factors, and summaries from raw document text.
"""

import json
import logging

from langchain_core.prompts import ChatPromptTemplate

from app.core.llm import get_ingestor_llm
from app.schemas.ingestor import (
    DocumentAnalysisResponse,
    ExtractedFinancials,
    ExtractedRisks,
)

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a financial document analyst specializing in Indian corporate credit "
        "assessment. Extract structured financial data from the given document text. "
        "Return ONLY valid JSON, no markdown fences, no extra text.",
    ),
    (
        "human",
        """Analyze the following document text and extract:
1. Financial metrics (revenue, net_profit, total_debt, ebitda, debt_to_equity, current_ratio, interest_coverage)
2. Key risks
3. Contingent liabilities
4. Related party transactions
5. Auditor qualifications
6. A brief summary

Document text (truncated to first 4000 chars):
---
{document_text}
---

Respond with this exact JSON structure:
{{
  "financials": {{
    "revenue": null,
    "net_profit": null,
    "total_debt": null,
    "ebitda": null,
    "debt_to_equity": null,
    "current_ratio": null,
    "interest_coverage": null
  }},
  "risks": {{
    "key_risks": [],
    "contingent_liabilities": [],
    "related_party_transactions": [],
    "auditor_qualifications": []
  }},
  "summary": ""
}}
""",
    ),
])


def extract_with_ai(document_text: str, file_name: str = "") -> DocumentAnalysisResponse:
    """
    Use LLM to extract structured data from raw document text.

    Falls back to empty results if LLM fails or returns invalid JSON.
    """
    try:
        llm = get_ingestor_llm()
        chain = EXTRACTION_PROMPT | llm

        # Truncate to avoid token limits
        truncated_text = document_text[:4000]
        result = chain.invoke({"document_text": truncated_text})

        # Parse LLM output
        content = result.content if hasattr(result, "content") else str(result)

        # Try to extract JSON from the response
        parsed = _parse_json_response(content)

        financials = ExtractedFinancials(**(parsed.get("financials", {})))
        risks = ExtractedRisks(**(parsed.get("risks", {})))
        summary = parsed.get("summary", "")

        return DocumentAnalysisResponse(
            file_name=file_name,
            document_type="annual_report",
            text_length=len(document_text),
            financials=financials,
            risks=risks,
            summary=summary,
        )

    except Exception as e:
        logger.error("AI extraction failed: %s", e)
        return DocumentAnalysisResponse(
            file_name=file_name,
            text_length=len(document_text),
            summary=f"AI extraction failed: {e}",
        )


def _parse_json_response(text: str) -> dict:
    """Attempt to parse JSON from LLM response, handling common formatting issues."""
    # Strip markdown code fences if present
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines)

    # Find the first { and last }
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1:
        cleaned = cleaned[start : end + 1]

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("Could not parse LLM JSON response")
        return {}
