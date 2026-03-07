from app.services.document_processing.pdf_extractor import extract_text_from_pdf
from app.services.document_processing.financial_extractor import extract_financial_metrics


def process_financial_document(file_path: str):
    """
    Full pipeline:
    PDF -> Text -> Financial metrics
    """

    text = extract_text_from_pdf(file_path)

    metrics = extract_financial_metrics(text)

    return {
        "text_length": len(text),
        "financial_metrics": metrics
    }