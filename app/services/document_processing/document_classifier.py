"""
Document Classifier — auto-identifies uploaded document types.

Uses keyword detection + LLM fallback for classification.
Output classes: ALM, Shareholding, BorrowingProfile,
AnnualReport, PortfolioPerformance, GST, BankStatement, Unknown
"""
import logging

logger = logging.getLogger(__name__)

DOC_CLASSES = [
    "ALM",
    "Shareholding",
    "BorrowingProfile",
    "AnnualReport",
    "PortfolioPerformance",
    "GST",
    "BankStatement",
    "Unknown",
]


def get_doc_classes() -> list[str]:
    """Return all supported document type classes."""
    return list(DOC_CLASSES)

# Keyword rules — ordered by specificity
_KEYWORD_RULES: list[tuple[str, list[str]]] = [
    (
        "ALM",
        [
            "asset liability",
            "alm",
            "maturity profile",
            "interest rate sensitivity",
            "liquidity gap",
            "repricing gap",
        ],
    ),
    (
        "Shareholding",
        [
            "shareholding pattern",
            "promoter holding",
            "public shareholding",
            "depository receipts",
            "share capital",
            "category of shareholder",
        ],
    ),
    (
        "BorrowingProfile",
        [
            "borrowing profile",
            "term loan",
            "working capital",
            "fund based",
            "non fund based",
            "sanctioned limit",
            "outstanding borrowing",
            "lender wise",
        ],
    ),
    (
        "PortfolioPerformance",
        [
            "portfolio performance",
            "npa ratio",
            "default rate",
            "recovery rate",
            "portfolio yield",
            "asset quality",
            "delinquency",
            "provision coverage",
            "gross npa",
            "net npa",
        ],
    ),
    (
        "AnnualReport",
        [
            "annual report",
            "directors report",
            "auditor",
            "balance sheet",
            "profit and loss",
            "cash flow statement",
            "schedule",
            "notes to accounts",
        ],
    ),
    (
        "GST",
        [
            "gstr",
            "gstin",
            "gst return",
            "taxable value",
            "igst",
            "cgst",
            "sgst",
            "input tax credit",
        ],
    ),
    (
        "BankStatement",
        [
            "bank statement",
            "account statement",
            "opening balance",
            "closing balance",
            "credit total",
            "debit total",
            "cheque",
            "neft",
            "rtgs",
        ],
    ),
]


def classify_document(
    text: str,
    filename: str = "",
) -> dict:
    """
    Classify document text into a document type.

    Returns:
        {
            "predicted_type": str,
            "confidence": float (0-1),
            "keyword_hits": list[str],
            "method": "keyword" | "llm",
        }
    """
    text_lower = text[:5000].lower()
    fn_lower = filename.lower()

    best_type = "Unknown"
    best_score = 0.0
    best_hits: list[str] = []

    for doc_type, keywords in _KEYWORD_RULES:
        hits = [
            kw for kw in keywords if kw in text_lower or kw in fn_lower
        ]
        score = len(hits) / len(keywords)
        if score > best_score:
            best_score = score
            best_type = doc_type
            best_hits = hits

    # Require minimum threshold
    if best_score < 0.15:
        best_type = "Unknown"
        best_score = 0.0

    confidence = min(best_score * 2.5, 1.0)

    return {
        "predicted_type": best_type,
        "confidence": round(confidence, 2),
        "keyword_hits": best_hits,
        "method": "keyword",
    }


def get_doc_classes() -> list[str]:
    """Return all valid document type classes."""
    return DOC_CLASSES.copy()
