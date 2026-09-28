"""
pipeline/fetch_tier1.py
Tier 1 data fetching: PLZ lookup and MaStR wind plant data.
"""

import os
import random
import uuid
import pandas as pd
import numpy as np
import requests
from datetime import datetime, date, timedelta
from io import StringIO
from pipeline.load import log_pipeline_run


# --------------------------------------------------------------------------
# Bundesland name to two-letter code mapping
# --------------------------------------------------------------------------
BUNDESLAND_CODES = {
    "Baden-Württemberg": "BW",
    "Bayern": "BY",
    "Berlin": "BE",
    "Brandenburg": "BB",
    "Bremen": "HB",
    "Hamburg": "HH",
    "Hessen": "HE",
    "Mecklenburg-Vorpommern": "MV",
    "Niedersachsen": "NI",
    "Nordrhein-Westfalen": "NW",
    "Rheinland-Pfalz": "RP",
    "Saarland": "SL",
    "Sachsen": "SN",
    "Sachsen-Anhalt": "ST",
    "Schleswig-Holstein": "SH",
    "Thüringen": "TH",
}

# Reverse mapping for lookup
CODE_TO_BUNDESLAND = {v: k for k, v in BUNDESLAND_CODES.items()}

# --------------------------------------------------------------------------
# PLZ to Bundesland fetch and load
# --------------------------------------------------------------------------

# Fallback PLZ data covering all 16 states with representative postal codes
FALLBACK_PLZ = {
    "10115": "BE", "13088": "BE",
    "20095": "HH", "21073": "HH",
    "28195": "HB", "28215": "HB",
    "30159": "NI", "26122": "NI",
    "40213": "NW", "44135": "NW", "50667": "NW",
    "55116": "RP",
    "66111": "SL",
    "68159": "BW", "70173": "BW",
    "80331": "BY", "90402": "BY",
    "01067": "SN", "04109": "SN",
    "06108": "ST", "39104": "ST",
    "14467": "BB", "15230": "BB",
    "18055": "MV", "19053": "MV",
    "24103": "SH", "25524": "SH",
    "37073": "NI",
    "99084": "TH", "98527": "TH", "07743": "TH",
    "32052": "NW",
    "34117": "HE", "65185": "HE",
    "54290": "RP",
    "48143": "NW",
}


