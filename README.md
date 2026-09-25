# GTP Wind Intelligence

Internal market analytics platform for German onshore wind energy, built for Greentech Partners.

The platform provides verified answers to investment and consulting questions regarding capacity distribution, pipeline velocity, permitting bottlenecks, and OEM commercial disclosures.

---

## Strategic Questions Answered & Actual Results

### Q1: Which Bundesländer have the most installed onshore wind capacity, and what is their historical trajectory?
Data extracted directly from the German Federal Network Agency (*Bundesnetzagentur* - BNetzA) master registry (**38,488 real onshore wind turbines**):
- **National Installed Operating Capacity:** **72,375.6 MW (~72.4 GW)** across **30,779 operating turbines**.
- **Top 5 Federal States by Operating Capacity:**
  1. **Niedersachsen (NI):** 14,551.6 MW (6,444 turbines) — 20.1% of national total
  2. **Schleswig-Holstein (SH):** 10,222.3 MW (3,705 turbines) — 14.1% of national total
  3. **Nordrhein-Westfalen (NW):** 10,052.7 MW (4,101 turbines) — 13.9% of national total
  4. **Brandenburg (BB):** 9,750.7 MW (4,151 turbines) — 13.5% of national total
  5. **Sachsen-Anhalt (ST):** 5,777.6 MW (2,679 turbines) — 8.0% of national total
- **Historical Growth (2000–2026):** Visualized via annual time-series snapshots in the interactive UI, showing expansion from under 10 GW in 2000 to 72.4 GW today.

### Q2: How healthy is Germany's onshore wind development pipeline, and how fast are projects being approved?
- **Total Planned Pipeline:** **49,986.0 MW (~50.0 GW)** across **8,130 planned turbines** registered in MaStR.
- **Pipeline-to-Operating Ratio:** **69.1%** (for every 10 MW operating, 6.9 MW are in development).
- **National Median Permitting Duration:** **25.7 months** (~770 days) from official MaStR registration to grid energization.
- **Regional Permitting Speeds:**
  - Northern coastal states (NI, SH): 18–22 months median.
  - Southern inland states (BY, BW): 30+ months median due to terrain constraints and species protection litigation (*Artenschutz*).

### Q3: What are wind OEMs disclosing regarding orders, installations, and financials?
Extracted from corporate earnings reports using multilingual semantic retrieval and LLM structured extraction (Nordex Q1 2024 Interim Disclosure):
- **Order Intake (`order_intake_mw`):** 1,680.0 MW (Confidence: 1.00)
- **Installed Capacity (`capacity_installed_mw`):** 1,156.0 MW (Confidence: 1.00)
- **Revenue (`revenue_eur_millions`):** 1,564.0 EUR_M (Confidence: 0.99)
- Every claim maintains bilingual traceability (verbatim German sentence paired with English translation) and an interactive "Mark as verified" human audit button.

---

## German Regulatory & Policy Context

The values shown in this platform directly reflect German statutory targets and spatial planning laws:

1. **EEG 2023 Statutory Targets:**
   - Germany mandates 80% renewable electricity by 2030.
   - Statutory milestone: **115 GW onshore wind by 2030** and **160 GW by 2040**.
   - Current operating capacity (72.4 GW) leaves a **42.6 GW expansion gap** to be built before 2030.
   - The planned pipeline (50.0 GW) proves project volume is adequate, but delivery speed is constrained by the 25.7-month permitting cycle.
2. **The Federal Immission Control Act (*BImSchG*):**
   - Every turbine must obtain a formal immission permit covering noise, shadow flicker, environmental impact assessments (EIA), and air traffic clearances.
3. **The North-South Divide (*Nord-Süd-Gefälle*):**
   - Four northern states (NI, SH, NW, BB) hold **61.6%** of all operating wind capacity.
   - Southern states like Bavaria (Bayern: 2,632 MW / 3.6%) were constrained by the **10H Rule** (which banned turbines within 10 times their tip height from settlements). Under the new **Wind-on-Land Act (*Wind-an-Land-Gesetz*)**, states must dedicate 1.8% to 2.2% of their land area to wind, opening the southern market.

