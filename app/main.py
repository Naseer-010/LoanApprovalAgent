from fastapi import FastAPI

from app.routes import (
    ingestor_routes,
    recommendation_routes,
    research_routes,
    upload_routes,
)

app = FastAPI(
    title="Intelli-Credit: AI-Powered Credit Decisioning Engine",
    description=(
        "Automates end-to-end preparation of a Comprehensive Credit Appraisal Memo (CAM). "
        "Ingests multi-source data, performs web-scale secondary research, "
        "and synthesizes primary due diligence into a final recommendation."
    ),
    version="1.0.0",
)

# Pillar 0: File Uploads (existing)
app.include_router(upload_routes.router)

# Pillar 1: Data Ingestor
app.include_router(ingestor_routes.router)

# Pillar 2: Research Agent
app.include_router(research_routes.router)

# Pillar 3: Recommendation Engine
app.include_router(recommendation_routes.router)


@app.get("/", tags=["Health"])
def health_check() -> dict:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Intelli-Credit Engine",
        "version": "1.0.0",
    }