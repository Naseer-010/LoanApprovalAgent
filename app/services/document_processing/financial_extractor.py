"""
Financial Extractor — structured extraction from text + tables.

Extracts key financial metrics using regex patterns, table parsing,
and Indian number format handling (lakhs/crores). Produces a
standardized financial schema.
"""

import logging
import re
from dataclasses import dataclass, field, asdict

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class FinancialSchema:
    """Standardized financial data extracted from documents."""
    revenue: float | None = None
    ebitda: float | None = None
    pat: float | None = None  # Profit After Tax
    net_profit: float | None = None
    total_debt: float | None = None
    equity: float | None = None
    current_assets: float | None = None
    current_liabilities: float | None = None
    interest_expense: float | None = None
    total_assets: float | None = None
    net_worth: float | None = None
    # Computed ratios
    debt_to_equity: float | None = None
    current_ratio: float | None = None
    interest_coverage: float | None = None
    ebitda_margin: float | None = None
    revenue_growth: float | None = None

    def compute_ratios(self):
        """Compute derived ratios from available data."""
        if self.equity and self.equity > 0 and self.total_debt is not None:
            self.debt_to_equity = round(self.total_debt / self.equity, 2)

        if self.current_liabilities and self.current_liabilities > 0 and self.current_assets:
            self.current_ratio = round(
                self.current_assets / self.current_liabilities, 2,
            )

        if self.interest_expense and self.interest_expense > 0 and self.ebitda:
            self.interest_coverage = round(
                self.ebitda / self.interest_expense, 2,
            )

        if self.revenue and self.revenue > 0 and self.ebitda:
            self.ebitda_margin = round(
                (self.ebitda / self.revenue) * 100, 2,
            )

    def to_dict(self) -> dict:
        """Return non-None fields as a dictionary."""
        self.compute_ratios()
        return {k: v for k, v in asdict(self).items() if v is not None}


# ── Regex patterns for text-based extraction ─────────────

METRIC_PATTERNS: dict[str, list[str]] = {
    "revenue": [
        r"(?:total\s+)?revenue(?:\s+from\s+operations)?\s*[:\-]?\s*₹?\$?\s*([\d,\.]+)\s*(?:cr(?:ore)?|lakh|mn|million|billion)?",
        r"turnover\s*[:\-]?\s*₹?\$?\s*([\d,\.]+)",
        r"net\s+sales\s*[:\-]?\s*₹?\$?\s*([\d,\.]+)",
        r"total\s+income\s*[:\-]?\s*₹?\$?\s*([\d,\.]+)",
    ],
    "ebitda": [
        r"ebitda\s*[:\-]?\s*₹?\$?\s*([\d,\.]+)",
        r"operating\s+profit\s*[:\-]?\s*₹?\$?\s*([\d,\.]+)",
        r"earnings\s+before\s+interest.*?[:\-]?\s*₹?\$?\s*([\d,\.]+)",
    ],
    "pat": [
        r"(?:profit|earnings?)\s+after\s+tax\s*[:\-]?\s*₹?\$?\s*([\d,\.]+)",
        r"pat\s*[:\-]?\s*₹?\$?\s*([\d,\.]+)",
    ],
    "net_profit": [
        r"net\s+(?:profit|income)\s*[:\-]?\s*₹?\$?\s*([\d,\.]+)",
    ],
    "total_debt": [
        r"total\s+(?:debt|borrowings?)\s*[:\-]?\s*₹?\$?\s*([\d,\.]+)",
        r"(?:long[\s\-]*term|short[\s\-]*term)\s+(?:debt|borrowings?)\s*[:\-]?\s*₹?\$?\s*([\d,\.]+)",
    ],
    "equity": [
        r"(?:total\s+)?(?:shareholders?['\s]*|share\s+)?equity\s*[:\-]?\s*₹?\$?\s*([\d,\.]+)",
        r"net\s+worth\s*[:\-]?\s*₹?\$?\s*([\d,\.]+)",
    ],
    "current_assets": [
        r"(?:total\s+)?current\s+assets\s*[:\-]?\s*₹?\$?\s*([\d,\.]+)",
    ],
    "current_liabilities": [
        r"(?:total\s+)?current\s+liabilities\s*[:\-]?\s*₹?\$?\s*([\d,\.]+)",
    ],
    "interest_expense": [
        r"(?:interest|finance)\s+(?:expense|cost|charges?)\s*[:\-]?\s*₹?\$?\s*([\d,\.]+)",
    ],
    "total_assets": [
        r"total\s+assets\s*[:\-]?\s*₹?\$?\s*([\d,\.]+)",
    ],
}

