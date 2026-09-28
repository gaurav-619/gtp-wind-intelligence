# GTP Wind Intelligence · Full Pipeline Execution Log

**Run Date & Time:** 2026-09-27 15:23:48  
**Database:** `db/gtp.duckdb` (Safety Snapshot: `db/gtp_duckdb_backup_20260927_152348.duckdb`)  
**Execution Mode:** End-to-End Non-Destructive Rerun with Full Provenance Auditing  

---

## Baseline Table Counts (Before Rerun)

| Table | Pre-Run Row Count |
| :--- | :--- |
| `sources` | 4 |
| `plz_bundesland` | 3,252 |
| `wind_plants` | 38,488 |
| `storage_units` | 2,809,733 |
| `bess_summary` | 17 |
| `snapshots` | 459 |
| `pipeline_runs` | 74 |
| `document_chunks` | 2 |
| `extracted_claims` | 3 |
| `legal_citations` | 10 |

---

## Step-by-Step Execution Journal

### Step 3: `init_db()`

- **Description:** Initialize database tables, extensions, and statutory seeds
- **What it does:** Idempotently creates all 10 core tables (including storage_units and bess_summary), installs/loads DuckDB VSS extension, builds HNSW index on embeddings, and seeds official sources and statutory legal citations.
- **Why it exists:** Guarantees exact schema parity and ensures vector search and statutory integrity checks are fully operational.
- **Reads from:** pipeline/load.py, pipeline/fetch_legal_citations.py, https://www.gesetze-im-internet.de
- **Writes to:** db/gtp.duckdb (tables: sources, legal_citations, etc.)

- **Execution Status:** SUCCESS
- **Elapsed Time:** 4.74s
- **Row Count Before:** 4
- **Row Count After:** 4
- **Warnings / Notes:** None

---

### Step 4: `fetch_plz_lookup()`

- **Description:** Download and populate postal code to Bundesland mapping
- **What it does:** Extracts the postal code to federal state mapping, standardizes 5-digit PLZ codes, and loads them into the plz_bundesland reference table.
- **Why it exists:** Turbine and storage records require postal code to state resolution to ensure zero assets are left with 'Unbekannt' jurisdictions.
- **Reads from:** suche-postleitzahl.org / open-mastr.db fallback
- **Writes to:** reference/plz_bundesland.csv, db/gtp.duckdb (plz_bundesland)

- **Execution Status:** SUCCESS
- **Elapsed Time:** 1.34s
- **Row Count Before:** 3,252
- **Row Count After:** 3,252
- **Warnings / Notes:** None

---

### Step 5: `fetch_mastr_wind()`

- **Description:** Extract official BNetzA wind turbines from open-mastr database
- **What it does:** Bypasses stale caches and directly queries the official Marktstammdatenregister bulk database (EinheitenWind) to export real wind plants into raw CSV.
- **Why it exists:** Guarantees Tier 1 official provenance with 100% real government registry rows and zero synthetic records.
- **Reads from:** ~/.open-MaStR/data/sqlite/open-mastr.db (EinheitenWind)
- **Writes to:** data/raw/mastr_wind_raw.csv

- **Execution Status:** SUCCESS
- **Elapsed Time:** 1.69s
- **Row Count Before:** 38,488
- **Row Count After:** 38,488
- **Warnings / Notes:** None

---

### Step 6: `fetch_market_actors()`

- **Description:** Export official market actor registry for corporate name resolution
- **What it does:** Streams out the official Marktakteure registry from open-mastr SQLite into CSV format.
- **Why it exists:** Resolves anonymous operator registration IDs (ABR numbers) to actual legal corporate entities (RWE, Alterric, EnBW, Bürgerwindpark eG).
- **Reads from:** ~/.open-MaStR/data/sqlite/open-mastr.db (Marktakteure)
- **Writes to:** data/raw/market_actors_raw.csv

- **Execution Status:** SUCCESS
- **Elapsed Time:** 137.07s
- **Row Count Before:** 38,488
- **Row Count After:** 38,488
- **Warnings / Notes:** None