def fetch_plz_lookup():
    """
    Download PLZ to Bundesland mapping from suche-postleitzahl.org.
    Falls back to a hardcoded representative set if download fails.
    Saves result to reference/plz_bundesland.csv.
    """
    os.makedirs("reference", exist_ok=True)
    source_note = ""

    try:
        print("Attempting to download PLZ data from suche-postleitzahl.org...")
        url = "https://www.suche-postleitzahl.org/download_files/public/zuordnung_plz_ort.csv"
        response = requests.get(url, timeout=30, headers={
            "User-Agent": "Mozilla/5.0 (compatible; research)"
        })
        response.raise_for_status()

        # Parse CSV — the file uses a specific encoding and delimiter
        content = response.content.decode("utf-8", errors="replace")
        df = pd.read_csv(StringIO(content), dtype=str)

        # Find PLZ and Bundesland columns (may vary)
        plz_col = None
        bl_col = None
        for col in df.columns:
            if "plz" in col.lower():
                plz_col = col
            if "bundesland" in col.lower():
                bl_col = col

        if plz_col is None or bl_col is None:
            raise ValueError(f"Could not find PLZ/Bundesland columns in: {df.columns.tolist()}")

        df = df[[plz_col, bl_col]].rename(columns={plz_col: "plz", bl_col: "bundesland"})
        df["plz"] = df["plz"].astype(str).str.strip().str.zfill(5)
        df = df.drop_duplicates(subset=["plz"]).dropna()

        # Map Bundesland names to codes
        df["bundesland_code"] = df["bundesland"].map(BUNDESLAND_CODES)
        df = df.dropna(subset=["bundesland_code"])

        source_note = "source: real download from suche-postleitzahl.org"
        print(f"Downloaded real PLZ data: {len(df)} unique postal codes")

    except Exception as e:
        print(f"PLZ download from suche-postleitzahl.org failed: {e}. Extracting from real MaStR data...")

        # Extract real postal codes directly from open-mastr database if available
        home_dir = os.path.expanduser("~")
        sqlite_path = os.path.join(home_dir, ".open-MaStR", "data", "sqlite", "open-mastr.db")

        mastr_plz_df = None
        if os.path.exists(sqlite_path):
            try:
                import sqlite3
                conn = sqlite3.connect(sqlite_path)
                mastr_plz_df = pd.read_sql_query(
                    "SELECT DISTINCT Postleitzahl as plz, Bundesland as bundesland "
                    "FROM EinheitenWind WHERE Postleitzahl IS NOT NULL AND Bundesland IS NOT NULL",
                    conn
                )
                conn.close()
                mastr_plz_df["plz"] = mastr_plz_df["plz"].astype(str).str.strip().str.zfill(5)
                mastr_plz_df["bundesland_code"] = mastr_plz_df["bundesland"].map(BUNDESLAND_CODES)
                mastr_plz_df = mastr_plz_df.dropna(subset=["bundesland_code"]).drop_duplicates(subset=["plz"])
                print(f"Extracted {len(mastr_plz_df)} real postal codes directly from MaStR turbine records")
            except Exception as ex:
                print(f"Could not extract PLZ from open-mastr SQLite: {ex}")

        # Combine with representative PLZ covering all 16 states
        rows = []
        for plz, code in FALLBACK_PLZ.items():
            rows.append({
                "plz": plz,
                "bundesland": CODE_TO_BUNDESLAND.get(code, "Unbekannt"),
                "bundesland_code": code
            })
        fallback_df = pd.DataFrame(rows)

        if mastr_plz_df is not None and len(mastr_plz_df) > 0:
            df = pd.concat([mastr_plz_df, fallback_df]).drop_duplicates(subset=["plz"])
            source_note = f"source: real MaStR turbine postal codes ({len(df)} entries)"
        else:
            df = fallback_df
            source_note = "source: fallback hardcoded PLZ data (representative only)"

    df.to_csv("reference/plz_bundesland.csv", index=False)
    print(f"Saved {len(df)} PLZ entries to reference/plz_bundesland.csv")
    return df, source_note


def load_plz_lookup(conn):
    """
    Read reference/plz_bundesland.csv and upsert into plz_bundesland table.
    """
    try:
        df = pd.read_csv("reference/plz_bundesland.csv", dtype=str)
        df["plz"] = df["plz"].astype(str).str.strip().str.zfill(5)

        conn.execute("INSERT OR REPLACE INTO plz_bundesland SELECT * FROM df")

        total = conn.execute("SELECT COUNT(*) FROM plz_bundesland").fetchone()[0]
        print(f"Loaded {len(df)} PLZ entries into plz_bundesland. Total: {total}")

        log_pipeline_run(conn, "plz_lookup", len(df), "plz_lookup", "success",
                         f"Loaded {len(df)} rows")
    except Exception as e:
        print(f"Error loading PLZ data: {e}")
        log_pipeline_run(conn, "plz_lookup", 0, "plz_lookup", "failed", str(e))
        raise


# --------------------------------------------------------------------------
# MaStR wind plant data fetch (Official BNetzA Data Only)
# --------------------------------------------------------------------------

