# GTP Wind Intelligence

Internal market data platform for onshore wind in Germany.
Built as a working prototype for Greentech Partners.

---

## What this answers

**Q1:** Which Bundesländer have the most installed onshore wind capacity, and which are growing fastest?

**Q2:** How healthy is Germany's onshore wind development pipeline, and how fast are projects being approved?

Questions Q3–Q5 (operator portfolios, BESS co-location, benchmarking) are designed and visible in the platform but not yet built. All use data already in the database.

---

## Why these questions

GTP consultants currently answer these questions manually from annual reports and press releases. This platform makes the answers available in seconds from a single trusted source, with every number traceable to its origin.

---

## Data sources and confidence tiers

**Tier 1 — Official (green indicator)**
Marktstammdatenregister (MaStR), Germany's official energy plant registry, operated by the Bundesnetzagentur. Every wind turbine commissioned in Germany is registered here. All figures carry official government authority.

Ingested using open-mastr, the community-maintained Python package for MaStR access, rather than a custom scraper.

**Tier 2 — Company claim (amber indicator, human verification required)**
OEM press releases (currently Nordex). Extracted from German-language PDFs using pdfplumber, chunked, embedded with sentence-transformers (multilingual model), and stored in DuckDB with vector search. Values extracted by LLM (Ollama qwen2.5:7b or OpenRouter fallback).

Every Tier 2 claim stores the original German sentence alongside the extracted value and its English translation. A human must verify the claim before it can be cited in client work.

---

## Design decisions

**Source confidence as a first-class field:** a number from an official government registry and a number from a company press release carry different levels of trust. Every fact in this platform has a confidence_tier and cannot be confused with another.

**Question-driven, not field-driven:** the platform is structured around questions consultants ask, not around fields available in the data.

**DuckDB for everything:** analytical queries, vector similarity search (VSS extension) and structured storage all in one file. No separate vector database, no server required.

**Pipeline log visible in the app:** a consultant always knows how fresh the data is and whether the last run succeeded.

**Ollama first, OpenRouter fallback:** LLM extraction runs locally by default so no data leaves the machine. OpenRouter free tier is the fallback for machines without Ollama.

**Built using Claude Code** as the primary development tool.

---

## How this extends

Adding a new OEM to Tier 2 requires one entry in `config/tier2_sources.yaml` — no code changes. The pipeline discovers new press releases, chunks and embeds them, extracts structured claims, and surfaces them for human review.

Q3 (operator portfolios) and Q4 (BESS co-location) require new Streamlit pages only — all data is already in `wind_plants`.

Q5 (benchmarking) requires combining MaStR with Tier 2 order intake data to compare a client's portfolio against peers.

In production: database moves to cloud storage (S3 or GCS), Streamlit deploys to Streamlit Community Cloud with a public URL, GitHub Actions reads and writes from cloud storage rather than committing the binary file to the repository.

---

## Questions I would ask before building the full platform

1. Which questions do GTP consultants ask most often, and which currently take the most time to answer manually?

2. Does GTP have access to any licensed data sources such as Wood Mackenzie, Bloomberg NEF or MAKE Consulting?

3. Should the platform prioritise BESS alongside wind from the start, or is onshore wind the immediate priority?

4. How should proprietary client engagement data be handled — separate schema, different access controls?

---

## How to run it

Install dependencies:
```
pip install -r requirements.txt
```

Optional: install Ollama for local LLM extraction:
https://ollama.ai — then: `ollama pull qwen2.5:7b`

Optional: set OpenRouter API key for cloud fallback:
Copy `.env.example` to `.env` and add your key

Run the full pipeline:
```
python -m pipeline.run_pipeline
```

Run Tier 1 only (official data, no LLM required):
```
python -m pipeline.run_pipeline tier1
```

Start the app:
```
streamlit run app/main.py
```

---

## Stack

Python · DuckDB (+ VSS extension) · Streamlit · Plotly · open-mastr · pdfplumber · sentence-transformers · Ollama

Data: Marktstammdatenregister (MaStR), Bundesnetzagentur · Nordex press releases
