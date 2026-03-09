"""
Indian Regulatory Checks — CIBIL, GSTR-2A/3B, MCA director analysis.

All data derived from documents, APIs, or web research.
No mock/simulated data — functions return "unavailable" status
when real API connections are not configured.
"""

import logging

from app.schemas.ingestor import (
    CIBILReport,
    GSTDataResponse,
    GSTRMismatch,
    MCADirectorCheck,
    RegulatoryCheckResult,
)

logger = logging.getLogger(__name__)


def run_regulatory_checks(
    company_name: str,
    gst_data: GSTDataResponse | None = None,
    promoter_names: list[str] | None = None,
) -> RegulatoryCheckResult:
    """
    Run consolidated Indian regulatory checks.

    CIBIL and MCA checks require real API integrations.
    When APIs are not connected, returns clear "unavailable" status.
    GSTR checks are computed from actual filed data.
    """
    flags: list[str] = []

    # CIBIL check — requires real API
    cibil = _cibil_check(company_name)
    if cibil.score > 0 and cibil.score < 650:
        flags.append(
            f"CIBIL score {cibil.score} below 650 threshold"
        )
    if cibil.overdue_accounts > 0:
        flags.append(
            f"{cibil.overdue_accounts} overdue account(s) "
            f"in credit history"
        )

    # GSTR mismatch — computed from actual data
    gstr = _check_gstr_mismatch(gst_data)
    if gstr.mismatch_percentage > 10:
        flags.append(
            f"GSTR-2A/3B ITC mismatch of "
            f"{gstr.mismatch_percentage:.1f}%"
        )

    # MCA director checks — requires real API
    directors = _mca_director_checks(
        company_name, promoter_names or [],
    )
    for d in directors:
        if d.defaulter_flag:
            flags.append(
                f"Director {d.director_name} flagged as defaulter"
            )
        if d.status == "Disqualified":
            flags.append(
                f"Director {d.director_name} disqualified by MCA"
            )

    risk = _assess_regulatory_risk(cibil, gstr, directors, flags)

    return RegulatoryCheckResult(
        cibil=cibil,
        gstr_mismatch=gstr,
        director_checks=directors,
        overall_regulatory_risk=risk,
        flags=flags,
    )


def _cibil_check(company_name: str) -> CIBILReport:
    """
    CIBIL commercial credit check.

    Requires CIBIL API integration for production use.
    Returns 'unavailable' status when API is not connected.

    To integrate: implement HTTP call to CIBIL Connect API
    with your CIBIL subscriber credentials.
    """
    # TODO: Replace with actual CIBIL API call
    # Example integration point:
    # response = cibil_api.get_commercial_report(company_name)
    # return CIBILReport(score=response.score, ...)

    logger.info(
        "CIBIL API not connected — returning unavailable status for '%s'",
        company_name,
    )

    return CIBILReport(
        score=0,
        rating="Not Available",
        credit_age_years=0,
        active_accounts=0,
        overdue_accounts=0,
        default_history=[],
        enquiry_count_6m=0,
        assessment=(
            "CIBIL score unavailable — connect CIBIL API for "
            "real credit bureau data. Score not fabricated."
        ),
    )


def _check_gstr_mismatch(
    gst_data: GSTDataResponse | None,
) -> GSTRMismatch:
    """
    Check GSTR-2A vs 3B mismatch using actual filed data.

    When GSTR-2A data is not available, only flags based on
    3B data anomalies (high ITC ratio, etc.) without fabricating
    2A numbers.
    """
    if not gst_data or gst_data.total_itc_claimed == 0:
        return GSTRMismatch()

    claimed = gst_data.total_itc_claimed

    # Without actual GSTR-2A data, we can only assess 3B anomalies
    # Check if ITC claimed seems unreasonable relative to turnover
    if gst_data.total_turnover > 0:
        itc_to_turnover = claimed / gst_data.total_turnover
        if itc_to_turnover > 0.18:  # 18% GST means ITC can't exceed ~18% of turnover
            excess = (itc_to_turnover - 0.18) * gst_data.total_turnover
            mismatch_pct = (excess / claimed) * 100 if claimed > 0 else 0

            return GSTRMismatch(
                itc_claimed_3b=round(claimed, 2),
                itc_eligible_2a=0.0,  # Not available without 2A data
                mismatch_amount=round(excess, 2),
                mismatch_percentage=round(mismatch_pct, 2),
                risk_flag=(
                    f"ITC claimed ({itc_to_turnover:.1%} of turnover) exceeds "
                    f"maximum GST rate of 18%. Potential over-claiming "
                    f"of ₹{excess:,.0f}. GSTR-2A data needed for confirmation."
                ),
            )

    # Check per-period ITC consistency
    if len(gst_data.entries) >= 2:
        itc_values = [e.itc_claimed for e in gst_data.entries if e.itc_claimed > 0]
        if itc_values:
            avg_itc = sum(itc_values) / len(itc_values)
            max_dev = max(abs(v - avg_itc) for v in itc_values)
            if avg_itc > 0 and max_dev / avg_itc > 0.5:
                return GSTRMismatch(
                    itc_claimed_3b=round(claimed, 2),
                    itc_eligible_2a=0.0,
                    mismatch_amount=0.0,
                    mismatch_percentage=0.0,
                    risk_flag=(
                        "Inconsistent ITC claims across periods — "
                        "variance exceeds 50%. May indicate selective "
                        "or opportunistic ITC claiming. "
                        "GSTR-2A reconciliation recommended."
                    ),
                )

    return GSTRMismatch(
        itc_claimed_3b=round(claimed, 2),
        itc_eligible_2a=0.0,
        mismatch_amount=0.0,
        mismatch_percentage=0.0,
        risk_flag=(
            "GSTR-2A data not available — unable to perform "
            "full 2A/3B reconciliation. Connect GST API for "
            "complete analysis."
        ),
    )


def _mca_director_checks(
    company_name: str,
    promoter_names: list[str],
) -> list[MCADirectorCheck]:
    """
    MCA director status checks.

    Requires MCA V3 API integration for production use.
    Returns 'unavailable' status for each director when
    API is not connected.

    To integrate: implement HTTP call to MCA V3 API
    with your registered credentials.
    """
    # TODO: Replace with actual MCA V3 API call
    # Example:
    # response = mca_api.search_director(din=din)
    # return MCADirectorCheck(...)

    results = []
    for name in promoter_names[:5]:
        if not name.strip():
            continue

        logger.info(
            "MCA API not connected — returning unavailable for director '%s'",
            name,
        )

        results.append(MCADirectorCheck(
            director_name=name.strip(),
            din="",
            status="Unknown",
            companies_linked=0,
            defaulter_flag=False,
            details=(
                f"MCA data for {name} unavailable — connect MCA V3 API "
                f"for director verification. Status not fabricated."
            ),
        ))

    return results


def _assess_regulatory_risk(
    cibil: CIBILReport,
    gstr: GSTRMismatch,
    directors: list[MCADirectorCheck],
    flags: list[str],
) -> str:
    """Determine overall regulatory risk level."""
    # If CIBIL is available and poor
    if cibil.score > 0 and cibil.score < 600:
        return "high"
    if any(d.defaulter_flag for d in directors):
        return "high"

    if (
        (cibil.score > 0 and cibil.score < 700)
        or gstr.mismatch_percentage > 15
        or any(d.status == "Disqualified" for d in directors)
    ):
        return "medium"

    if len(flags) > 2:
        return "medium"

    # If no real data available, return unknown
    if cibil.score == 0 and not any(d.din for d in directors):
        return "unknown"

    return "low"
