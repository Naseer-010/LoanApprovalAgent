"""
ALM Extractor — extracts key metrics from Asset Liability
Management documents.

Metrics: maturity profile, liquidity gap, interest rate
sensitivity, repricing buckets, duration gaps.
"""
import logging
import re

logger = logging.getLogger(__name__)


def extract_alm_metrics(text: str) -> dict:
    """
    Extract ALM metrics from document text.

    Returns dict with keys:
        maturity_buckets, liquidity_gap, interest_rate_sensitivity,
        repricing_gap, total_assets, total_liabilities,
        duration_gap, structural_liquidity_summary
    """
    metrics: dict = {
        "maturity_buckets": [],
        "liquidity_gap": None,
        "liquidity_gap_percentage": None,
        "interest_rate_sensitivity": None,
        "repricing_gap": None,
        "total_assets": None,
        "total_liabilities": None,
        "duration_gap": None,
        "structural_liquidity_summary": "",
    }

    text_lower = text.lower()

    # ── Maturity buckets ──
    bucket_patterns = [
        r"(\d+[-–]\d+)\s*(?:days?|months?|years?)[:\s]+"
        r"(?:inr|rs\.?)?\s*([\d,]+(?:\.\d+)?)",
        r"(up\s+to\s+\d+\s*(?:days?|months?))[:\s]+"
        r"(?:inr|rs\.?)?\s*([\d,]+(?:\.\d+)?)",
        r"(over\s+\d+\s*(?:years?|months?))[:\s]+"
        r"(?:inr|rs\.?)?\s*([\d,]+(?:\.\d+)?)",
    ]
    for pat in bucket_patterns:
        matches = re.findall(pat, text_lower)
        for bucket, amount in matches:
            val = _parse_number(amount)
            if val is not None:
                metrics["maturity_buckets"].append(
                    {"bucket": bucket.strip(), "amount": val}
                )

    # ── Liquidity gap ──
    gap_patterns = [
        r"(?:cumulative\s+)?liquidity\s+gap[:\s]+(?:inr|rs\.?)?"
        r"\s*(-?[\d,]+(?:\.\d+)?)",
        r"(?:net\s+)?(?:liquidity|funding)\s+gap[:\s]+"
        r"(?:inr|rs\.?)?\s*(-?[\d,]+(?:\.\d+)?)",
    ]
    for pat in gap_patterns:
        m = re.search(pat, text_lower)
        if m:
            metrics["liquidity_gap"] = _parse_number(m.group(1))
            break

    # ── Liquidity gap percentage ──
    gap_pct = re.search(
        r"liquidity\s+gap[:\s]+.*?(-?\d+\.?\d*)\s*%", text_lower
    )
    if gap_pct:
        metrics["liquidity_gap_percentage"] = float(gap_pct.group(1))

    # ── Interest rate sensitivity ──
    irs_patterns = [
        r"interest\s+rate\s+sensitivity[:\s]+(-?\d+\.?\d*)\s*%",
        r"(?:nii|net\s+interest\s+income)\s+impact[:\s]+"
        r"(-?\d+\.?\d*)\s*%",
        r"impact\s+on\s+(?:nii|earnings?)[:\s]+(-?\d+\.?\d*)\s*%",
    ]
    for pat in irs_patterns:
        m = re.search(pat, text_lower)
        if m:
            metrics["interest_rate_sensitivity"] = float(m.group(1))
            break

    # ── Repricing gap ──
    rg = re.search(
        r"repricing\s+gap[:\s]+(?:inr|rs\.?)?\s*(-?[\d,]+(?:\.\d+)?)",
        text_lower,
    )
    if rg:
        metrics["repricing_gap"] = _parse_number(rg.group(1))

    # ── Total assets / liabilities ──
    ta = re.search(
        r"total\s+assets[:\s]+(?:inr|rs\.?)?\s*([\d,]+(?:\.\d+)?)",
        text_lower,
    )
    if ta:
        metrics["total_assets"] = _parse_number(ta.group(1))

    tl = re.search(
        r"total\s+liabilities[:\s]+(?:inr|rs\.?)?\s*([\d,]+(?:\.\d+)?)",
        text_lower,
    )
    if tl:
        metrics["total_liabilities"] = _parse_number(tl.group(1))

    # ── Duration gap ──
    dg = re.search(r"duration\s+gap[:\s]+(-?\d+\.?\d*)", text_lower)
    if dg:
        metrics["duration_gap"] = float(dg.group(1))

    # ── Summary heuristic ──
    gap = metrics.get("liquidity_gap_percentage")
    if gap is not None:
        if abs(gap) < 5:
            metrics["structural_liquidity_summary"] = "Well-matched"
        elif abs(gap) < 15:
            metrics["structural_liquidity_summary"] = "Moderate mismatch"
        else:
            metrics["structural_liquidity_summary"] = "Significant mismatch"

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
