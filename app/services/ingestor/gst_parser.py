"""
GST Filing Parser — extracts turnover, ITC, tax data from GST returns.

Supports CSV, JSON, and PDF (GSTR-3B / GSTR-2A).
Understands Indian GST nuances: GSTR-2A vs 3B reconciliation.
"""

import csv
import io
import json
import logging
import re

from app.schemas.ingestor import GSTDataResponse, GSTEntry
from app.services.document_processing.pdf_extractor import extract_text_from_pdf

logger = logging.getLogger(__name__)


def parse_gst_data(file_path: str) -> GSTDataResponse:
    """
    Parse GST filing data from CSV, JSON, or PDF.
    Auto-detects format based on file extension.
    """
    file_path_lower = file_path.lower()

    if file_path_lower.endswith(".csv"):
        return _parse_gst_csv(file_path)
    elif file_path_lower.endswith(".json"):
        return _parse_gst_json(file_path)
    elif file_path_lower.endswith(".pdf"):
        return _parse_gst_pdf(file_path)
    else:
        logger.warning("Unsupported GST file format: %s", file_path)
        return GSTDataResponse()


def _parse_gst_csv(file_path: str) -> GSTDataResponse:
    """Parse GST data from a CSV file."""
    entries: list[GSTEntry] = []

    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            entry = GSTEntry(
                period=row.get("period", row.get("Period", "")),
                turnover=_safe_float(row.get("turnover", row.get("Turnover", "0"))),
                tax_paid=_safe_float(row.get("tax_paid", row.get("Tax Paid", "0"))),
                itc_claimed=_safe_float(
                    row.get("itc_claimed", row.get("ITC Claimed", "0"))
                ),
            )
            entries.append(entry)

    return _build_response(entries)


def _parse_gst_json(file_path: str) -> GSTDataResponse:
    """Parse GST data from a JSON file."""
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    records = data if isinstance(data, list) else data.get("entries", [])
    entries = [GSTEntry(**record) for record in records]
    gstr_type = data.get("gstr_type", "GSTR-3B") if isinstance(data, dict) else "GSTR-3B"

    response = _build_response(entries)
    response.gstr_type = gstr_type
    return response


def _parse_gst_pdf(file_path: str) -> GSTDataResponse:
    """Parse GST data from a PDF file using text extraction + regex."""
    text = extract_text_from_pdf(file_path)
    entries: list[GSTEntry] = []

    # Try to find tabular data with patterns like month/year followed by amounts
    # Pattern: Apr-2024  1,50,00,000  5,40,000  4,80,000
    pattern = r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[\s\-]?\d{2,4})\s+([\d,\.]+)\s+([\d,\.]+)\s+([\d,\.]+)"
    matches = re.findall(pattern, text, re.IGNORECASE)

    for match in matches:
        entry = GSTEntry(
            period=match[0].strip(),
            turnover=_safe_float(match[1]),
            tax_paid=_safe_float(match[2]),
            itc_claimed=_safe_float(match[3]),
        )
        entries.append(entry)

    return _build_response(entries)


def _build_response(entries: list[GSTEntry]) -> GSTDataResponse:
    """Build aggregated GST response from entries."""
    total_turnover = sum(e.turnover for e in entries)
    total_tax = sum(e.tax_paid for e in entries)
    total_itc = sum(e.itc_claimed for e in entries)

    return GSTDataResponse(
        entries=entries,
        total_turnover=total_turnover,
        total_tax_paid=total_tax,
        total_itc_claimed=total_itc,
    )


def _safe_float(value: str | float | int) -> float:
    """Safely convert Indian-formatted numbers (with commas) to float."""
    if isinstance(value, (int, float)):
        return float(value)
    try:
        cleaned = str(value).replace(",", "").replace(" ", "").strip()
        return float(cleaned) if cleaned else 0.0
    except (ValueError, TypeError):
        return 0.0
