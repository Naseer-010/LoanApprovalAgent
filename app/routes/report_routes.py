"""
Report download routes — serves generated DOCX and PDF reports.
"""
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.config import CAM_OUTPUT_DIR

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["Report Downloads"])


@router.get("/download/{filename}")
def download_report(filename: str):
    """Download a generated report file (PDF or DOCX)."""
    # Sanitize filename — prevent path traversal
    safe_name = Path(filename).name
    file_path = CAM_OUTPUT_DIR / safe_name

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Report '{safe_name}' not found",
        )

    # Determine media type
    suffix = file_path.suffix.lower()
    media_type_map = {
        ".pdf": "application/pdf",
        ".docx": (
            "application/vnd.openxmlformats-officedocument"
            ".wordprocessingml.document"
        ),
        ".json": "application/json",
        ".csv": "text/csv",
    }
    media_type = media_type_map.get(suffix, "application/octet-stream")

    return FileResponse(
        path=str(file_path),
        filename=safe_name,
        media_type=media_type,
    )


@router.get("/list")
def list_reports():
    """List all available reports in the output directory."""
    CAM_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    files = []
    for f in CAM_OUTPUT_DIR.iterdir():
        if f.is_file() and f.suffix.lower() in (
            ".pdf", ".docx", ".json", ".csv",
        ):
            files.append({
                "filename": f.name,
                "size_bytes": f.stat().st_size,
                "type": f.suffix.lower().lstrip("."),
                "download_url": f"/reports/download/{f.name}",
            })
    return {"reports": files}
