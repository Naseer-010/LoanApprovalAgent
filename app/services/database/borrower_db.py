"""
Borrower History Database — SQLite-backed storage for historical
credit evaluations.

Stores every completed loan analysis as a historical record.
Enables trend analysis and trust scoring for repeat applicants.
"""

import logging
import sqlite3
from datetime import datetime
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

DB_DIR = settings.BASE_DIR / "data" / "db"
DB_PATH = DB_DIR / "borrower_history.db"

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS borrower_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT NOT NULL,
    application_date TEXT NOT NULL,
    risk_score REAL DEFAULT 0.0,
    loan_amount_requested REAL DEFAULT 0.0,
    loan_amount_approved REAL DEFAULT 0.0,
    interest_rate REAL DEFAULT 0.0,
    decision TEXT DEFAULT 'REFER',
    fraud_risk_score REAL DEFAULT 0.0,
    sector_risk_score REAL DEFAULT 0.0,
    promoter_risk_score REAL DEFAULT 0.0,
    early_warning_score REAL DEFAULT 0.0,
    five_cs_score REAL DEFAULT 0.0,
    working_capital_score REAL DEFAULT 0.0,
    explanation_summary TEXT DEFAULT ''
);
"""

CREATE_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_company_name
ON borrower_history (company_name COLLATE NOCASE);
"""


def _get_connection() -> sqlite3.Connection:
    """Get a SQLite connection, creating the DB if needed."""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initialize the borrower_history table if it doesn't exist."""
    try:
        conn = _get_connection()
        conn.execute(CREATE_TABLE_SQL)
        conn.execute(CREATE_INDEX_SQL)
        conn.commit()
        conn.close()
        logger.info("Borrower history DB initialized at %s", DB_PATH)
    except Exception as e:
        logger.error("Failed to initialize borrower DB: %s", e)


def store_application(
    company_name: str,
    risk_score: float = 0.0,
    loan_amount_requested: float = 0.0,
    loan_amount_approved: float = 0.0,
    interest_rate: float = 0.0,
    decision: str = "REFER",
    fraud_risk_score: float = 0.0,
    sector_risk_score: float = 0.0,
    promoter_risk_score: float = 0.0,
    early_warning_score: float = 0.0,
    five_cs_score: float = 0.0,
    working_capital_score: float = 0.0,
    explanation_summary: str = "",
) -> int | None:
    """
    Store a completed loan application analysis as a historical record.

    Returns the row ID of the inserted record, or None on failure.
    """
    try:
        conn = _get_connection()
        cursor = conn.execute(
            """
            INSERT INTO borrower_history (
                company_name, application_date, risk_score,
                loan_amount_requested, loan_amount_approved,
                interest_rate, decision, fraud_risk_score,
                sector_risk_score, promoter_risk_score,
                early_warning_score, five_cs_score,
                working_capital_score, explanation_summary
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                company_name,
                datetime.now().isoformat(),
                risk_score,
                loan_amount_requested,
                loan_amount_approved,
                interest_rate,
                decision,
                fraud_risk_score,
                sector_risk_score,
                promoter_risk_score,
                early_warning_score,
                five_cs_score,
                working_capital_score,
                explanation_summary,
            ),
        )
        conn.commit()
        row_id = cursor.lastrowid
        conn.close()
        logger.info(
            "Stored borrower history for '%s' (id=%s)",
            company_name, row_id,
        )
        return row_id
    except Exception as e:
        logger.error("Failed to store borrower history: %s", e)
        return None


def get_history(company_name: str) -> list[dict]:
    """
    Retrieve all historical records for a company.

    Uses case-insensitive LIKE matching to handle variations.
    Returns records sorted by application_date ascending.
    """
    try:
        conn = _get_connection()
        # Ensure table exists
        conn.execute(CREATE_TABLE_SQL)
        conn.commit()

        rows = conn.execute(
            """
            SELECT * FROM borrower_history
            WHERE company_name LIKE ?
            ORDER BY application_date ASC
            """,
            (f"%{company_name.strip()}%",),
        ).fetchall()
        conn.close()

        return [dict(row) for row in rows]
    except Exception as e:
        logger.error("Failed to query borrower history: %s", e)
        return []


# Initialize DB on module import
init_db()