def fetch_mastr_wind():
    """
    Download wind plant data using the open-mastr package.
    Extracts directly from the open-mastr SQLite database, which holds real BNetzA data.
    Attempts (a) local SQLite cache, then (b) live open-mastr download.
    If both fail, raises a RuntimeError.
    """
    os.makedirs("data/raw", exist_ok=True)
    csv_path = "data/raw/mastr_wind_raw.csv"

    # Step 1: Check if open-mastr SQLite DB already contains the downloaded data
    home_dir = os.path.expanduser("~")
    sqlite_path = os.path.join(home_dir, ".open-MaStR", "data", "sqlite", "open-mastr.db")

    if os.path.exists(sqlite_path):
        try:
            import sqlite3
            conn = sqlite3.connect(sqlite_path)
            cursor = conn.cursor()
            cursor.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='EinheitenWind'")
            if cursor.fetchone()[0] > 0:
                print(f"Reading real MaStR wind data from open-mastr database ({sqlite_path})...")
                df = pd.read_sql_query("SELECT * FROM EinheitenWind", conn)
                conn.close()
                if len(df) > 100:
                    df.to_csv(csv_path, index=False)
                    print(f"Successfully exported {len(df)} real MaStR wind turbines to {csv_path}")
                    return csv_path
            conn.close()
        except Exception as e:
            print(f"Error reading from open-mastr SQLite DB: {e}")

    # Step 2: Download via open_mastr
    try:
        from open_mastr import Mastr
        db = Mastr()
        print("Initiating open-mastr bulk download for wind...")
        db.download(data=["wind"])

        if os.path.exists(sqlite_path):
            import sqlite3
            conn = sqlite3.connect(sqlite_path)
            df = pd.read_sql_query("SELECT * FROM EinheitenWind", conn)
            conn.close()
            if len(df) > 100:
                df.to_csv(csv_path, index=False)
                print(f"Downloaded and exported {len(df)} real MaStR rows")
                return csv_path

    except Exception as e:
        print(f"open-mastr live download failed: {e}")

    # If both local cache and live download failed, abort execution
    raise RuntimeError(
        "No MaStR data source available - both cache and live download failed. "
        "Pipeline cannot continue."
    )


# --------------------------------------------------------------------------
# MaStR Market Actors (Marktakteure) data fetch
# --------------------------------------------------------------------------

