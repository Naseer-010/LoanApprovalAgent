import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pathlib import Path

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

logger = logging.getLogger(__name__)
from app.routes import (
    ingestor_routes,
    onboarding_routes,
    pipeline_routes,
    recommendation_routes,
    report_routes,
    research_routes,
    upload_routes,
    agent_routes,
)
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])

app = FastAPI(
    title="Intelli-Credit: AI-Powered Credit Decisioning Engine",
    description=(
        "Automates end-to-end preparation of a Comprehensive "
        "Credit Appraisal Memo (CAM)."
    ),
    version="1.0.0",
)

# Rate Limiting setup
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Global fallback exception handler to prevent hard crashes in frontend
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Failed to process {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred during processing. Please verify your inputs and try again."},
    )

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Routers
app.include_router(upload_routes.router)
app.include_router(onboarding_routes.router)
app.include_router(ingestor_routes.router)
app.include_router(research_routes.router)
app.include_router(recommendation_routes.router)
app.include_router(pipeline_routes.router)
app.include_router(agent_routes.router)
app.include_router(report_routes.router)


@app.get("/", tags=["Frontend"], include_in_schema=False)
def serve_frontend() -> FileResponse:
    """Serve the single-page frontend."""
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/api/health", tags=["Health"])
def health_check() -> dict:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Intelli-Credit Engine",
        "version": "1.0.0",
    }