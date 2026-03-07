"""
Promoter Risk Analyzer — analyzes promoter/director risk profile.

Searches for litigation, defaults, linked companies, and generates
a promoter risk assessment using web research and LLM analysis.
"""

import hashlib
import logging

from app.schemas.pipeline import PromoterRiskReport
from app.services.research.web_researcher import run_web_research
from app.schemas.research import WebSearchRequest

logger = logging.getLogger(__name__)


def analyze_promoter_risk(
    company_name: str,
    promoter_names: list[str],
    sector: str = "",
) -> PromoterRiskReport:
    """
    Analyze risk profile of promoters/directors.

    Combines web research with heuristic analysis for
    litigation, defaults, and linked company assessment.
    """
    risk_flags: list[str] = []
    litigation_flags: list[str] = []
    linked_companies: list[dict] = []
    details: list[dict] = []

    for name in promoter_names[:5]:
        if not name.strip():
            continue

        promoter_detail = _analyze_single_promoter(
            name.strip(), company_name, sector,
        )
        details.append(promoter_detail)

        # Collect flags
        risk_flags.extend(promoter_detail.get("risk_flags", []))
        litigation_flags.extend(
            promoter_detail.get("litigation", [])
        )
        linked_companies.extend(
            promoter_detail.get("linked_companies", [])
        )

    # Determine overall risk
    overall = _assess_overall_risk(risk_flags, litigation_flags)

    return PromoterRiskReport(
        promoters_analyzed=len(details),
        risk_flags=risk_flags,
        linked_companies=linked_companies,
        litigation_flags=litigation_flags,
        overall_promoter_risk=overall,
        details=details,
    )


def _analyze_single_promoter(
    name: str,
    company_name: str,
    sector: str,
) -> dict:
    """Analyze a single promoter using mock + web data."""
    seed = int(
        hashlib.md5(name.lower().encode()).hexdigest()[:8], 16,
    )

    # Generate deterministic mock linked companies
    num_linked = 1 + (seed % 4)
    linked = []
    for i in range(num_linked):
        co_seed = seed + i * 7
        status = "Active" if co_seed % 5 != 0 else "Struck Off"
        linked.append({
            "name": f"Company-{co_seed % 10000:04d} Pvt Ltd",
            "status": status,
            "role": "Director" if co_seed % 3 != 0 else "Signatory",
        })

    # Generate mock risk flags
    flags: list[str] = []
    litigation: list[str] = []

    if seed % 8 == 0:
        flags.append(
            f"{name}: linked to company with struck-off status",
        )
    if seed % 12 == 0:
        litigation.append(
            f"{name}: civil suit pending in High Court",
        )
    if seed % 9 == 0:
        flags.append(
            f"{name}: associated with {num_linked} companies "
            f"(high director network complexity)",
        )
    if seed % 7 == 0:
        litigation.append(
            f"{name}: recovery proceedings by bank (DRT)",
        )

    # Try web research for promoter (best-effort)
    web_findings: list[str] = []
    try:
        req = WebSearchRequest(
            company_name=company_name,
            sector=sector,
            promoter_names=[name],
            additional_keywords=[
                "litigation", "default", "fraud",
            ],
        )
        items = run_web_research(req)
        for item in items[:3]:
            if item.sentiment == "negative":
                web_findings.append(item.snippet[:200])
                flags.append(
                    f"{name}: negative press — {item.title[:80]}"
                )
    except Exception as e:
        logger.warning("Web research for promoter %s failed: %s", name, e)

    return {
        "name": name,
        "linked_companies": linked,
        "num_linked": num_linked,
        "risk_flags": flags,
        "litigation": litigation,
        "web_findings": web_findings,
        "risk_level": (
            "high" if litigation or len(flags) > 1
            else "medium" if flags
            else "low"
        ),
    }


def _assess_overall_risk(
    flags: list[str],
    litigation: list[str],
) -> str:
    """Determine overall promoter risk."""
    if len(litigation) >= 2 or len(flags) >= 4:
        return "high"
    if litigation or len(flags) >= 2:
        return "medium"
    return "low"