# Labels commonly found in financial statement tables
TABLE_LABEL_MAP: dict[str, str] = {
    "revenue from operations": "revenue",
    "total revenue": "revenue",
    "net sales": "revenue",
    "total income": "revenue",
    "turnover": "revenue",
    "ebitda": "ebitda",
    "operating profit": "ebitda",
    "profit after tax": "pat",
    "pat": "pat",
    "net profit": "net_profit",
    "net income": "net_profit",
    "total debt": "total_debt",
    "total borrowings": "total_debt",
    "long term borrowings": "total_debt",
    "shareholders equity": "equity",
    "shareholders' equity": "equity",
    "total equity": "equity",
    "net worth": "net_worth",
    "current assets": "current_assets",
    "total current assets": "current_assets",
    "current liabilities": "current_liabilities",
    "total current liabilities": "current_liabilities",
    "interest expense": "interest_expense",
    "finance costs": "interest_expense",
    "finance cost": "interest_expense",
    "interest and finance charges": "interest_expense",
    "total assets": "total_assets",
}


def extract_financial_metrics(text: str) -> dict:
    """
    Extract financial metrics from raw text using regex patterns.
    Returns a dictionary of found metrics.
    """
    results = {}

    for metric, patterns in METRIC_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = _parse_indian_number(match.group(1))
                if value is not None and value > 0:
                    results[metric] = value
                    break

    return results


def extract_financial_from_tables(
    tables: list[list[list[str]]],
) -> dict:
    """
    Extract financial metrics from pre-extracted tables.

    Searches table rows for known financial labels and extracts
    the corresponding numeric values.
    """
    results = {}

    for table in tables:
        if len(table) < 2:
            continue

        for row in table:
            if not row:
                continue
            # First non-empty cell is usually the label
            label = str(row[0]).strip().lower()
            label = re.sub(r"[^a-z\s\']", "", label).strip()

            if label in TABLE_LABEL_MAP:
                metric_name = TABLE_LABEL_MAP[label]
                # Try to find a numeric value in remaining cells
                for cell in row[1:]:
                    value = _parse_indian_number(str(cell))
                    if value is not None and value > 0:
                        # Take the first (most recent year) value
                        if metric_name not in results:
                            results[metric_name] = value
                        break

    return results


def build_financial_schema(
    text_metrics: dict,
    table_metrics: dict,
    ai_metrics: dict | None = None,
) -> FinancialSchema:
    """
    Build a standardized FinancialSchema by merging metrics from
    multiple sources. Priority: table > text > AI.
    """
    schema = FinancialSchema()

    # Layer 1: AI metrics (lowest priority)
    if ai_metrics:
        _apply_metrics(schema, ai_metrics)

    # Layer 2: Text regex metrics
    _apply_metrics(schema, text_metrics)

    # Layer 3: Table-extracted metrics (highest priority)
    _apply_metrics(schema, table_metrics)

    # Compute derived ratios
    schema.compute_ratios()

    # net_profit fallback to pat
    if schema.net_profit is None and schema.pat is not None:
        schema.net_profit = schema.pat

    # net_worth fallback to equity
    if schema.net_worth is None and schema.equity is not None:
        schema.net_worth = schema.equity
    elif schema.equity is None and schema.net_worth is not None:
        schema.equity = schema.net_worth

    return schema


def _apply_metrics(schema: FinancialSchema, metrics: dict) -> None:
    """Apply metrics dict to schema, only overwriting if value is non-None."""
    for key, value in metrics.items():
        if value is not None and hasattr(schema, key):
            setattr(schema, key, value)


def _parse_indian_number(text: str) -> float | None:
    """
    Parse Indian-formatted numbers.

    Handles:
    - Comma-separated: 1,50,00,000
    - Decimal: 150.50
    - Crore/Lakh suffixes: 150 Cr, 2.5 Lakh
    """
    if not text:
        return None

    text = text.strip()

    # Remove currency symbols
    text = re.sub(r"[₹$€£]", "", text).strip()

    if not text:
        return None

    # Check for crore/lakh suffix
    multiplier = 1.0
    cr_match = re.search(r"([\d,\.]+)\s*(?:cr(?:ore)?s?)", text, re.IGNORECASE)
    lakh_match = re.search(r"([\d,\.]+)\s*(?:lakh|lac)s?", text, re.IGNORECASE)
    mn_match = re.search(r"([\d,\.]+)\s*(?:mn|million)s?", text, re.IGNORECASE)
    bn_match = re.search(r"([\d,\.]+)\s*(?:bn|billion)s?", text, re.IGNORECASE)

    if cr_match:
        text = cr_match.group(1)
        multiplier = 10_000_000  # 1 crore = 10 million
    elif lakh_match:
        text = lakh_match.group(1)
        multiplier = 100_000
    elif mn_match:
        text = mn_match.group(1)
        multiplier = 1_000_000
    elif bn_match:
        text = bn_match.group(1)
        multiplier = 1_000_000_000

    # Remove commas and spaces
    cleaned = text.replace(",", "").replace(" ", "").strip()

    # Handle parentheses for negatives: (123) -> -123
    neg = False
    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = cleaned[1:-1]
        neg = True

    try:
        value = float(cleaned) * multiplier
        return -value if neg else value
    except (ValueError, TypeError):
        return None