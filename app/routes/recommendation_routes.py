"""API routes for the Recommendation Engine (Pillar 3)."""

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.config import CAM_OUTPUT_DIR
from app.schemas.recommendation import (
    CAMRequest,
    CreditAppraisalMemo,
    FiveCsScoreRequest,
    FiveCsScoreResponse,
    LoanDecision,
    LoanDecisionRequest,
)
from app.services.recommendation.cam_generator import generate_cam
from app.services.recommendation.decision_engine import make_decision
from app.services.recommendation.five_cs_scorer import score_five_cs

router = APIRouter(prefix="/recommendation", tags=["Recommendation Engine"])


@router.post("/score")
def get_five_cs_score(request: FiveCsScoreRequest) -> FiveCsScoreResponse:
    """Score a company on the Five Cs of Credit."""
    return score_five_cs(request)


@router.post("/decision")
def get_loan_decision(request: LoanDecisionRequest) -> LoanDecision:
    """Get loan decision: APPROVE / REJECT / REFER with amount and rate."""
    return make_decision(request)


@router.post("/generate-cam")
def generate_credit_memo(request: CAMRequest) -> CreditAppraisalMemo:
    """Generate a full Credit Appraisal Memo with DOCX/PDF export."""
    return generate_cam(request)


@router.get("/download-cam/{filename}")
def download_cam(filename: str):
    """Download a generated CAM file (DOCX or PDF)."""
    filepath = CAM_OUTPUT_DIR / filename

    if not filepath.exists():
        raise HTTPException(
            status_code=404,
            detail=f"CAM file '{filename}' not found",
        )

    media_type = (
        "application/pdf" if filename.endswith(".pdf")
        else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

    return FileResponse(
        path=str(filepath),
        filename=filename,
        media_type=media_type,
    )