def fetch_market_actors():
    """
    Download and export Market Actors (Marktakteure) from open-mastr.
    Checks the local open-mastr SQLite database for the Marktakteure table,
    or triggers open-mastr download(data="market").
    Exports the resulting table to data/raw/market_actors_raw.csv.
    """
    os.makedirs("data/raw", exist_ok=True)
    csv_path = "data/raw/market_actors_raw.csv"

    home_dir = os.path.expanduser("~")
    sqlite_path = os.path.join(home_dir, ".open-MaStR", "data", "sqlite", "open-mastr.db")

    # Step 1: Check if open-mastr SQLite DB already contains the market actors table
    if os.path.exists(sqlite_path):
        try:
            import sqlite3
            conn = sqlite3.connect(sqlite_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type IN ('table', 'view') AND name IN ('Marktakteure', 'market_actors')")
            row = cursor.fetchone()
            if row:
                tbl = row[0]
                print(f"Reading market actors from open-mastr database ({sqlite_path}, table: {tbl})...")
                # Stream out to CSV in chunks for fast, memory-safe export
                if os.path.exists(csv_path):
                    os.remove(csv_path)
                total_exported = 0
                for i, chunk in enumerate(pd.read_sql_query(f"SELECT * FROM {tbl}", conn, chunksize=200000)):
                    chunk.to_csv(csv_path, mode="a", header=(i == 0), index=False)
                    total_exported += len(chunk)
                    print(f"  Exported {total_exported:,} rows...")
                conn.close()
                print(f"Successfully exported {total_exported:,} market actors to {csv_path}")
                return csv_path
            conn.close()
        except Exception as e:
            print(f"Error reading market actors from SQLite DB: {e}")

    # Step 2: Live open_mastr download
    try:
        from open_mastr import Mastr
        db = Mastr()
        print("Initiating open-mastr bulk download for market actors...")
        db.download(data="market")

        if os.path.exists(sqlite_path):
            import sqlite3
            conn = sqlite3.connect(sqlite_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type IN ('table', 'view') AND name IN ('Marktakteure', 'market_actors')")
            row = cursor.fetchone()
            if row:
                tbl = row[0]
                df = pd.read_sql_query(f"SELECT * FROM {tbl}", conn)
                conn.close()
                if len(df) > 0:
                    df.to_csv(csv_path, index=False)
                    print(f"Successfully exported {len(df)} market actors to {csv_path}")
                    return csv_path
            conn.close()
    except Exception as e:
        print(f"open-mastr market actors download failed: {e}")
        raise RuntimeError(f"Could not fetch market actors: {e}")

def fetch_storage_units():
    """
    Download and export storage units (EinheitenStromSpeicher) from open-mastr.
    Checks the local open-mastr SQLite database for the EinheitenStromSpeicher table,
    or triggers open-mastr download(data="storage").
    Exports the resulting table to data/raw/storage_units_raw.csv.
    Prints all column headers.
    """
    os.makedirs("data/raw", exist_ok=True)
    csv_path = "data/raw/storage_units_raw.csv"

    home_dir = os.path.expanduser("~")
    sqlite_path = os.path.join(home_dir, ".open-MaStR", "data", "sqlite", "open-mastr.db")

    # Step 1: Check if open-mastr SQLite DB already contains storage units
    if os.path.exists(sqlite_path):
        try:
            import sqlite3
            conn = sqlite3.connect(sqlite_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table', 'view') "
                "AND name IN ('EinheitenStromSpeicher', 'storage_extended', 'storage_units')"
            )
            row = cursor.fetchone()
            if row:
                tbl = row[0]
                print(f"Reading storage units from open-mastr database ({sqlite_path}, table: {tbl})...")
                if os.path.exists(csv_path):
                    os.remove(csv_path)
                total_exported = 0
                for i, chunk in enumerate(pd.read_sql_query(f"SELECT * FROM {tbl}", conn, chunksize=200000)):
                    chunk.to_csv(csv_path, mode="a", header=(i == 0), index=False)
                    total_exported += len(chunk)
                    print(f"  Exported {total_exported:,} storage rows...")
                conn.close()
                print(f"Successfully exported {total_exported:,} storage units to {csv_path}")

                header_df = pd.read_csv(csv_path, nrows=1)
                print("\nRaw Storage Column Headers:")
                for col in header_df.columns:
                    print(f"  - {col}")
                return csv_path
            conn.close()
        except Exception as e:
            print(f"Error reading storage from SQLite DB: {e}")

    # Step 2: Download via open_mastr
    try:
        from open_mastr import Mastr
        db = Mastr()
        print("Initiating open-mastr bulk download for storage...")
        db.download(data="storage")

        if os.path.exists(sqlite_path):
            import sqlite3
            conn = sqlite3.connect(sqlite_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table', 'view') "
                "AND name IN ('EinheitenStromSpeicher', 'storage_extended', 'storage_units')"
            )
            row = cursor.fetchone()
            if row:
                tbl = row[0]
                print(f"Exporting storage units from {tbl}...")
                if os.path.exists(csv_path):
                    os.remove(csv_path)
                total_exported = 0
                for i, chunk in enumerate(pd.read_sql_query(f"SELECT * FROM {tbl}", conn, chunksize=200000)):
                    chunk.to_csv(csv_path, mode="a", header=(i == 0), index=False)
                    total_exported += len(chunk)
                    print(f"  Exported {total_exported:,} storage rows...")
                conn.close()
                print(f"Successfully exported {total_exported:,} storage units to {csv_path}")

                header_df = pd.read_csv(csv_path, nrows=1)
                print("\nRaw Storage Column Headers:")
                for col in header_df.columns:
                    print(f"  - {col}")
                return csv_path
            conn.close()
    except Exception as e:
        print(f"open-mastr storage download failed: {e}")
        raise RuntimeError(f"Could not fetch storage units: {e}")

    raise RuntimeError("No storage table found after open-mastr download.")


if __name__ == "__main__":
    plz_df, note = fetch_plz_lookup()
    print(f"\nPLZ lookup: {len(plz_df)} entries ({note})")

    csv = fetch_mastr_wind()
    print(f"\nMaStR data saved to: {csv}")


