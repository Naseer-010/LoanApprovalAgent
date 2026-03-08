"""
PDF Extractor — hybrid text + table extraction with OCR fallback.

Uses pdfplumber for text and table extraction. Falls back to pytesseract
OCR for scanned documents. Optionally uses camelot/tabula for complex tables.
"""

import logging
from pathlib import Path

import pdfplumber

logger = logging.getLogger(__name__)


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from PDF using pdfplumber."""
    text_content = []

    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                text_content.append(text)

    full_text = "\n".join(text_content)

    # If very little text was extracted, try OCR
    if len(full_text.strip()) < 100:
        ocr_text = _ocr_fallback(file_path)
        if ocr_text:
            return ocr_text

    return full_text


def extract_tables_from_pdf(file_path: str) -> list[list[list[str]]]:
    """
    Extract tables from PDF using pdfplumber's table extraction.

    Returns a list of tables, where each table is a list of rows,
    and each row is a list of cell strings.
    """
    all_tables = []

    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                if tables:
                    for table in tables:
                        # Clean None cells
                        cleaned = [
                            [cell.strip() if cell else "" for cell in row]
                            for row in table
                            if row  # skip empty rows
                        ]
                        if cleaned:
                            all_tables.append(cleaned)
    except Exception as e:
        logger.warning("pdfplumber table extraction failed: %s", e)

    # Fallback: try camelot for complex tables
    if not all_tables:
        all_tables = _camelot_fallback(file_path)

    return all_tables


def _ocr_fallback(file_path: str) -> str:
    """Use pytesseract OCR for scanned PDFs."""
    try:
        from PIL import Image
        import pytesseract

        text_content = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                # Convert page to image
                img = page.to_image(resolution=300)
                pil_image = img.original
                text = pytesseract.image_to_string(pil_image)
                if text.strip():
                    text_content.append(text)

        return "\n".join(text_content)

    except ImportError:
        logger.warning(
            "pytesseract not available — OCR fallback skipped. "
            "Install with: pip install pytesseract Pillow"
        )
        return ""
    except Exception as e:
        logger.warning("OCR fallback failed: %s", e)
        return ""


def _camelot_fallback(file_path: str) -> list[list[list[str]]]:
    """Try camelot-py for table extraction as fallback."""
    try:
        import camelot

        tables = camelot.read_pdf(file_path, pages="all", flavor="lattice")
        if not tables:
            tables = camelot.read_pdf(file_path, pages="all", flavor="stream")

        all_tables = []
        for table in tables:
            df = table.df
            rows = df.values.tolist()
            cleaned = [
                [str(cell).strip() for cell in row]
                for row in rows
                if any(str(c).strip() for c in row)
            ]
            if cleaned:
                all_tables.append(cleaned)

        return all_tables

    except ImportError:
        logger.debug("camelot-py not available — skipping camelot fallback")
        return []
    except Exception as e:
        logger.debug("camelot fallback failed: %s", e)
        return []