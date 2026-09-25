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
        print(f"PLZ download failed: {e}. Using fallback data.")

        # FALLBACK: hardcoded representative PLZ covering all 16 states
        rows = []
        for plz, code in FALLBACK_PLZ.items():
            rows.append({
                "plz": plz,
                "bundesland": CODE_TO_BUNDESLAND[code],
                "bundesland_code": code
            })
        df = pd.DataFrame(rows)
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
# MaStR wind plant data fetch (Prompt 4)
# --------------------------------------------------------------------------

# Real PLZ values for synthetic data generation, spread across all 16 states
SAMPLE_PLZ = [
    "10115", "20095", "28195", "30159", "40213", "44135", "50667", "55116",
    "66111", "68159", "70173", "80331", "90402", "01067", "04109", "06108",
    "14467", "18055", "24103", "39104", "99084", "34117", "54290", "32052",
    "48143", "65185", "26122", "37073", "15230", "19053", "25524", "98527",
]

SAMPLE_OPERATORS = [
    "Energiekontor AG", "wpd AG", "Enercon GmbH",
    "Stadtwerke Hannover AG", "EnBW Energie Baden-Württemberg AG",
    "RWE Renewables GmbH", "juwi AG", "PNE AG",
    "ABO Wind AG", "VSB Neue Energien Deutschland GmbH",
    "BayWa r.e. Wind GmbH", "UKA Umweltgerechte Kraftanlagen GmbH",
    "Trianel Windkraftwerk GmbH", "Windpark Verwaltungs GmbH",
    "Norderland GbR", "WPD Windmanager GmbH",
]

SAMPLE_CITIES = [
    "Aurich", "Bremerhaven", "Cuxhaven", "Dithmarschen", "Emden",
    "Flensburg", "Güstrow", "Husum", "Itzehoe", "Jever",
    "Kiel", "Leer", "Magdeburg", "Nordenham", "Oldenburg",
    "Prenzlau", "Quedlinburg", "Rostock", "Stralsund", "Trier",
    "Uelzen", "Verden", "Wismar", "Xanten", "Zwickau",
    "Aachen", "Bielefeld", "Cottbus", "Dresden", "Erfurt",
    "Frankfurt (Oder)", "Göttingen", "Halle", "Jena", "Kassel",
    "Leipzig", "Münster", "Neubrandenburg", "Osnabrück", "Potsdam",
    "Schwerin", "Wilhelmshaven", "Wittenberg", "Dessau", "Stendal",
    "Greifswald", "Pasewalk", "Parchim", "Rendsburg", "Heide",
]


def _generate_synthetic_data(n=500):
    """
    Generate synthetic wind plant data matching open-mastr output format.
    FOR PROTOTYPE DEMONSTRATION ONLY.
    """
    random.seed(42)
    np.random.seed(42)

    rows = []
    for i in range(n):
        # Status distribution: 85% In Betrieb, 10% In Planung, 5% Stillgelegt
        status_roll = random.random()
        if status_roll < 0.85:
            status = "In Betrieb"
        elif status_roll < 0.95:
            status = "In Planung"
        else:
            status = "Stillgelegt"

        # Commissioning date range: 1995-01-01 to 2024-12-31
        start_date = date(1995, 1, 1)
        end_date = date(2024, 12, 31)
        days_range = (end_date - start_date).days
        inbetriebnahme = start_date + timedelta(days=random.randint(0, days_range))

        # Registration date: after 2019-01-01, before Inbetriebnahme for operating plants
        reg_start = date(2019, 1, 1)
        if status == "In Betrieb" and inbetriebnahme > reg_start:
            reg_days = (inbetriebnahme - reg_start).days
            if reg_days > 0:
                registrierung = reg_start + timedelta(days=random.randint(0, reg_days))
            else:
                registrierung = reg_start
        else:
            reg_end = date(2024, 12, 31)
            reg_days = (reg_end - reg_start).days
            registrierung = reg_start + timedelta(days=random.randint(0, reg_days))

        bruttoleistung = random.uniform(500, 6000)
        plz = random.choice(SAMPLE_PLZ)
        city = random.choice(SAMPLE_CITIES)

        rows.append({
            "EinheitMastrNummer": f"SEE{random.randint(100000000000, 999999999999)}",
            "EinheitBetriebsstatus": status,
            "Inbetriebnahmedatum": inbetriebnahme.isoformat(),
            "Registrierungsdatum": registrierung.isoformat(),
            "Energietraeger": "Wind",
            "Bruttoleistung": round(bruttoleistung, 1),
            "Nettonennleistung": round(bruttoleistung * 0.97, 1),
            "Postleitzahl": plz,
            "Einheitname": f"Windpark {city}",
            "AnlagenbetreiberName": random.choice(SAMPLE_OPERATORS),
            "DatumLetzteAktualisierung": date(2024, random.randint(1, 12),
                                               random.randint(1, 28)).isoformat(),
        })

    return pd.DataFrame(rows)


def fetch_mastr_wind():
    """
    Download wind plant data using the open-mastr package.
    Falls back to synthetic data if open-mastr is not available.
    """
    os.makedirs("data/raw", exist_ok=True)
    csv_path = "data/raw/mastr_wind_raw.csv"

    # Attempt 1: open-mastr
    try:
        from open_mastr import Mastr

        db = Mastr()
        db.download(data=["wind"])
        df = db.to_dataframe(data="wind")

        if df is not None and len(df) > 100:
            df.to_csv(csv_path, index=False)
            print(f"Downloaded real MaStR data: {len(df)} rows")
            return csv_path

    except Exception as e:
        print(f"open-mastr failed: {e}. Using synthetic fallback.")

    # Fallback: synthetic dataset
    print("Generating synthetic wind plant data for prototype...")
    df = _generate_synthetic_data(500)

    # Add comment header to indicate synthetic data
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("# SYNTHETIC DATA - FOR PROTOTYPE DEMONSTRATION ONLY\n")
        f.write("# Replace with real open-mastr download before production use\n")
    df.to_csv(csv_path, mode="a", index=False)

    print(f"Generated synthetic data: {len(df)} rows")
    print(f"\nFirst 3 rows:")
    print(df.head(3).to_string())
    print(f"\nTotal rows: {len(df)}")

    return csv_path


if __name__ == "__main__":
    plz_df, note = fetch_plz_lookup()
    print(f"\nPLZ lookup: {len(plz_df)} entries ({note})")

    csv = fetch_mastr_wind()
    print(f"\nMaStR data saved to: {csv}")
