"""
Portfolio Extractor — extracts key metrics from portfolio
performance / asset quality documents.

Metrics: Portfolio Yield, Default Rate, Recovery Rate,
NPA Ratio, Provision Coverage, Delinquency buckets.
"""
import logging
import re

logger = logging.getLogger(__name__)


def extract_portfolio_metrics(text: str) -> dict:
    """
    Extract portfolio performance metrics from document text.

    Returns dict with keys:
        portfolio_yield, default_rate, recovery_rate,
        gross_npa_ratio, net_npa_ratio, provision_coverage,
        total_portfolio_size, delinquency_buckets,
        asset_quality_summary
    """
    metrics: dict = {
        "portfolio_yield": None,
        "default_rate": None,
        "recovery_rate": None,
        "gross_npa_ratio": None,
        "net_npa_ratio": None,
        "provision_coverage": None,
        "total_portfolio_size": None,
        "delinquency_buckets": [],
        "asset_quality_summary": "",
    }

    text_lower = text.lower()

    # ── Percentage patterns ──
    pct_patterns = {
        "portfolio_yield": [
            r"portfolio\s+yield[:\s]+(\d+\.?\d*)\s*%",
            r"yield[:\s]+(\d+\.?\d*)\s*%",
        ],
        "default_rate": [
            r"default\s+rate[:\s]+(\d+\.?\d*)\s*%",
            r"cumulative\s+default[:\s]+(\d+\.?\d*)\s*%",
        ],
        "recovery_rate": [
            r"recovery\s+rate[:\s]+(\d+\.?\d*)\s*%",
        ],
        "gross_npa_ratio": [
            r"gross\s+npa[:\s]+(\d+\.?\d*)\s*%",
            r"gnpa[:\s]+(\d+\.?\d*)\s*%",
        ],
        "net_npa_ratio": [
            r"net\s+npa[:\s]+(\d+\.?\d*)\s*%",
            r"nnpa[:\s]+(\d+\.?\d*)\s*%",
        ],
        "provision_coverage": [
            r"provision\s+coverage[:\s]+(\d+\.?\d*)\s*%",
            r"pcr[:\s]+(\d+\.?\d*)\s*%",
        ],
    }

    for field, patterns in pct_patterns.items():
        for pat in patterns:
            m = re.search(pat, text_lower)
            if m:
                metrics[field] = float(m.group(1))
                break

    # ── Portfolio size ──
    size_patterns = [
        r"total\s+portfolio[:\s]+(?:inr|rs\.?)\s*([\d,]+(?:\.\d+)?)\s*(?:cr|crore)",
        r"aum[:\s]+(?:inr|rs\.?)\s*([\d,]+(?:\.\d+)?)\s*(?:cr|crore)",
        r"portfolio\s+size[:\s]+(?:inr|rs\.?)\s*([\d,]+(?:\.\d+)?)",
    ]
    for pat in size_patterns:
        m = re.search(pat, text_lower)
        if m:
            val = float(m.group(1).replace(",", ""))
            metrics["total_portfolio_size"] = val
            break

    # ── Delinquency buckets ──
    bucket_pattern = r"(\d+[-–]\d+)\s*(?:days?|dpd)[:\s]+(\d+\.?\d*)\s*%"
    buckets = re.findall(bucket_pattern, text_lower)
    if buckets:
        metrics["delinquency_buckets"] = [
            {"bucket": b[0], "percentage": float(b[1])}
            for b in buckets
        ]

    # ── Summary heuristic ──
    gnpa = metrics.get("gross_npa_ratio")
    if gnpa is not None:
        if gnpa < 2:
            metrics["asset_quality_summary"] = "Strong"
        elif gnpa < 5:
            metrics["asset_quality_summary"] = "Moderate"
        elif gnpa < 10:
            metrics["asset_quality_summary"] = "Weak"
        else:
            metrics["asset_quality_summary"] = "Critical"

    return metrics
