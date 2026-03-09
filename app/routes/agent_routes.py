import logging
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.agents.early_warning_agent import run_early_warning_analysis
from app.agents.promoter_network_agent import run_promoter_network_analysis
from app.agents.sector_risk_agent import run_sector_risk_analysis
from app.agents.historical_trust_agent import run_historical_trust_analysis
from app.agents.working_capital_agent import run_working_capital_analysis
from app.schemas.pipeline import (
    EarlyWarningReport,
    HistoricalTrustReport,
    PromoterRiskReport,
    SectorRiskReport,
    WorkingCapitalReport,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["Advanced Agents"])


@router.get("/promoter-network", response_model=PromoterRiskReport)
def get_promoter_network(
    company_name: str,
    promoter_names: Annotated[list[str], Query()],
    sector: str = "",
):
    """Run graph-based promoter network analysis."""
    if not company_name or not promoter_names:
        raise HTTPException(
            status_code=400,
            detail=(
                "company_name and at least one "
                "promoter_name required"
            ),
        )

    try:
        report_dict = run_promoter_network_analysis(
            company_name, promoter_names, sector,
        )
        return PromoterRiskReport(**report_dict)
    except Exception as e:
        logger.error("Promoter network agent failed: %s", e)
        raise HTTPException(
            status_code=500, detail=str(e),
        )


@router.get(
    "/sector-risk", response_model=SectorRiskReport,
)
def get_sector_risk(company_name: str, sector: str):
    """Run multi-source sector risk intelligence."""
    if not company_name or not sector:
        raise HTTPException(
            status_code=400,
            detail="company_name and sector required",
        )

    try:
        report_dict = run_sector_risk_analysis(
            company_name, sector,
        )
        return SectorRiskReport(**report_dict)
    except Exception as e:
        logger.error("Sector risk agent failed: %s", e)
        raise HTTPException(
            status_code=500, detail=str(e),
        )


@router.post(
    "/early-warning", response_model=EarlyWarningReport,
)
def get_early_warning(
    company_name: str,
    financial_data: dict,
    fraud_data: dict = None,
    research_data: dict = None,
    sector_risk: dict = None,
):
    """Run early warning signal detection."""
    if not company_name or not financial_data:
        raise HTTPException(
            status_code=400,
            detail="company_name and financial_data required",
        )

    try:
        report_dict = run_early_warning_analysis(
            company_name,
            financial_data,
            fraud_data=fraud_data,
            research_data=research_data,
            sector_risk=sector_risk,
        )
        return EarlyWarningReport(**report_dict)
    except Exception as e:
        logger.error("Early warning agent failed: %s", e)
        raise HTTPException(
            status_code=500, detail=str(e),
        )


@router.get(
    "/historical-analysis",
    response_model=HistoricalTrustReport,
)
def get_historical_analysis(company_name: str):
    """Query borrower history and compute trust score."""
    if not company_name:
        raise HTTPException(
            status_code=400,
            detail="company_name required",
        )
    try:
        report_dict = run_historical_trust_analysis(
            company_name,
        )
        return HistoricalTrustReport(**report_dict)
    except Exception as e:
        logger.error(
            "Historical trust agent failed: %s", e,
        )
        raise HTTPException(
            status_code=500, detail=str(e),
        )


class WorkingCapitalRequest(BaseModel):
    """Request body for working capital analysis."""

    company_name: str
    financial_data: dict = Field(default_factory=dict)


@router.post(
    "/working-capital-analysis",
    response_model=WorkingCapitalReport,
)
def get_working_capital_analysis(
    request: WorkingCapitalRequest,
):
    """Analyse working capital stress from financial data."""
    if not request.company_name:
        raise HTTPException(
            status_code=400,
            detail="company_name required",
        )
    try:
        report_dict = run_working_capital_analysis(
            request.company_name,
            request.financial_data,
        )
        return WorkingCapitalReport(**report_dict)
    except Exception as e:
        logger.error(
            "Working capital agent failed: %s", e,
        )
        raise HTTPException(
            status_code=500, detail=str(e),
        )
