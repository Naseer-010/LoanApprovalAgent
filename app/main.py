from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from app.routes import (
    ingestor_routes,
    pipeline_routes,
    recommendation_routes,
    research_routes,
    upload_routes,
    agent_routes,
)

app = FastAPI(
    title="Intelli-Credit: AI-Powered Credit Decisioning Engine",
    description=(
        "Automates end-to-end preparation of a Comprehensive "
        "Credit Appraisal Memo (CAM)."
    ),
    version="1.0.0",
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
app.include_router(ingestor_routes.router)
app.include_router(research_routes.router)
app.include_router(recommendation_routes.router)
app.include_router(pipeline_routes.router)
app.include_router(agent_routes.router)


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