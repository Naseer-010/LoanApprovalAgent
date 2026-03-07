"""
Unified pipeline endpoint — chains all three pillars end-to-end.

Accepts company info, uploaded documents, and qualitative notes in a
single request. Returns a complete analysis including fraud detection,
regulatory checks, promoter risk, and financial ratio modeling.
"""

import json
import logging
from typing import Annotated

from fastapi import APIRouter, File, Form, UploadFile

from app.config import ANNUAL_REPORT_DIR, BANK_DIR, GST_DIR
from app.schemas.ingestor import (
    BankStatementSummary,
    CrossVerificationResult,
    DocumentAnalysisResponse,
    GSTDataResponse,
)
from app.schemas.pipeline import FullAnalysisResponse
from app.schemas.recommendation import (
    CAMRequest,
    FiveCsScoreRequest,
    FiveCsScoreResponse,
    LoanDecision,
    LoanDecisionRequest,
)
from app.schemas.research import (
    PrimaryInsight,
    PrimaryInsightsRequest,
    PrimaryInsightsResponse,
    ResearchReport,
    WebSearchRequest,
)
from app.services.document_processing.ai_extractor import (
    extract_with_ai,
)
from app.services.document_processing.pdf_extractor import (
    extract_text_from_pdf,
)
from app.services.file_service import save_file
from app.services.ingestor.bank_statement_parser import (
    parse_bank_statement,
)
from app.services.ingestor.cross_verification import cross_verify
from app.services.ingestor.fraud_detector import detect_fraud
from app.services.ingestor.gst_parser import parse_gst_data
from app.services.ingestor.indian_regulatory import (
    run_regulatory_checks,
)
from app.services.recommendation.cam_generator import generate_cam
from app.services.recommendation.decision_engine import (
    make_decision,
)
from app.services.recommendation.five_cs_scorer import score_five_cs
from app.services.research.news_aggregator import (
    build_research_report,
)
from app.services.research.primary_insights import (
    process_primary_insights,
)
from app.services.research.promoter_analyzer import (
    analyze_promoter_risk,
)
from app.services.research.web_researcher import run_web_research

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pipeline", tags=["Pipeline"])


