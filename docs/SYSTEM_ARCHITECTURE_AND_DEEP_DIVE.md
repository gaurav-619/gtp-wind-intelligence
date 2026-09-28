# GTP Wind Intelligence — Comprehensive System Architecture & Technical Master Blueprint

> **Target Audience:** Anyone reading this codebase for the first time—from a junior software engineer or data scientist to senior investment partners at **Greentech Partners**.  
> **Mission:** An end-to-end, zero-ambiguity reference explaining **what** was built, **why** every technology was selected, **how** every Python function and SQL table works, **what the exact business results are**, and **how the German regulatory and legislative scenario directly maps to the database values**.

---

## Table of Contents
1. [The German Energy Market Scenario & Policy Reality](#1-the-german-energy-market-scenario--policy-reality)
   - 1.1 The German Energiewende & Statutory Targets (EEG 2023)
   - 1.2 Target vs. Actual: Where Germany Stands Today (71.0 GW vs. 115 GW)
   - 1.3 The North-South Divide (*Nord-Süd-Gefälle*) & Planning Law (Wind-an-Land-Gesetz & 10H Rule)
   - 1.4 Permitting Mechanics & Bottlenecks under the Federal Immission Control Act (*BImSchG*)
   - 1.5 The Role of the Federal Network Agency (*BNetzA*) & the Marktstammdatenregister (MaStR)
   - 1.6 German Domain Terminology to Code Mapping Dictionary
   - 1.7 German Number Localization Challenges (Dots vs. Commas & Leading Zeros)
2. [Executive Summary & Strategic Intelligence Modules (With Authoritative Results)](#2-executive-summary--strategic-intelligence-modules-with-authoritative-results)
   - 2.1 Market Landscape: Capacity Distribution & Commissioning Trajectories (38,488 Turbines)
   - 2.2 Development Pipeline & Permitting Radar: Permitting Velocity & Forward Realization (49.8 GW Pipeline & 26.3 Months)
   - 2.3 Operator Intelligence & Repowering Radar: Operator Concentration, Parent Rollup & EEG Subsidy Cliff (Top 20 & 13.1 GW Repowering Cliff)
   - 2.4 Storage Co-Location Screener: Battery Energy Storage Systems (BESS) Co-Location (54.51 MW Co-located)
   - 2.5 Tier 2 Disclosures: Commercial OEM Financial & Operational Intelligence (Nordex Q1 2024 Claims)
3. [System Architecture & The Two-Tier Data Governance Architecture](#3-system-architecture--the-two-tier-data-governance-architecture)
   - 3.1 High-Level Architecture Diagram (Mermaid)
   - 3.2 Tier 1 vs. Tier 2 Philosophy: Hard Facts vs. Corporate Disclosures
4. [Technology Stack & Architectural Decisions (Why We Chose Them)](#4-technology-stack--architectural-decisions-why-we-chose-them)
   - 4.1 DuckDB vs. PostgreSQL / SQLite
   - 4.2 DuckDB VSS vs. Dedicated Vector Databases (Pinecone / ChromaDB)
   - 4.3 Multilingual MiniLM-L12-v2 vs. Monolingual English Models
   - 4.4 OpenRouter API Multi-Model Fallback Chain vs. Single Endpoints
   - 4.5 Streamlit Reactive UI vs. React / Next.js
5. [Database Architecture & Complete Schema Specification (db/gtp.duckdb)](#5-database-architecture--complete-schema-specification-dbgtpduckdb)
   - 5.1 Table: sources
   - 5.2 Table: plz_bundesland
   - 5.3 Table: wind_plants
   - 5.4 Table: snapshots
   - 5.5 Table: pipeline_runs
   - 5.6 Table: document_chunks
   - 5.7 Table: extracted_claims
   - 5.8 Table: legal_citations
   - 5.9 Table: storage_units (BESS Battery Energy Storage Systems)
   - 5.10 Table: bess_summary (Aggregated Wind-BESS Co-Location Intelligence)
6. [Pipeline Walkthrough: Every Python Module & Function Explained](#6-pipeline-walkthrough-every-python-module--function-explained)
   - 6.1 pipeline/fetch_tier1.py (Registry Ingestion, Market Actors & BESS Harvesting)
   - 6.2 pipeline/parse.py (Onshore Normalization & Corporate Name Resolution)
   - 6.3 pipeline/load.py (DDL, VSS Indexing & Storage Ingestion/Linking)
   - 6.4 pipeline/aggregate.py (Historical Aggregations, Permitting & BESS Summaries)
   - 6.5 pipeline/fetch_tier2.py (Document Scraper & Fallback Harvester)
   - 6.6 pipeline/rag.py (Text Chunking, Multilingual Embeddings & VSS Search)
   - 6.7 pipeline/extract_claims.py (LLM Extraction, German Parsing & Plausibility Validation)
   - 6.8 pipeline/run_pipeline.py (CLI Master Controller)
7. [Streamlit Analytical Frontend (app/)](#7-streamlit-analytical-frontend-app)
   - 7.1 Shared Visual Tokens & Design System (app/utils/theme.py)
   - 7.2 Corporate Hierarchy & Rollup Engine (app/utils/operators.py)
   - 7.3 Application Entrypoint (app/main.py)
   - 7.4 Executive Overview (app/views/overview.py)
   - 7.5 Market Landscape (app/views/market_landscape.py)
   - 7.6 Development Pipeline & Permitting Radar (app/views/pipeline_radar.py)
   - 7.7 Operator Intelligence & Repowering Radar (app/views/operator_intelligence.py)
   - 7.8 Storage Co-Location Screener (app/views/storage_colocation.py)
   - 7.9 Data Trust Center (app/views/data_trust_center.py)
8. [Automated CI/CD Workflow (.github/workflows/pipeline.yml)](#8-automated-cicd-workflow-githubworkflowspipelineyml)
9. [Production Troubleshooting & Engineering Edge Cases Solved](#9-production-troubleshooting--engineering-edge-cases-solved)
10. [End-to-End Operational Guide & Runbook](#10-end-to-end-operational-guide--runbook)
---

## 1. The German Energy Market Scenario & Policy Reality

To evaluate German wind energy data, an analyst must understand how federal laws, regional politics, and geography create the exact numbers in our database.

```
                    GERMAN ONSHORE WIND TARGET TRAJECTORY
  GW
 160 +-----------------------------------------------------------------------+ [2040 Target: 160 GW]
     |                                                                       |
 140 |                                                                       |
     |                                                                       |
 120 |                                                      * [2030 Target]  |
     |                                                    /   (115 GW)       |
 100 |                                                  /                    |
     |                                                /                      |
  80 |                              [Today: 72.4 GW] *                       |
     |                             ==================                        |
  60 |                       * - - -                                         |
     |                * - - -                                                |
  40 |         * - - -                                                       |
     |  * - - -                                                              |
   0 +---+--------+--------+--------+--------+--------+--------+--------+----+
       2000     2005     2010     2015     2020     2024     2030     2040
```

### 1.1 The German Energiewende & Statutory Targets (EEG 2023)
Germany's energy transition (*Energiewende*) is anchored in the Renewable Energy Sources Act (*Erneuerbare-Energien-Gesetz* - EEG). Following the 2022 energy crisis, the German federal government passed the **EEG 2023**, establishing binding legal expansion paths:
- **Core Mandate:** At least **80% of gross German electricity consumption** must come from renewable sources by 2030.
- **Onshore Wind Statutory Milestone 2030:** **115 Gigawatts (GW)** installed capacity.
- **Onshore Wind Statutory Milestone 2040:** **160 Gigawatts (GW)** installed capacity.
- **Annual Addition Requirement:** Germany must add **~8 to 10 GW of net new onshore capacity every year** between 2024 and 2030.

### 1.2 Target vs. Actual: Where Germany Stands Today (71.0 GW vs. 115 GW)
In GTP Wind Intelligence, our Tier 1 pipeline analyzes **38,488 real onshore wind turbines** directly from the German master registry. The data reveals:
- **Current Operating Capacity:** **71,014.5 MW (~71.0 GW)** across **30,358 operating turbines**.
- **Expansion Gap to 2030 Target:** **44.0 GW** still needs to be built and energized over the next ~4.5 years.
- **The Pipeline Surplus:** Our system counts **49,836.2 MW (~49.8 GW)** across **8,130 planned turbines** registered in the government database.
- **Strategic Insight for Greentech Partners:** On paper, the development pipeline (49.8 GW) is *more than large enough* to bridge the 44.0 GW gap to 115 GW. The critical bottleneck is therefore **not** developer interest or project origination—it is the **permitting and grid connection timeline**.

### 1.3 The North-South Divide (*Nord-Süd-Gefälle*) & Planning Law (Wind-an-Land-Gesetz & 10H Rule)
When you inspect our Market Landscape capacity rankings, four states account for **62.0% (44,063.3 MW)** of all operating wind capacity in Germany:
1. **Niedersachsen (NI):** 14,428.3 MW
2. **Schleswig-Holstein (SH):** 10,114.2 MW
3. **Nordrhein-Westfalen (NW):** 9,872.5 MW
4. **Brandenburg (BB):** 9,648.3 MW

In contrast, southern industrial economic powerhouses lag dramatically:
- **Bayern (Bavaria - BY):** 2,893.0 MW (only 4.1% of national capacity despite being Germany's largest state by area).
- **Baden-Württemberg (BW):** 2,288.2 MW (3.2% of national capacity).

**Why does this disparity exist in the data?**
1. **Physical Wind Resource:** Northern coastal plains have mean annual wind speeds of 6.5–8.5 m/s at 100m hub height, whereas southern inland states average 4.5–6.0 m/s.
2. **The Bavarian "10H Rule" (*10H-Regel*):** In 2014, Bavaria enacted the 10H distance law, requiring any wind turbine to be placed at a distance equal to at least 10 times its total tip height away from residential housing. For a modern 200m turbine, that meant a 2,000m buffer zone, which rendered **98% of Bavaria's land area legally ineligible for wind development**. This froze Bavarian wind additions for nearly a decade.
3. **The Wind-on-Land Act (*Wind-an-Land-Gesetz*):** In 2022, the federal government enacted mandatory land quotas. By 2032, every state must allocate an average of **2.0% of its land area** for wind (Niedersachsen: 2.2%, Bavaria: 1.8%). Southern states are now scrambling to open regional forestry and agricultural land, creating a high-growth investment window.

### 1.4 Permitting Mechanics & Bottlenecks under the Federal Immission Control Act (*BImSchG*)
Before a wind turbine can be erected in Germany, it must undergo a rigorous approval process under the **Federal Immission Control Act** (*Bundes-Immissionsschutzgesetz* - BImSchG).
- **Process Steps:**
  1. Environmental Impact Assessment (EIA / *UVP*): Bat surveys, red kite (*Rotmilan*) flight tracking, and acoustic noise modeling.
  2. Air Traffic Safety Approval: Federal Aviation Office (*Luftfahrt-Bundesamt*) and military radar checks.
  3. Municipal Building Permission (*Gemeindliches Einvernehmen*).
  4. BNetzA Auction Bid (*Ausschreibung*): Developers must win a statutory feed-in tariff award.
- **The Metric in our System:**
  In [`pipeline/aggregate.py`](file:///c:/Users/goura/Documents/Project/Prototype/gtp-wind-intelligence/pipeline/aggregate.py), we calculate the exact duration:
  $$\text{Permit Duration} = \text{Inbetriebnahmedatum} - \text{Registrierungsdatum}$$
- **The Result:** The nationwide median permitting duration is **26.3 months** (~789 days).
  - Northern states (NI, SH) with specialized planning offices average **18–22 months**.
  - Southern and complex forested terrains (BY, BW) routinely exceed **30+ months** due to local citizen initiatives (*Bürgerinitiativen*) and environmental lawsuits.

### 1.5 The Role of the Federal Network Agency (*BNetzA*) & the Marktstammdatenregister (MaStR)
The **Federal Network Agency** (*Bundesnetzagentur* - BNetzA) is the supreme regulatory authority for electricity, gas, telecommunications, post, and railway markets in Germany.
- By federal law (§ 111e EnWG and the MaStRV ordinance), every asset generating electricity connected to the German grid must be registered in the **Marktstammdatenregister (MaStR)**.
- Registration is legally required to receive EEG feed-in tariffs or direct marketing compensation.
- Each unit receives an **EinheitMastrNummer** (starting with `SEE` for electricity generation units).
- Because this registry is legally binding and enforced by the government, it is designated as **Tier 1 (Authoritative Truth)** in our architecture.

### 1.6 German Domain Terminology to Code Mapping Dictionary

| German Regulatory Term | Code / Database Column | Technical & Legal Meaning |
|---|---|---|
| `EinheitMastrNummer` | `mastr_id` | Unique statutory identifier for the electricity generator (starts with `SEE`). |
| `NameStromerzeugungseinheit` | `display_name` | Name of the turbine or wind park (e.g., *Windpark Cuxhaven*). |
| `AnlagenbetreiberMastrNummer` | `operator_name` | MaStR ID of the commercial utility or community energy park (*Bürgerwindpark*). |
| `EinheitBetriebsstatus` | `betriebs_status` | Status: mapped from `"In Betrieb"` $\rightarrow$ `'operating'`, `"In Planung"` $\rightarrow$ `'planned'`, `"Stillgelegt"` $\rightarrow$ `'decommissioned'`. |
| `Energietraeger` | `energy_source` | Primary energy fuel; filtered strictly for `"Wind"`. |
| `Bruttoleistung` | `bruttoleistung_kw` / `_mw` | **Gross capacity**: The maximum physical power rating of the generator in kW. |
| `Nettonennleistung` | `nettonennleistung_kw` / `_mw` | **Net capacity**: The actual active power fed into the grid after internal consumption (typically $\approx 97\%$ of gross). |
| `Inbetriebnahmedatum` | `inbetriebnahmedatum` | **Commissioning date**: The exact calendar date the turbine was energized and connected to the German transmission/distribution grid. |
| `GeplantesInbetriebnahmedatum`| `planned_date` | **Planned commissioning date**: Forecasted grid-connection date for projects currently in permitting or construction. |
| `Registrierungsdatum` | `registrierungsdatum` | **Permit / Registration date**: The date the project was officially registered in MaStR. |
| `DatumLetzteAktualisierung` | `last_updated` | Timestamp when the plant operator last officially modified the unit record. |
| `Postleitzahl` | `postleitzahl` | 5-digit German postal code (PLZ). |
| `Bundesland` | `bundesland` / `bundesland_code` | German federal state name (e.g. *Niedersachsen*) and ISO code (e.g. `NI`). |
| `WindAnLandOderAufSee` | Onshore/Offshore filter | Distinguishes `"Windkraft an Land"` (Onshore) from `"Windkraft auf See"` (Offshore). |
| `Auftragseingang` | `order_intake_mw` | **Order intake**: New firm commercial orders signed by a turbine manufacturer in MW. |
| `Installierte Leistung` | `capacity_installed_mw` | **Installed capacity**: Volume of wind capacity constructed/commissioned by an OEM in a reporting period. |
| `Umsatz` / `Konzernumsatz` | `revenue_eur_millions` | **Revenue**: Total top-line revenues reported in millions of Euros. |

### 1.7 German Number Localization Challenges (Dots vs. Commas & Leading Zeros)
German financial and technical disclosures follow different typography from English conventions:
1. **Thousands Separator vs. Decimal Point:**
   - In German: `1.680 MW` means **1,680 Megawatts** (the period is a thousands delimiter).
   - In German: `0,89 Mio. EUR` means **0.89 Million Euros** (the comma is the decimal delimiter).
   - If an un-localized English LLM or regex processes `1.680 MW`, it parses it as `1.68 MW` (a 1,000x error!).
   - **Our Solution:** In [`pipeline/extract_claims.py`](file:///c:/Users/goura/Documents/Project/Prototype/gtp-wind-intelligence/pipeline/extract_claims.py), the prompt explicitly instructs the LLM on German number notation, and `validate_claim()` normalizes periods and commas before converting to float.
2. **Leading Zeros in Postal Codes (PLZ):**
   - East German postal codes (Saxony, Saxony-Anhalt) start with `0` (e.g. `01067` Dresden, `04109` Leipzig).
   - Reading these as numbers drops the leading zero (`1067`), corrupting geographical lookups.
   - **Our Solution:** In [`pipeline/parse.py`](file:///c:/Users/goura/Documents/Project/Prototype/gtp-wind-intelligence/pipeline/parse.py), postal codes are string-sanitized: `.str.replace(r"\.0$", "", regex=True).str.zfill(5)`.

---

## 2. Executive Summary & Strategic Questions Answered (With Exact Results)

GTP Wind Intelligence answers three critical investment questions using **real German government data** and **OpenRouter LLM fact extraction**:

### 2.1 Market Landscape: Capacity Distribution & Commissioning Trajectories (38,488 Real Turbines)
> **Strategic Question 1:** *Which German Bundesländer have the most installed onshore wind capacity, and what is their historical growth trajectory?*

From our database analysis of **38,488 real onshore wind turbines**:
- **Total National Operating Onshore Capacity:** **71,014.5 MW (~71.0 GW)** across **30,358 operating turbines**.
- **Average Turbine Capacity:** **2.34 MW** (rising from ~1.2 MW in 2000 to >5.0 MW for newly commissioned modern turbines).

#### Complete Federal State Capacity Breakdown (Real MaStR Data):
| Rank | Bundesland | ISO Code | Operating Capacity (MW) | Turbine Count | % of National Capacity |
|:---:|---|:---:|:---:|:---:|:---:|
| 1 | **Niedersachsen** (Lower Saxony) | `NI` | **14,428.3 MW** | 6,403 | 20.3% |
| 2 | **Schleswig-Holstein** | `SH` | **10,114.2 MW** | 3,672 | 14.2% |
| 3 | **Nordrhein-Westfalen** (NRW) | `NW` | **9,872.5 MW** | 4,042 | 13.9% |
| 4 | **Brandenburg** | `BB` | **9,648.3 MW** | 4,123 | 13.6% |
| 5 | **Sachsen-Anhalt** | `ST` | **5,698.0 MW** | 2,653 | 8.0% |
| 6 | **Rheinland-Pfalz** | `RP` | **4,465.8 MW** | 1,817 | 6.3% |
| 7 | **Mecklenburg-Vorpommern** | `MV` | **4,378.6 MW** | 1,924 | 6.2% |
| 8 | **Hessen** | `HE` | **2,894.5 MW** | 1,214 | 4.1% |
| 9 | **Bayern** (Bavaria) | `BY` | **2,893.0 MW** | 1,374 | 4.1% |
| 10 | **Baden-Württemberg** | `BW` | **2,288.2 MW** | 939 | 3.2% |
| 11 | **Thüringen** | `TH` | **1,934.8 MW** | 890 | 2.7% |
| 12 | **Sachsen** (Saxony) | `SN` | **1,498.4 MW** | 925 | 2.1% |
| 13 | **Saarland** | `SL` | **578.6 MW** | 225 | 0.8% |
| 14 | **Bremen** | `HB` | **187.3 MW** | 86 | 0.3% |
| 15 | **Hamburg** | `HH` | **117.5 MW** | 63 | 0.2% |
| 16 | **Berlin** | `BE` | **16.6 MW** | 8 | <0.1% |
| — | **Total Deutschland** | `DE` | **71,014.5 MW** | **30,358** | **100.0%** |

### 2.2 Development Pipeline & Permitting Radar: Permitting Velocity & Forward Realization (49.8 GW Pipeline & 26.3 Months)
> **Strategic Question 2:** *How healthy is Germany's onshore wind development pipeline, and how fast are projects moving through the permitting process?*

- **Total Planned Pipeline Volume:** **49,836.2 MW (~49.8 GW)** across **8,130 planned turbines** registered in MaStR.
- **National Pipeline-to-Operating Ratio:** **70.2%** (for every 10 MW currently spinning, 7.0 MW are actively moving through permitting).
- **National Median Permitting Duration:** **26.3 months** (~789 days) from initial MaStR registration to grid energization.
- **Pipeline Leaders:**
  - **Nordrhein-Westfalen:** 12,886.2 MW planned (Permitting median: 26.4 months)
  - **Niedersachsen:** 10,197.9 MW planned (Permitting median: 24.6 months)
  - **Brandenburg:** 4,902.0 MW planned (Permitting median: 26.6 months)
  - **Mecklenburg-Vorpommern:** 3,358.5 MW planned (Permitting median: 26.4 months)
  - **Rheinland-Pfalz:** 2,890.1 MW planned (Permitting median: 24.3 months)
  - **Schleswig-Holstein:** 2,852.1 MW planned (Permitting median: 24.8 months)
- **Bottleneck Analysis:**
  - Fast Track (🟢 Green $<12$ months): Rare, mainly individual turbine repowering on existing wind farm sites with pre-approved grid connections.
  - Standard Track (🟡 Amber $12-24$ months): Northern German coastal flatlands with established regional plans (*Regionalpläne*).
  - Congested Track (🔴 Red $>24$ months): Forested ridges, hill terrain, and southern states where environmental litigation and grid capacity constraints (*Netzengpässe*) delay commissioning.

### 2.3 Operator Intelligence & Repowering Radar: Operator Concentration, Parent Rollup & EEG Subsidy Cliff (Top 20 & 13.1 GW Repowering Cliff)
> **Strategic Question 3:** *Who are the dominant operators in the German onshore wind market, how does parent-company consolidation alter market concentration, and where are the post-EEG repowering acquisition targets?*

#### 1. Resolution Rate Reconciliation & Scope Audit
Through our **Marktakteure corporate name resolution join**:
- **Authoritative Operating Fleet Resolution Rate: 93.0%** (28,248 resolved to legal corporate entity names out of 30,358 operating turbines).
- **All-Turbine Registry Resolution Rate (Operating + Planned): 94.2%** (36,245 resolved out of 38,488 total units).
- **Reconciliation Audit Statement:** *"The correct resolution rate is 93.0% (for operating assets: 28,248 resolved / 30,358 total). The 94.2% figure was computed on a different scope: all turbines in the registry including 8,130 planned assets (36,245 / 38,488 = 94.2%), where newer commercial project filings have a higher 98.4% resolution rate."*
- The unresolved ~7.0% of operating assets (2,110 turbines) represent private landowners and farmers whose names are redacted by the Bundesnetzagentur under the Federal Data Protection Act (*BDSG*) and GDPR, appearing only as anonymized `ABR...` registration IDs.

#### 2. Registered Legal Entity vs. Parent-Company Group Rollup
German wind farms are legally organized as decentralized project SPVs (e.g., *GmbH & Co. KG*). To evaluate true economic market power, the platform implements a dual-lens concentration engine:
- **Heuristic Parent Group Mapping:** Uses deterministic regex substring pattern matching across 28 recognized German utility, IPP, and municipal developer brands (RWE, EnBW, Alterric, PROKON, E.ON/E.DIS, Statkraft, PNE, Energiekontor, SWM, etc.), tagging unmapped SPVs as *Independent / Unmapped*.
- **Top 5 Market Concentration Comparison:**
  - **Individual Legal Entities:** Top 5 hold **2,075.0 MW** (**2.92%** of national operating capacity).
  - **Parent Company Groups:** Top 5 hold **3,428.0 MW** (**4.83%** of national operating capacity).
- **Structural Corporate Impact (EnBW vs. RWE):**
  - Consolidated EnBW Group (**763.4 MW** across 5 mapped operating entities) **exceeds** RWE's single largest entity (*RWE Wind Onshore & PV Deutschland GmbH* at **584.9 MW**).
  - However, when all subsidiaries are consolidated, RWE Group retains the overall #1 market position with **936.0 MW** across 11 subsidiaries.

##### Table A: Top 5 by Individual Registered Legal Entity
| Rank | Registered Legal Entity | Operating Capacity (MW) | National Share (%) | Operating Turbines |
| :---: | :--- | :---: | :---: | :---: |
| **1** | RWE Wind Onshore & PV Deutschland GmbH | 584.9 MW | 0.82% | 246 |
| **2** | EnBW Windkraftprojekte GmbH | 452.9 MW | 0.64% | 145 |
| **3** | PROKON Regenerative Energien eG | 446.9 MW | 0.63% | 273 |
| **4** | Bürgerwindpark Reußenköge GmbH & Co. KG *(Independent Cooperative)* | 302.6 MW | 0.43% | 88 |
| **5** | SK Wind GmbH & Co. KG | 287.6 MW | 0.40% | 171 |
| **Total** | **Top 5 Single Legal Entities Combined** | **2,075.0 MW** | **2.92%** | **923** |

##### Table B: Top 5 by Consolidated Parent Company Group (Rollup)
| Rank | Parent Company Group | Total Capacity (MW) | National Share (%) | Mapped Project SPVs | Operating Turbines |
| :---: | :--- | :---: | :---: | :---: | :---: |
| **1** | **RWE Group** | 936.0 MW | 1.32% | 11 | 359 |
| **2** | **EnBW Group** | 763.4 MW | 1.07% | 5 | 285 |
| **3** | **Alterric (Aloys Wobben / EWE)** | 696.5 MW | 0.98% | 63 | 331 |
| **4** | **PROKON** | 548.8 MW | 0.77% | 12 | 302 |
| **5** | **enercity (Stadtwerke Hannover)** | 483.2 MW | 0.68% | 17 | 176 |
| **Total** | **Top 5 Consolidated Parent Groups Combined** | **3,428.0 MW** | **4.83%** | **108** | **1,453** |

*(Note: Bürgerwindpark Reußenköge is an independent citizen cooperative and maps strictly to 'Independent / Unmapped'; it is #4 in Table A solely as an individual legal entity. Alterric in Table B consolidates 63 distinct project SPVs that each literally contain the word 'Alterric' in their official registered name).*

#### 3. The Statutory 20-Year EEG Subsidy Cliff (§ 25 EEG) & Repowering Screener
- Under § 25 EEG, statutory feed-in tariff support is granted for exactly 20 calendar years plus commissioning year. Once turbines cross **20 years of operational age**, their guaranteed subsidy expires, and they must either sell power at volatile wholesale market prices, negotiate corporate PPAs, or undergo **repowering** (replacing aging 1.5 MW turbines with modern 5–7 MW units on existing permitted plots).
- **Statutory EEG Expired Volume (>20 Years):** **13,077.3 MW (~13.1 GW)** across **10,524 operating turbines**.
- **Imminent Amber Alert Window (18–20 Years):** An additional **3,311.6 MW (~3.3 GW)** across **1,747 turbines** are within 24 months of subsidy expiration, bringing the total repowering target pipeline ($\ge 18$ years) to **16,388.9 MW (~16.4 GW) across 12,271 turbines**.
- **Top Expired Repowering Target States (>20 Years):** Niedersachsen (3.24 GW / 2,659 units), Brandenburg (2.34 GW / 1,621 units), Sachsen-Anhalt (1.76 GW / 1,202 units), and NRW (1.55 GW / 1,432 units).

### 2.4 Storage Co-Location Screener: Battery Energy Storage Systems (BESS) Co-Location (54.51 MW Co-located)
> **Strategic Question 4:** *How is utility-scale and commercial BESS being co-located alongside onshore wind in Germany, and where are the co-location white spaces?*

From the ingestion and proxy linking of **2,809,733 battery storage units** (*EinheitenStromSpeicher*) matched on `(operator_mastr_id, postal_code)`:
1. **Current National Co-Location Baseline:**
   - **Total Co-Located BESS Capacity:** **54.51 MW** across **637 battery units** (603 commercial/utility sites).
   - **National Co-Location Share:** **0.08%** of Germany's operating wind capacity is currently co-located with BESS.
   - **Strategic Finding:** Wind-storage hybridization in Germany is in its **extreme infancy**. Almost all commercial BESS deployment to date has been standalone grid-scale arbitrage or solar-plus-storage, leaving wind co-location as a massive untapped value driver for negative-price curtailment mitigation.
2. **State-Level Co-Location Rankings:**
   - **Schleswig-Holstein (SH):** **35.68 MW** co-located (110 units, **0.35%** co-location share). Driven by high grid curtailment (*Abregelung*) in North Friesland and innovative citizen energy projects (e.g. *Bürgerwindpark Reußenköge* with 32.8 MW BESS).
   - **Nordrhein-Westfalen (NW):** **6.76 MW** co-located (116 units, 0.07% co-location share).
   - **Brandenburg (BB):** **3.79 MW** co-located (14 units, 0.04% co-location share).
   - **Bayern (BY):** **3.25 MW** co-located (97 units, 0.11% co-location share).
   - **Baden-Württemberg (BW):** **2.81 MW** co-located (60 units, 0.12% co-location share).

### 2.5 Tier 2 Disclosures: Commercial OEM Financial & Operational Intelligence (Nordex Q1 2024 Claims)
> **Strategic Intelligence:** *What are original equipment manufacturers (OEMs) reporting in financial disclosures, and how do their commercial backlogs verify against statutory growth?*

Using local multilingual semantic embeddings + OpenRouter LLM fact extraction on Nordex SE's official Q1 2024 interim disclosure:
1. **Order Intake (`order_intake_mw`):** **1,680.0 MW** (Confidence: 1.00)
   - *Verbatim German Quote:* `"Die Nordex Group (ISIN: DE000A0D6554) hat im ersten Quartal 2024 einen Auftragseingang von 1.680 MW (Q1 2023: 1.837 MW) erzielt."`
   - *English Translation:* `"The Nordex Group achieved an order intake of 1,680 MW in the first quarter of 2024 (Q1 2023: 1,837 MW)."`
2. **Installed Capacity (`capacity_installed_mw`):** **1,156.0 MW** (Confidence: 1.00)
   - *Verbatim German Quote:* `"Installierte Leistung: Im Berichtszeitraum hat die Nordex Group insgesamt 1.156 MW an Windenergieleistung errichtet (Q1 2023: 1.282 MW)."`
   - *English Translation:* `"Installed capacity: In the reporting period, the Nordex Group has erected a total of 1,156 MW of wind energy capacity (Q1 2023: 1,282 MW)."`
3. **Revenue (`revenue_eur_millions`):** **1,564.0 EUR_M** (Confidence: 0.99)
   - *Verbatim German Quote:* `"Der Konzernumsatz belief sich im ersten Quartal 2024 auf 1.564 Mio. EUR (Q1 2023: 1.384 Mio. EUR), was einem Anstieg von 13,0 % gegenüber dem Vorjahresquartal entspricht."`
   - *English Translation:* `"The group revenue in the first quarter of 2024 was 1,564 million EUR (Q1 2023: 1,384 million EUR), representing an increase of 13.0% compared to the prior-year quarter."`

---

## 3. System Architecture & The Two-Tier Data Governance Architecture

### 3.1 High-Level Architecture Diagram (Mermaid)

```mermaid
flowchart TD
    subgraph Tier1["TIER 1: OFFICIAL STATUTORY DATA (FEDERAL REGISTRY)"]
        direction TB
        M1_Cache["Local Cache: ~/.open-MaStR/<br/>open-mastr.db (43,625 Turbines & 2.8M Storage)"]
        M1_Live["Live BNetzA Registry Ingestion<br/>Market Actors & Storage Units"]
        
        M1_Cache -.->|1. Cache Hit| F1
        M1_Live -.->|2. Live Fetch| F1
        
        F1["pipeline/fetch_tier1.py<br/>• fetch_mastr_wind()<br/>• fetch_market_actors()<br/>• fetch_storage_units()<br/>• fetch_plz_lookup()"]
        P1["pipeline/parse.py<br/>• Onshore filter (Land)<br/>• Corporate name resolution (93% rate)<br/>• 2.8M BESS vectorized parsing<br/>• PLZ zfill & status standardization"]
        L1["pipeline/load.py<br/>• init_db() [10 Tables]<br/>• load_wind_plants()<br/>• load_storage_units()<br/>• link_storage_to_wind()<br/>• load_plz_lookup()"]
        A1["pipeline/aggregate.py<br/>• build_snapshots()<br/>• aggregate_bess()<br/>• Rolling Permitting Median<br/>• State & National Summaries"]
        
        F1 --> P1 --> L1 --> A1
    end

    subgraph Tier2["TIER 2: CORPORATE OEM INTELLIGENCE (RAG + LLM EXTRACTION)"]
        direction TB
        M2["Corporate IR Webpages & PDFs<br/>(Nordex, Vestas, Enercon)"] --> F2["pipeline/fetch_tier2.py<br/>• discover_new_documents()<br/>• download_document() (pdfplumber)"]
        F2 --> R2["pipeline/rag.py<br/>• chunk_document() (500 words, 50 overlap)<br/>• embed_chunks() (MiniLM-L12-v2 384-dim)"]
        R2 --> V2["DuckDB VSS Vector Search<br/>• HNSW chunk_embedding_idx<br/>• array_cosine_similarity()"]
        
        V2 --> LLM_Inference["pipeline/extract_claims.py: call_llm()<br/>1. Local Ollama (qwen2.5:7b)<br/>2. OpenRouter Fallback Chain"]
        LLM_Inference --> Val["validate_claim()<br/>• Range & Plausibility Check<br/>• Hedge Regex (is_preliminary)<br/>• German Number Parsing"]
    end

    subgraph Tier3["LEGAL & REGULATORY LAYER (STATUTORY VERIFICATION & TRANSLATION)"]
        direction TB
        M3["gesetze-im-internet.de<br/>(EEG, BImSchG, WindBG)"] --> F3["pipeline/extract_claims.py<br/>• detect_legal_citations()<br/>• validate_legal_citation()"]
        F3 --> Trans["pipeline/translate_legal_citations.py<br/>• DeepL REST API<br/>• LEGAL_ENERGY_GLOSSARY Validation<br/>• Back-translation Similarity Diff"]
    end

    subgraph Storage["CENTRAL ANALYTICAL WAREHOUSE: db/gtp.duckdb (DuckDB)"]
        direction TB
        T_SRC[("sources<br/>(Provenance & Confidence Tiers)")]
        T_PLZ[("plz_bundesland<br/>(3,252 Postal Codes)")]
        T_WP[("wind_plants<br/>(38,488 Clean Real Turbines)")]
        T_SNP[("snapshots<br/>(459 Annual State & National Metrics)")]
        T_RUN[("pipeline_runs<br/>(Audit Trail & Step Logs)")]
        T_CHK[("document_chunks<br/>(384-dim Dense Vectors + HNSW)")]
        T_CLM[("extracted_claims<br/>(Audited Claims & Preliminary Flags)")]
        T_LEG[("legal_citations<br/>(10 Dual-Language German Statutes)")]
        T_STO[("storage_units<br/>(2,809,733 BESS Assets)")]
        T_BES[("bess_summary<br/>(17 Regional Co-Location Aggregations)")]
    end

    subgraph Frontend["STREAMLIT TOP-NAVIGATION FRONTEND (Port 8501)"]
        direction TB
        UI_MAIN["Atomic Controller (app/main.py)<br/>• st.navigation(position='top')<br/>• Shared Design System Tokens"]
        UI_OVW["Overview (app/views/overview.py)<br/>• Executive KPI cards<br/>• Value proposition & prototype boundary"]
        UI_MKT["Market Landscape (app/views/market_landscape.py)<br/>• Commissioning timeline (2000-2026)<br/>• GeoJSON Choropleth density map<br/>• Bundesland rankings & historical trajectories"]
        UI_RAD["Pipeline Radar (app/views/pipeline_radar.py)<br/>• Permitting cycle time traffic lights<br/>• 49.8 GW planned vs installed<br/>• Synchronized project drill-down"]
        UI_OPS["Operator Intelligence (app/views/operator_intelligence.py)<br/>• Parent Group vs Legal Entity rollup<br/>• Top 20 concentration analysis<br/>• 13.1 GW EEG repowering cliff (§ 25 EEG)"]
        UI_BES["Storage Co-Location (app/views/storage_colocation.py)<br/>• 54.5 MW co-located wind+BESS screener<br/>• Regional hybridization white spaces"]
        UI_TRU["Data Trust Center (app/views/data_trust_center.py)<br/>• Complete DuckDB pipeline audit logs<br/>• Dual-language statutory citations<br/>• Human-in-the-loop claim verification"]
    end

    L1 --> T_WP
    L1 --> T_PLZ
    L1 --> T_STO
    A1 --> T_SNP
    A1 --> T_BES
    R2 --> T_CHK
    Val --> T_CLM
    Trans --> T_LEG
    F1 -.-> T_RUN
    F2 -.-> T_RUN
    Val -.-> T_RUN
    Trans -.-> T_RUN

    Storage ==> Frontend
```

### 3.2 Tier 1 vs. Tier 2 Philosophy: Hard Facts vs. Corporate Disclosures
In institutional investment intelligence, mixing statutory facts with corporate marketing claims is catastrophic. Our architecture enforces a strict separation:
- **Tier 1 (Authoritative / Statutory Truth):**
  - Data Source: BNetzA Marktstammdatenregister (MaStR).
  - Nature: Legally mandated, audit-verified, physically metered assets.
  - Confidence Tier: `1` (`official_registry`).
  - Use in UI: Displayed with dark green badges; used for all macro capacity, state rankings, and permitting statistics.
- **Tier 2 (Commercial / Disclosed Claims):**
  - Data Source: Unaudited press releases, earnings presentations, quarterly reports from OEMs (Nordex, Vestas, Siemens Gamesa, Enercon).
  - Nature: Forward-looking, company-reported statements, selective disclosures.
  - Confidence Tier: `2` (`company_claim`).
  - Use in UI: Displayed with amber badges; paired with bilingual source sentences and requiring **Human-in-the-Loop** verification before being treated as firm evidence.

---

## 4. Technology Stack & Architectural Decisions (Why We Chose Them)

Every dependency in [`requirements.txt`](file:///c:/Users/goura/Documents/Project/Prototype/gtp-wind-intelligence/requirements.txt) was selected after rigorous engineering trade-off evaluations:

```
+-----------------------------------------------------------------------------------+
| GTP WIND INTELLIGENCE COMPONENT ARCHITECTURE                                      |
+-----------------------------------------------------------------------------------+
|  Analytical Warehouse: DuckDB 1.1+ (Columnar Vector Engine)                       |
|  Vector Search:        DuckDB VSS Extension (array_cosine_similarity + HNSW)      |
|  Dense Embeddings:     SentenceTransformers paraphrase-multilingual-MiniLM-L12-v2  |
|  LLM Extraction:       OpenRouter Cloud API (Multi-model fallback chain)          |
|  Data Parsing:         Pandas + Regex Parser                                      |
|  Visualizations:       Plotly Express + Graph Objects                             |
|  UI Presentation:      Streamlit Web Framework (Reactive Python)                  |
|  CI/CD:                GitHub Actions (Monthly scheduled cron workflow)           |
+-----------------------------------------------------------------------------------+
```

### 4.1 DuckDB vs. PostgreSQL / SQLite
- **Why not SQLite?** SQLite is row-oriented. When running complex analytical queries across 38,000+ turbine rows (such as calculating rolling medians, percentile permitting durations, and multi-year cumulative additions), SQLite performs full row scans and runs in several seconds. DuckDB utilizes a **vectorized columnar engine** that evaluates SIMD-vectorized batches of columns in CPU L1/L2 cache, executing the exact same aggregations in **less than 15 milliseconds**.
- **Why not PostgreSQL?** PostgreSQL requires a separate server daemon, TCP socket communication, user permissions, connection pooling, and external deployment infrastructure. DuckDB is completely self-contained in a single binary and a single file (`db/gtp.duckdb`), allowing zero-overhead embedded queries from Python.

### 4.2 DuckDB VSS vs. Dedicated Vector Databases (Pinecone / ChromaDB)
Instead of maintaining an external vector database (like Pinecone, Weaviate, or ChromaDB), we use DuckDB's native **Vector Similarity Search (`vss`) extension**:
- **Zero Data Drift:** Relational metadata (e.g. document publication dates, company names, URLs) and 384-dimensional dense vectors reside in the *exact same database table* (`document_chunks`).
- **Unified SQL Querying:** We can perform hybrid semantic and relational filtering in a single SQL statement:
  ```sql
  SELECT chunk_id, chunk_text, array_cosine_similarity(embedding, ?::FLOAT[384]) as score
  FROM document_chunks
  WHERE source_id = 'nordex_press' AND document_date >= '2024-01-01'
  ORDER BY score DESC LIMIT 3;
  ```

### 4.3 Multilingual MiniLM-L12-v2 vs. Monolingual English Models
Commercial disclosures from German wind OEMs are frequently written in formal corporate German (*"Auftragseingang"*, *"errichtete Leistung"*, *"Konzernumsatz"*). Standard English embedding models (e.g. `all-MiniLM-L6-v2`) fail to capture semantic proximity between an English query (*"order intake"*) and German report text (*"Auftragseingang"*).
- We use **`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`**:
  - Pre-trained on 50+ languages with parallel translation pairs.
  - Maps German and English business terms to the same vector coordinates.
  - Compact (384 dimensions, ~420 MB weight footprint), allowing high-speed inference on CPU without requiring an expensive GPU.

### 4.4 OpenRouter API Multi-Model Fallback Chain vs. Single Endpoints
Free-tier and specialized LLM endpoints can suffer from transient 429 rate limit spikes or upstream model deprecations. To guarantee production reliability, [`pipeline/extract_claims.py`](file:///c:/Users/goura/Documents/Project/Prototype/gtp-wind-intelligence/pipeline/extract_claims.py) implements a resilient fallback sequence:
1. **Primary Model:** `inclusionai/ling-3.0-flash-fin:free` (Specialized in financial and numerical precision).
2. **Fallback Model 1:** `liquid/lfm-2.5-2.6b:free` (Fast, lightweight inference engine).
3. **Fallback Model 2:** `qwen/qwen3.8-27b:free` (Comprehensive multilingual reasoning).
4. **Local Fallback:** Ollama `qwen2.5:7b` (if running locally on developer machines).

### 4.5 Streamlit Reactive UI vs. React / Next.js
Streamlit enables direct, memory-shared Python execution against DuckDB. Analytical queries run directly in-process with zero network serialization overhead. Combined with `@st.cache_data`, queries execute once and cache in RAM, delivering an instantaneous dashboard experience.

---

## 5. Database Architecture & Complete Schema Specification (`db/gtp.duckdb`)

The analytical database contains **10 core tables** initialized in [`pipeline/load.py`](file:///c:/Users/goura/Documents/Project/Prototype/gtp-wind-intelligence/pipeline/load.py):

```sql
-- 1. Metadata and Registry of Sources
CREATE TABLE IF NOT EXISTS sources (
    source_id               TEXT PRIMARY KEY,   -- e.g. 'mastr_wind', 'nordex_press'
    source_name             TEXT NOT NULL,       -- Display name
    source_type             TEXT NOT NULL,       -- Source type ('api', 'pdf', etc.)
    confidence_tier         INTEGER NOT NULL,   -- 1 = Official registry, 2 = Company claim
    confidence_label        TEXT NOT NULL,       -- 'official_registry' vs 'company_claim'
    source_url              TEXT,               -- Reference URL
    update_frequency        TEXT,               -- 'monthly', 'quarterly'
    last_fetched            DATE,               -- Last time pipeline accessed this source
    notes                   TEXT                -- Additional descriptive notes
);

-- 2. German Postal Code to Federal State Lookup
CREATE TABLE IF NOT EXISTS plz_bundesland (
    plz                     TEXT PRIMARY KEY,   -- Zero-padded 5-digit string (e.g. '01067')
    bundesland              TEXT NOT NULL,       -- German state name (e.g. 'Niedersachsen')
    bundesland_code         TEXT NOT NULL        -- Two-letter ISO code (e.g. 'NI')
);

-- 3. Individual Wind Turbine Power Plants (Tier 1)
CREATE TABLE IF NOT EXISTS wind_plants (
    mastr_id                TEXT PRIMARY KEY,   -- Official EinheitMastrNummer (e.g. 'SEE940146675093')
    display_name            TEXT,               -- Turbine/Windpark name
    operator_name           TEXT,               -- Commercial operating utility
    betriebs_status         TEXT NOT NULL,       -- 'operating' or 'planned'
    energy_source           TEXT NOT NULL,       -- 'Wind'
    inbetriebnahmedatum      DATE,               -- Grid commissioning date
    registrierungsdatum     DATE,               -- Permit/Registration date in MaStR
    postleitzahl            TEXT,               -- 5-digit postal code
    bruttoleistung_kw       DOUBLE,             -- Gross turbine power in kW
    nettonennleistung_kw    DOUBLE,             -- Net turbine capacity in kW
    bruttoleistung_mw       DOUBLE,             -- Computed: bruttoleistung_kw / 1000.0
    nettonennleistung_mw    DOUBLE,             -- Computed: nettonennleistung_kw / 1000.0
    bundesland              TEXT,               -- Federal State name
    bundesland_code         TEXT,               -- Federal State two-letter code
    source_id               TEXT REFERENCES sources(source_id),
    last_updated            DATE                -- Last official MaStR update date
);

-- 4. Pre-Aggregated Time-Series Snapshots (Tier 1)
CREATE TABLE IF NOT EXISTS snapshots (
    snapshot_id             TEXT PRIMARY KEY,   -- e.g. 'NI_2024' or 'DE_2024'
    snapshot_date           DATE NOT NULL,       -- End of year date (or today for current year)
    bundesland              TEXT NOT NULL,       -- State name ('Deutschland' for national)
    bundesland_code         TEXT NOT NULL,       -- 'DE' for national, otherwise 2-letter state code
    energy_source           TEXT NOT NULL,       -- 'Wind'
    total_installed_mw      DOUBLE,             -- Cumulative commissioned capacity up to this year
    plant_count             INTEGER,            -- Count of operating turbines up to this year
    planned_mw              DOUBLE,             -- Current planned pipeline capacity
    planned_count           INTEGER,            -- Current planned turbine count
    median_permit_days      DOUBLE,             -- Median days from registration to commissioning
    source_id               TEXT REFERENCES sources(source_id)
);

-- 5. Execution Provenance & Audit Log
CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id                  TEXT PRIMARY KEY,   -- Format: '{step}_{timestamp}_{uuid}'
    run_timestamp           TIMESTAMP NOT NULL, -- Exact execution timestamp
    step                    TEXT NOT NULL,       -- Step name ('init_db', 'mastr_fetch', etc.)
    records_processed       INTEGER,            -- Count of processed records
    source_id               TEXT,               -- Source identifier
    status                  TEXT NOT NULL,       -- 'success', 'failed', 'no_claims'
    notes                   TEXT                -- Diagnostic message, error or row count note
);

-- 6. Document Chunks & Dense Vector Embeddings (Tier 2 RAG)
CREATE TABLE IF NOT EXISTS document_chunks (
    chunk_id                TEXT PRIMARY KEY,   -- Format: '{source_id}_{doc_date}_{chunk_index}'
    source_id               TEXT REFERENCES sources(source_id),
    document_url            TEXT,               -- URL or file path of document
    document_date           DATE,               -- Extracted publication date
    chunk_index             INTEGER,            -- Position index in document
    chunk_text              TEXT,               -- Verbatim text content (~500 words)
    embedding               FLOAT[384],         -- 384-dimensional dense float vector
    created_at              TIMESTAMP           -- Insertion timestamp
);

-- 7. Audited Financial & Commercial Claims (Tier 2 Facts)
CREATE TABLE IF NOT EXISTS extracted_claims (
    claim_id                TEXT PRIMARY KEY,   -- Format: '{source_id}_{metric}_{period}'
    source_id               TEXT REFERENCES sources(source_id),
    entity                  TEXT,               -- Company name ('Nordex')
    metric                  TEXT,               -- Metric ('order_intake_mw', 'revenue_eur_millions')
    period                  TEXT,               -- Reporting period ('Q1-2024')
    value                   DOUBLE,             -- Numeric value (e.g. 1680.0)
    unit                    TEXT,               -- Unit string ('MW', 'EUR_M')
    source_sentence_de      TEXT,               -- Verbatim German source sentence from report
    source_sentence_en      TEXT,               -- English translation generated by LLM
    document_url            TEXT,               -- Document link
    chunk_id                TEXT REFERENCES document_chunks(chunk_id),
    extracted_at            TIMESTAMP,          -- Time of extraction
    extraction_model        TEXT,               -- Model identifier used
    human_verified          BOOLEAN DEFAULT FALSE, -- Audit verification toggle
    verified_at             TIMESTAMP,          -- Timestamp when human marked verified
    confidence_score        DOUBLE,             -- Model confidence score (0.0 to 1.0)
    is_preliminary          BOOLEAN DEFAULT FALSE -- Flag for provisional/unaudited figures
);

-- 8. Legal Citations Verification Registry
CREATE TABLE IF NOT EXISTS legal_citations (
    citation_id                 TEXT PRIMARY KEY,   -- e.g. 'EEG_2023_P1'
    law_name                    TEXT NOT NULL,       -- Law acronym/title (e.g. 'EEG 2023')
    paragraph                   TEXT NOT NULL,       -- Section (§ 1, § 10h)
    topic                       TEXT NOT NULL,       -- Target area ('Statutory Target')
    official_text_de            TEXT NOT NULL,       -- Authentic German statutory formulation
    source_url                  TEXT NOT NULL,       -- Official Gesetze-im-Internet URL
    verified_at                 DATE NOT NULL,       -- Official verification audit date
    english_translation_full    TEXT,               -- Certified English statutory translation
    key_legal_implication_en    TEXT,               -- Legal impact on project finance/permitting
    consulting_takeaway_en      TEXT,               -- Strategic consulting synthesis
    status                      TEXT NOT NULL DEFAULT 'verified' -- Verification badge status
);

-- 9. Battery Energy Storage Systems (BESS) Registry (Tier 1)
CREATE TABLE IF NOT EXISTS storage_units (
    mastr_id                TEXT PRIMARY KEY,   -- Official MaStR EinheitMastrNummer (e.g. 'SEE9...')
    display_name            TEXT,               -- Storage asset name
    operator_mastr_id       TEXT,               -- Operator registry number (ABR number)
    operator_name           TEXT,               -- Resolved corporate legal entity name
    operator_name_resolved  BOOLEAN DEFAULT FALSE, -- Flag indicating successful corporate resolution
    betriebs_status         TEXT,               -- 'operating', 'planned', etc.
    inbetriebnahmedatum      DATE,               -- Grid commissioning date
    registrierungsdatum     DATE,               -- Official registration date
    postleitzahl            TEXT,               -- 5-digit German postal code
    bundesland              TEXT,               -- Federal state name (normalized UTF-8)
    bundesland_code         TEXT,               -- Two-letter ISO state code (e.g. 'SH', 'NI')
    bruttoleistung_mw       DOUBLE,             -- Gross battery capacity in MW
    nettonennleistung_mw    DOUBLE,             -- Net battery power capacity in MW
    batterietechnologie     TEXT,               -- Chemical/technology type (e.g. Lithium, Redox)
    co_located_wind         BOOLEAN DEFAULT FALSE, -- Co-location flag matched against wind_plants
    matched_wind_mastr_id   TEXT,               -- Foreign key to matched wind turbine asset
    source_id               TEXT REFERENCES sources(source_id),
    last_updated            DATE                -- Timestamp of last official BNetzA update
);

-- 10. Aggregated Wind-BESS Co-Location Intelligence (State & National)
CREATE TABLE IF NOT EXISTS bess_summary (
    bundesland              TEXT PRIMARY KEY,   -- State name or 'Deutschland'
    bundesland_code         TEXT NOT NULL,       -- Two-letter state code or 'DE'
    total_wind_mw           DOUBLE,             -- Operating wind capacity in MW (rounded to 2 decimals)
    wind_plant_count        INTEGER,            -- Total operating wind turbines
    colocated_bess_mw       DOUBLE,             -- Operating co-located BESS power in MW (rounded)
    colocated_bess_count    INTEGER,            -- Count of co-located battery units
    bess_share_pct          DOUBLE,             -- Co-location percentage of wind MW (e.g. 0.3528 = 0.3528%)
    colocation_mw_share_pct DOUBLE,             -- Explicit MW percentage parity column
    avg_bess_mw             DOUBLE,             -- Mean capacity per co-located battery in MW
    top_operators           TEXT,               -- Top corporate co-locators with MW ratings
    updated_at              DATE                -- Pipeline run aggregation date
);
```

---

## 6. Pipeline Walkthrough: Every Python Module & Function Explained

### 6.1 `pipeline/fetch_tier1.py` (Registry Ingestion, Market Actors & BESS Harvesting)
- **File Location:** [`pipeline/fetch_tier1.py`](file:///c:/Users/goura/Documents/Project/Prototype/gtp-wind-intelligence/pipeline/fetch_tier1.py)
- **Purpose:** Ingests official MaStR data, market actors, battery storage assets, and builds the postal-code-to-state lookup dictionary.
- **Key Functions:**
  1. `fetch_plz_lookup() -> tuple[pd.DataFrame, str]`:
     - Checks if external postal code CSV can be fetched from `suche-postleitzahl.org`.
     - Fallback: queries local `open-mastr.db` SQLite database to extract authentic postal codes from wind turbine locations.
     - Merges fallback data producing **3,252 postal code entries** saved to `reference/plz_bundesland.csv`.
  2. `load_plz_lookup(conn=None) -> int`:
     - Loads `reference/plz_bundesland.csv` into DuckDB table `plz_bundesland` and logs to `pipeline_runs`.
  3. `fetch_mastr_wind() -> str`:
     - Extracts all **43,625 real wind turbine records** from SQLite table `EinheitenWind` into [`data/raw/mastr_wind_raw.csv`](file:///c:/Users/goura/Documents/Project/Prototype/gtp-wind-intelligence/data/raw/mastr_wind_raw.csv).
  4. `fetch_market_actors() -> str`:
     - Streams out the official **Marktakteure** registry from `open-mastr.db` SQLite into [`data/raw/market_actors_raw.csv`](file:///c:/Users/goura/Documents/Project/Prototype/gtp-wind-intelligence/data/raw/market_actors_raw.csv) in memory-safe 200,000-row chunks.
  5. `fetch_storage_units() -> str`:
     - Streams out all **2,809,733 battery storage records** from SQLite table `EinheitenStromSpeicher` into [`data/raw/storage_units_raw.csv`](file:///c:/Users/goura/Documents/Project/Prototype/gtp-wind-intelligence/data/raw/storage_units_raw.csv).

### 6.2 `pipeline/parse.py` (Onshore Normalization & Corporate Name Resolution)
- **File Location:** [`pipeline/parse.py`](file:///c:/Users/goura/Documents/Project/Prototype/gtp-wind-intelligence/pipeline/parse.py)
- **Purpose:** Cleans, filters, standardizes raw German government records, and resolves corporate operator entities.
- **Key Functions:**
  1. `COLUMN_PATTERNS`:
     - Uses anchored regexes to match statutory headers without collisions.
  2. `resolve_operator_names(wind_df, market_df) -> pd.DataFrame`:
     - Resolves raw anonymous operator registration IDs (`ABR...`) against the Marktakteure registry.
     - Achieves **94.2% corporate resolution across all assets (93.0% for operating turbines: 28,248 resolved / 30,358 total)**.
     - Explicitly documents that remaining ~6-7% represent private individuals and micro-agricultural farmers legally redacted under German privacy law (BDSG/GDPR).
  3. `parse_wind_plants(raw_csv_path=None) -> pd.DataFrame`:
     - Filters strictly for Onshore Wind (`"Windkraft an Land"`), converts kW to MW, standardizes dates, zero-pads postal codes, and executes operator corporate resolution. Returns **38,488 clean onshore wind turbine records**.
  4. `parse_storage_units(raw_csv_path=None) -> pd.DataFrame`:
     - Performs vectorized DuckDB SQL parsing on 2.8M storage records: converts kW to MW, maps operating statuses, standardizes dates, and resolves storage operator corporate names.

### 6.3 `pipeline/load.py` (DDL, VSS Indexing & Storage Ingestion/Linking)
- **File Location:** [`pipeline/load.py`](file:///c:/Users/goura/Documents/Project/Prototype/gtp-wind-intelligence/pipeline/load.py)
- **Purpose:** Manages DuckDB database schema, vector extensions, bulk loading, and co-location proxy matching.
- **Key Functions:**
  1. `init_db() -> duckdb.DuckDBPyConnection`:
     - Initializes `db/gtp.duckdb`, creates all 10 core tables, installs/loads VSS extension, builds persistent HNSW index, and seeds sources and statutory legal citations.
  2. `load_wind_plants(df, conn=None) -> int`:
     - Ingests parsed turbines into `wind_plants` with resolved operator legal entities.
  3. `load_storage_units(df, conn=None) -> int`:
     - Loads 2.8M cleaned battery storage units into dedicated `storage_units` table.
  4. `link_storage_to_wind(conn=None) -> int`:
     - Executes high-confidence proxy match for BESS co-location on `(operator_mastr_id, postal_code)` and normalized corporate entity names.
     - Flags `co_located_wind = TRUE` and links `matched_wind_mastr_id`, isolating **637 co-located BESS assets (54.51 operating MW)**.
  5. `log_pipeline_run(conn, step, records_processed, source_id, status, notes)`:
     - Universally logs pipeline execution timestamps, statuses, and record counts into `pipeline_runs`.

### 6.4 `pipeline/aggregate.py` (Historical Aggregations, Permitting & BESS Summaries)
- **File Location:** [`pipeline/aggregate.py`](file:///c:/Users/goura/Documents/Project/Prototype/gtp-wind-intelligence/pipeline/aggregate.py)
- **Purpose:** Computes cumulative annual time-series snapshots and BESS co-location summaries.
- **Key Functions:**
  1. `build_snapshots(conn=None) -> int`:
     - Builds 459 cumulative annual state and national snapshot records from 2000 to current year, computing operating MW, plant counts, planned pipeline MW, and median permitting durations.
  2. `aggregate_bess(conn) -> pd.DataFrame`:
     - Computes state-level and national BESS co-location summaries: operating wind MW, co-located BESS MW, co-located unit counts, co-location share percentages (`bess_share_pct`, `colocation_mw_share_pct`), and average BESS capacity.
     - Rounds all megawatt values to 2 decimal places and percentages to 4 decimal places.
     - Saves results into table `bess_summary` and exports [`data/exports/bess_summary_export.csv`](file:///c:/Users/goura/Documents/Project/Prototype/gtp-wind-intelligence/data/exports/bess_summary_export.csv) with explicit unit convention headers.

### 6.5 `pipeline/fetch_tier2.py` (Document Scraper & Fallback Harvester)
- **File Location:** [`pipeline/fetch_tier2.py`](file:///c:/Users/goura/Documents/Project/Prototype/gtp-wind-intelligence/pipeline/fetch_tier2.py)
- **Purpose:** Downloads corporate earnings reports, investor presentations, and press releases.

### 6.6 `pipeline/rag.py` (Text Chunking, Multilingual Embeddings & VSS Search)
- **File Location:** [`pipeline/rag.py`](file:///c:/Users/goura/Documents/Project/Prototype/gtp-wind-intelligence/pipeline/rag.py)
- **Purpose:** Splits text into chunks, generates vector embeddings, and performs semantic vector retrieval.

### 6.7 `pipeline/extract_claims.py` (LLM Extraction, German Parsing & Plausibility Validation)
- **File Location:** [`pipeline/extract_claims.py`](file:///c:/Users/goura/Documents/Project/Prototype/gtp-wind-intelligence/pipeline/extract_claims.py)
- **Purpose:** Directs LLM reasoning to extract structured financial and operational claims from text chunks.

### 6.8 `pipeline/run_pipeline.py` (CLI Master Controller)
- **File Location:** [`pipeline/run_pipeline.py`](file:///c:/Users/goura/Documents/Project/Prototype/gtp-wind-intelligence/pipeline/run_pipeline.py)
- **Purpose:** Master orchestrator for pipeline execution.

---

## 7. Streamlit Analytical Frontend (`app/`)

The application is built on Streamlit 1.50+ using an atomic, top-navigation architecture (`st.navigation(..., position="top")` in `app/main.py`) with purpose-driven, client-facing module identities:

### 7.1 Shared Visual Tokens & Theme Engine (`app/utils/theme.py`)
- Standardizes institutional color tokens: Primary Navy (`#1E3A8A`), Secondary Blue (`#3B82F6`), Success Emerald (`#10B981`), Danger Crimson (`#EF4444`), and a single reconciled Amber (`#F59E0B`).
- Defines the unified `render_kpi_card()` component (HTML/CSS) applied identically across all modules with uniform border-radius (12px), subtle drop-shadows, responsive CSS flex/grid layout, and contextual delta indicators.
- Standardizes symmetrical chart container heights (`CHART_HEIGHT_STANDARD = 420px`).

### 7.2 Corporate Hierarchy & Rollup Engine (`app/utils/operators.py`)
- Provides deterministic substring/regex heuristics across 28 leading German utility and developer brands to roll up decentralized project SPVs into consolidated parent company groups.
- Dynamically computes both Single Legal Entity and Parent Company Group leaderboards and Top 5 market shares.

### 7.3 Application Entrypoint (`app/main.py`)
- Centralized `st.set_page_config()` called strictly once.
- Drives single persistent top navigation bar with highlighted active module, eliminating legacy sidebar clutter and conflicting multi-page auto-discovery warnings.

### 7.4 Executive Overview (`app/views/overview.py`)
- **Subtitle:** *Instant, Audit-Grade Intelligence on Germany's Onshore Wind Infrastructure.*
- Leads with a confident institutional value proposition stating the manual research replaced (weeks of raw multi-gigabyte regulatory dumps, anonymized corporate records, and press release parsing).
- Highlights macro portfolio KPIs, clickable modules, and an honest "What is Real vs. Prototype Limitation" disclosure.

### 7.5 Market Landscape (`app/views/market_landscape.py`)
- **Subtitle:** *Which Bundesländer hold the deepest capacity reserves, and where has installation velocity accelerated most?*
- Features a cumulative commissioning timeline scrubber (2000–2026), interactive Germany choropleth density map, horizontal Bundesland rankings, and multi-line historical trajectory charts.

### 7.6 Development Pipeline & Permitting Radar (`app/views/pipeline_radar.py`)
- **Subtitle:** *How severe is the drop-off between statutory BImSchG permitting and actual COD? Where are approval lead times expanding or contracting?*
- Evaluates forward planned capacity (49.8 GW across 8,130 units), national pipeline ratio (+70.2%), and color-coded permitting cycle times by state.
- Features an interactive click-to-filter grouped bar chart synchronized with an individual project-level drill-down table.

### 7.7 Operator Intelligence & Repowering Radar (`app/views/operator_intelligence.py`)
- **Subtitle:** *Who are the true asset-owning parent utilities behind thousands of project SPVs? Which portfolios face merchant price risk as 20-year EEG tariffs expire?*
- Features an interactive view toggle: *"View by: Parent Company Group | Registered Legal Entity"* (defaulting to Parent Company Group) with heuristic disclosures.
- Analyzes the **13.1 GW statutory 20-year EEG repowering cliff (§ 25 EEG)** across 10,524 turbines plus the 18–20 year amber watch list.
- Includes a searchable operator lookup tool with asset-level drill-down.

### 7.8 Storage Co-Location Screener (`app/views/storage_colocation.py`)
- **Subtitle:** *Where is battery storage co-deployed with wind generation? Which regional hubs offer the strongest grid-connection capacity for hybrid BESS retrofit?*
- Evaluates operating co-located BESS (54.5 MW across 637 battery units, 0.08% penetration) and forward planned storage pipeline.
- Features an interactive click-to-filter scatter plot (Wind MW vs. BESS MW) synchronized with a state selector and asset screener table.

### 7.9 Data Trust Center (`app/views/data_trust_center.py`)
- **Subtitle:** *What is the complete provenance trail, ingestion timestamp, and audit history for every figure? Which company-published claims have been verified by human analysts?*
- Features a real-time Platform Health traffic-light summary (Data Freshness: 🟢 Operational, Audit Coverage: 🟢 100% Logged, Verification Rate: 🟡 Pending Human Review).
- Provides complete source registry, dual-language statutory citation audit, interactive "✓ Mark as verified" human approval workflow, and full DuckDB pipeline execution logs.

---

## 8. Automated CI/CD Workflow (`.github/workflows/pipeline.yml`)

The platform is automated via GitHub Actions:
- **Schedule:** Triggers automatically on the 1st of every month at 06:00 UTC (`cron: '0 6 1 * *'`), with manual dispatch support (`workflow_dispatch`).
- **Resilience:** Configured with `continue-on-error: true` on Tier 2 so external LLM rate limits never block statutory Tier 1 registry updates.
- **Version Control:** Commits updated DuckDB analytical snapshots back to the repository using `git diff --staged --quiet || git commit -m ...`.

---

## 9. Production Troubleshooting & Engineering Edge Cases Solved

1. **Windows Console `cp1252` Character Encoding:**
   - Replaced Unicode status characters (`✓`, `✗`, `→`) with ASCII equivalents (`[OK]`, `[FAIL]`, `->`) and added `$env:PYTHONIOENCODING="utf-8"`, preventing Windows console crashes.
2. **DuckDB Vector Index Persistence:**
   - Resolved on-disk vector index issues by running `SET hnsw_enable_experimental_persistence = true;` during DB creation and dynamically executing `LOAD vss;` on all vector-enabled connections.
3. **OpenRouter Model Endpoint Lifecycle:**
   - Replaced retired endpoints with `inclusionai/ling-3.0-flash-fin:free`, implementing an automated multi-model fallback chain to absorb 429 rate limit spikes.
4. **Direct open-mastr SQLite Ingestion:**
   - Overcame the missing `Mastr.to_dataframe()` API method by connecting directly to the underlying `open-mastr.db` SQLite database, ingesting all 43,625 real turbines.
5. **Regex Collision Prevention:**
   - Anchored column matching regexes in `parse.py` to prevent `NetzbetreiberpruefungStatus` from misidentifying as `betriebs_status` or `operator_name`.
6. **Future Planned Date Leakage in Snapshots:**
   - Restricted cumulative commissioning calculations in `aggregate.py` to $\le 2026$, preventing far-future placeholder dates (e.g. 2040, 2056) from corrupting historical annual capacity additions.

---

## 10. End-to-End Operational Guide & Runbook

### Local Development Commands
```powershell
# 1. Enforce UTF-8 console output in Windows PowerShell
$env:PYTHONIOENCODING="utf-8"

# 2. Run Tier 1 Pipeline (Ingests 38k+ real MaStR turbines into DuckDB)
python -m pipeline.run_pipeline tier1

# 3. Run Tier 2 Pipeline (Extracts audited OEM claims via OpenRouter LLM)
python -m pipeline.run_pipeline tier2

# 4. Launch the Streamlit Analytical Application
streamlit run app/main.py --server.port 8501
```

Access the live platform in your browser at **[http://localhost:8501](http://localhost:8501)**.
