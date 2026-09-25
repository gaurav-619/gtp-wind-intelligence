"""
app/utils/db.py
Database helper functions for the Streamlit app.
Provides read-only and write connections, query helpers,
and utility functions for pipeline status and source registry.
"""

from dotenv import load_dotenv
load_dotenv()

import duckdb
import pandas as pd
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "db", "gtp.duckdb")


def get_connection():
    """Return a read-only DuckDB connection to the database."""
    if not os.path.exists(DB_PATH):
        print(f"Warning: Database not found at {DB_PATH}. Run the pipeline first.")
        # Create the database if it doesn't exist
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        conn = duckdb.connect(DB_PATH, read_only=False)
        conn.close()
    return duckdb.connect(DB_PATH, read_only=True)


def get_write_connection():
    """Return a writable DuckDB connection to the database."""
    if not os.path.exists(DB_PATH):
        print(f"Warning: Database not found at {DB_PATH}. Run the pipeline first.")
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return duckdb.connect(DB_PATH, read_only=False)


def query(sql: str, params: list = None) -> pd.DataFrame:
    """Execute a SQL query and return results as a DataFrame."""
    try:
        conn = get_connection()
        if params:
            result = conn.execute(sql, params).df()
        else:
            result = conn.execute(sql).df()
        conn.close()
        return result
    except Exception as e:
        print(f"Query error: {e}")
        return pd.DataFrame()


def get_latest_snapshot_date() -> str:
    """Get the most recent snapshot date as a string."""
    result = query("SELECT MAX(snapshot_date) as d FROM snapshots")
    if result.empty or result["d"].iloc[0] is None:
        return "Unknown"
    return str(result["d"].iloc[0])


def get_pipeline_status() -> pd.DataFrame:
    """Get the most recent pipeline run log entries."""
    return query("""
        SELECT run_timestamp, step, status, records_processed, notes
        FROM pipeline_runs
        ORDER BY run_timestamp DESC
        LIMIT 20
    """)


def get_source_registry() -> pd.DataFrame:
    """Get all registered data sources."""
    return query("""
        SELECT source_name, source_type, confidence_tier, 
               confidence_label, last_fetched, update_frequency, notes
        FROM sources
        ORDER BY confidence_tier, source_name
    """)


def verify_claim(claim_id: str):
    """Mark an extracted claim as human-verified."""
    conn = get_write_connection()
    conn.execute("""
        UPDATE extracted_claims 
        SET human_verified = True, verified_at = NOW()
        WHERE claim_id = ?
    """, [claim_id])
    conn.close()


def get_legal_citations() -> pd.DataFrame:
    """Get all verified legal citations."""
    return query("""
        SELECT citation_id, law_name, paragraph, topic, official_text_de, source_url, verified_at
        FROM legal_citations
        ORDER BY law_name, paragraph
    """)


def add_or_verify_legal_citation(citation_id: str, law_name: str, paragraph: str,
                                topic: str, official_text_de: str, source_url: str):
    """Add or update a verified statutory provision in legal_citations."""
    conn = get_write_connection()
    conn.execute("""
        INSERT OR REPLACE INTO legal_citations VALUES (?, ?, ?, ?, ?, ?, CURRENT_DATE)
    """, [citation_id, law_name, paragraph, topic, official_text_de, source_url])
    conn.close()

