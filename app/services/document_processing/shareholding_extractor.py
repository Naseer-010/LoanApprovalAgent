"""
Shareholding Extractor — extracts ownership structure from
shareholding pattern documents.

Metrics: promoter holding, public holding, FII/DII holding,
pledged shares, ESOP, top shareholders.
"""
import logging
import re

logger = logging.getLogger(__name__)


def extract_shareholding_metrics(text: str) -> dict:
    """
    Extract shareholding pattern metrics from document text.

    Returns dict with keys:
        promoter_holding_pct, public_holding_pct,
        fii_holding_pct, dii_holding_pct, pledged_pct,
        total_shares, top_shareholders, shareholding_summary
    """
    metrics: dict = {
        "promoter_holding_pct": None,
        "public_holding_pct": None,
        "fii_holding_pct": None,
        "dii_holding_pct": None,
        "pledged_pct": None,
        "total_shares": None,
        "top_shareholders": [],
        "shareholding_concentration": "",
        "shareholding_summary": "",
    }

    text_lower = text.lower()

    # ── Promoter holding ──
    promo_patterns = [
        r"promoter(?:s)?(?:\s+(?:and|&)\s+promoter\s+group)?"
        r"[:\s]+(\d+\.?\d*)\s*%",
        r"promoter\s+holding[:\s]+(\d+\.?\d*)\s*%",
        r"promoter\s+shareholding[:\s]+(\d+\.?\d*)\s*%",
    ]
    for pat in promo_patterns:
        m = re.search(pat, text_lower)
        if m:
            metrics["promoter_holding_pct"] = float(m.group(1))
            break

    # ── Public holding ──
    pub_patterns = [
        r"public\s+(?:shareholding|holding)[:\s]+(\d+\.?\d*)\s*%",
        r"non[- ]?promoter[:\s]+(\d+\.?\d*)\s*%",
    ]
    for pat in pub_patterns:
        m = re.search(pat, text_lower)
        if m:
            metrics["public_holding_pct"] = float(m.group(1))
            break

    # If we have promoter, derive public
    if (
        metrics["promoter_holding_pct"] is not None
        and metrics["public_holding_pct"] is None
    ):
        metrics["public_holding_pct"] = round(
            100.0 - metrics["promoter_holding_pct"], 2
        )

    # ── FII holding ──
    fii_patterns = [
        r"(?:fii|fpi|foreign\s+(?:institutional|portfolio)\s+"
        r"investor)[:\s]+(\d+\.?\d*)\s*%",
    ]
    for pat in fii_patterns:
        m = re.search(pat, text_lower)
        if m:
            metrics["fii_holding_pct"] = float(m.group(1))
            break

    # ── DII holding ──
    dii_patterns = [
        r"(?:dii|domestic\s+institutional\s+investor)"
        r"[:\s]+(\d+\.?\d*)\s*%",
        r"mutual\s+fund[:\s]+(\d+\.?\d*)\s*%",
    ]
    for pat in dii_patterns:
        m = re.search(pat, text_lower)
        if m:
            metrics["dii_holding_pct"] = float(m.group(1))
            break

    # ── Pledged shares ──
    pledge_patterns = [
        r"(?:shares?\s+)?pledged[:\s]+(\d+\.?\d*)\s*%",
        r"pledge(?:d)?\s+(?:of|%|percent)[:\s]+(\d+\.?\d*)",
    ]
    for pat in pledge_patterns:
        m = re.search(pat, text_lower)
        if m:
            metrics["pledged_pct"] = float(m.group(1))
            break

    # ── Total shares ──
    ts = re.search(
        r"total\s+(?:no\.?\s+of\s+)?shares[:\s]+([\d,]+)",
        text_lower,
    )
    if ts:
        metrics["total_shares"] = int(
            ts.group(1).replace(",", "")
        )

    # ── Summary heuristic ──
    promo = metrics.get("promoter_holding_pct")
    pledged = metrics.get("pledged_pct")

    if promo is not None:
        if promo >= 60:
            metrics["shareholding_concentration"] = "High promoter control"
        elif promo >= 40:
            metrics["shareholding_concentration"] = "Moderate promoter stake"
        else:
            metrics["shareholding_concentration"] = "Dispersed ownership"

    summary_parts = []
    if promo is not None:
        summary_parts.append(f"Promoter holding: {promo}%")
    if pledged is not None and pledged > 0:
        risk = "HIGH RISK" if pledged > 20 else "moderate"
        summary_parts.append(f"Pledged: {pledged}% ({risk})")
    if metrics["fii_holding_pct"] is not None:
        summary_parts.append(f"FII: {metrics['fii_holding_pct']}%")

    metrics["shareholding_summary"] = " | ".join(summary_parts)

    return metrics
