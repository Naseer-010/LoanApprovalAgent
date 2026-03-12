# Intelli-Credit: AI-Powered Corporate Credit Decisioning Engine

> A production-grade credit appraisal platform that automates end-to-end **Credit Appraisal Memo (CAM)** generation for Indian corporate lending. Built for the hackathon theme: *Next-Gen Corporate Credit Appraisal: Bridging the Intelligence Gap.*

---

## Table of Contents

- [Architecture](#architecture)
- [Key Features](#key-features)
- [AI Agent Network](#ai-agent-network)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [Usage Guide](#usage-guide)
- [API Reference](#api-reference)
- [Security & Hardening](#security--hardening)
- [Project Structure](#project-structure)
- [Docker Deployment](#docker-deployment)
- [License](#license)

---

## Architecture

```
┌───────────────────────────────────────────────────────────────────────┐
│                       Frontend (Single-Page App)                      │
│   3-step wizard: Entity Onboarding → Loan Details → Document Upload   │
│   Live SSE Investigation Timeline → Results Dashboard                 │
├───────────────────────────────────────────────────────────────────────┤
│                         FastAPI Backend                                │
│                    Rate-limited · Exception-safe                       │
├──────────┬───────────────┬──────────────┬─────────────────────────────┤
│ Pillar 1 │   Pillar 2    │  Pillar 3    │      AI Agent Network       │
│ Data     │   Research    │  Recommend.  │                             │
│ Ingestor │   Agent       │  Engine      │  • Promoter Network Agent   │
│          │               │              │  • Sector Risk Agent        │
│ • PDF    │ • Web Search  │ • Five Cs    │  • Early Warning Agent      │
│ • GST    │ • Promoter    │ • Fin Ratios │  • Working Capital Agent    │
│ • Bank   │   Risk        │ • ML Model   │  • Historical Trust Agent   │
│ • Cross  │ • eCourts     │ • Decision   │  • Portfolio Agent          │
│   Verify │ • RBI/SEBI    │   Engine     │  • SWOT Agent               │
│ • Fraud  │ • Primary     │ • CAM Writer │  • Financial Trend Agent    │
│ • Regs   │   Insights    │ • Explain.   │                             │
├──────────┴───────────────┴──────────────┴─────────────────────────────┤
│   Document Intelligence     │  ML Credit Risk Model  │  SQLite DB     │
│   • Classifier + Validator  │  • XGBoost + SHAP      │  • Borrower    │
│   • Schema Mapper           │  • Feature Engineering  │    History     │
│   • ALM / Shareholding      │  • Probability Scoring  │  • Trust Score │
└─────────────────────────────┴────────────────────────┴────────────────┘
```

---

## Key Features

### Pillar 1: Data Ingestor

| Module | Description |
|--------|-------------|
| **PDF/AI Extraction** | `pdfplumber` text extraction + HuggingFace LLM structured financial parsing with confidence scoring |
| **Document Classification** | Auto-classifies uploaded documents (Annual Report, GST, Bank Statement, etc.) with confidence threshold — flags low-confidence (< 0.7) for analyst review |
| **Human-in-the-Loop Validation** | Analysts can approve, edit, or reject AI classification before pipeline proceeds |
| **Schema Mapping** | Maps extracted data to user-defined schemas, exports as JSON or CSV |
| **GST Filing Parser** | Handles CSV/JSON/PDF, extracts per-period turnover, tax payable, ITC breakdown |
| **Bank Statement Parser** | Total credits, debits, balance, transaction counts, monthly activity pattern |
| **Cross-Verification** | Compares GST reported turnover against bank statement credits — flags >10% discrepancies |
| **Fraud Detection** | 10+ fraud patterns including revenue spikes, ITC inflation, circular trading, shell company indicators, round-number transaction anomalies, high velocity layering |
| **Indian Regulatory Checks** | Simulated CIBIL (300–900), GSTR-2A vs 3B ITC mismatch, MCA director DIN status with defaulter/disqualification flags |

### Pillar 2: Research Agent

| Module | Description |
|--------|-------------|
| **LangChain Web Research** | DuckDuckGo-powered search targeting financial news, litigation, MCA filings, RBI regulations, and sector outlook |
| **Promoter Network Analysis** | Linked company detection, director network graph (vis.js), litigation flags |
| **Primary Insights Processor** | Processes qualitative observations from factory visits and management interviews with severity scoring and risk adjustments |
| **News Aggregation** | Categorized research report with sentiment analysis (positive/negative/neutral) |

### Pillar 3: Recommendation Engine

| Module | Description |
|--------|-------------|
| **Financial Ratio Modeling** | DSCR, ICR, Leverage, Current Ratio, Debt/Equity, EBITDA Margin — each assessed against banking benchmarks as Pass/Watch/Fail |
| **Five Cs Scorer** | Character, Capacity, Capital, Collateral, Conditions — scored 0–10 via LLM + rule-based hybrid, weighted aggregation |
| **ML Credit Risk Model** | XGBoost classifier trained on financial features, outputs default probability + SHAP explainability |
| **Decision Engine** | Aggregates all signals — mandatory rejection for critical fraud/defaulter flags, structured conditions for conditional approvals |
| **Explainability Engine** | Rigidly structured `[Financial Reason → Risk Signal → Supporting Metric]` format for every decision |
| **CAM Generator** | LLM-written professional Credit Appraisal Memo (DOCX + PDF), 8 structured sections |

### Frontend Dashboard

| Component | Description |
|-----------|-------------|
| **3-Step Onboarding Wizard** | Entity Info → Loan Details → Documents with step progress indicator |
| **Entity Onboarding** | Captures CIN, PAN, sector, sub-sector, turnover, headquarters, promoter names |
| **Drag-and-Drop Upload** | Annual Report, GST, Bank Statement, ALM, Shareholding, Portfolio — with file preview |
| **Live Investigation Timeline** | SSE-powered real-time pipeline step tracker with ✔/⚠/❌ status icons |
| **Decision Banner** | Large APPROVE/REJECT/REFER verdict with risk grade, confidence, and recommended amount |
| **Risk Heatmap Dashboard** | 5-pillar visual grid (Financial, Sector, Fraud, Promoter, Portfolio) with color-coded cells |
| **Credit Committee Simulation** | Tabs for Recommendation, Risk Factors, and Evidence — simulated panel review |
| **Financial Trend Analysis** | Multi-metric trend cards with severity-coded direction indicators |
| **Promoter Network Graph** | Interactive vis.js network visualization of linked entities |
| **Schema Mapping Builder** | Select fields from analysis results and export as JSON/CSV |
| **CAM Report Download** | One-click DOCX and PDF download of the AI-generated Credit Appraisal Memo |

---

## AI Agent Network

The system deploys **8 specialized AI agents**, each analyzing a distinct risk dimension:

| Agent | File | Purpose |
|-------|------|---------|
| **Promoter Network Agent** | `promoter_network_agent.py` | Scans promoter histories, maps linked entities, flags litigation and directorship risks |
| **Sector Risk Agent** | `sector_risk_agent.py` | Evaluates macro-economic sector headwinds, regulatory pressure, and cyclicality |
| **Early Warning Agent** | `early_warning_agent.py` | Detects warning triggers from financial deterioration, fraud signals, and sector stress |
| **Working Capital Agent** | `working_capital_agent.py` | Calculates Cash Conversion Cycle, receivable/inventory/payable days, liquidity stress indicators |
| **Historical Trust Agent** | `historical_trust_agent.py` | Queries borrower history database for past loan performance, trust scoring |
| **Portfolio Agent** | `portfolio_agent.py` | Analyzes portfolio concentration, NPA rates, provision coverage at book level |
| **SWOT Agent** | `swot_agent.py` | Generates Strengths, Weaknesses, Opportunities, Threats from all available data streams |
| **Financial Trend Agent** | `financial_trend_agent.py` | Detects revenue growth trends, margin compression, stability assessment across metrics |

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | FastAPI, Python 3.10+, Uvicorn |
| **AI / LLM** | LangChain, HuggingFace Inference API (Mistral-7B default) |
| **Machine Learning** | XGBoost, scikit-learn, SHAP |
| **Document Processing** | pdfplumber, camelot-py, tabula-py, pytesseract, Pillow |
| **Network Analysis** | NetworkX, vis.js (frontend) |
| **Report Generation** | python-docx, ReportLab, Matplotlib |
| **Web Search** | DuckDuckGo (via langchain-community), GNews |
| **Database** | SQLite (borrower history) |
| **Security** | slowapi (rate limiting), Pydantic strict validation |
| **Frontend** | Vanilla HTML/CSS/JS, SVG icon library, SSE streaming |
| **Styling** | Custom CSS — flat dark fintech theme (`#0F0F0F` / `#00FF9C`) |
| **Deployment** | Docker, Docker Compose |

---

## Getting Started

### Prerequisites

- **Python 3.10+**
- **HuggingFace API token** (free at [huggingface.co](https://huggingface.co/settings/tokens))
- Optional: `tesseract-ocr` for image-based PDF extraction

### Installation

```bash
# Clone the repository
git clone <repo-url>
cd LoanApprovalAgent

# Create virtual environment
python -m venv venv
source venv/bin/activate      # Linux/Mac
# venv\Scripts\activate       # Windows

# Install dependencies
pip install -r requirements.txt
```

### Configuration

```bash
# Copy the environment template
cp .env.example .env

# Edit .env and add your HuggingFace token
# HUGGINGFACEHUB_API_TOKEN=hf_xxxxxxxxxxxxx
```

### Run

```bash
python run.py
```

The server starts at **http://localhost:8000**. Open this URL in your browser to access the dashboard.

Interactive API documentation is available at **http://localhost:8000/docs** (Swagger UI).

---

## Usage Guide

### Step 1: Entity Onboarding

Enter the borrower's corporate details:

- **Company Name** (required)
- **CIN** — Corporate Identification Number (validated: `L17110MH1973PLC019786` format)
- **PAN** — Permanent Account Number (validated: `AAACR5055K` format)
- **Sector / Sub-Sector** — e.g., Oil & Gas / Refining
- **Annual Turnover** — in INR Crores
- **Headquarters** — City, State
- **Promoter Names** — Comma-separated list

### Step 2: Loan Request

Specify loan facility details:

- **Loan Type** — Term Loan, Working Capital, Project Finance, WCDL, Overdraft, LC, BG
- **Requested Amount** — in INR
- **Tenure** — in months
- **Proposed Interest Rate** — percentage

### Step 3: Document Upload & Analysis

Upload financial documents (all optional):

- **Annual Report** — PDF only
- **GST Filing** — CSV, JSON, or PDF
- **Bank Statement** — CSV or PDF
- **ALM Report** — Asset Liability Management
- **Shareholding Pattern** — Ownership structure
- **Portfolio Cuts** — Historical performance data

Add **Primary Due Diligence Notes** — qualitative observations from factory visits, management interviews, or site inspections.

Click **Run Full Analysis** to launch the investigation. The SSE-powered timeline provides real-time visibility into each pipeline stage.

---

## API Reference

### Pipeline Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/pipeline/full-analysis` | Run complete credit analysis pipeline (synchronous) |
| `POST` | `/pipeline/investigate` | Run pipeline with SSE live streaming results |

### Entity Onboarding

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/onboarding` | Register borrower entity with validated CIN/PAN |
| `GET` | `/onboarding/{company_name}` | Retrieve onboarding record |

### Document Intelligence

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/ingest/analyze-document` | Upload PDF and extract structured financial data |
| `POST` | `/ingest/parse-gst` | Parse GST filing |
| `POST` | `/ingest/parse-bank-statement` | Parse bank statement |
| `POST` | `/ingest/cross-verify` | Cross-verify GST turnover vs bank credits |
| `POST` | `/ingest/classify` | Auto-classify document type with confidence score |
| `GET` | `/ingest/doc-classes` | List all supported document type classes |
| `POST` | `/ingest/validate-classification` | Human-in-the-loop: approve/edit/reject AI classification |
| `POST` | `/ingest/schema-map` | Map extracted data to custom schema, export JSON/CSV |

### Research

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/research/web-search` | Run web research for a company |
| `POST` | `/research/primary-insights` | Process qualitative due diligence notes |
| `GET` | `/research/report/{company}` | Retrieve cached research report |

### Recommendation Engine

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/recommendation/score` | Five Cs scoring |
| `POST` | `/recommendation/decision` | Generate loan decision with explainability |
| `POST` | `/recommendation/generate-cam` | Generate Credit Appraisal Memo (DOCX + PDF) |

### AI Agents

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/agents/promoter-network` | Promoter network analysis |
| `POST` | `/agents/sector-risk` | Sector risk intelligence |
| `POST` | `/agents/early-warning` | Early warning signal detection |
| `POST` | `/agents/working-capital` | Working capital stress analysis |
| `POST` | `/agents/historical-trust` | Historical borrower trust scoring |
| `POST` | `/agents/portfolio` | Portfolio performance analysis |
| `POST` | `/agents/swot` | SWOT analysis generation |
| `POST` | `/agents/financial-trends` | Financial trend detection |

### File Upload

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/upload/annual-report` | Upload annual report PDF |
| `POST` | `/upload/gst` | Upload GST filing |
| `POST` | `/upload/bank-statement` | Upload bank statement |

### Reports & Utility

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/reports/borrower-history/{company}` | Query borrower loan history |
| `GET` | `/api/health` | Health check |

> **Interactive API Docs**: `http://localhost:8000/docs`

---

## Security & Hardening

### File Upload Protection

- ✅ **Extension whitelist** — Only `.pdf`, `.csv`, `.xlsx`, `.png`, `.jpg`, `.jpeg` accepted
- ✅ **20 MB file size limit** — Rejects oversized uploads before processing
- ✅ **Executable content detection** — Scans first bytes for ELF/MZ/PE signatures
- ✅ **UUID-based filenames** — Prevents path traversal attacks

### API Rate Limiting

- ✅ **slowapi** middleware — 100 requests/minute per client IP
- ✅ Returns `429 Too Many Requests` on threshold breach

### Input Validation

- ✅ **CIN regex** — `^[A-Z]{1}\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}$`
- ✅ **PAN regex** — `^[A-Z]{5}\d{4}[A-Z]$`
- ✅ **Positive-only** loan amounts, turnovers
- ✅ **Financial schema guards** — Revenue ≥ 0, Total Debt ≥ 0 via `@model_validator`

### Error Handling

- ✅ **Global exception handler** — Returns structured JSON on unhandled errors
- ✅ **Pipeline isolation** — Each analysis step wrapped in `try-except`, failures report gracefully without crashing the pipeline

---

## Project Structure

```
LoanApprovalAgent/
├── app/
│   ├── agents/                          # 8 Specialized AI Agents
│   │   ├── promoter_network_agent.py    # Promoter graph & litigation
│   │   ├── sector_risk_agent.py         # Macro-economic sector analysis
│   │   ├── early_warning_agent.py       # EWS trigger detection
│   │   ├── working_capital_agent.py     # Cash conversion cycle & liquidity
│   │   ├── historical_trust_agent.py    # Borrower history scoring
│   │   ├── portfolio_agent.py           # Portfolio NPA & concentration
│   │   ├── swot_agent.py                # SWOT analysis generation
│   │   └── financial_trend_agent.py     # Multi-metric trend analysis
│   ├── core/
│   │   └── llm.py                       # LLM factory (HuggingFace)
│   ├── routes/
│   │   ├── pipeline_routes.py           # Full analysis + SSE investigate
│   │   ├── onboarding_routes.py         # Entity onboarding with CIN/PAN
│   │   ├── ingestor_routes.py           # Classification, schema mapping
│   │   ├── research_routes.py           # Web research endpoints
│   │   ├── recommendation_routes.py     # Five Cs, decision, CAM
│   │   ├── agent_routes.py              # Individual agent endpoints
│   │   ├── upload_routes.py             # File upload handlers
│   │   └── report_routes.py             # Borrower history queries
│   ├── schemas/
│   │   ├── ingestor.py                  # Financial extraction + validation
│   │   ├── research.py                  # Research report models
│   │   ├── recommendation.py            # Decision + structured reasoning
│   │   └── pipeline.py                  # Full analysis response model
│   ├── services/
│   │   ├── document_processing/
│   │   │   ├── pdf_extractor.py         # pdfplumber text extraction
│   │   │   ├── ai_extractor.py          # LLM structured extraction
│   │   │   ├── document_classifier.py   # Auto-classification + confidence
│   │   │   ├── document_service.py      # Regex-based fallback extraction
│   │   │   ├── schema_mapper.py         # Field mapping & export
│   │   │   ├── alm_extractor.py         # ALM report parser
│   │   │   ├── shareholding_extractor.py# Shareholding pattern parser
│   │   │   ├── portfolio_extractor.py   # Portfolio data parser
│   │   │   ├── borrowing_extractor.py   # Borrowing profile parser
│   │   │   └── financial_extractor.py   # Deep financial statement parser
│   │   ├── ingestor/
│   │   │   ├── gst_parser.py            # GST filing parser
│   │   │   ├── bank_statement_parser.py # Bank statement parser
│   │   │   ├── cross_verification.py    # GST vs bank cross-check
│   │   │   ├── fraud_detector.py        # 10+ fraud pattern detection
│   │   │   └── indian_regulatory.py     # CIBIL, GSTR, MCA checks
│   │   ├── research/
│   │   │   ├── web_researcher.py        # LangChain DuckDuckGo agent
│   │   │   ├── news_aggregator.py       # Research report builder
│   │   │   └── primary_insights.py      # Qualitative analysis
│   │   ├── recommendation/
│   │   │   ├── five_cs_scorer.py        # Five Cs LLM + rules scorer
│   │   │   ├── decision_engine.py       # Loan decision logic
│   │   │   └── cam_generator.py         # AI DOCX/PDF CAM writer
│   │   ├── explainability/
│   │   │   └── explainability.py        # Structured reasoning engine
│   │   ├── ml_model/
│   │   │   ├── credit_risk_model.py     # XGBoost + SHAP prediction
│   │   │   └── train_model.py           # Model training pipeline
│   │   ├── database/
│   │   │   └── borrower_db.py           # SQLite borrower history
│   │   └── file_service.py              # Secure file upload handler
│   ├── config.py                        # Paths & environment config
│   └── main.py                          # FastAPI app + middleware
├── static/
│   ├── index.html                       # Single-page frontend
│   ├── style.css                        # Flat dark fintech theme
│   ├── icons.js                         # SVG icon library
│   └── app.js                           # Frontend logic & rendering
├── data/                                # Runtime data directory
│   ├── uploads/                         # Uploaded documents
│   ├── cam_reports/                     # Generated CAM reports
│   └── models/                          # Trained ML models
├── Dockerfile                           # Container image
├── docker-compose.yml                   # Docker Compose config
├── requirements.txt                     # Python dependencies
├── run.py                               # Development server entry
└── README.md
```

---

## Docker Deployment

### Using Docker Compose (Recommended)

```bash
# Build and run
docker-compose up --build

# Access at http://localhost:8000
```

### Using Docker Directly

```bash
# Build the image
docker build -t intelli-credit .

# Run the container
docker run -p 8000:8000 --env-file .env intelli-credit
```

The container:
- Uses `python:3.10-slim` as base
- Pre-creates all required data directories
- Exposes port `8000`
- Runs Uvicorn with `--host 0.0.0.0`

---

## Design System

The frontend uses a strict **flat dark fintech** aesthetic:

| Element | Value |
|---------|-------|
| Background | `#0F0F0F` |
| Card Surface | `#1A1A1A` |
| Primary Accent | `#00FF9C` (Neon Green) |
| Secondary Accent | `#FFB800` (Gold) |
| Error | `#FF4D4D` |
| Text Primary | `#FFFFFF` |
| Text Secondary | `#CFCFCF` |
| Borders | `#333333` |
| Font | Inter (Google Fonts) |

> No gradients. No glassmorphism. No blue. Flat modern fintech.

---

## License

This project was built for a hackathon demonstration. All rights reserved.
