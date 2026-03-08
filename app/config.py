from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment / .env file."""

    # --- Paths ---
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    UPLOAD_DIR: Path = BASE_DIR / "data" / "uploads"
    ANNUAL_REPORT_DIR: Path = UPLOAD_DIR / "annual_reports"
    GST_DIR: Path = UPLOAD_DIR / "gst"
    BANK_DIR: Path = UPLOAD_DIR / "bank_statements"
    LEGAL_DIR: Path = UPLOAD_DIR / "legal_docs"
    CAM_OUTPUT_DIR: Path = BASE_DIR / "data" / "cam_reports"
    ML_MODEL_DIR: Path = BASE_DIR / "data" / "models"

    # --- HuggingFace ---
    HUGGINGFACEHUB_API_TOKEN: str = "your_token_here"

    # --- Research API Keys (optional — DuckDuckGo fallback) ---
    GNEWS_API_KEY: str = ""
    SERPER_API_KEY: str = ""
    NEWSAPI_KEY: str = ""

    # --- Model IDs (swap these to change models) ---
    INGESTOR_MODEL: str = "mistralai/Mistral-7B-Instruct-v0.3"
    RESEARCH_MODEL: str = "mistralai/Mistral-7B-Instruct-v0.3"
    RECOMMENDATION_MODEL: str = "mistralai/Mistral-7B-Instruct-v0.3"

    # --- LLM Parameters ---
    LLM_MAX_NEW_TOKENS: int = 1024
    LLM_TEMPERATURE: float = 0.1

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()

# Re-export for backward compatibility with existing code
BASE_DIR = settings.BASE_DIR
UPLOAD_DIR = settings.UPLOAD_DIR
ANNUAL_REPORT_DIR = settings.ANNUAL_REPORT_DIR
GST_DIR = settings.GST_DIR
BANK_DIR = settings.BANK_DIR
LEGAL_DIR = settings.LEGAL_DIR
CAM_OUTPUT_DIR = settings.CAM_OUTPUT_DIR
ML_MODEL_DIR = settings.ML_MODEL_DIR