---

## Data Confidence Tiers

| Tier | Classification | Data Source | Authority Level | UI Indicator | Verification Policy |
|---|---|---|---|:---:|---|
| **Tier 1** | Official Statutory | Marktstammdatenregister (MaStR) / BNetzA | Legally binding, metered grid assets | 🟢 Green badge | Automated ingestion |
| **Tier 2** | Corporate Disclosure | OEM press releases & quarterly reports (PDF) | Unaudited forward-looking statements | 🟡 Amber badge | Requires human verification |

---

## Architecture & Technology Stack

```
+-----------------------------------------------------------------------------------+
| COMPONENT ARCHITECTURE                                                            |
+-----------------------------------------------------------------------------------+
|  Analytical Warehouse: DuckDB 1.1+ (Columnar storage, vectorized engine)          |
|  Vector Search:        DuckDB VSS Extension (array_cosine_similarity + HNSW index)|
|  Dense Embeddings:     SentenceTransformers paraphrase-multilingual-MiniLM-L12-v2  |
|  LLM Extraction:       OpenRouter API (inclusionai/ling-3.0-flash-fin + fallback) |
|  Data Parsing:         Pandas + Regex Header Matcher                              |
|  Visualizations:       Plotly Express + Graph Objects                             |
|  Web Framework:        Streamlit (Reactive Python, port 8501)                     |
|  CI/CD:                GitHub Actions (.github/workflows/pipeline.yml)           |
+-----------------------------------------------------------------------------------+
```

### Architectural Decisions
- **DuckDB over SQLite/Postgres:** Columnar storage evaluates aggregations across 38,000+ rows in under 15 milliseconds. Embeds locally without managing external database server infrastructure.
- **DuckDB VSS Extension:** Native vector cosine similarity runs inside the same SQL database file (`db/gtp.duckdb`), eliminating the need for external vector databases.
- **Multilingual Embeddings:** `paraphrase-multilingual-MiniLM-L12-v2` maps German industrial terms (*"Auftragseingang"*) and English concepts (*"order intake"*) to identical vector coordinates. Runs on CPU with a 420 MB memory footprint.
- **OpenRouter Multi-Model Fallback:** Chains `inclusionai/ling-3.0-flash-fin:free` to `liquid/lfm-2.5-2.6b:free` and `qwen/qwen3.8-27b:free` to absorb upstream rate limits without pipeline failure.

---

## Directory Structure

```
gtp-wind-intelligence/
├── .env.example                       # Environment variable template
├── .gitignore                          # Git exclusions (.env, db/*.duckdb, data/raw/*)
├── README.md                           # Project documentation
├── requirements.txt                    # Python dependencies
├── .github/
│   └── workflows/
│       └── pipeline.yml                # Monthly automated pipeline run (cron)
├── config/
│   └── tier2_sources.yaml              # OEM source configurations and PDF regex patterns
├── data/
│   └── raw/                            # Raw data dumps (git-ignored)
├── db/                                 # DuckDB storage directory
├── docs/
│   └── SYSTEM_ARCHITECTURE_AND_DEEP_DIVE.md  # Detailed technical reference
├── reference/
│   └── plz_bundesland.csv              # 3,252 German postal code to state mappings
├── pipeline/
│   ├── __init__.py
│   ├── fetch_tier1.py                  # Ingests real MaStR turbines & extracts PLZ records
│   ├── parse.py                        # Onshore filtering, unit conversion & regex matching
│   ├── load.py                         # DuckDB DDL, VSS vector index setup & bulk insert
│   ├── aggregate.py                    # Time-series cumulative sums & permitting medians
│   ├── fetch_tier2.py                  # Scrapes IR portals & downloads OEM disclosures
│   ├── rag.py                          # 500-word chunking, embeddings & VSS cosine search
│   ├── extract_claims.py               # OpenRouter LLM extraction & schema validation
│   └── run_pipeline.py                 # Master CLI orchestrator (tier1, tier2, all)
└── app/
    ├── __init__.py
    ├── main.py                         # Streamlit landing page with KPI cards
    ├── pages/
    │   ├── q1_capacity.py              # State capacity rankings & historical trends
    │   ├── q2_pipeline.py              # Pipeline volume & permitting traffic light charts
    │   └── provenance.py               # Audit portal with bilingual cards & verification
    └── utils/
        ├── __init__.py
        ├── charts.py                   # Standardized Plotly styling and colors
        └── db.py                       # DuckDB connection handling & query wrappers
```

