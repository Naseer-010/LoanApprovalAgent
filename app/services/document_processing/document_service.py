"""
Document Service — hybrid extraction pipeline.

Pipeline: PDF → Text + Table extraction → Financial structuring → AI augmentation.
Tables get priority over text regex. AI fills gaps only when rule-based methods miss data.
"""

import logging

from app.services.document_processing.pdf_extractor import (
    extract_text_from_pdf,
    extract_tables_from_pdf,
)
from app.services.document_processing.financial_extractor import (
    extract_financial_metrics,
    extract_financial_from_tables,
    build_financial_schema,
)

logger = logging.getLogger(__name__)


def process_financial_document(file_path: str) -> dict:
    """
    Hybrid extraction pipeline:
      1. Extract raw text from PDF
      2. Extract tables from PDF
      3. Run regex extraction on text
      4. Run table-based extraction
      5. Merge into standardized schema (table > text priority)

    Returns dict with text_length, financial_metrics, tables_found, and extraction_sources.
    """
    # Step 1: Extract text
    text = extract_text_from_pdf(file_path)

    # Step 2: Extract tables
    tables = extract_tables_from_pdf(file_path)

    # Step 3: Regex-based extraction
    text_metrics = extract_financial_metrics(text)

    # Step 4: Table-based extraction
    table_metrics = extract_financial_from_tables(tables)

    # Step 5: Build merged schema
    schema = build_financial_schema(
        text_metrics=text_metrics,
        table_metrics=table_metrics,
    )

    sources = []
    if table_metrics:
        sources.append("table_extraction")
    if text_metrics:
        sources.append("text_regex")

    return {
        "text_length": len(text),
        "tables_found": len(tables),
        "financial_metrics": schema.to_dict(),
        "extraction_sources": sources,
        "raw_text_metrics": text_metrics,
        "raw_table_metrics": table_metrics,
    }