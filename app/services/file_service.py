import shutil
from pathlib import Path

def save_file(file, destination: Path):
    """
    Save uploaded file to destination folder
    """
    destination.mkdir(parents=True, exist_ok=True)

    file_location = destination / file.filename

    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return str(file_location)