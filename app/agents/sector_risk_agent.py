"""
Sector Risk Intelligence Agent — industry-level risk analysis.

Evaluates sector-specific headwinds, regulatory changes, and macro risks
using multi-source research. Generates sector_risk_score and structured
sector intelligence.
"""

import logging

from app.config import settings
from app.schemas.research import WebSearchRequest
from app.services.research.web_researcher import (
    run_web_research,
    compute_risk_signals,
    _classify_sentiment,
)

logger = logging.getLogger(__name__)

# Sector-specific search query templates
SECTOR_QUERIES = [
    "{sector} India sector outlook 2024 2025",
    "{sector} India regulatory changes impact",
    "{sector} industry slowdown India",
    "{sector} India government policy reform",
    "{sector} India NPA stress credit risk",
    "{sector} India growth forecast demand supply",
    "RBI circular {sector} India",
    "{sector} India competition disruption risk",
]

# Risk keywords per category
HEADWIND_KEYWORDS = [
    "slowdown", "decline", "contraction", "stress", "headwind",
    "downturn", "recession", "weak demand", "overcapacity",
    "falling prices", "margin pressure", "price war",
]

REGULATORY_KEYWORDS = [
    "regulation", "policy", "circular", "guideline", "compliance",
    "rbi", "sebi", "ban", "restriction", "mandate", "reform",
    "gst rate change", "tax change", "environmental norm",
]

MACRO_KEYWORDS = [
    "inflation", "interest rate", "forex", "crude oil",
    "commodity price", "supply chain", "global recession",
    "geopolitical", "trade war", "tariff", "currency",
]


def run_sector_risk_analysis(
    company_name: str,
    sector: str,
) -> dict:
    """
    Comprehensive sector risk intelligence analysis.

    Returns:
    - sector_risk_score (0-100)
    - sector_headwinds: list of identified headwinds
    - regulatory_changes: list of regulatory signals
    - macro_risks: list of macro risks
    - sector_summary: narrative assessment
    - risk_level: low/medium/high/critical
    """
    if not sector:
        return _empty_result(company_name, sector)

    # Run multi-source research
    all_findings = []
    for template in SECTOR_QUERIES:
        query = template.format(sector=sector)
        try:
            req = WebSearchRequest(
                company_name=company_name,
                sector=sector,
                additional_keywords=[query],
            )
            items = run_web_research(req)
            all_findings.extend(items)
        except Exception as e:
            logger.warning("Sector query failed ('%s'): %s", query, e)

    if not all_findings:
        return _empty_result(company_name, sector)

    # Classify findings
    sector_headwinds = []
    regulatory_changes = []
    macro_risks = []
    negative_count = 0

    for item in all_findings:
        text = f"{item.title} {item.snippet}".lower()

        # Re-classify sentiment
        if item.sentiment == "neutral":
            item.sentiment = _classify_sentiment(text)

        if item.sentiment == "negative":
            negative_count += 1

        # Categorize signals
        if any(kw in text for kw in HEADWIND_KEYWORDS):
            sector_headwinds.append({
                "signal": item.title[:100],
                "detail": item.snippet[:200],
                "source": item.source,
                "severity": "high" if item.sentiment == "negative" else "medium",
            })

        if any(kw in text for kw in REGULATORY_KEYWORDS):
            regulatory_changes.append({
                "signal": item.title[:100],
                "detail": item.snippet[:200],
                "source": item.source,
                "impact": "negative" if item.sentiment == "negative" else "neutral",
            })

        if any(kw in text for kw in MACRO_KEYWORDS):
            macro_risks.append({
                "signal": item.title[:100],
                "detail": item.snippet[:200],
                "source": item.source,
            })

    # Compute sector risk score (0-100)
    sector_risk_score = _compute_sector_score(
        sector_headwinds, regulatory_changes, macro_risks,
        negative_count, len(all_findings),
    )

    risk_level = _risk_level(sector_risk_score)

    # Build narrative summary
    sector_summary = _build_summary(
        sector, sector_headwinds, regulatory_changes,
        macro_risks, sector_risk_score, risk_level,
    )

    return {
        "company_name": company_name,
        "sector": sector,
        "sector_risk_score": sector_risk_score,
        "risk_level": risk_level,
        "sector_headwinds": sector_headwinds[:10],
        "regulatory_changes": regulatory_changes[:10],
        "macro_risks": macro_risks[:10],
        "sector_summary": sector_summary,
        "findings_analyzed": len(all_findings),
        "negative_signal_ratio": round(
            negative_count / max(len(all_findings), 1), 2,
        ),
    }


def _compute_sector_score(
    headwinds: list[dict],
    regulatory: list[dict],
    macro: list[dict],
    negative_count: int,
    total_findings: int,
) -> float:
    """Compute sector risk score (0-100)."""
    score = 20.0  # baseline

    # Headwinds: 6 pts each (high severity = 10)
    for h in headwinds[:10]:
        score += 10 if h.get("severity") == "high" else 6

    # Regulatory changes with negative impact: 5 pts each
    neg_reg = sum(1 for r in regulatory if r.get("impact") == "negative")
    score += neg_reg * 5

    # Macro risks: 4 pts each
    score += len(macro[:10]) * 4

    # Negative sentiment ratio adjustment
    if total_findings > 0:
        neg_ratio = negative_count / total_findings
        if neg_ratio > 0.6:
            score += 15
        elif neg_ratio > 0.4:
            score += 8

    return min(100.0, round(score, 1))


def _risk_level(score: float) -> str:
    if score >= 70:
        return "critical"
    if score >= 50:
        return "high"
    if score >= 30:
        return "medium"
    return "low"


def _build_summary(
    sector: str,
    headwinds: list[dict],
    regulatory: list[dict],
    macro: list[dict],
    score: float,
    risk_level: str,
) -> str:
    """Build narrative sector risk summary."""
    parts = [
        f"Sector Risk Assessment for {sector.title()}: "
        f"{risk_level.upper()} (Score: {score:.0f}/100).",
    ]

    if headwinds:
        hw_list = ", ".join(h["signal"][:50] for h in headwinds[:3])
        parts.append(f"Key headwinds identified: {hw_list}.")

    if regulatory:
        parts.append(
            f"{len(regulatory)} regulatory signal(s) detected "
            f"that may impact the sector."
        )

    if macro:
        parts.append(
            f"{len(macro)} macro-level risk(s) identified "
            f"affecting the sector outlook."
        )

    if not headwinds and not regulatory and not macro:
        parts.append(
            "No significant sector-specific risk signals detected."
        )

    return " ".join(parts)


def _empty_result(company_name: str, sector: str) -> dict:
    return {
        "company_name": company_name,
        "sector": sector or "unknown",
        "sector_risk_score": 0.0,
        "risk_level": "unknown",
        "sector_headwinds": [],
        "regulatory_changes": [],
        "macro_risks": [],
        "sector_summary": "Sector not specified or no data available.",
        "findings_analyzed": 0,
        "negative_signal_ratio": 0.0,
    }
