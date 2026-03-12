"""
Borrowing Extractor — extracts borrowing profile data from
borrowing/debt documents.

Metrics: total borrowings, term loans, working capital limits,
lender-wise breakdown, fund vs non-fund based, utilization.
"""
import logging
import re

logger = logging.getLogger(__name__)


def extract_borrowing_metrics(text: str) -> dict:
    """
    Extract borrowing profile metrics from document text.

    Returns dict with keys:
        total_borrowings, term_loans, working_capital_limit,
        fund_based, non_fund_based, total_sanctioned,
        total_outstanding, utilization_pct,
        debt_maturity_profile, lender_breakdown,
        borrowing_summary
    """
    metrics: dict = {
        "total_borrowings": None,
        "term_loans": None,
        "working_capital_limit": None,
        "fund_based": None,
        "non_fund_based": None,
        "total_sanctioned": None,
        "total_outstanding": None,
        "utilization_pct": None,
        "debt_maturity_profile": [],
        "lender_breakdown": [],
        "borrowing_summary": "",
    }

    text_lower = text.lower()

    # ── Parse amounts helper ──
    def _find_amount(patterns: list[str]) -> float | None:
        for pat in patterns:
            m = re.search(pat, text_lower)
            if m:
                return _parse_number(m.group(1))
        return None

    # ── Total borrowings ──
    metrics["total_borrowings"] = _find_amount([
        r"total\s+(?:borrowings?|debt)[:\s]+(?:inr|rs\.?)?"
        r"\s*([\d,]+(?:\.\d+)?)",
    ])

    # ── Term loans ──
    metrics["term_loans"] = _find_amount([
        r"term\s+loan[:\s]+(?:inr|rs\.?)?\s*([\d,]+(?:\.\d+)?)",
        r"long[- ]term\s+(?:borrowings?|debt)[:\s]+"
        r"(?:inr|rs\.?)?\s*([\d,]+(?:\.\d+)?)",
    ])

    # ── Working capital ──
    metrics["working_capital_limit"] = _find_amount([
        r"working\s+capital\s+(?:limit|facility)[:\s]+"
        r"(?:inr|rs\.?)?\s*([\d,]+(?:\.\d+)?)",
        r"(?:cc|cash\s+credit)\s+limit[:\s]+"
        r"(?:inr|rs\.?)?\s*([\d,]+(?:\.\d+)?)",
    ])

    # ── Fund based / Non-fund based ──
    metrics["fund_based"] = _find_amount([
        r"fund[- ]based[:\s]+(?:inr|rs\.?)?\s*([\d,]+(?:\.\d+)?)",
    ])
    metrics["non_fund_based"] = _find_amount([
        r"non[- ]fund[- ]based[:\s]+(?:inr|rs\.?)?"
        r"\s*([\d,]+(?:\.\d+)?)",
    ])

    # ── Sanctioned / Outstanding ──
    metrics["total_sanctioned"] = _find_amount([
        r"(?:total\s+)?sanctioned\s+(?:limit)?[:\s]+"
        r"(?:inr|rs\.?)?\s*([\d,]+(?:\.\d+)?)",
    ])
    metrics["total_outstanding"] = _find_amount([
        r"(?:total\s+)?outstanding[:\s]+(?:inr|rs\.?)?"
        r"\s*([\d,]+(?:\.\d+)?)",
    ])

    # ── Utilization ──
    util = re.search(
        r"utilization[:\s]+(\d+\.?\d*)\s*%", text_lower
    )
    if util:
        metrics["utilization_pct"] = float(util.group(1))
    elif (
        metrics["total_sanctioned"]
        and metrics["total_outstanding"]
        and metrics["total_sanctioned"] > 0
    ):
        metrics["utilization_pct"] = round(
            (metrics["total_outstanding"] / metrics["total_sanctioned"])
            * 100,
            1,
        )

    # ── Debt maturity profile ──
    maturity_pattern = (
        r"(\d{4}[-–]\d{2,4}|\d{4})[:\s]+"
        r"(?:inr|rs\.?)?\s*([\d,]+(?:\.\d+)?)"
    )
    maturities = re.findall(maturity_pattern, text_lower)
    for year, amount in maturities[:10]:
        val = _parse_number(amount)
        if val and val > 0:
            metrics["debt_maturity_profile"].append(
                {"year": year.strip(), "amount": val}
            )

    # ── Lender breakdown ──
    lender_patterns = [
        r"((?:sbi|hdfc|icici|axis|bob|pnb|canara|union|"
        r"kotak|yes|idbi|bandhan|indusind|rbl|federal|"
        r"indian\s+overseas|central\s+bank|bank\s+of\s+"
        r"(?:baroda|india|maharashtra))[^:]*)[:\s]+"
        r"(?:inr|rs\.?)?\s*([\d,]+(?:\.\d+)?)",
    ]
    for pat in lender_patterns:
        matches = re.findall(pat, text_lower)
        for lender, amount in matches[:10]:
            val = _parse_number(amount)
            if val and val > 0:
                metrics["lender_breakdown"].append(
                    {"lender": lender.strip().title(), "amount": val}
                )

    # ── Summary ──
    parts = []
    if metrics["total_borrowings"]:
        parts.append(
            f"Total Borrowings: INR {metrics['total_borrowings']:,.0f}"
        )
    if metrics["utilization_pct"]:
        parts.append(f"Utilization: {metrics['utilization_pct']:.1f}%")
    if len(metrics["lender_breakdown"]) > 0:
        parts.append(f"{len(metrics['lender_breakdown'])} lenders identified")
    metrics["borrowing_summary"] = " | ".join(parts)

    return metrics


def _parse_number(text: str) -> float | None:
    """Parse comma-separated numbers."""
    if not text:
        return None
    cleaned = text.replace(",", "").replace(" ", "").strip()
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return None
