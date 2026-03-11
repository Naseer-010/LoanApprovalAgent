"""
Entity Onboarding Routes — stores borrower profile + loan request.
"""
import logging
import sqlite3
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.database.borrower_db import DB_DIR

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/onboarding", tags=["Entity Onboarding"])

# ── In-memory store (SQLite-backed for persistence) ──

_DB_NAME = "entity_profiles.db"


def _init_entity_db():
    db = DB_DIR / _DB_NAME
    conn = sqlite3.connect(str(db))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL,
            cin TEXT DEFAULT '',
            pan TEXT DEFAULT '',
            sector TEXT DEFAULT '',
            sub_sector TEXT DEFAULT '',
            annual_turnover REAL DEFAULT 0,
            headquarters TEXT DEFAULT '',
            loan_type TEXT DEFAULT '',
            requested_amount REAL DEFAULT 0,
            tenure_months INTEGER DEFAULT 0,
            proposed_rate REAL DEFAULT 0,
            promoter_names TEXT DEFAULT '',
            created_at TEXT DEFAULT '',
            status TEXT DEFAULT 'draft'
        )
    """)
    conn.commit()
    conn.close()


def _store_entity(data: dict) -> int:
    _init_entity_db()
    db = DB_DIR / _DB_NAME
    conn = sqlite3.connect(str(db))
    cur = conn.execute(
        """
        INSERT INTO entities (
            company_name, cin, pan, sector, sub_sector,
            annual_turnover, headquarters, loan_type,
            requested_amount, tenure_months, proposed_rate,
            promoter_names, created_at, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data["company_name"],
            data.get("cin", ""),
            data.get("pan", ""),
            data.get("sector", ""),
            data.get("sub_sector", ""),
            data.get("annual_turnover", 0),
            data.get("headquarters", ""),
            data.get("loan_type", ""),
            data.get("requested_amount", 0),
            data.get("tenure_months", 0),
            data.get("proposed_rate", 0),
            data.get("promoter_names", ""),
            datetime.utcnow().isoformat(),
            "onboarded",
        ),
    )
    conn.commit()
    entity_id = cur.lastrowid
    conn.close()
    return entity_id


# ── Request / Response schemas ──


class EntityOnboardingRequest(BaseModel):
    """Multi-step onboarding payload."""

    # Step 1 — Entity Details
    company_name: str
    cin: str = ""
    pan: str = ""
    sector: str = ""
    sub_sector: str = ""
    annual_turnover: float = 0.0
    headquarters: str = ""

    # Step 2 — Loan Details
    loan_type: str = ""
    requested_amount: float = 0.0
    tenure_months: int = 0
    proposed_rate: float = 0.0

    # Extra
    promoter_names: str = ""


class EntityOnboardingResponse(BaseModel):
    entity_id: int
    company_name: str
    status: str = "onboarded"
    message: str = ""


# ── Endpoint ──


@router.post(
    "",
    response_model=EntityOnboardingResponse,
)
def onboard_entity(request: EntityOnboardingRequest):
    """Store entity profile and loan request details."""
    if not request.company_name.strip():
        raise HTTPException(
            status_code=400,
            detail="company_name is required",
        )
    try:
        entity_id = _store_entity(request.model_dump())
        return EntityOnboardingResponse(
            entity_id=entity_id,
            company_name=request.company_name,
            status="onboarded",
            message=(
                f"Entity '{request.company_name}' "
                f"onboarded successfully."
            ),
        )
    except Exception as e:
        logger.error("Onboarding failed: %s", e)
        raise HTTPException(
            status_code=500, detail=str(e),
        )


@router.get("/{entity_id}")
def get_entity(entity_id: int):
    """Retrieve an onboarded entity profile."""
    _init_entity_db()
    db = DB_DIR / _DB_NAME
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM entities WHERE id = ?",
        (entity_id,),
    ).fetchone()
    conn.close()
    if not row:
        raise HTTPException(
            status_code=404, detail="Entity not found",
        )
    return dict(row)
