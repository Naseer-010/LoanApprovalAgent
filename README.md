# Intelli-Credit: AI-Powered Corporate Credit Decisioning Engine

A next-generation credit appraisal platform that automates end-to-end **Credit Appraisal Memo (CAM)** generation for Indian corporate lending. Built for the hackathon theme: *Next-Gen Corporate Credit Appraisal: Bridging the Intelligence Gap.*

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    Frontend (SPA)                         │
│  Single-page app with dark glassmorphism UI               │
│  Upload docs → Run Analysis → View Results                │
├──────────────────────────────────────────────────────────┤
│                   FastAPI Backend                         │
├────────────┬────────────────┬────────────────────────────┤
│  Pillar 1  │   Pillar 2     │        Pillar 3            │
│  Data      │   Research     │        Recommendation       │
│  Ingestor  │   Agent        │        Engine               │
│            │                │                             │
│ • PDF/CSV  │ • Web Search   │ • Five Cs Scorer            │
│ • GST      │ • Promoter     │ • Financial Ratios          │
│ • Bank     │   Risk         │   (DSCR, ICR, Leverage)     │
│ • Cross-   │ • eCourts/MCA  │ • Decision Engine           │
│   verify   │ • RBI/Sector   │ • AI CAM Writer             │
│ • Fraud    │ • Primary      │                             │
│   Detector │   Insights     │                             │
│ • Indian   │                │                             │
│   Regulatory│               │                             │
└────────────┴────────────────┴────────────────────────────┘
```

## Features

### Pillar 1: Data Ingestor
- **Multi-format document processing** — PDF annual reports parsed with `pdfplumber`, structured data extraction via LLM
- **GST filing parser** — CSV/JSON/PDF, per-period breakdown with turnover, tax, ITC
- **Bank statement parser** — credits, debits, balances, transaction counts
- **Cross-verification** — compares GST turnover vs bank credits, detects discrepancies
- **Fraud Detection** — 10+ fraud patterns including:
  - Revenue spikes (>100% period-over-period)
  - ITC inflation / GSTR-2A vs 3B mismatch
  - Circular trading (uniform revenue patterns)
  - Shell company indicators (high turnover, low balance)
  - Round-number credit transactions
  - High velocity with low balance (layering)
- **Indian Regulatory Checks**:
  - Simulated CIBIL commercial credit report (300-900 score)
  - GSTR-2A vs 3B ITC mismatch analysis
  - MCA director DIN status, disqualification, defaulter flags

### Pillar 2: Research Agent
- **LangChain + DuckDuckGo** agent-based web research
- **Targeted search queries** for:
  - Company financial news
  - Promoter litigation (eCourts, NCLT, DRT targeted)
  - MCA filings and annual returns
  - RBI regulatory impact and sector outlook
  - CRISIL/ICRA/CARE credit ratings
- **Promoter Risk Analyzer** — linked company detection, litigation flags, director network analysis
- **Primary Insights Processor** — qualitative observations from factory visits and management interviews

### Pillar 3: Recommendation Engine
- **Financial Ratio Modeling**:
  - DSCR (Debt Service Coverage Ratio) = EBITDA / Debt Payments
  - ICR (Interest Coverage Ratio) = EBITDA / Interest Expense
  - Leverage Ratio = Total Debt / EBITDA
  - Current Ratio, Debt/Equity, EBITDA Margin
  - Each ratio assessed as Pass / Watch / Fail with benchmarks
- **Five Cs Scorer** — Character, Capacity, Capital, Collateral, Conditions (LLM + rule-based hybrid)
- **Decision Engine** with deep explainability:
  - Structured bullet-point reasons citing specific data sources
  - Fraud, regulatory, and promoter signals feed into decision
  - Critical override logic (automatic reject for severe fraud/defaulter flags)
  - Financial covenant conditions
- **AI CAM Writer** — LLM-generated professional Credit Appraisal Memo with Executive Summary and 8 sections

### Frontend
- **Single-page dashboard** with dark glassmorphism theme
- **Professional SVG icons** throughout (no emojis)
- **Drag-and-drop file uploads** for Annual Report, GST, Bank Statement
- **Skeleton pulse animation** during processing
- **Comprehensive result rendering**:
  - Decision banner (APPROVE / REJECT / REFER) with verdict icon
  - Financial ratio gauge cards with pass/watch/fail color coding
  - CIBIL score circular gauge
  - Five Cs progress bars with animated fill
  - Fraud alerts with severity badges and evidence
  - Regulatory checks (GSTR mismatch, MCA director status)
  - Promoter risk cards with linked company count
  - Expandable CAM sections
  - Research findings with sentiment tags

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI, Python 3.10+ |
| AI/LLM | LangChain, HuggingFace Inference API |
| Document Processing | pdfplumber |
| Web Search | DuckDuckGo (via langchain-community) |
| Frontend | Vanilla HTML/CSS/JS, SVG icons |
| Styling | Custom CSS (dark glassmorphism) |

## Getting Started

### Prerequisites
- Python 3.10+
- HuggingFace API token (free at [huggingface.co](https://huggingface.co))

### Setup

```bash
# Clone the repository
git clone <repo-url>
cd loan_decisioning

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your HuggingFace token:
# HUGGINGFACE_API_TOKEN=hf_xxxxxxxxxxxxx
```

### Run

```bash
python run.py
# Server starts at http://localhost:8000
```

Open `http://localhost:8000` in your browser.

