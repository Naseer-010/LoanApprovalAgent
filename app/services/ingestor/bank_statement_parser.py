"""
Bank Statement Parser — extracts transaction summaries from bank statements.

Supports CSV and PDF formats. Computes credit/debit totals, average balances, patterns.
"""

import csv
import logging
import re

from app.schemas.ingestor import BankStatementSummary
from app.services.document_processing.pdf_extractor import extract_text_from_pdf

logger = logging.getLogger(__name__)


def parse_bank_statement(file_path: str) -> BankStatementSummary:
    """
    Parse bank statement from CSV or PDF.
    Auto-detects format based on file extension.
    """
    file_path_lower = file_path.lower()

    if file_path_lower.endswith(".csv"):
        return _parse_csv_statement(file_path)
    elif file_path_lower.endswith(".pdf"):
        return _parse_pdf_statement(file_path)
    else:
        logger.warning("Unsupported bank statement format: %s", file_path)
        return BankStatementSummary()


def _parse_csv_statement(file_path: str) -> BankStatementSummary:
    """Parse a bank statement CSV with columns like Date, Description, Debit, Credit, Balance."""
    credits: list[float] = []
    debits: list[float] = []
    balances: list[float] = []

    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            credit = _safe_float(
                row.get("credit", row.get("Credit", row.get("Cr", "0")))
            )
            debit = _safe_float(
                row.get("debit", row.get("Debit", row.get("Dr", "0")))
            )
            balance = _safe_float(
                row.get("balance", row.get("Balance", row.get("Bal", "0")))
            )

            if credit > 0:
                credits.append(credit)
            if debit > 0:
                debits.append(debit)
            if balance != 0:
                balances.append(balance)

    return _build_summary(credits, debits, balances)


def _parse_pdf_statement(file_path: str) -> BankStatementSummary:
    """Parse bank statement from PDF using text extraction + regex."""
    text = extract_text_from_pdf(file_path)
    credits: list[float] = []
    debits: list[float] = []
    balances: list[float] = []

    # Try to find transaction-like lines:
    # Date  Description  Debit  Credit  Balance
    # Pattern: date followed by some text and numbers
    lines = text.split("\n")
    for line in lines:
        # Look for lines with amounts (Indian format: 1,50,000.00)
        amounts = re.findall(r"([\d,]+\.?\d*)", line)
        if len(amounts) >= 2:
            # Heuristic: last amount is often balance, others are debit/credit
            try:
                values = [_safe_float(a) for a in amounts]
                if len(values) >= 3:
                    balances.append(values[-1])
                    # If the second-to-last is non-zero, treat as credit or debit
                    if values[-2] > 0:
                        credits.append(values[-2])
                    if values[-3] > 0:
                        debits.append(values[-3])
            except (ValueError, IndexError):
                continue

    return _build_summary(credits, debits, balances)


def _build_summary(
    credits: list[float],
    debits: list[float],
    balances: list[float],
) -> BankStatementSummary:
    """Build summary from extracted transaction data."""
    total_credits = sum(credits)
    total_debits = sum(debits)
    avg_balance = sum(balances) / len(balances) if balances else 0.0
    peak = max(balances) if balances else 0.0
    lowest = min(balances) if balances else 0.0

    return BankStatementSummary(
        total_credits=total_credits,
        total_debits=total_debits,
        average_balance=round(avg_balance, 2),
        peak_balance=peak,
        lowest_balance=lowest,
        credit_count=len(credits),
        debit_count=len(debits),
    )


def _safe_float(value: str | float | int) -> float:
    """Safely convert Indian-formatted numbers to float."""
    if isinstance(value, (int, float)):
        return float(value)
    try:
        cleaned = str(value).replace(",", "").replace(" ", "").strip()
        return float(cleaned) if cleaned else 0.0
    except (ValueError, TypeError):
        return 0.0
