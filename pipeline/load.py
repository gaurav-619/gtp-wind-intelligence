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
            operator_mastr_id       TEXT,
            operator_name           TEXT,
            operator_name_resolved  BOOLEAN DEFAULT FALSE,
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

    # Ensure operator_mastr_id exists on existing tables
    try:
        conn.execute("ALTER TABLE wind_plants ADD COLUMN IF NOT EXISTS operator_mastr_id TEXT")
    except Exception:
        pass

    # 3b. Battery Storage (BESS) units registry (separate asset type)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS storage_units (
            mastr_id                TEXT PRIMARY KEY,
            display_name            TEXT,
            operator_mastr_id       TEXT,
            operator_name           TEXT,
            operator_name_resolved  BOOLEAN DEFAULT FALSE,
            betriebs_status         TEXT,
            inbetriebnahmedatum     DATE,
            registrierungsdatum     DATE,
            postleitzahl            TEXT,
            bundesland              TEXT,
            bundesland_code         TEXT,
            bruttoleistung_mw       DOUBLE,
            nettonennleistung_mw    DOUBLE,
            batterietechnologie     TEXT,
            co_located_wind         BOOLEAN DEFAULT FALSE,
            matched_wind_mastr_id   TEXT,
            source_id               TEXT REFERENCES sources(source_id),
            last_updated            DATE
        )
    """)

    # 3c. BESS co-location summary
    conn.execute("""
        CREATE TABLE IF NOT EXISTS bess_summary (
            bundesland              TEXT PRIMARY KEY,
            bundesland_code         TEXT NOT NULL,
            total_wind_mw           DOUBLE,
            wind_plant_count        INTEGER,
            colocated_bess_mw       DOUBLE,
            colocated_bess_count    INTEGER,
            colocation_mw_share_pct DOUBLE,
            avg_bess_mw             DOUBLE,
            top_operators           TEXT,
            updated_at              DATE
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
            confidence_score        DOUBLE,
            is_preliminary          BOOLEAN DEFAULT FALSE,
            UNIQUE (source_id, entity, metric, period)
        )
    """)

    # 8. Legal citations verification registry
    conn.execute("""
        CREATE TABLE IF NOT EXISTS legal_citations (
            citation_id                 TEXT PRIMARY KEY,
            law_name                    TEXT NOT NULL,
            paragraph                   TEXT NOT NULL,
            topic                       TEXT NOT NULL,
            official_text_de            TEXT NOT NULL,
            source_url                  TEXT NOT NULL,
            verified_at                 DATE NOT NULL,
            official_text_en            TEXT,
            translation_verified        BOOLEAN DEFAULT FALSE,
            translation_model           TEXT,
            back_translation_de         TEXT,
            back_translation_similarity DOUBLE,
            glossary_violations         TEXT
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

    conn.execute("""
        INSERT OR REPLACE INTO sources VALUES
        ('mastr_storage', 'Marktstammdatenregister - Battery Storage', 'official', 1, 'official_registry',
         'https://www.marktstammdatenregister.de/MaStR', 'monthly', NULL,
         'Official German energy storage registry, Bundesnetzagentur')
    """)

    # Seed verified statutory provisions live from gesetze-im-internet.de
    try:
        from pipeline.fetch_legal_citations import fetch_and_seed_legal_citations
        fetch_and_seed_legal_citations(conn)
    except Exception as e:
        print(f"Warning: could not live-fetch legal citations during init_db: {e}")

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
        "mastr_id", "display_name", "operator_mastr_id", "operator_name", "operator_name_resolved", "energy_source",
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
        # Ensure column exists if table was created in an earlier migration
        conn.execute("ALTER TABLE wind_plants ADD COLUMN IF NOT EXISTS operator_mastr_id TEXT")
        conn.execute("ALTER TABLE wind_plants ADD COLUMN IF NOT EXISTS operator_name_resolved BOOLEAN DEFAULT FALSE")
        # Clear existing mastr_wind plants to prevent stale/residual records
        conn.execute("DELETE FROM wind_plants WHERE source_id = 'mastr_wind'")
        # Upsert using explicit column matching
        cols_str = ", ".join(required_cols)
        conn.execute(f"INSERT OR REPLACE INTO wind_plants ({cols_str}) SELECT {cols_str} FROM df")

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


def load_storage_units(df, conn):
    """
    Load parsed storage units data into the storage_units table.
    """
    required_cols = [
        "mastr_id", "display_name", "operator_mastr_id", "operator_name", "operator_name_resolved",
        "betriebs_status", "inbetriebnahmedatum", "registrierungsdatum",
        "postleitzahl", "bundesland", "bundesland_code", "bruttoleistung_mw",
        "nettonennleistung_mw", "batterietechnologie", "source_id", "last_updated"
    ]

    for col in required_cols:
        if col not in df.columns:
            df[col] = None

    df = df[required_cols].copy()

    try:
        conn.execute("DELETE FROM storage_units WHERE source_id = 'mastr_storage'")
        cols_str = ", ".join(required_cols)
        conn.execute(f"INSERT OR REPLACE INTO storage_units ({cols_str}) SELECT {cols_str} FROM df")

        conn.execute("""
            UPDATE sources SET last_fetched = CURRENT_DATE 
            WHERE source_id = 'mastr_storage'
        """)

        total = conn.execute("SELECT COUNT(*) FROM storage_units").fetchone()[0]
        print(f"Loaded {len(df):,} rows into storage_units. Total rows now: {total:,}")

        log_pipeline_run(conn, "load_storage_units", len(df), "mastr_storage", "success",
                         f"Loaded {len(df):,} storage rows, total now {total:,}")
    except Exception as e:
        print(f"Error loading storage units: {e}")
        log_pipeline_run(conn, "load_storage_units", 0, "mastr_storage", "failed", str(e))
        raise


def link_storage_to_wind(conn):
    """
    Match storage units to wind plants to identify co-located BESS assets.
    Primary key: direct link field if present.
    Best available proxy: matching on (operator_mastr_id, postal_code) and (operator_name, postal_code).
    Updates storage_units.co_located_wind and matched_wind_mastr_id.
    Reports:
      - Total storage units found
      - Total successfully matched to a wind plant
      - Total unmatched
      - Total co-located capacity in MW
    """
    print("\nLinking storage units to wind plants (BESS co-location analysis)...")
    conn.execute("UPDATE storage_units SET co_located_wind = FALSE, matched_wind_mastr_id = NULL")

    # Perform matching
    conn.execute("""
        UPDATE storage_units
        SET co_located_wind = TRUE,
            matched_wind_mastr_id = sub.wind_mastr_id
        FROM (
            SELECT 
                s.mastr_id as storage_mastr_id,
                MIN(w.mastr_id) as wind_mastr_id
            FROM storage_units s
            JOIN wind_plants w ON (
                (s.operator_mastr_id IS NOT NULL AND w.operator_mastr_id IS NOT NULL 
                 AND s.operator_mastr_id = w.operator_mastr_id 
                 AND s.postleitzahl = w.postleitzahl)
                OR
                (s.operator_name IS NOT NULL AND w.operator_name IS NOT NULL
                 AND s.operator_name = w.operator_name
                 AND s.operator_name_resolved = TRUE AND w.operator_name_resolved = TRUE
                 AND s.postleitzahl = w.postleitzahl)
            )
            GROUP BY s.mastr_id
        ) sub
        WHERE storage_units.mastr_id = sub.storage_mastr_id
    """)

    stats = conn.execute("""
        SELECT 
            COUNT(*) as total_storage,
            COUNT(CASE WHEN co_located_wind THEN 1 END) as matched_storage,
            COUNT(CASE WHEN NOT co_located_wind THEN 1 END) as unmatched_storage,
            COALESCE(SUM(CASE WHEN co_located_wind AND betriebs_status = 'operating' THEN nettonennleistung_mw END), 0) as colocated_operating_mw,
            COALESCE(SUM(CASE WHEN co_located_wind THEN nettonennleistung_mw END), 0) as colocated_total_mw
        FROM storage_units
    """).fetchone()

    total_storage = stats[0]
    matched_storage = stats[1]
    unmatched_storage = stats[2]
    colocated_operating_mw = stats[3]
    colocated_total_mw = stats[4]

    print("=" * 60)
    print("BESS CO-LOCATION MATCH REPORT")
    print("=" * 60)
    print(f"Total storage units in registry:    {total_storage:,}")
    print(f"Successfully matched to wind:       {matched_storage:,}")
    print(f"Unmatched storage units:            {unmatched_storage:,}")
    print(f"Co-located operating BESS capacity: {colocated_operating_mw:,.2f} MW")
    print(f"Co-located total (inc planned):     {colocated_total_mw:,.2f} MW")
    print("=" * 60)

    log_pipeline_run(conn, "link_storage_to_wind", matched_storage, "mastr_storage", "success",
                     f"Matched {matched_storage:,} BESS units ({colocated_operating_mw:,.2f} operating MW)")

    return {
        "total_storage": total_storage,
        "matched_storage": matched_storage,
        "unmatched_storage": unmatched_storage,
        "colocated_operating_mw": colocated_operating_mw,
        "colocated_total_mw": colocated_total_mw
    }


if __name__ == "__main__":
    init_db()
    print("Database initialised at db/gtp.duckdb")
