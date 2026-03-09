"""
Promoter Network Agent — graph-based promoter relationship analysis.

Maps relationships between company → promoters → directors → related companies.
Serializes the graph into JSON for API response and frontend visualization.
Detects hidden corporate risk networks using networkx.
"""

import logging

import networkx as nx

from app.services.research.promoter_analyzer import analyze_promoter_risk
from app.schemas.pipeline import PromoterRiskReport

logger = logging.getLogger(__name__)


def run_promoter_network_analysis(
    company_name: str,
    promoter_names: list[str],
    sector: str = "",
    mca_data: list[dict] | None = None,
) -> dict:
    """
    Full promoter network analysis with graph serialization.

    Returns:
    - promoter_network_risk_score (0-100)
    - graph_structure (JSON-serializable nodes + edges)
    - risk_flags, litigation_flags
    - details per promoter
    """
    # Get risk report from existing analyzer
    report = analyze_promoter_risk(
        company_name, promoter_names, sector, mca_data,
    )

    # Build the graph and serialize it
    graph = _build_graph(company_name, promoter_names, report)
    graph_structure = _serialize_graph(graph)

    # Compute graph-based risk metrics
    graph_risk_signals = _compute_graph_risk_signals(graph)

    return {
        "company_name": company_name,
        "promoter_network_risk_score": report.promoter_risk_score,
        "overall_risk": report.overall_promoter_risk,
        "graph_structure": graph_structure,
        "graph_risk_signals": graph_risk_signals,
        "risk_flags": report.risk_flags,
        "litigation_flags": report.litigation_flags,
        "linked_companies": report.linked_companies,
        "promoters_analyzed": report.promoters_analyzed,
        "details": report.details,
    }


def _build_graph(
    company_name: str,
    promoter_names: list[str],
    report: PromoterRiskReport,
) -> nx.Graph:
    """Build networkx graph from promoter analysis results."""
    G = nx.Graph()

    # Central company node
    G.add_node(
        company_name,
        node_type="company",
        status="Active",
        is_primary=True,
    )

    # Add promoter nodes
    for name in promoter_names:
        if not name.strip():
            continue
        G.add_node(
            name.strip(),
            node_type="promoter",
        )
        G.add_edge(
            name.strip(),
            company_name,
            relationship="promoter_of",
        )

    # Add linked companies from report details
    for detail in report.details:
        promoter_name = detail.get("name", "")
        for linked in detail.get("linked_companies", []):
            co_name = linked.get("name", "")
            co_status = linked.get("status", "Active")
            role = linked.get("role", "Director")
            if co_name and co_name != company_name:
                G.add_node(
                    co_name,
                    node_type="company",
                    status=co_status,
                    is_primary=False,
                )
                G.add_edge(
                    promoter_name,
                    co_name,
                    relationship=role.lower(),
                )

    # Add litigation flags as risk nodes
    for i, flag in enumerate(report.litigation_flags[:5]):
        node_id = f"litigation_{i}"
        G.add_node(node_id, node_type="risk", label=flag[:80])
        # Link to the promoter mentioned
        for name in promoter_names:
            if name.lower() in flag.lower():
                G.add_edge(name, node_id, relationship="litigation")
                break

    return G


def _serialize_graph(graph: nx.Graph) -> dict:
    """
    Serialize networkx graph to JSON-compatible structure
    suitable for frontend vis-network rendering.
    """
    nodes = []
    for node_id, attrs in graph.nodes(data=True):
        node_type = attrs.get("node_type", "unknown")
        color_map = {
            "company": "#4CAF50" if attrs.get("is_primary") else "#2196F3",
            "promoter": "#FF9800",
            "risk": "#F44336",
        }

        shape_map = {
            "company": "dot",
            "promoter": "diamond",
            "risk": "triangle",
        }

        nodes.append({
            "id": str(node_id),
            "label": attrs.get("label", str(node_id))[:40],
            "type": node_type,
            "color": color_map.get(node_type, "#9E9E9E"),
            "shape": shape_map.get(node_type, "dot"),
            "status": attrs.get("status", ""),
            "is_primary": attrs.get("is_primary", False),
        })

    edges = []
    for source, target, attrs in graph.edges(data=True):
        edges.append({
            "from": str(source),
            "to": str(target),
            "label": attrs.get("relationship", ""),
            "color": (
                "#F44336" if attrs.get("relationship") == "litigation"
                else "#999999"
            ),
        })

    return {
        "nodes": nodes,
        "edges": edges,
        "node_count": len(nodes),
        "edge_count": len(edges),
    }


def _compute_graph_risk_signals(graph: nx.Graph) -> dict:
    """Compute risk metrics from the graph structure."""
    if graph.number_of_nodes() < 2:
        return {
            "network_complexity": "simple",
            "dissolved_company_ratio": 0.0,
            "max_promoter_connections": 0,
            "director_overlaps": 0,
        }

    company_nodes = [
        n for n, d in graph.nodes(data=True)
        if d.get("node_type") == "company" and not d.get("is_primary")
    ]
    promoter_nodes = [
        n for n, d in graph.nodes(data=True)
        if d.get("node_type") == "promoter"
    ]

    # Dissolved ratio
    dissolved = sum(
        1 for n in company_nodes
        if graph.nodes[n].get("status") in (
            "Struck Off", "Dissolved", "Inactive",
        )
    )
    dissolved_ratio = dissolved / max(len(company_nodes), 1)

    # Max connections
    max_connections = 0
    for p in promoter_nodes:
        max_connections = max(max_connections, graph.degree(p))

    # Director overlaps (companies shared by 2+ promoters)
    overlaps = 0
    for c in company_nodes:
        connected_promoters = [
            n for n in graph.neighbors(c)
            if n in promoter_nodes
        ]
        if len(connected_promoters) >= 2:
            overlaps += 1

    complexity = (
        "complex" if len(company_nodes) > 5 or max_connections > 4
        else "moderate" if len(company_nodes) > 2
        else "simple"
    )

    return {
        "network_complexity": complexity,
        "dissolved_company_ratio": round(dissolved_ratio, 2),
        "max_promoter_connections": max_connections,
        "director_overlaps": overlaps,
        "total_linked_companies": len(company_nodes),
        "risk_nodes": sum(
            1 for _, d in graph.nodes(data=True)
            if d.get("node_type") == "risk"
        ),
    }
