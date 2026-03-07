"""API routes for the Recommendation Engine (Pillar 3)."""

from fastapi import APIRouter

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
    """Generate a full Credit Appraisal Memo."""
    return generate_cam(request)
