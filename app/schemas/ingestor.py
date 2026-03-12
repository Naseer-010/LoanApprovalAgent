"""Pydantic schemas for Data Ingestor (Pillar 1)."""

from pydantic import BaseModel, Field, model_validator


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
    # Working capital fields
    cogs: float | None = None
    accounts_receivable: float | None = None
    accounts_payable: float | None = None
    inventory: float | None = None
    
    # Reliability metrics
    extraction_confidence: float = 0.85
    extraction_method: str = "hybrid"
    
    @model_validator(mode="after")
    def validate_financial_sanity(self):
        if self.revenue is not None and self.revenue < 0:
            raise ValueError("Revenue cannot be negative.")
        if self.total_debt is not None and self.total_debt < 0:
            raise ValueError("Total debt cannot be negative.")
        return self


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
    financials: ExtractedFinancials = Field(
        default_factory=ExtractedFinancials,
    )
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
    fraud_report: "FraudReport | None" = None


# --- Fraud Detection ---

class FraudAlert(BaseModel):
    """A single fraud detection alert."""
    alert_type: str
    severity: str = "medium"
    title: str
    description: str
    evidence: str = ""
    confidence: float = 0.5  # 0–1


class FraudReport(BaseModel):
    """Full fraud detection report."""
    total_alerts: int = 0
    critical_count: int = 0
    high_count: int = 0
    alerts: list[FraudAlert] = Field(default_factory=list)
    overall_fraud_risk: str = "low"
    fraud_score: float = 0.0  # 0–100


# --- Indian Regulatory Checks ---

class CIBILReport(BaseModel):
    """CIBIL commercial credit report (requires API integration)."""
    score: int = 0  # 300–900
    rating: str = ""
    credit_age_years: int = 0
    active_accounts: int = 0
    overdue_accounts: int = 0
    default_history: list[str] = Field(default_factory=list)
    enquiry_count_6m: int = 0
    assessment: str = ""


class GSTRMismatch(BaseModel):
    """GSTR-2A vs 3B mismatch result."""
    itc_claimed_3b: float = 0.0
    itc_eligible_2a: float = 0.0
    mismatch_amount: float = 0.0
    mismatch_percentage: float = 0.0
    risk_flag: str = ""


class MCADirectorCheck(BaseModel):
    """MCA director status check result."""
    director_name: str
    din: str = ""
    status: str = "Active"  # Active, Disqualified, Struck Off
    companies_linked: int = 0
    defaulter_flag: bool = False
    details: str = ""


class RegulatoryCheckResult(BaseModel):
    """Consolidated Indian regulatory check results."""
    cibil: CIBILReport = Field(default_factory=CIBILReport)
    gstr_mismatch: GSTRMismatch = Field(default_factory=GSTRMismatch)
    director_checks: list[MCADirectorCheck] = Field(
        default_factory=list,
    )
    overall_regulatory_risk: str = "low"
    flags: list[str] = Field(default_factory=list)
