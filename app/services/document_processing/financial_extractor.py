import re


def extract_financial_metrics(text: str):

    patterns = {
        "revenue": r"revenue\s*[:\-]?\s*₹?\$?\s*([\d,]+)",
        "net_profit": r"net\s*(income|profit)\s*[:\-]?\s*₹?\$?\s*([\d,]+)",
        "total_debt": r"(total\s*debt|long[-\s]*term\s*debt)\s*[:\-]?\s*₹?\$?\s*([\d,]+)",
        "ebitda": r"ebitda\s*[:\-]?\s*₹?\$?\s*([\d,]+)"
    }

    results = {}

    for key, pattern in patterns.items():

        match = re.search(pattern, text, re.IGNORECASE)

        if match:

            # get last captured numeric group
            value = match.groups()[-1]

            if value:
                value = value.replace(",", "")

                try:
                    results[key] = int(value)
                except:
                    results[key] = None
            else:
                results[key] = None

        else:
            results[key] = None

    return results