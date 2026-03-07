"""
Indian Regulatory Checks — mock CIBIL, GSTR-2A/3B, MCA director analysis.

Simulates checks against Indian regulatory databases for hackathon demo.
In production these would call real APIs (CIBIL, GST portal, MCA V3).
"""

import hashlib
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

    In production, these call real APIs. This version generates
    deterministic mock data for demo/hackathon purposes.
    """
    flags: list[str] = []

    cibil = _mock_cibil_check(company_name)
    if cibil.score < 650:
        flags.append(
            f"CIBIL score {cibil.score} below 650 threshold"
        )
    if cibil.overdue_accounts > 0:
        flags.append(
            f"{cibil.overdue_accounts} overdue account(s) "
            f"in credit history"
        )

    gstr = _check_gstr_mismatch(gst_data)
    if gstr.mismatch_percentage > 10:
        flags.append(
            f"GSTR-2A/3B ITC mismatch of "
            f"{gstr.mismatch_percentage:.1f}%"
        )

    directors = _mock_mca_director_checks(promoter_names or [])
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


def _mock_cibil_check(company_name: str) -> CIBILReport:
    """
    Generate deterministic mock CIBIL commercial credit report.

    Uses hash of company name for reproducible demo scores.
    """
    seed = int(
        hashlib.md5(company_name.lower().encode()).hexdigest()[:8], 16
    )

    # Score between 550–850 based on hash
    score = 550 + (seed % 300)
    overdue = 1 if seed % 7 == 0 else 0
    defaults = []
    if seed % 11 == 0:
        defaults.append("Overdue on term loan (2022)")
    if seed % 13 == 0:
        defaults.append("Late payment on working capital (2023)")

    if score >= 750:
        rating = "A (Low Risk)"
    elif score >= 700:
        rating = "B (Moderate Risk)"
    elif score >= 650:
        rating = "C (Elevated Risk)"
    else:
        rating = "D (High Risk)"

    credit_age = 3 + (seed % 15)
    active = 2 + (seed % 6)
    enquiries = seed % 5

    if score >= 750:
        assessment = (
            "Strong credit profile with consistent repayment "
            "history. No significant delinquencies observed."
        )
    elif score >= 700:
        assessment = (
            "Moderate credit profile. Minor delays noted in "
            "repayment history but overall satisfactory."
        )
    elif score >= 650:
        assessment = (
            "Below-average credit profile. Some delinquencies "
            "and payment irregularities require monitoring."
        )
    else:
        assessment = (
            "Weak credit profile with significant repayment "
            "issues. High risk of default based on credit "
            "history patterns."
        )

    return CIBILReport(
        score=score,
        rating=rating,
        credit_age_years=credit_age,
        active_accounts=active,
        overdue_accounts=overdue,
        default_history=defaults,
        enquiry_count_6m=enquiries,
        assessment=assessment,
    )


def _check_gstr_mismatch(
    gst_data: GSTDataResponse | None,
) -> GSTRMismatch:
    """
    Check GSTR-2A vs 3B mismatch.

    GSTR-3B ITC claimed vs GSTR-2A eligible ITC (simulated as
    90% of claimed, since we don't have actual 2A data).
    """
    if not gst_data or gst_data.total_itc_claimed == 0:
        return GSTRMismatch()

    claimed = gst_data.total_itc_claimed
    # Simulate 2A eligible as 85-95% of claimed (common scenario)
    seed = int(str(int(claimed))[:4]) if claimed > 0 else 0
    eligible_pct = 0.85 + (seed % 10) * 0.01
    eligible = claimed * eligible_pct

    mismatch = claimed - eligible
    mismatch_pct = (mismatch / claimed) * 100 if claimed > 0 else 0

    if mismatch_pct > 20:
        flag = (
            "CRITICAL: Large GSTR-2A/3B ITC mismatch. "
            "Possible fraudulent ITC claims."
        )
    elif mismatch_pct > 10:
        flag = (
            "WARNING: Moderate ITC mismatch. Reconciliation "
            "with suppliers recommended."
        )
    elif mismatch_pct > 5:
        flag = (
            "MINOR: Small ITC difference within acceptable "
            "tolerance."
        )
    else:
        flag = "No significant mismatch detected."

    return GSTRMismatch(
        itc_claimed_3b=round(claimed, 2),
        itc_eligible_2a=round(eligible, 2),
        mismatch_amount=round(mismatch, 2),
        mismatch_percentage=round(mismatch_pct, 2),
        risk_flag=flag,
    )


def _mock_mca_director_checks(
    promoter_names: list[str],
) -> list[MCADirectorCheck]:
    """
    Mock MCA director status checks.

    Uses hash of director name for reproducible demo data.
    """
    results = []
    for name in promoter_names[:5]:
        if not name.strip():
            continue
        seed = int(
            hashlib.md5(name.lower().encode()).hexdigest()[:8], 16
        )
        din = f"{10000000 + seed % 90000000}"
        linked = 1 + (seed % 5)

        # ~10% chance of being flagged
        defaulter = seed % 10 == 0
        status = "Disqualified" if seed % 15 == 0 else "Active"

        if defaulter:
            detail = (
                f"Director {name} has been flagged as a "
                f"defaulter. History shows involvement in "
                f"loan default at a previous company."
            )
        elif status == "Disqualified":
            detail = (
                f"Director {name} is disqualified by MCA "
                f"under Section 164(2) for non-filing of "
                f"annual returns."
            )
        else:
            detail = (
                f"Director {name} has an active DIN with "
                f"{linked} company linkage(s). No adverse "
                f"findings in MCA records."
            )

        results.append(MCADirectorCheck(
            director_name=name.strip(),
            din=din,
            status=status,
            companies_linked=linked,
            defaulter_flag=defaulter,
            details=detail,
        ))

    return results


def _assess_regulatory_risk(
    cibil: CIBILReport,
    gstr: GSTRMismatch,
    directors: list[MCADirectorCheck],
    flags: list[str],
) -> str:
    """Determine overall regulatory risk level."""
    if cibil.score < 600 or any(d.defaulter_flag for d in directors):
        return "high"
    if (
        cibil.score < 700
        or gstr.mismatch_percentage > 15
        or any(d.status == "Disqualified" for d in directors)
    ):
        return "medium"
    if len(flags) > 2:
        return "medium"
    return "low"
