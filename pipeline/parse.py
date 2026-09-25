"""
pipeline/parse.py
Parse and clean MaStR wind plant data.
Handles both real open-mastr output and synthetic fallback format.
"""

import pandas as pd
import numpy as np
import os
import re


# Column mapping rules: exact or partial regex matching
COLUMN_PATTERNS = {
    "mastr_id":             [r"^EinheitMastrNummer$", r"^MastrNummer$", r"mastr_nr", r"mastr_id"],
    "display_name":         [r"^NameStromerzeugungseinheit$", r"^NameWindpark$", r"^Einheitname$", r"^name$"],
    "operator_name":        [r"^AnlagenbetreiberName$", r"^AnlagenbetreiberMastrNummer$", r"^Betreiber$", r"^operator$"],
    "betriebs_status":      [r"^EinheitBetriebsstatus$", r"^Betriebsstatus$", r"^status$"],
    "energy_source":        [r"^Energietraeger$", r"^quelle$"],
    "inbetriebnahmedatum":  [r"^Inbetriebnahmedatum$"],
    "planned_date":         [r"^GeplantesInbetriebnahmedatum$"],
    "registrierungsdatum":  [r"^Registrierungsdatum$", r"^Registrierung$"],
    "postleitzahl":         [r"^Postleitzahl$", r"^plz$"],
    "bruttoleistung_kw":    [r"^Bruttoleistung$"],
    "nettonennleistung_kw": [r"^Nettonennleistung$"],
    "last_updated":         [r"^DatumLetzteAktualisierung$", r"^Aktualisierung$"],
    "bundesland":           [r"^Bundesland$"],
}

# Bundesland name to code mapping
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
    "Ausschließliche Wirtschaftszone": "AWZ",
}

# Status value mapping to English
STATUS_MAP = {
    "In Betrieb":   "operating",
    "Betrieb":      "operating",
    "In Planung":   "planned",
    "Geplant":      "planned",
    "Stillgelegt":  "decommissioned",
    "Endgültig stillgelegt": "decommissioned",
    "Vorübergehend stillgelegt": "decommissioned",
}

# Valid statuses to keep
VALID_STATUSES = ["In Betrieb", "Betrieb", "In Planung", "Geplant"]


def _match_columns(df):
    """
    Match DataFrame columns to standardised names using partial string matching.
    Returns a renamed DataFrame and prints what was matched.
    """
    rename_map = {}
    matched_source_cols = set()

    for target_name, patterns in COLUMN_PATTERNS.items():
        matched = False
        for col in df.columns:
            if col in matched_source_cols:
                continue
            for pattern in patterns:
                if re.search(pattern, col, re.IGNORECASE):
                    rename_map[col] = target_name
                    matched_source_cols.add(col)
                    print(f"  Column matched: '{col}' -> '{target_name}'")
                    matched = True
                    break
            if matched:
                break
        if not matched:
            print(f"  Warning: no match found for '{target_name}'")

    return df.rename(columns=rename_map)