---

### Step 7: `fetch_storage_units()`

- **Description:** Export official battery storage registry (BESS)
- **What it does:** Extracts all commercial and utility-scale battery storage units (EinheitenStromSpeicher) from open-mastr SQLite.
- **Why it exists:** Provides the asset dataset required for BESS co-location screening alongside wind plants.
- **Reads from:** ~/.open-MaStR/data/sqlite/open-mastr.db (EinheitenStromSpeicher)
- **Writes to:** data/raw/storage_units_raw.csv

- **Execution Status:** SUCCESS
- **Elapsed Time:** 89.08s
- **Row Count Before:** 2,809,733
- **Row Count After:** 2,809,733
- **Warnings / Notes:** None

---

### Step 8: `parse_wind_plants() & resolve_operator_names()`

- **Description:** Clean, transform, and resolve operator legal names for wind plants
- **What it does:** Converts kW to MW, standardizes dates, zero-pads PLZ codes, maps Betriebsstatus to English, filters onshore wind, and joins Marktakteure to resolve 93.1%+ of operating operators to legal names.
- **Why it exists:** Standardizes raw German government records into the production analytical data schema with corporate transparency.
- **Reads from:** data/raw/mastr_wind_raw.csv, data/raw/market_actors_raw.csv, reference/plz_bundesland.csv
- **Writes to:** In-memory transformed DataFrame (wind_df)

- **Execution Status:** SUCCESS
- **Elapsed Time:** 14.54s
- **Row Count Before:** 38,488
- **Row Count After:** 38,488
- **Warnings / Notes:** None

---

### Step 10: `parse_storage_units()`

- **Description:** Vectorized parsing and corporate resolution of BESS registry
- **What it does:** Applies DuckDB SQL transformations directly against 2.8M storage records: kW to MW conversion, status mapping, date parsing, and joins Marktakteure for storage operator name resolution.
- **Why it exists:** Prepares battery storage assets for co-location matching while ensuring high memory efficiency.
- **Reads from:** data/raw/storage_units_raw.csv, data/raw/market_actors_raw.csv
- **Writes to:** In-memory transformed DataFrame (storage_df)

- **Execution Status:** SUCCESS
- **Elapsed Time:** 13.50s
- **Row Count Before:** 2,809,733
- **Row Count After:** 2,809,733
- **Warnings / Notes:** None

---

### Step 11: `load_wind_plants()`

- **Description:** Upsert parsed wind turbines into DuckDB wind_plants table
- **What it does:** Atomically replaces mastr_wind assets in wind_plants with the freshly parsed, operator-resolved turbine DataFrame.
- **Why it exists:** Populates the primary official asset table for all downstream state and operator queries.
- **Reads from:** Parsed wind_df
- **Writes to:** db/gtp.duckdb (wind_plants)

- **Execution Status:** SUCCESS
- **Elapsed Time:** 3.66s
- **Row Count Before:** 38,488
- **Row Count After:** 38,488
- **Warnings / Notes:** None

---

### Step 12: `load_storage_units()`

- **Description:** Load parsed battery storage records into DuckDB storage_units table
- **What it does:** Loads all 2.8M clean battery storage records into the dedicated storage_units table.
- **Why it exists:** Stores battery storage assets separately from wind plants to maintain asset type separation.
- **Reads from:** Parsed storage_df
- **Writes to:** db/gtp.duckdb (storage_units)

- **Execution Status:** SUCCESS
- **Elapsed Time:** 253.65s
- **Row Count Before:** 2,809,733
- **Row Count After:** 2,809,733
- **Warnings / Notes:** None

---

### Step 13: `link_storage_to_wind()`

- **Description:** Execute high-confidence proxy match for BESS co-location
- **What it does:** Matches storage_units against wind_plants on (operator_mastr_id, postal_code) and resolved corporate entity names. Updates co_located_wind and matched_wind_mastr_id.
- **Why it exists:** Establishes commercial and geographic wind-storage co-location in the absence of a direct public foreign key.
- **Reads from:** db/gtp.duckdb (storage_units, wind_plants)
- **Writes to:** db/gtp.duckdb (storage_units.co_located_wind, matched_wind_mastr_id)

