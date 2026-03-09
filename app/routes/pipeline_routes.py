"""
Unified pipeline endpoint — chains all three pillars end-to-end.

Accepts company info, uploaded documents, and qualitative notes in a
single request. Returns a complete analysis including fraud detection,
regulatory checks, promoter risk, and financial ratio modeling.
"""

import json
import logging
import asyncio
from typing import Annotated

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import StreamingResponse

from app.config import ANNUAL_REPORT_DIR, BANK_DIR, GST_DIR
from app.schemas.ingestor import (
    BankStatementSummary,
    CrossVerificationResult,
    DocumentAnalysisResponse,
    GSTDataResponse,
)
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
from app.agents.promoter_network_agent import (
    run_promoter_network_analysis,
)
from app.agents.sector_risk_agent import (
    run_sector_risk_analysis,
)
from app.agents.early_warning_agent import (
    run_early_warning_analysis,
)
from app.agents.working_capital_agent import (
    run_working_capital_analysis,
)
from app.agents.historical_trust_agent import (
    run_historical_trust_analysis,
)
from app.services.research.web_researcher import run_web_research
from app.services.database.borrower_db import store_application

from app.schemas.pipeline import (
    FullAnalysisResponse,
    PromoterRiskReport,
    SectorRiskReport,
    EarlyWarningReport,
    WorkingCapitalReport,
    HistoricalTrustReport,
)

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
    promoter_risk: PromoterRiskReport | None = None
    sector_risk: SectorRiskReport | None = None
    early_warning: EarlyWarningReport | None = None
    working_capital: WorkingCapitalReport | None = None
    historical_trust: HistoricalTrustReport | None = None
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
                text,
                file_name=annual_report.filename,
                file_path=path,
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
            report_dict = run_promoter_network_analysis(
                company_name, promoter_list, sector, mca_data=None,
            )
            promoter_risk = PromoterRiskReport(**report_dict)
            steps.append("promoter_network_analysis")
        except Exception as e:
            logger.error("Promoter analysis failed: %s", e)
            errors.append(f"Promoter analysis: {e}")

    # ── Sector Risk Intelligence ─────────────────

    sector_risk = None
    if sector:
        try:
            sec_dict = run_sector_risk_analysis(company_name, sector)
            # FullAnalysisResponse schemas check for fields
            # Wait, the pipeline schema SectorRiskReport matches exactly what run_sector_risk_analysis returns.
            # I will instantiate it later when creating FullAnalysisResponse, or use dict.
            # But the schema `SectorRiskReport` expects kwargs.
            # pipeline.py `FullAnalysisResponse` expects instances.
            # I'll instantiate it when creating FullAnalysisResponse since it's just dict now, 
            # Oh wait, let me just keep it as a dict and unpack it if I need to.
            # Let me just import SectorRiskReport and EarlyWarningReport
            from app.schemas.pipeline import SectorRiskReport, EarlyWarningReport
            sector_risk = SectorRiskReport(**sec_dict)
            steps.append("sector_risk_analysis")
        except Exception as e:
            logger.error("Sector risk failed: %s", e)
            errors.append(f"Sector risk: {e}")

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
                "cogs": f.cogs,
                "accounts_receivable": f.accounts_receivable,
                "accounts_payable": f.accounts_payable,
                "inventory": f.inventory,
            }.items()
            if v is not None
        }

    # ── Working Capital Analysis ─────────────────

    working_capital = None
    try:
        wc_dict = run_working_capital_analysis(
            company_name, financial,
        )
        working_capital = WorkingCapitalReport(**wc_dict)
        steps.append("working_capital_analysis")
    except Exception as e:
        logger.error("Working capital analysis failed: %s", e)
        errors.append(f"Working capital: {e}")

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
    sector_dict = (
        sector_risk.model_dump() if sector_risk else {}
    )
    
    early_warning = None
    try:
        ew_dict = run_early_warning_analysis(
            company_name=company_name,
            financial_data=financial,
            fraud_data=fraud_dict,
            research_data=research_dict,
            sector_risk=sector_dict,
        )
        from app.schemas.pipeline import EarlyWarningReport
        early_warning = EarlyWarningReport(**ew_dict)
        steps.append("early_warning_analysis")
    except Exception as e:
        logger.error("Early warning failed: %s", e)
        errors.append(f"Early warning: {e}")
        
    ew_dict = early_warning.model_dump() if early_warning else {}

    # ── Historical Trust Analysis ────────────────

    historical_trust = None
    try:
        ht_dict = run_historical_trust_analysis(company_name)
        historical_trust = HistoricalTrustReport(**ht_dict)
        steps.append("historical_trust_analysis")
    except Exception as e:
        logger.error("Historical trust failed: %s", e)
        errors.append(f"Historical trust: {e}")

    wc_dict = (
        working_capital.model_dump() if working_capital else {}
    )
    ht_dict = (
        historical_trust.model_dump() if historical_trust else {}
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
            sector_data=sector_dict,
            early_warning_data=ew_dict,
            working_capital_data=wc_dict,
            historical_trust_data=ht_dict,
        )
        decision = make_decision(decision_req)
        steps.append("loan_decision")
    except Exception as e:
        logger.error("Loan decision failed: %s", e)
        errors.append(f"Loan decision: {e}")

    # ── Store Borrower History ────────────────────

    try:
        if decision:
            wc_score = (
                working_capital.working_capital_score
                if working_capital else 0.0
            )
            store_application(
                company_name=company_name,
                risk_score=decision.final_credit_risk_score,
                loan_amount_requested=requested_amount,
                loan_amount_approved=decision.recommended_amount,
                interest_rate=decision.interest_rate,
                decision=decision.decision,
                fraud_risk_score=(
                    fraud_report.fraud_score if fraud_report else 0.0
                ),
                sector_risk_score=(
                    sector_risk.sector_risk_score
                    if sector_risk else 0.0
                ),
                promoter_risk_score=(
                    promoter_risk.promoter_risk_score
                    if promoter_risk else 0.0
                ),
                early_warning_score=(
                    early_warning.early_warning_score
                    if early_warning else 0.0
                ),
                five_cs_score=(
                    five_cs.weighted_total if five_cs else 0.0
                ),
                working_capital_score=wc_score,
                explanation_summary=(
                    decision.explanation[:500]
                    if decision.explanation else ""
                ),
            )
    except Exception as e:
        logger.error("Failed to store borrower history: %s", e)

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
            promoter_network=promo_dict,
            sector_risk=sector_dict,
            early_warning=ew_dict,
            working_capital=wc_dict,
            historical_trust=ht_dict,
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
        sector_risk=sector_risk,
        early_warning=early_warning,
        working_capital=working_capital,
        historical_trust=historical_trust,
        five_cs_scores=five_cs,
        loan_decision=decision,
        credit_memo=cam,
        steps_completed=steps,
        errors=errors,
    )