### Usage

1. Enter company name, sector, and promoter names
2. Upload financial documents (optional)
3. Add qualitative observations from site visits
4. Click **Run Full Analysis**
5. View the comprehensive credit assessment

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/pipeline/full-analysis` | Run end-to-end analysis pipeline |
| `POST` | `/upload/annual-report` | Upload annual report |
| `POST` | `/upload/gst` | Upload GST filing |
| `POST` | `/upload/bank-statement` | Upload bank statement |
| `POST` | `/ingest/analyze-document` | AI document analysis |
| `POST` | `/ingest/parse-gst` | Parse GST data |
| `POST` | `/ingest/parse-bank-statement` | Parse bank statement |
| `POST` | `/ingest/cross-verify` | Cross-verify GST vs bank |
| `POST` | `/research/web-search` | Web research |
| `POST` | `/research/primary-insights` | Process qualitative notes |
| `GET`  | `/research/report/{company}` | Get research report |
| `POST` | `/recommendation/score` | Five Cs scoring |
| `POST` | `/recommendation/decision` | Loan decision |
| `POST` | `/recommendation/generate-cam` | Generate CAM |
| `GET`  | `/api/health` | Health check |

Interactive API docs: `http://localhost:8000/docs`

## Project Structure

```
loan_decisioning/
├── app/
│   ├── core/
│   │   └── llm.py                    # LLM factory (HuggingFace)
│   ├── routes/
│   │   ├── upload_routes.py           # File upload endpoints
│   │   ├── ingestor_routes.py         # Pillar 1 endpoints
│   │   ├── research_routes.py         # Pillar 2 endpoints
│   │   ├── recommendation_routes.py   # Pillar 3 endpoints
│   │   └── pipeline_routes.py         # Unified pipeline
│   ├── schemas/
│   │   ├── ingestor.py               # Data models (fraud, regulatory)
│   │   ├── research.py               # Research models
│   │   ├── recommendation.py         # Decision models (ratios)
│   │   └── pipeline.py               # Pipeline response model
│   ├── services/
│   │   ├── document_processing/
│   │   │   ├── pdf_extractor.py      # PDF text extraction
│   │   │   ├── ai_extractor.py       # LLM financial extraction
│   │   │   └── document_service.py   # Orchestrator
│   │   ├── ingestor/
│   │   │   ├── gst_parser.py         # GST filing parser
│   │   │   ├── bank_statement_parser.py
│   │   │   ├── cross_verification.py # GST vs bank
│   │   │   ├── fraud_detector.py     # 10+ fraud patterns
│   │   │   └── indian_regulatory.py  # CIBIL, GSTR, MCA
│   │   ├── research/
│   │   │   ├── web_researcher.py     # LangChain agent
│   │   │   ├── news_aggregator.py    # Report builder
│   │   │   ├── primary_insights.py   # Qualitative analysis
│   │   │   └── promoter_analyzer.py  # Promoter risk
│   │   └── recommendation/
│   │       ├── five_cs_scorer.py     # Five Cs + LLM
│   │       ├── decision_engine.py    # DSCR/ICR/Leverage
│   │       └── cam_generator.py      # AI CAM writer
│   ├── config.py
│   └── main.py
├── static/
│   ├── index.html                    # Single-page frontend
│   ├── style.css                     # Dark glassmorphism theme
│   ├── icons.js                      # SVG icon library
│   └── app.js                        # Frontend logic
├── requirements.txt
├── run.py
└── README.md
```

## License

This project was built for a hackathon demonstration.