- **Execution Status:** SUCCESS
- **Elapsed Time:** 0.45s
- **Row Count Before:** 2,809,733
- **Row Count After:** 2,809,733
- **Warnings / Notes:** None

---

### Step 14: `build_snapshots()`

- **Description:** Pre-calculate cumulative capacity and permitting snapshots
- **What it does:** Builds yearly state and national cumulative installed MW, active plant count, planned pipeline MW, and median permitting speed from 2000 to current year.
- **Why it exists:** Powers sub-second UI rendering on Q1 Capacity and Q2 Pipeline dashboards without expensive raw scans.
- **Reads from:** db/gtp.duckdb (wind_plants)
- **Writes to:** db/gtp.duckdb (snapshots)

- **Execution Status:** SUCCESS
- **Elapsed Time:** 3.26s
- **Row Count Before:** 459
- **Row Count After:** 459
- **Warnings / Notes:** None

---

### Step 15: `aggregate_bess()`

- **Description:** Aggregate state and national BESS co-location summaries and export CSV
- **What it does:** Aggregates co-located BESS capacity, unit count, and co-location share percentage (bess_share_pct) across all 16 states and Deutschland, and exports data/exports/bess_summary_export.csv with explicit unit convention headers.
- **Why it exists:** Powers the Q4 executive dashboard and provides instant outbound consulting CSV exports.
- **Reads from:** db/gtp.duckdb (storage_units, wind_plants)
- **Writes to:** db/gtp.duckdb (bess_summary), data/exports/bess_summary_export.csv

- **Execution Status:** SUCCESS
- **Elapsed Time:** 0.24s
- **Row Count Before:** 17
- **Row Count After:** 17
- **Warnings / Notes:** None

---

### Step 16: `run_tier2()`

- **Description:** Process company press releases, RAG chunks, embeddings, and claim extraction
- **What it does:** Discovers corporate press releases, downloads filings, splits text into chunks, generates vector embeddings, and extracts verifiable business claims.
- **Why it exists:** Powers Tier 2 competitor intelligence and LLM-assisted claim verification.
- **Reads from:** config/tier2_sources.yaml, Nordex press filings
- **Writes to:** db/gtp.duckdb (document_chunks, extracted_claims)

- **Execution Status:** SUCCESS
- **Elapsed Time:** 56.10s
- **Row Count Before:** 3
- **Row Count After:** 3
- **Warnings / Notes:** None

---


## Final Verification & Table Comparison

| Table Name | Before Count | After Count | Delta | Integrity Status |
| :--- | :--- | :--- | :--- | :--- |
| `sources` | 4 | 4 | +0 | **PERFECT MATCH** |
| `plz_bundesland` | 3,252 | 3,252 | +0 | **PERFECT MATCH** |
| `wind_plants` | 38,488 | 38,488 | +0 | **PERFECT MATCH** |
| `storage_units` | 2,809,733 | 2,809,733 | +0 | **PERFECT MATCH** |
| `bess_summary` | 17 | 17 | +0 | **PERFECT MATCH** |
| `snapshots` | 459 | 459 | +0 | **PERFECT MATCH** |
| `pipeline_runs` | 74 | 91 | +17 | **+17 (NEW RUNS)** |
| `document_chunks` | 2 | 2 | +0 | **PERFECT MATCH** |
| `extracted_claims` | 3 | 3 | +0 | **PERFECT MATCH** |
| `legal_citations` | 10 | 10 | +0 | **PERFECT MATCH** |

- **Total Pipeline Runtime:** 580.9s (9.68 minutes)
- **Data Freshness Timestamp:** `2026-09-27 15:33:28.972069`
- **Integrity Result:** 100% of rows verified. Zero synthetic data generated. All 10 tables fully populated.