@router.post("/full-analysis")
def full_analysis(
    company_name: Annotated[str, Form()],
    sector: Annotated[str, Form()] = "",
    promoter_names: Annotated[str, Form()] = "[]",
    requested_amount: Annotated[float, Form()] = 0.0,
    primary_notes: Annotated[str, Form()] = "[]",
    annual_report: Annotated[
        UploadFile | None,
        File(description="Annual report PDF"),
    ] = None,
    gst_file: Annotated[
        UploadFile | None,
        File(description="GST filing"),
    ] = None,
    bank_file: Annotated[
        UploadFile | None,
        File(description="Bank statement"),
    ] = None,
) -> FullAnalysisResponse:
    """Run the full credit analysis pipeline end-to-end."""
    steps: list[str] = []
    errors: list[str] = []

    doc_analysis: DocumentAnalysisResponse | None = None
    gst_data: GSTDataResponse | None = None
    bank_data: BankStatementSummary | None = None
    cross_ver: CrossVerificationResult | None = None
    research: ResearchReport | None = None
    insights_resp: PrimaryInsightsResponse | None = None
    five_cs: FiveCsScoreResponse | None = None
    decision: LoanDecision | None = None

    try:
        promoter_list = json.loads(promoter_names)
    except (json.JSONDecodeError, TypeError):
        promoter_list = []

    try:
        notes_list = json.loads(primary_notes)
    except (json.JSONDecodeError, TypeError):
        notes_list = []

    # ── PILLAR 1: Data Ingestor ──────────────────

    if annual_report and annual_report.filename:
        try:
            path = save_file(annual_report, ANNUAL_REPORT_DIR)
            text = extract_text_from_pdf(path)
            doc_analysis = extract_with_ai(
                text, file_name=annual_report.filename,
            )
            steps.append("document_analysis")
        except Exception as e:
            logger.error("Document analysis failed: %s", e)
            errors.append(f"Document analysis: {e}")

    if gst_file and gst_file.filename:
        try:
            gst_path = save_file(gst_file, GST_DIR)
            gst_data = parse_gst_data(gst_path)
            steps.append("gst_parsing")
        except Exception as e:
            logger.error("GST parsing failed: %s", e)
            errors.append(f"GST parsing: {e}")

    if bank_file and bank_file.filename:
        try:
            bank_path = save_file(bank_file, BANK_DIR)
            bank_data = parse_bank_statement(bank_path)
            steps.append("bank_statement_parsing")
        except Exception as e:
            logger.error("Bank parsing failed: %s", e)
            errors.append(f"Bank parsing: {e}")

    if gst_data and bank_data:
        try:
            cross_ver = cross_verify(gst_data, bank_data)
            steps.append("cross_verification")
        except Exception as e:
            logger.error("Cross-verification failed: %s", e)
            errors.append(f"Cross-verification: {e}")

    # ── Fraud Detection ──────────────────────────

    fraud_report = None
    try:
        fraud_report = detect_fraud(gst_data, bank_data)
        if cross_ver:
            cross_ver.fraud_report = fraud_report
        steps.append("fraud_detection")
    except Exception as e:
        logger.error("Fraud detection failed: %s", e)
        errors.append(f"Fraud detection: {e}")

    # ── Indian Regulatory Checks ─────────────────

    reg_checks = None
    try:
        reg_checks = run_regulatory_checks(
            company_name, gst_data, promoter_list,
        )
        steps.append("regulatory_checks")
    except Exception as e:
        logger.error("Regulatory checks failed: %s", e)
        errors.append(f"Regulatory checks: {e}")

    # ── PILLAR 2: Research Agent ─────────────────

    if company_name:
        try:
            search_req = WebSearchRequest(
                company_name=company_name,
                sector=sector,
                promoter_names=promoter_list,
            )
            news_items = run_web_research(search_req)
            research = build_research_report(
                search_req, news_items,
            )
            steps.append("web_research")
        except Exception as e:
            logger.error("Web research failed: %s", e)
            errors.append(f"Web research: {e}")

    # ── Promoter Risk Analysis ───────────────────

    promoter_risk = None
    if promoter_list:
        try:
            promoter_risk = analyze_promoter_risk(
                company_name, promoter_list, sector,
            )
            steps.append("promoter_risk_analysis")
        except Exception as e:
            logger.error("Promoter analysis failed: %s", e)
            errors.append(f"Promoter analysis: {e}")

    if notes_list:
        try:
            insights = [
                PrimaryInsight(
                    insight_type=n.get("type", "general"),
                    observation=n.get(
                        "observation", n.get("text", ""),
                    ),
                    severity=n.get("severity", "neutral"),
                )
                for n in notes_list
                if isinstance(n, dict)
            ]
            if insights:
                ins_req = PrimaryInsightsRequest(
                    company_name=company_name,
                    insights=insights,
                )
                insights_resp = process_primary_insights(ins_req)
                steps.append("primary_insights")
        except Exception as e:
            logger.error("Primary insights failed: %s", e)
            errors.append(f"Primary insights: {e}")

    # ── PILLAR 3: Recommendation Engine ──────────

    financial = {}
    if doc_analysis and doc_analysis.financials:
        f = doc_analysis.financials
        financial = {
            k: v
            for k, v in {
                "revenue": f.revenue,
                "net_profit": f.net_profit,
                "total_debt": f.total_debt,
                "ebitda": f.ebitda,
                "debt_to_equity": f.debt_to_equity,
                "current_ratio": f.current_ratio,
                "interest_coverage": f.interest_coverage,
            }.items()
            if v is not None
        }

    research_dict = research.model_dump() if research else {}
    insights_dict = (
        insights_resp.model_dump() if insights_resp else {}
    )
    cross_dict = cross_ver.model_dump() if cross_ver else {}
    fraud_dict = (
        fraud_report.model_dump() if fraud_report else {}
    )
    reg_dict = reg_checks.model_dump() if reg_checks else {}
    promo_dict = (
        promoter_risk.model_dump() if promoter_risk else {}
    )

    try:
        score_req = FiveCsScoreRequest(
            company_name=company_name,
            financial_data=financial,
            research_data=research_dict,
            primary_insights=insights_dict,
            cross_verification=cross_dict,
        )
        five_cs = score_five_cs(score_req)
        steps.append("five_cs_scoring")
    except Exception as e:
        logger.error("Five Cs scoring failed: %s", e)
        errors.append(f"Five Cs scoring: {e}")

    try:
        risk_adj = []
        if insights_resp and insights_resp.risk_adjustments:
            risk_adj = [
                r.model_dump()
                for r in insights_resp.risk_adjustments
            ]

        decision_req = LoanDecisionRequest(
            company_name=company_name,
            requested_amount=requested_amount,
            five_cs_scores=five_cs,
            financial_data=financial,
            research_data=research_dict,
            risk_adjustments=risk_adj,
            fraud_data=fraud_dict,
            regulatory_data=reg_dict,
            promoter_data=promo_dict,
        )
        decision = make_decision(decision_req)
        steps.append("loan_decision")
    except Exception as e:
        logger.error("Loan decision failed: %s", e)
        errors.append(f"Loan decision: {e}")

    cam = None
    try:
        cam_req = CAMRequest(
            company_name=company_name,
            financial_data=financial,
            research_report=research_dict,
            five_cs_scores=(
                five_cs.model_dump() if five_cs else {}
            ),
            loan_decision=(
                decision.model_dump() if decision else {}
            ),
            primary_insights=[
                n for n in notes_list if isinstance(n, dict)
            ],
            cross_verification=cross_dict,
        )
        cam = generate_cam(cam_req)
        steps.append("cam_generation")
    except Exception as e:
        logger.error("CAM generation failed: %s", e)
        errors.append(f"CAM generation: {e}")

    return FullAnalysisResponse(
        company_name=company_name,
        status=(
            "completed" if not errors
            else "completed_with_errors"
        ),
        document_analysis=doc_analysis,
        gst_data=gst_data,
        bank_statement=bank_data,
        cross_verification=cross_ver,
        fraud_report=fraud_report,
        regulatory_checks=reg_checks,
        research_report=research,
        primary_insights=insights_resp,
        promoter_risk=promoter_risk,
        five_cs_scores=five_cs,
        loan_decision=decision,
        credit_memo=cam,
        steps_completed=steps,
        errors=errors,
    )
