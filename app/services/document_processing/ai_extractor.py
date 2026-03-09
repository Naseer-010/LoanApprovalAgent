"""
AI-powered document extraction — gap-filler role.

Only invoked for fields not found by table/regex extraction.
Augments the standardized FinancialSchema rather than replacing it.
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
from app.services.document_processing.pdf_extractor import (
    extract_tables_from_pdf,
)
from app.services.document_processing.financial_extractor import (
    extract_financial_metrics,
    extract_financial_from_tables,
    build_financial_schema,
)

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a financial document analyst specializing in Indian corporate credit "
        "assessment. Extract structured financial data from the given document text. "
        "Only extract values that are explicitly stated in the text. "
        "Do NOT fabricate or estimate any values. "
        "Return ONLY valid JSON, no markdown fences, no extra text.",
    ),
    (
        "human",
        """Analyze the following document text and extract:
1. Financial metrics (revenue, net_profit, total_debt, ebitda, pat, equity,
   current_assets, current_liabilities, interest_expense, total_assets, net_worth,
   debt_to_equity, current_ratio, interest_coverage)
2. Key risks
3. Contingent liabilities
4. Related party transactions
5. Auditor qualifications
6. A brief summary

The following metrics have ALREADY been extracted by other methods.
Only fill in metrics that are MISSING (null) from this list:
{already_extracted}

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
    "pat": null,
    "equity": null,
    "current_assets": null,
    "current_liabilities": null,
    "interest_expense": null,
    "total_assets": null,
    "net_worth": null,
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


def extract_with_ai(
    document_text: str,
    file_name: str = "",
    file_path: str | None = None,
) -> DocumentAnalysisResponse:
    """
    Hybrid AI extraction:
      1. Run rule-based extraction first (text regex + tables)
      2. Use LLM to fill gaps and extract qualitative data (risks, summary)
      3. Merge all results into the response

    Falls back to rule-based-only results if LLM fails.
    """
    # Step 1: Rule-based extraction
    text_metrics = extract_financial_metrics(document_text)

    table_metrics = {}
    if file_path:
        try:
            tables = extract_tables_from_pdf(file_path)
            table_metrics = extract_financial_from_tables(tables)
        except Exception as e:
            logger.warning("Table extraction failed: %s", e)

    # Merge rule-based results
    schema = build_financial_schema(
        text_metrics=text_metrics,
        table_metrics=table_metrics,
    )
    rule_based = schema.to_dict()

    # Step 2: LLM gap-filling + qualitative extraction
    ai_financials = {}
    risks = ExtractedRisks()
    summary = ""

    try:
        llm = get_ingestor_llm()
        chain = EXTRACTION_PROMPT | llm

        # Tell the LLM what we already have
        already_extracted = json.dumps(rule_based, indent=2)

        truncated_text = document_text[:4000]
        result = chain.invoke({
            "document_text": truncated_text,
            "already_extracted": already_extracted,
        })

        content = result.content if hasattr(result, "content") else str(result)
        parsed = _parse_json_response(content)

        # Extract qualitative data
        risks = ExtractedRisks(**(parsed.get("risks", {})))
        summary = parsed.get("summary", "")

        # Extract financial gaps from AI
        ai_raw = parsed.get("financials", {})
        ai_financials = {
            k: v for k, v in ai_raw.items()
            if v is not None and k not in rule_based
        }

    except Exception as e:
        logger.error("AI extraction failed: %s", e)
        summary = f"AI extraction failed (rule-based results available): {e}"

    # Step 3: Merge all - rebuild schema with AI gaps filled
    final_schema = build_financial_schema(
        text_metrics=text_metrics,
        table_metrics=table_metrics,
        ai_metrics=ai_financials,
    )
    final_metrics = final_schema.to_dict()

    # Build ExtractedFinancials from merged data
    financials = ExtractedFinancials(
        revenue=final_metrics.get("revenue"),
        net_profit=final_metrics.get("net_profit"),
        total_debt=final_metrics.get("total_debt"),
        ebitda=final_metrics.get("ebitda"),
        debt_to_equity=final_metrics.get("debt_to_equity"),
        current_ratio=final_metrics.get("current_ratio"),
        interest_coverage=final_metrics.get("interest_coverage"),
    )

    return DocumentAnalysisResponse(
        file_name=file_name,
        document_type="annual_report",
        text_length=len(document_text),
        financials=financials,
        risks=risks,
        summary=summary,
        raw_metrics={
            "rule_based": rule_based,
            "ai_gap_fills": ai_financials,
            "sources": ["table", "regex", "ai"],
        },
    )


def _parse_json_response(text: str) -> dict:
    """Attempt to parse JSON from LLM response, handling common formatting issues."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines)

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1:
        cleaned = cleaned[start : end + 1]

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("Could not parse LLM JSON response")
        return {}
