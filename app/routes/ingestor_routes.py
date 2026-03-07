"""API routes for the Data Ingestor (Pillar 1)."""

from typing import Annotated

from fastapi import APIRouter, File, UploadFile

from app.config import ANNUAL_REPORT_DIR, BANK_DIR, GST_DIR
from app.schemas.ingestor import (
    BankStatementSummary,
    CrossVerificationResult,
    DocumentAnalysisResponse,
    GSTDataResponse,
)
from app.services.document_processing.ai_extractor import extract_with_ai
from app.services.document_processing.document_service import process_financial_document
from app.services.document_processing.pdf_extractor import extract_text_from_pdf
from app.services.file_service import save_file
from app.services.ingestor.bank_statement_parser import parse_bank_statement
from app.services.ingestor.cross_verification import cross_verify
from app.services.ingestor.gst_parser import parse_gst_data

router = APIRouter(prefix="/ingest", tags=["Data Ingestor"])


@router.post("/analyze-document")
def analyze_document(
    file: Annotated[UploadFile, File(description="PDF annual report or financial document")],
) -> DocumentAnalysisResponse:
    """Upload a document and extract structured data using AI."""
    path = save_file(file, ANNUAL_REPORT_DIR)

    # Extract raw text
    text = extract_text_from_pdf(path)

    # Run AI extraction
    result = extract_with_ai(text, file_name=file.filename or "unknown")

    # Also get regex-based metrics as raw_metrics
    raw_metrics = process_financial_document(path)
    result.raw_metrics = raw_metrics

    return result


@router.post("/parse-gst")
def parse_gst(
    file: Annotated[UploadFile, File(description="GST filing (CSV, JSON, or PDF)")],
) -> GSTDataResponse:
    """Parse GST filing data from uploaded file."""
    path = save_file(file, GST_DIR)
    return parse_gst_data(path)


@router.post("/parse-bank-statement")
def parse_bank_stmt(
    file: Annotated[UploadFile, File(description="Bank statement (CSV or PDF)")],
) -> BankStatementSummary:
    """Parse bank statement from uploaded file."""
    path = save_file(file, BANK_DIR)
    return parse_bank_statement(path)


@router.post("/cross-verify")
def cross_verify_data(
    gst_file: Annotated[UploadFile, File(description="GST filing")],
    bank_file: Annotated[UploadFile, File(description="Bank statement")],
) -> CrossVerificationResult:
    """Cross-verify GST turnover against bank statement credits."""
    gst_path = save_file(gst_file, GST_DIR)
    bank_path = save_file(bank_file, BANK_DIR)

    gst_data = parse_gst_data(gst_path)
    bank_data = parse_bank_statement(bank_path)

    return cross_verify(gst_data, bank_data)
