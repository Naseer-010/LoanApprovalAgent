"""
Promoter Risk Analyzer — network graph analysis for promoter/director risk.

Builds a Promoter → Companies → Directors network graph using web research
data. Detects red flags: director overlaps, dissolved companies, frequent
shutdowns. Derives promoter_risk_score from graph metrics.

No mock/simulated data — all analysis from web research and document inputs.
"""

import logging

import networkx as nx

from app.schemas.pipeline import PromoterRiskReport
from app.services.research.web_researcher import (
    run_web_research,
    compute_risk_signals,
)
from app.schemas.research import WebSearchRequest

logger = logging.getLogger(__name__)


def analyze_promoter_risk(
    company_name: str,
    promoter_names: list[str],
    sector: str = "",
    mca_data: list[dict] | None = None,
) -> PromoterRiskReport:
    """
    Analyze risk profile of promoters/directors.

    Uses web research + optional MCA data to build a network graph
    and compute promoter risk score. No mock data generation.
    """
    risk_flags: list[str] = []
    litigation_flags: list[str] = []
    linked_companies: list[dict] = []
    details: list[dict] = []
    graph = nx.Graph()

    for name in promoter_names[:5]:
        if not name.strip():
            continue

        promoter_detail = _analyze_single_promoter(
            name.strip(), company_name, sector, mca_data,
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

        # Build network graph
        _add_to_graph(graph, name, promoter_detail)

    # Analyze graph for red flags
    graph_flags = _analyze_graph(graph)
    risk_flags.extend(graph_flags)

    # Compute promoter risk score
    promoter_risk_score = _compute_risk_score(
        risk_flags, litigation_flags, graph, len(promoter_names),
    )

    # Determine overall risk
    overall = _assess_overall_risk(
        risk_flags, litigation_flags, promoter_risk_score,
    )

    return PromoterRiskReport(
        promoters_analyzed=len(details),
        risk_flags=risk_flags,
        linked_companies=linked_companies,
        litigation_flags=litigation_flags,
        overall_promoter_risk=overall,
        promoter_risk_score=promoter_risk_score,
        details=details,
    )


def _analyze_single_promoter(
    name: str,
    company_name: str,
    sector: str,
    mca_data: list[dict] | None = None,
) -> dict:
    """Analyze a single promoter using web research + MCA data."""
    flags: list[str] = []
    litigation: list[str] = []
    linked = []

    # Use MCA data if available
    if mca_data:
        for record in mca_data:
            directors = record.get("directors", [])
            for director in directors:
                dir_name = director.get("name", "").lower()
                if name.lower() in dir_name or dir_name in name.lower():
                    co_name = record.get("company_name", "Unknown")
                    co_status = record.get("status", "Active")
                    linked.append({
                        "name": co_name,
                        "status": co_status,
                        "role": director.get("role", "Director"),
                    })
                    if co_status in ("Struck Off", "Dissolved", "Inactive"):
                        flags.append(
                            f"{name}: linked to {co_status.lower()} company '{co_name}'"
                        )

    # Web research for promoter
    web_findings: list[str] = []
    try:
        req = WebSearchRequest(
            company_name=company_name,
            sector=sector,
            promoter_names=[name],
            additional_keywords=["litigation", "default", "fraud"],
        )
        items = run_web_research(req)
        for item in items[:5]:
            if item.sentiment == "negative":
                web_findings.append(item.snippet[:200])
                text_lower = f"{item.title} {item.snippet}".lower()

                # Check for litigation keywords
                litigation_kws = [
                    "court", "case", "litigation", "nclt",
                    "drt", "tribunal", "sued",
                ]
                if any(kw in text_lower for kw in litigation_kws):
                    litigation.append(
                        f"{name}: {item.title[:100]}"
                    )
                else:
                    flags.append(
                        f"{name}: negative press — {item.title[:80]}"
                    )

    except Exception as e:
        logger.warning(
            "Web research for promoter %s failed: %s", name, e,
        )

    risk_level = (
        "high" if litigation or len(flags) > 1
        else "medium" if flags
        else "low"
    )

    return {
        "name": name,
        "linked_companies": linked,
        "num_linked": len(linked),
        "risk_flags": flags,
        "litigation": litigation,
        "web_findings": web_findings,
        "risk_level": risk_level,
    }


def _add_to_graph(
    graph: nx.Graph,
    promoter_name: str,
    detail: dict,
) -> None:
    """Add promoter and linked companies to the network graph."""
    graph.add_node(promoter_name, node_type="promoter")

    for company in detail.get("linked_companies", []):
        co_name = company.get("name", "")
        co_status = company.get("status", "Active")
        if co_name:
            graph.add_node(
                co_name,
                node_type="company",
                status=co_status,
            )
            graph.add_edge(
                promoter_name,
                co_name,
                role=company.get("role", "Director"),
            )


def _analyze_graph(graph: nx.Graph) -> list[str]:
    """Analyze the promoter-company network graph for red flags."""
    flags: list[str] = []

    if graph.number_of_nodes() < 2:
        return flags

    # Check for director overlaps (promoters sharing companies)
    promoter_nodes = [
        n for n, d in graph.nodes(data=True)
        if d.get("node_type") == "promoter"
    ]
    company_nodes = [
        n for n, d in graph.nodes(data=True)
        if d.get("node_type") == "company"
    ]

    # Detect shared company connections
    for company in company_nodes:
        connected_promoters = [
            n for n in graph.neighbors(company)
            if graph.nodes[n].get("node_type") == "promoter"
        ]
        if len(connected_promoters) >= 2:
            names = ", ".join(connected_promoters)
            flags.append(
                f"Director overlap: {names} are both linked to '{company}'"
            )

    # Detect high number of dissolved companies
    dissolved = [
        n for n in company_nodes
        if graph.nodes[n].get("status") in (
            "Struck Off", "Dissolved", "Inactive",
        )
    ]
    if len(dissolved) >= 2:
        flags.append(
            f"Multiple dissolved companies ({len(dissolved)}) found "
            f"in promoter network — frequent company shutdowns"
        )

    # Detect high degree centrality (too many connections)
    for promoter in promoter_nodes:
        degree = graph.degree(promoter)
        if degree >= 5:
            flags.append(
                f"{promoter}: unusually high network connectivity "
                f"({degree} linked entities) — complex corporate structure"
            )

    return flags


def _compute_risk_score(
    risk_flags: list[str],
    litigation_flags: list[str],
    graph: nx.Graph,
    num_promoters: int,
) -> float:
    """
    Compute promoter risk score (0-100) from collected signals.

    Based on:
    - Number and severity of risk flags
    - Litigation count
    - Network graph metrics (dissolved ratio, complexity)
    """
    score = 0.0

    # Risk flags: 8 points each
    score += min(40, len(risk_flags) * 8)

    # Litigation: 15 points each
    score += min(45, len(litigation_flags) * 15)

    # Graph-based: dissolved company ratio
    company_nodes = [
        n for n, d in graph.nodes(data=True)
        if d.get("node_type") == "company"
    ]
    if company_nodes:
        dissolved = sum(
            1 for n in company_nodes
            if graph.nodes[n].get("status") in (
                "Struck Off", "Dissolved", "Inactive",
            )
        )
        dissolved_ratio = dissolved / len(company_nodes)
        score += dissolved_ratio * 20

    return min(100.0, round(score, 1))


def _assess_overall_risk(
    flags: list[str],
    litigation: list[str],
    risk_score: float,
) -> str:
    """Determine overall promoter risk."""
    if risk_score >= 60 or len(litigation) >= 3:
        return "high"
    if risk_score >= 30 or len(litigation) >= 1 or len(flags) >= 3:
        return "medium"
    return "low"
