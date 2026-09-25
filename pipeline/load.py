"""
pipeline/load.py
Database initialisation and data loading functions.
Creates all tables in DuckDB, installs VSS extension, seeds source registry.
"""

import duckdb
import pandas as pd
import os
import uuid
from datetime import datetime, date


DB_PATH = os.path.join(os.path.dirname(__file__), "..", "db", "gtp.duckdb")


def init_db():
    """
    Connect to db/gtp.duckdb and create all tables.
    Install and load the DuckDB VSS extension for vector similarity search.
    """
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = duckdb.connect(DB_PATH)

    # 1. Source registry
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sources (
            source_id           TEXT PRIMARY KEY,
            source_name         TEXT NOT NULL,
            source_type         TEXT NOT NULL,
            confidence_tier     INTEGER NOT NULL,
            confidence_label    TEXT NOT NULL,
            source_url          TEXT,
            update_frequency    TEXT,
            last_fetched        DATE,
            notes               TEXT
        )
    """)

    # 2. PLZ to Bundesland reference
    conn.execute("""
        CREATE TABLE IF NOT EXISTS plz_bundesland (
            plz                 TEXT PRIMARY KEY,
            bundesland          TEXT NOT NULL,
            bundesland_code     TEXT NOT NULL
        )
    """)

    # 3. Wind plant registry
    conn.execute("""
        CREATE TABLE IF NOT EXISTS wind_plants (
            mastr_id                TEXT PRIMARY KEY,
            display_name            TEXT,
            operator_name           TEXT,
            energy_source           TEXT NOT NULL,
            betriebs_status         TEXT,
            inbetriebnahmedatum     DATE,
            registrierungsdatum     DATE,
            postleitzahl            TEXT,
            bundesland              TEXT,
            bundesland_code         TEXT,
            bruttoleistung_mw       DOUBLE,
            nettonennleistung_mw    DOUBLE,
            source_id               TEXT REFERENCES sources(source_id),
            last_updated            DATE
        )
    """)

    # 4. Pre-aggregated snapshots
    conn.execute("""
        CREATE TABLE IF NOT EXISTS snapshots (
            snapshot_id             TEXT PRIMARY KEY,
            snapshot_date           DATE NOT NULL,
            bundesland              TEXT NOT NULL,
            bundesland_code         TEXT NOT NULL,
            energy_source           TEXT NOT NULL,
            total_installed_mw      DOUBLE,
            plant_count             INTEGER,
            planned_mw              DOUBLE,
            planned_count           INTEGER,
            median_permit_days      DOUBLE,
            source_id               TEXT REFERENCES sources(source_id)
        )
    """)

    # 5. Pipeline run log
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pipeline_runs (
            run_id                  TEXT PRIMARY KEY,
            run_timestamp           TIMESTAMP NOT NULL,
            step                    TEXT NOT NULL,
            records_processed       INTEGER,
            source_id               TEXT,
            status                  TEXT NOT NULL,
            notes                   TEXT
        )
    """)

    # 6. Document chunks for RAG
    conn.execute("""
        CREATE TABLE IF NOT EXISTS document_chunks (
            chunk_id                TEXT PRIMARY KEY,
            source_id               TEXT REFERENCES sources(source_id),
            document_url            TEXT,
            document_date           DATE,
            chunk_index             INTEGER,
            chunk_text              TEXT,
            embedding               FLOAT[384],
            created_at              TIMESTAMP
        )
    """)

    # 7. Extracted claims from Tier 2 sources
    conn.execute("""
        CREATE TABLE IF NOT EXISTS extracted_claims (
            claim_id                TEXT PRIMARY KEY,
            source_id               TEXT REFERENCES sources(source_id),
            entity                  TEXT,
            metric                  TEXT,
            period                  TEXT,
            value                   DOUBLE,
            unit                    TEXT,
            source_sentence_de      TEXT,
            source_sentence_en      TEXT,
            document_url            TEXT,
            chunk_id                TEXT REFERENCES document_chunks(chunk_id),
            extracted_at            TIMESTAMP,
            extraction_model        TEXT,
            human_verified          BOOLEAN DEFAULT FALSE,
            verified_at             TIMESTAMP,
            confidence_score        DOUBLE
        )
    """)

    # Install and load VSS extension for vector similarity search
    try:
        conn.execute("INSTALL vss;")
        conn.execute("LOAD vss;")
        print("VSS extension installed and loaded.")
    except Exception as e:
        print(f"VSS extension note: {e}")
        # Try just loading if already installed
        try:
            conn.execute("LOAD vss;")
            print("VSS extension loaded (was already installed).")
        except Exception as e2:
            print(f"VSS extension could not be loaded: {e2}")

    # Create HNSW index on document_chunks for fast similarity search
    try:
        conn.execute("SET hnsw_enable_experimental_persistence = true;")
        conn.execute("""
            CREATE INDEX IF NOT EXISTS chunk_embedding_idx 
            ON document_chunks 
            USING HNSW (embedding)
            WITH (metric = 'cosine')
        """)
        print("HNSW index created on document_chunks.embedding.")
    except Exception as e:
        print(f"HNSW index note: {e}")

    # Seed the sources table
    conn.execute("""
        INSERT OR REPLACE INTO sources VALUES
        ('mastr_wind', 'Marktstammdatenregister - Wind', 'official', 1, 'official_registry',
         'https://www.marktstammdatenregister.de/MaStR', 'monthly', NULL,
         'Official German energy plant registry, Bundesnetzagentur')
    """)

    conn.execute("""
        INSERT OR REPLACE INTO sources VALUES
        ('plz_lookup', 'PLZ to Bundesland Reference', 'reference', 1, 'reference',
         'https://www.suche-postleitzahl.org/downloads', 'static', NULL,
         'Static postal code to federal state mapping')
    """)

    conn.execute("""
        INSERT OR REPLACE INTO sources VALUES
        ('nordex_press', 'Nordex Press Releases', 'company_claim', 2, 'company_claim',
         'https://www.nordex-online.com/de/investor-relations/pressemitteilungen/',
         'quarterly', NULL,
         'Quarterly press releases from Nordex SE, German language')
    """)

    print("Tables created and sources seeded.")
    conn.close()