def parse_wind_plants():
    """
    Read, clean and transform MaStR wind plant data.
    Returns a cleaned DataFrame ready for loading into DuckDB.
    """
    csv_path = "data/raw/mastr_wind_raw.csv"

    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Raw data file not found: {csv_path}")

    print(f"Reading {csv_path}...")
    df = pd.read_csv(csv_path, comment="#", dtype=str)
    print(f"Raw rows: {len(df)}, columns: {len(df.columns)}")

    # Step 1: Filter onshore wind if offshore designation column exists
    if "WindAnLandOderAufSee" in df.columns:
        before_onshore = len(df)
        df = df[df["WindAnLandOderAufSee"].str.contains("Land", na=False)]
        print(f"Filtered to Onshore wind: {before_onshore} -> {len(df)} rows")

    # Step 2: Rename columns by matching
    print("\nColumn matching:")
    df = _match_columns(df)

    # Step 3: Apply transformations

    # Convert kW to MW
    if "bruttoleistung_kw" in df.columns:
        df["bruttoleistung_kw"] = pd.to_numeric(df["bruttoleistung_kw"], errors="coerce")
        df["bruttoleistung_mw"] = df["bruttoleistung_kw"] / 1000.0
    else:
        df["bruttoleistung_mw"] = np.nan

    if "nettonennleistung_kw" in df.columns:
        df["nettonennleistung_kw"] = pd.to_numeric(df["nettonennleistung_kw"], errors="coerce")
        df["nettonennleistung_mw"] = df["nettonennleistung_kw"] / 1000.0
    else:
        df["nettonennleistung_mw"] = np.nan

    # Parse dates
    for date_col in ["inbetriebnahmedatum", "planned_date", "registrierungsdatum", "last_updated"]:
        if date_col in df.columns:
            df[date_col] = pd.to_datetime(df[date_col], errors="coerce").dt.date

    # For planned plants without commissioning date, use planned date
    if "inbetriebnahmedatum" in df.columns and "planned_date" in df.columns:
        df["inbetriebnahmedatum"] = df["inbetriebnahmedatum"].fillna(df["planned_date"])

    # Clean postleitzahl: strip whitespace, zero-pad to 5 digits
    if "postleitzahl" in df.columns:
        df["postleitzahl"] = (
            df["postleitzahl"]
            .astype(str)
            .str.strip()
            .str.replace(r"\.0$", "", regex=True)
            .str.zfill(5)
        )

    # Step 4: Filter

    # Keep only wind energy
    if "energy_source" in df.columns:
        before = len(df)
        df = df[df["energy_source"].str.contains("Wind", case=False, na=False)]
        print(f"\nFiltered to Wind energy: {before} -> {len(df)} rows")

    # Keep only valid statuses
    if "betriebs_status" in df.columns:
        before = len(df)
        df = df[df["betriebs_status"].isin(VALID_STATUSES)]
        print(f"Filtered to valid statuses: {before} -> {len(df)} rows")

    # Drop rows where mastr_id is null
    if "mastr_id" in df.columns:
        before = len(df)
        df = df.dropna(subset=["mastr_id"])
        print(f"Dropped null mastr_id: {before} -> {len(df)} rows")

    # Drop duplicate mastr_id keeping most recently updated
    if "mastr_id" in df.columns:
        before = len(df)
        if "last_updated" in df.columns:
            df = df.sort_values("last_updated", ascending=False).drop_duplicates(
                subset=["mastr_id"], keep="first"
            )
        else:
            df = df.drop_duplicates(subset=["mastr_id"], keep="first")
        print(f"Deduplicated by mastr_id: {before} -> {len(df)} rows")

    # Step 5: Map status values to English
    if "betriebs_status" in df.columns:
        df["betriebs_status"] = df["betriebs_status"].map(STATUS_MAP).fillna("unknown")

    # Step 6: Map Bundesland & Bundesland code
    if "bundesland" in df.columns:
        df["bundesland_code"] = df["bundesland"].map(BUNDESLAND_CODES).fillna("XX")
    else:
        df["bundesland"] = "Unbekannt"
        df["bundesland_code"] = "XX"

    # If any Bundesland is missing, join with reference PLZ
    missing_bl = df["bundesland"].isna() | (df["bundesland"] == "Unbekannt")
    if missing_bl.any():
        plz_path = "reference/plz_bundesland.csv"
        if os.path.exists(plz_path):
            plz_df = pd.read_csv(plz_path, dtype=str)
            plz_df["plz"] = plz_df["plz"].astype(str).str.strip().str.zfill(5)
            plz_map = dict(zip(plz_df["plz"], plz_df["bundesland"]))
            code_map = dict(zip(plz_df["plz"], plz_df["bundesland_code"]))

            df.loc[missing_bl, "bundesland"] = df.loc[missing_bl, "postleitzahl"].map(plz_map).fillna("Unbekannt")
            df.loc[missing_bl, "bundesland_code"] = df.loc[missing_bl, "postleitzahl"].map(code_map).fillna("XX")

    # Step 7: Ensure standard output columns match DuckDB wind_plants schema
    df["source_id"] = "mastr_wind"

    expected_cols = [
        "mastr_id", "display_name", "operator_name", "betriebs_status",
        "energy_source", "inbetriebnahmedatum", "registrierungsdatum",
        "postleitzahl", "bruttoleistung_kw", "nettonennleistung_kw",
        "bruttoleistung_mw", "nettonennleistung_mw", "bundesland",
        "bundesland_code", "source_id", "last_updated"
    ]

    for col in expected_cols:
        if col not in df.columns:
            df[col] = np.nan

    df = df[expected_cols]
    print("\n" + "=" * 60)
    print("PARSE SUMMARY")
    print("=" * 60)
    print(f"Total rows after cleaning:    {len(df)}")

    operating = df[df["betriebs_status"] == "operating"]
    planned = df[df["betriebs_status"] == "planned"]
    print(f"Rows with status 'operating': {len(operating)}")
    print(f"Rows with status 'planned':   {len(planned)}")

    no_bl = len(df[df["bundesland"] == "Unbekannt"])
    print(f"Rows with no Bundesland:      {no_bl}")

    total_mw = operating["nettonennleistung_mw"].sum()
    print(f"Total installed MW (operating): {total_mw:,.1f} MW")

    if "inbetriebnahmedatum" in df.columns:
        valid_dates = df["inbetriebnahmedatum"].dropna()
        if len(valid_dates) > 0:
            print(f"Date range: {min(valid_dates)} to {max(valid_dates)}")
    print("=" * 60)

    return df


if __name__ == "__main__":
    df = parse_wind_plants()
    print(f"\nParsed DataFrame shape: {df.shape}")
