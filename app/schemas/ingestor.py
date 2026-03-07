"""Pydantic schemas for Data Ingestor (Pillar 1)."""

from pydantic import BaseModel, Field


# --- Document Analysis ---

class ExtractedFinancials(BaseModel):
    """Structured financial data extracted from documents."""
    revenue: float | None = None
    net_profit: float | None = None
    total_debt: float | None = None
    ebitda: float | None = None
    debt_to_equity: float | None = None
    current_ratio: float | None = None
    interest_coverage: float | None = None


class ExtractedRisks(BaseModel):
    """Risk factors extracted from documents."""
    key_risks: list[str] = Field(default_factory=list)
    contingent_liabilities: list[str] = Field(default_factory=list)
    related_party_transactions: list[str] = Field(default_factory=list)
    auditor_qualifications: list[str] = Field(default_factory=list)


class DocumentAnalysisResponse(BaseModel):
    """Response from AI-powered document analysis."""
    file_name: str
    document_type: str = "unknown"
    text_length: int = 0
    financials: ExtractedFinancials = Field(default_factory=ExtractedFinancials)
    risks: ExtractedRisks = Field(default_factory=ExtractedRisks)
    summary: str = ""
    raw_metrics: dict | None = None


# --- GST Data ---

class GSTEntry(BaseModel):
    """Single GST filing period entry."""
    period: str = ""
    turnover: float = 0.0
    tax_paid: float = 0.0
    itc_claimed: float = 0.0


class GSTDataResponse(BaseModel):
    """Parsed GST filing data."""
    gstr_type: str = "GSTR-3B"
    entries: list[GSTEntry] = Field(default_factory=list)
    total_turnover: float = 0.0
    total_tax_paid: float = 0.0
    total_itc_claimed: float = 0.0


# --- Bank Statement ---

class BankStatementSummary(BaseModel):
    """Summary of parsed bank statement."""
    account_holder: str = ""
    bank_name: str = ""
    period_from: str = ""
    period_to: str = ""
    total_credits: float = 0.0
    total_debits: float = 0.0
    average_balance: float = 0.0
    peak_balance: float = 0.0
    lowest_balance: float = 0.0
    credit_count: int = 0
    debit_count: int = 0


# --- Cross Verification ---

class AnomalyFlag(BaseModel):
    """A single anomaly detected during cross-verification."""
    anomaly_type: str
    severity: str = "medium"  # low, medium, high, critical
    description: str
    evidence: str = ""


class CrossVerificationResult(BaseModel):
    """Result of GST vs Bank Statement cross-verification."""
    gst_total_turnover: float = 0.0
    bank_total_credits: float = 0.0
    discrepancy_percentage: float = 0.0
    anomalies: list[AnomalyFlag] = Field(default_factory=list)
    risk_level: str = "low"  # low, medium, high, critical
    ai_analysis: str = ""
