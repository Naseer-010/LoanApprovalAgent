import shutil
import uuid
import logging
from pathlib import Path
from fastapi import UploadFile, HTTPException

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".pdf", ".csv", ".xlsx", ".png", ".jpg", ".jpeg"}
MAX_FILE_SIZE_MB = 20
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

def save_file(file: UploadFile, destination: Path) -> str:
    """
    Securely save uploaded file to destination folder with robust validation.
    """
    # 1. Validate Extension
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # 2. Prevent Executables / Magic Bytes (Basic)
    if ext in {".exe", ".bat", ".cmd", ".sh", ".msi"}:
        raise HTTPException(status_code=400, detail="Executable files are strictly prohibited.")

    # 3. Size Limit
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)
    if size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum allowed size is {MAX_FILE_SIZE_MB}MB."
        )
    
    if size == 0:
        raise HTTPException(status_code=400, detail="File is empty.")

    # 4. Prevent Path Traversal by generating unique safe filename
    safe_filename = f"{uuid.uuid4().hex}{ext}"
    
    destination.mkdir(parents=True, exist_ok=True)
    file_location = destination / safe_filename

    try:
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        logger.error(f"Failed to save file: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during file upload.")

    return str(file_location)