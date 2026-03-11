"""
Schema Mapper — maps extracted data to user-defined schemas.
Supports JSON and CSV export.
"""
import csv
import io
import json
import logging

logger = logging.getLogger(__name__)


def map_to_schema(
    extracted_data: dict,
    schema_fields: list[str],
) -> dict:
    """
    Map extracted data dictionary to a user-defined schema.

    Args:
        extracted_data: flat dict of all extracted data
        schema_fields: list of field names the user wants

    Returns:
        dict with only the requested fields (None if missing)
    """
    result = {}
    flat = _flatten_dict(extracted_data)

    for field in schema_fields:
        key_lower = field.lower().replace(" ", "_")
        # Try exact match first
        if key_lower in flat:
            result[field] = flat[key_lower]
        else:
            # Fuzzy match
            matched = False
            for k, v in flat.items():
                if key_lower in k or k in key_lower:
                    result[field] = v
                    matched = True
                    break
            if not matched:
                result[field] = None

    return result


def export_json(data: dict) -> str:
    """Export mapped data as JSON string."""
    return json.dumps(data, indent=2, default=str)


def export_csv(data: dict) -> str:
    """Export mapped data as CSV string."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Field", "Value"])
    for k, v in data.items():
        writer.writerow([k, v])
    return output.getvalue()


def _flatten_dict(
    d: dict, parent_key: str = "", sep: str = "_",
) -> dict:
    """Flatten nested dict into single-level dict."""
    items: list[tuple[str, object]] = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        new_key = new_key.lower()
        if isinstance(v, dict):
            items.extend(
                _flatten_dict(v, new_key, sep).items(),
            )
        else:
            items.append((new_key, v))
    return dict(items)
