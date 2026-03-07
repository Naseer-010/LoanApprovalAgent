import pdfplumber


def extract_text_from_pdf(file_path: str) -> str:
    """
    Extract text from PDF using pdfplumber
    """
    text_content = []

    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()

            if text:
                text_content.append(text)

    return "\n".join(text_content)