@router.post("/investigate")
def investigate_pipeline(
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
) -> StreamingResponse:
    """Run pipeline and return steps via Server-Sent Events (SSE)."""

    async def event_generator():
        yield f"data: {json.dumps({'step': 'Initializing Investigation', 'status': 'in_progress'})}\n\n"
        await asyncio.sleep(0.1)

        # We will run the synchronous processing in steps and yield progress
        # Since this is a hackathon demo, yielding between sync calls is acceptable
        # for achieving the "Live Investigation Timeline" UI effect.
        
        try:
            promoter_list = json.loads(promoter_names)
        except (json.JSONDecodeError, TypeError):
            promoter_list = []

        try:
            notes_list = json.loads(primary_notes)
        except (json.JSONDecodeError, TypeError):
            notes_list = []

        # Step 1: Document Processing
        doc_analysis = None
        if annual_report and annual_report.filename:
            yield f"data: {json.dumps({'step': 'Parsing Financial Documents', 'status': 'in_progress'})}\n\n"
            await asyncio.sleep(0.1)
            try:
                path = save_file(annual_report, ANNUAL_REPORT_DIR)
                text = extract_text_from_pdf(path)
                doc_analysis = extract_with_ai(text, file_name=annual_report.filename, file_path=path)
                yield f"data: {json.dumps({'step': 'Parsing Financial Documents', 'status': 'completed'})}\n\n"
            except Exception as e:
                logger.error(e)
                yield f"data: {json.dumps({'step': 'Parsing Financial Documents', 'status': 'error', 'detail': str(e)})}\n\n"

        # Step 2: GST & Bank Parsing
        gst_data = None
        bank_data = None
        if gst_file or bank_file:
            yield f"data: {json.dumps({'step': 'Processing GST & Bank Statements', 'status': 'in_progress'})}\n\n"
            await asyncio.sleep(0.1)
            try:
                if gst_file and gst_file.filename:
                    gst_path = save_file(gst_file, GST_DIR)
                    gst_data = parse_gst_data(gst_path)
                if bank_file and bank_file.filename:
                    bank_path = save_file(bank_file, BANK_DIR)
                    bank_data = parse_bank_statement(bank_path)
                yield f"data: {json.dumps({'step': 'Processing GST & Bank Statements', 'status': 'completed'})}\n\n"
            except Exception as e:
                logger.error(e)
                yield f"data: {json.dumps({'step': 'Processing GST & Bank Statements', 'status': 'error', 'detail': str(e)})}\n\n"

        # Step 3: Fraud & Regulatory Check
        cross_ver = None
        fraud_report = None
        reg_checks = None
        yield f"data: {json.dumps({'step': 'Running Fraud & Regulatory Checks', 'status': 'in_progress'})}\n\n"
        await asyncio.sleep(0.1)
        try:
            if gst_data and bank_data:
                cross_ver = cross_verify(gst_data, bank_data)
                fraud_report = detect_fraud(gst_data, bank_data)
                cross_ver.fraud_report = fraud_report
            reg_checks = run_regulatory_checks(company_name, gst_data, promoter_list)
            yield f"data: {json.dumps({'step': 'Running Fraud & Regulatory Checks', 'status': 'completed'})}\n\n"
        except Exception as e:
            logger.error(e)
            yield f"data: {json.dumps({'step': 'Running Fraud & Regulatory Checks', 'status': 'error'})}\n\n"

        # Step 4: Web Research
        research = None
        yield f"data: {json.dumps({'step': 'Gathering Web Intelligence', 'status': 'in_progress'})}\n\n"
        await asyncio.sleep(0.1)
        try:
            if company_name:
                search_req = WebSearchRequest(company_name=company_name, sector=sector, promoter_names=promoter_list)
                news_items = run_web_research(search_req)
                research = build_research_report(search_req, news_items)
            yield f"data: {json.dumps({'step': 'Gathering Web Intelligence', 'status': 'completed'})}\n\n"
        except Exception as e:
            logger.error(e)
            yield f"data: {json.dumps({'step': 'Gathering Web Intelligence', 'status': 'error'})}\n\n"

        # Step 5: Web Research for Sector Risk & Primary Insights
        sector_risk = None
        insights_resp = None
        yield f"data: {json.dumps({'step': 'Analyzing Sector Risk & Qualitative Notes', 'status': 'in_progress'})}\n\n"
        await asyncio.sleep(0.1)
        try:
            if sector:
                sec_dict = run_sector_risk_analysis(company_name, sector)
                sector_risk = SectorRiskReport(**sec_dict)
            if notes_list:
                insights = [PrimaryInsight(insight_type=n.get("type", "general"), observation=n.get("observation", n.get("text", "")), severity=n.get("severity", "neutral")) for n in notes_list if isinstance(n, dict)]
                if insights:
                    insights_resp = process_primary_insights(PrimaryInsightsRequest(company_name=company_name, insights=insights))
            yield f"data: {json.dumps({'step': 'Analyzing Sector Risk & Qualitative Notes', 'status': 'completed'})}\n\n"
        except Exception as e:
            logger.error(e)
            yield f"data: {json.dumps({'step': 'Analyzing Sector Risk & Qualitative Notes', 'status': 'error'})}\n\n"

        # Step 6: Promoter Network Graph
        promoter_risk = None
        yield f"data: {json.dumps({'step': 'Building Promoter Network Graph', 'status': 'in_progress'})}\n\n"
        await asyncio.sleep(0.1)
        try:
            if promoter_list:
                report_dict = run_promoter_network_analysis(company_name, promoter_list, sector, mca_data=None)
                promoter_risk = PromoterRiskReport(**report_dict)
            yield f"data: {json.dumps({'step': 'Building Promoter Network Graph', 'status': 'completed'})}\n\n"
        except Exception as e:
            logger.error(e)
            yield f"data: {json.dumps({'step': 'Building Promoter Network Graph', 'status': 'error'})}\n\n"

        # Construct Financial Dictionary
        financial = {}
        if doc_analysis and doc_analysis.financials:
            f = doc_analysis.financials
            financial = {k: v for k, v in {"revenue": f.revenue, "net_profit": f.net_profit, "total_debt": f.total_debt, "ebitda": f.ebitda, "debt_to_equity": f.debt_to_equity, "current_ratio": f.current_ratio, "interest_coverage": f.interest_coverage, "cogs": f.cogs, "accounts_receivable": f.accounts_receivable, "accounts_payable": f.accounts_payable, "inventory": f.inventory}.items() if v is not None}

        # Step 7a: Working Capital Analysis
        working_capital = None
        yield f"data: {json.dumps({'step': 'Analyzing Working Capital Stress', 'status': 'in_progress'})}\n\n"
        await asyncio.sleep(0.1)
        try:
            wc_dict = run_working_capital_analysis(company_name, financial)
            working_capital = WorkingCapitalReport(**wc_dict)
            yield f"data: {json.dumps({'step': 'Analyzing Working Capital Stress', 'status': 'completed'})}\n\n"
        except Exception as e:
            logger.error(e)
            yield f"data: {json.dumps({'step': 'Analyzing Working Capital Stress', 'status': 'error'})}\n\n"

        # Step 7: Early Warning Signals
        early_warning = None
        yield f"data: {json.dumps({'step': 'Detecting Early Warning Signals', 'status': 'in_progress'})}\n\n"
        await asyncio.sleep(0.1)
        try:
            ew_dict = run_early_warning_analysis(company_name=company_name, financial_data=financial, fraud_data=fraud_report.model_dump() if fraud_report else {}, research_data=research.model_dump() if research else {}, sector_risk=sector_risk.model_dump() if sector_risk else {})
            early_warning = EarlyWarningReport(**ew_dict)
            yield f"data: {json.dumps({'step': 'Detecting Early Warning Signals', 'status': 'completed'})}\n\n"
        except Exception as e:
            logger.error(e)
            yield f"data: {json.dumps({'step': 'Detecting Early Warning Signals', 'status': 'error'})}\n\n"

        # Step 8a: Historical Trust Analysis
        historical_trust = None
        yield f"data: {json.dumps({'step': 'Querying Borrower History & Trust', 'status': 'in_progress'})}\n\n"
        await asyncio.sleep(0.1)
        try:
            ht_dict = run_historical_trust_analysis(company_name)
            historical_trust = HistoricalTrustReport(**ht_dict)
            yield f"data: {json.dumps({'step': 'Querying Borrower History & Trust', 'status': 'completed'})}\n\n"
        except Exception as e:
            logger.error(e)
            yield f"data: {json.dumps({'step': 'Querying Borrower History & Trust', 'status': 'error'})}\n\n"

        # Step 8: Recommendation Engine & ML Score
        five_cs = None
        decision = None
        yield f"data: {json.dumps({'step': 'Executing Credit Recommendation & ML Engine', 'status': 'in_progress'})}\n\n"
        await asyncio.sleep(0.1)
        try:
            cross_dict = cross_ver.model_dump() if cross_ver else {}
            research_dict = research.model_dump() if research else {}
            insights_dict = insights_resp.model_dump() if insights_resp else {}
            fraud_dict = fraud_report.model_dump() if fraud_report else {}
            reg_dict = reg_checks.model_dump() if reg_checks else {}
            promo_dict = promoter_risk.model_dump() if promoter_risk else {}
            sector_dict = sector_risk.model_dump() if sector_risk else {}
            ew_dict = early_warning.model_dump() if early_warning else {}
            wc_dict = working_capital.model_dump() if working_capital else {}
            ht_dict = historical_trust.model_dump() if historical_trust else {}

            score_req = FiveCsScoreRequest(company_name=company_name, financial_data=financial, research_data=research_dict, primary_insights=insights_dict, cross_verification=cross_dict)
            five_cs = score_five_cs(score_req)
            risk_adj = [r.model_dump() for r in insights_resp.risk_adjustments] if insights_resp and insights_resp.risk_adjustments else []
            
            decision_req = LoanDecisionRequest(company_name=company_name, requested_amount=requested_amount, five_cs_scores=five_cs, financial_data=financial, research_data=research_dict, risk_adjustments=risk_adj, fraud_data=fraud_dict, regulatory_data=reg_dict, promoter_data=promo_dict, sector_data=sector_dict, early_warning_data=ew_dict, working_capital_data=wc_dict, historical_trust_data=ht_dict)
            decision = make_decision(decision_req)
            yield f"data: {json.dumps({'step': 'Executing Credit Recommendation & ML Engine', 'status': 'completed'})}\n\n"
        except Exception as e:
            logger.error(e)
            yield f"data: {json.dumps({'step': 'Executing Credit Recommendation & ML Engine', 'status': 'error'})}\n\n"

        # Store borrower history
        try:
            if decision:
                store_application(
                    company_name=company_name,
                    risk_score=decision.final_credit_risk_score,
                    loan_amount_requested=requested_amount,
                    loan_amount_approved=decision.recommended_amount,
                    interest_rate=decision.interest_rate,
                    decision=decision.decision,
                    fraud_risk_score=fraud_report.fraud_score if fraud_report else 0.0,
                    sector_risk_score=sector_risk.sector_risk_score if sector_risk else 0.0,
                    promoter_risk_score=promoter_risk.promoter_risk_score if promoter_risk else 0.0,
                    early_warning_score=early_warning.early_warning_score if early_warning else 0.0,
                    five_cs_score=five_cs.weighted_total if five_cs else 0.0,
                    working_capital_score=working_capital.working_capital_score if working_capital else 0.0,
                    explanation_summary=decision.explanation[:500] if decision.explanation else "",
                )
        except Exception as e:
            logger.error("Failed to store borrower history: %s", e)

        # Step 9: Generate CAM
        cam = None
        yield f"data: {json.dumps({'step': 'Generating CAM Report', 'status': 'in_progress'})}\n\n"
        await asyncio.sleep(0.1)
        try:
            cam_req = CAMRequest(company_name=company_name, financial_data=financial, research_report=research_dict, five_cs_scores=(five_cs.model_dump() if five_cs else {}), loan_decision=(decision.model_dump() if decision else {}), primary_insights=[n for n in notes_list if isinstance(n, dict)], cross_verification=cross_dict, promoter_network=promo_dict, sector_risk=sector_dict, early_warning=ew_dict, working_capital=wc_dict, historical_trust=ht_dict)
            cam = generate_cam(cam_req)
            yield f"data: {json.dumps({'step': 'Generating CAM Report', 'status': 'completed'})}\n\n"
        except Exception as e:
            logger.error(e)
            yield f"data: {json.dumps({'step': 'Generating CAM Report', 'status': 'error'})}\n\n"

        # Compile final result matching FullAnalysisResponse
        final_result = FullAnalysisResponse(
            company_name=company_name,
            document_analysis=doc_analysis,
            gst_data=gst_data,
            bank_statement=bank_data,
            cross_verification=cross_ver,
            fraud_report=fraud_report,
            regulatory_checks=reg_checks,
            research_report=research,
            primary_insights=insights_resp,
            promoter_risk=promoter_risk,
            sector_risk=sector_risk,
            early_warning=early_warning,
            working_capital=working_capital,
            historical_trust=historical_trust,
            five_cs_scores=five_cs,
            loan_decision=decision,
            credit_memo=cam,
        ).model_dump()

        yield f"data: {json.dumps({'step': 'Finalizing', 'status': 'completed', 'result': final_result})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