def log_pipeline_run(conn, step: str, records_processed: int = 0,
                     source_id: str = None, status: str = "success",
                     notes: str = None):
    """Helper to log a pipeline run step."""
    run_id = f"{step}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    conn.execute("""
        INSERT OR REPLACE INTO pipeline_runs VALUES (?, ?, ?, ?, ?, ?, ?)
    """, [run_id, datetime.now(), step, records_processed, source_id, status, notes])


def load_wind_plants(df, conn):
    """
    Load parsed wind plant data into the wind_plants table.
    Aligns DataFrame columns to match the table schema exactly.
    """
    # Required columns in order
    required_cols = [
        "mastr_id", "display_name", "operator_name", "energy_source",
        "betriebs_status", "inbetriebnahmedatum", "registrierungsdatum",
        "postleitzahl", "bundesland", "bundesland_code", "bruttoleistung_mw",
        "nettonennleistung_mw", "source_id", "last_updated"
    ]

    # Add missing columns as None
    for col in required_cols:
        if col not in df.columns:
            df[col] = None

    # Keep only required columns in order, drop extras
    df = df[required_cols].copy()

    try:
        # Clear existing mastr_wind plants to prevent stale/residual records
        conn.execute("DELETE FROM wind_plants WHERE source_id = 'mastr_wind'")
        # Upsert using DuckDB's pandas integration
        conn.execute("INSERT OR REPLACE INTO wind_plants SELECT * FROM df")

        # Update sources table with last_fetched date
        conn.execute("""
            UPDATE sources SET last_fetched = CURRENT_DATE 
            WHERE source_id = 'mastr_wind'
        """)

        total = conn.execute("SELECT COUNT(*) FROM wind_plants").fetchone()[0]
        print(f"Loaded {len(df)} rows into wind_plants. Total rows now: {total}")

        log_pipeline_run(conn, "load_wind_plants", len(df), "mastr_wind", "success",
                         f"Loaded {len(df)} rows, total now {total}")

    except Exception as e:
        print(f"Error loading wind plants: {e}")
        log_pipeline_run(conn, "load_wind_plants", 0, "mastr_wind", "failed", str(e))
        raise


if __name__ == "__main__":
    init_db()
    print("Database initialised at db/gtp.duckdb")