---

## Database Schema (`db/gtp.duckdb`)

1. **`sources`:** Metadata registry of all ingested sources with confidence tier (1 or 2).
2. **`plz_bundesland`:** 3,252 five-digit German postal codes mapped to federal states and ISO codes.
3. **`wind_plants`:** 38,488 real onshore wind turbines with capacities, dates, locations, and operators.
4. **`snapshots`:** 459 annual state and national aggregates (2000–2026) for capacity, pipeline, and permitting speed.
5. **`pipeline_runs`:** Timestamped execution log of all pipeline steps and processed record counts.
6. **`document_chunks`:** 500-word text chunks stored alongside 384-dimensional dense float vectors (`FLOAT[384]`).
7. **`extracted_claims`:** Audited OEM commercial metrics with German quotes, English translations, confidence scores, and verification status.

---

## Getting Started

### 1. Prerequisites
- Python 3.10+ (tested on Python 3.11 / 3.12)
- Windows, macOS, or Linux

### 2. Installation
Clone the repository and install dependencies:
```bash
git clone https://github.com/your-org/gtp-wind-intelligence.git
cd gtp-wind-intelligence
pip install -r requirements.txt
```

### 3. Environment Configuration
Copy `.env.example` to `.env` and set your OpenRouter API key:
```bash
cp .env.example .env
```
Inside `.env`:
```ini
OPENROUTER_API_KEY=your_openrouter_api_key_here
```
*(Note: If you have Ollama installed locally with `qwen2.5:7b`, the pipeline will use Ollama first and fallback to OpenRouter).*

### 4. Running the Pipeline

**Run Tier 1 only (Official MaStR statutory data, no LLM required):**
```bash
python -m pipeline.run_pipeline tier1
```

**Run Tier 2 only (OEM document discovery, embeddings, and LLM claim extraction):**
```bash
python -m pipeline.run_pipeline tier2
```

**Run End-to-End Pipeline (Tier 1 + Tier 2):**
```bash
python -m pipeline.run_pipeline all
```

### 5. Launching the Web Application
```bash
streamlit run app/main.py --server.port 8501
```
Open your browser and navigate to: **[http://localhost:8501](http://localhost:8501)**

---

## Verification & Audit Workflow

When consultants prepare reports for client engagements:
1. Navigate to the **Data Provenance & Audit** page in the Streamlit application.
2. Review the **Tier 2 Extracted Claims** table.
3. Compare the **Original German Sentence** from the earnings release against the **English Translation** and the extracted numerical value.
4. Click the **✓ Mark as verified** button. This updates `human_verified = True` and sets `verified_at` to the current timestamp in `db/gtp.duckdb`. Unverified claims are flagged with warning badges across all analytics views.

---

## Automated CI/CD Execution
The repository includes a monthly automation workflow in [`.github/workflows/pipeline.yml`](.github/workflows/pipeline.yml).
- **Trigger:** First day of every month at 06:00 UTC, or manually via `workflow_dispatch`.
- **Fault Tolerance:** Tier 2 has `continue-on-error: true` so external API limits do not prevent Tier 1 government registry updates.
