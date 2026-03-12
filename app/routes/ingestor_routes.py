"""API routes for the Data Ingestor (Pillar 1)."""

import logging
from typing import Annotated

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.config import ANNUAL_REPORT_DIR, BANK_DIR, GST_DIR, UPLOAD_DIR
from app.schemas.ingestor import (
    BankStatementSummary,
    CrossVerificationResult,
    DocumentAnalysisResponse,
    GSTDataResponse,
)
from app.services.document_processing.ai_extractor import extract_with_ai
from app.services.document_processing.document_classifier import (
    classify_document,
    get_doc_classes,
)
from app.services.document_processing.document_service import (
    process_financial_document,
)
from app.services.document_processing.pdf_extractor import (
    extract_text_from_pdf,
)
from app.services.document_processing.schema_mapper import (
    export_csv,
    export_json,
    map_to_schema,
)
from app.services.file_service import save_file
from app.services.ingestor.bank_statement_parser import parse_bank_statement
from app.services.ingestor.cross_verification import cross_verify
from app.services.ingestor.gst_parser import parse_gst_data

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingest", tags=["Data Ingestor"])

# ── In-memory store for classified docs (per session) ─────
_classified_docs: dict[str, dict] = {}


@router.post("/analyze-document")
def analyze_document(
    file: Annotated[
        UploadFile,
        File(description="PDF annual report or financial document"),
    ],
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
    file: Annotated[
        UploadFile,
        File(description="GST filing (CSV, JSON, or PDF)"),
    ],
) -> GSTDataResponse:
    """Parse GST filing data from uploaded file."""
    path = save_file(file, GST_DIR)
    return parse_gst_data(path)


@router.post("/parse-bank-statement")
def parse_bank_stmt(
    file: Annotated[
        UploadFile,
        File(description="Bank statement (CSV or PDF)"),
    ],
) -> BankStatementSummary:
    """Parse bank statement from uploaded file."""
    path = save_file(file, BANK_DIR)
    return parse_bank_statement(path)


@router.post("/cross-verify")
def cross_verify_data(
    gst_file: Annotated[UploadFile, File(description="GST filing")],
    bank_file: Annotated[
        UploadFile, File(description="Bank statement")
    ],
) -> CrossVerificationResult:
    """Cross-verify GST turnover against bank statement credits."""
    gst_path = save_file(gst_file, GST_DIR)
    bank_path = save_file(bank_file, BANK_DIR)

    gst_data = parse_gst_data(gst_path)
    bank_data = parse_bank_statement(bank_path)

    return cross_verify(gst_data, bank_data)


# ─── Document Classification (Stage 2) ──────────────────


@router.post("/classify")
def classify_uploaded_document(
    file: Annotated[
        UploadFile,
        File(description="Any financial document for classification"),
    ],
):
    """Classify an uploaded document and return predicted type."""
    path = save_file(file, UPLOAD_DIR)
    text = ""
    try:
        text = extract_text_from_pdf(path)
    except Exception:
        # Non-PDF — read as text
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()[:5000]
        except Exception:
            text = ""

    result = classify_document(text, filename=file.filename or "")
    doc_id = file.filename or str(hash(text[:200]))
    result["doc_id"] = doc_id
    result["file_path"] = str(path)
    
    # Enforce confidence threshold
    if result.get("confidence", 0) < 0.7:
        result["status"] = "pending_validation"
        result["requires_manual_review"] = True
    else:
        result["status"] = "auto_validated"
        result["validated_type"] = result.get("predicted_type", "Unknown")
        result["requires_manual_review"] = False
        
    _classified_docs[doc_id] = result

    return result


@router.get("/doc-classes")
def list_doc_classes():
    """Return all supported document type classes."""
    return {"classes": get_doc_classes()}


class ValidationRequest(BaseModel):
    """Human-in-the-loop validation request."""

    doc_id: str
    action: str = "approve"  # approve, edit, reject
    corrected_type: str = ""


@router.post("/validate-classification")
def validate_classification(req: ValidationRequest):
    """
    Human-in-the-loop: analyst approves, edits, or rejects
    the auto-classified document type.
    """
    doc = _classified_docs.get(req.doc_id)
    if not doc:
        return JSONResponse(
            status_code=404,
            content={"detail": "Document not found in session"},
        )

    if req.action == "approve":
        doc["status"] = "validated"
        doc["validated_type"] = doc["predicted_type"]
    elif req.action == "edit":
        if not req.corrected_type:
            return JSONResponse(
                status_code=400,
                content={"detail": "corrected_type required for edit"},
            )
        doc["status"] = "validated"
        doc["validated_type"] = req.corrected_type
    elif req.action == "reject":
        doc["status"] = "rejected"
        doc["validated_type"] = "Rejected"
    else:
        return JSONResponse(
            status_code=400,
            content={"detail": "action must be approve, edit, or reject"},
        )

    _classified_docs[req.doc_id] = doc
    return doc


# ─── Schema Mapping (Stage 3) ───────────────────────────


class SchemaMappingRequest(BaseModel):
    """Request to map extracted data to a user-defined schema."""

    extracted_data: dict = Field(default_factory=dict)
    schema_fields: list[str] = Field(default_factory=list)
    export_format: str = "json"  # json or csv


@router.post("/schema-map")
def schema_map(req: SchemaMappingRequest):
    """
    Map extracted data to a user-defined schema and export.
    Supports JSON and CSV output.
    """
    if not req.schema_fields:
        return JSONResponse(
            status_code=400,
            content={"detail": "schema_fields list is required"},
        )

    mapped = map_to_schema(req.extracted_data, req.schema_fields)

    if req.export_format == "csv":
        return JSONResponse(
            content={
                "format": "csv",
                "data": export_csv(mapped),
                "mapped": mapped,
            },
        )

    return {
        "format": "json",
        "data": export_json(mapped),
        "mapped": mapped,
    }
