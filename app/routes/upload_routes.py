from typing import Annotated

from fastapi import APIRouter, File, UploadFile

from app.config import ANNUAL_REPORT_DIR, BANK_DIR, GST_DIR, LEGAL_DIR
from app.services.document_processing.document_service import process_financial_document
from app.services.file_service import save_file

router = APIRouter(prefix="/upload", tags=["File Uploads"])


@router.post("/annual-report")
def upload_annual_report(
    file: Annotated[UploadFile, File(description="Annual report PDF")],
) -> dict:
    path = save_file(file, ANNUAL_REPORT_DIR)
    return {"message": "Annual report uploaded", "path": path}


@router.post("/gst")
def upload_gst(
    file: Annotated[UploadFile, File(description="GST filing document")],
) -> dict:
    path = save_file(file, GST_DIR)
    return {"message": "GST document uploaded", "path": path}


@router.post("/bank-statement")
def upload_bank_statement(
    file: Annotated[UploadFile, File(description="Bank statement")],
) -> dict:
    path = save_file(file, BANK_DIR)
    return {"message": "Bank statement uploaded", "path": path}


@router.post("/legal-doc")
def upload_legal_doc(
    file: Annotated[UploadFile, File(description="Legal document")],
) -> dict:
    path = save_file(file, LEGAL_DIR)
    return {"message": "Legal document uploaded", "path": path}


@router.post("/process/annual-report")
def process_annual_report(
    file: Annotated[UploadFile, File(description="Annual report to process")],
) -> dict:
    path = save_file(file, ANNUAL_REPORT_DIR)
    result = process_financial_document(path)
    return {"file_path": path, "analysis": result}