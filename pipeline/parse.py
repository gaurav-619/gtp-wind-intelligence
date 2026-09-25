"""
pipeline/parse.py
Parse and clean MaStR wind plant data.
Handles both real open-mastr output and synthetic fallback format.
"""

import pandas as pd
import numpy as np
import os
import re


# Column mapping rules: partial string matching (case-insensitive)
COLUMN_PATTERNS = {
    "mastr_id":             [r"MastrNummer", r"mastr_nr", r"mastr_id"],
    "display_name":         [r"Einheitname", r"name"],
    "operator_name":        [r"Betreiber", r"operator"],
    "betriebs_status":      [r"Betriebsstatus", r"status"],
    "energy_source":        [r"Energietraeger", r"quelle", r"energietr"],
    "inbetriebnahmedatum":  [r"Inbetriebnahme"],
    "registrierungsdatum":  [r"Registrierung"],
    "postleitzahl":         [r"Postleitzahl", r"plz"],
    "bruttoleistung_kw":    [r"Bruttoleistung"],
    "nettonennleistung_kw": [r"Nettonennleistung"],
    "last_updated":         [r"Aktualisierung"],
}

# Status value mapping to English
STATUS_MAP = {
    "In Betrieb":   "operating",
    "Betrieb":      "operating",
    "In Planung":   "planned",
    "Geplant":      "planned",
    "Stillgelegt":  "decommissioned",
}

# Valid statuses to keep
VALID_STATUSES = ["In Betrieb", "Betrieb", "In Planung", "Geplant"]


def _match_columns(df):
    """
    Match DataFrame columns to standardised names using partial string matching.
    Returns a renamed DataFrame and prints what was matched.
    """
    rename_map = {}

    for target_name, patterns in COLUMN_PATTERNS.items():
        matched = False
        for col in df.columns:
            for pattern in patterns:
                if re.search(pattern, col, re.IGNORECASE):
                    rename_map[col] = target_name
                    print(f"  Column matched: '{col}' → '{target_name}'")
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
    print(f"Raw rows: {len(df)}, columns: {list(df.columns)}")

    # Step 1: Rename columns by partial string matching
    print("\nColumn matching:")
    df = _match_columns(df)

    # Step 2: Apply transformations

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
    for date_col in ["inbetriebnahmedatum", "registrierungsdatum", "last_updated"]:
        if date_col in df.columns:
            df[date_col] = pd.to_datetime(df[date_col], errors="coerce").dt.date

    # Clean postleitzahl: strip whitespace, zero-pad to 5 digits
    if "postleitzahl" in df.columns:
        df["postleitzahl"] = (
            df["postleitzahl"]
            .astype(str)
            .str.strip()
            .str.replace(r"\.0$", "", regex=True)
            .str.zfill(5)
        )

    # Step 3: Filter

    # Keep only wind energy
    if "energy_source" in df.columns:
        before = len(df)
        df = df[df["energy_source"].str.contains("Wind", case=False, na=False)]
        print(f"\nFiltered to Wind energy: {before} → {len(df)} rows")

    # Keep only valid statuses
    if "betriebs_status" in df.columns:
        before = len(df)
        df = df[df["betriebs_status"].isin(VALID_STATUSES)]
        print(f"Filtered to valid statuses: {before} → {len(df)} rows")

    # Drop rows where mastr_id is null
    if "mastr_id" in df.columns:
        before = len(df)
        df = df.dropna(subset=["mastr_id"])
        print(f"Dropped null mastr_id: {before} → {len(df)} rows")

    # Drop duplicate mastr_id keeping most recently updated
    if "mastr_id" in df.columns:
        before = len(df)
        if "last_updated" in df.columns:
            df = df.sort_values("last_updated", ascending=False).drop_duplicates(
                subset=["mastr_id"], keep="first"
            )
        else:
            df = df.drop_duplicates(subset=["mastr_id"], keep="first")
        print(f"Deduplicated by mastr_id: {before} → {len(df)} rows")

    # Step 4: Map status values to English
    if "betriebs_status" in df.columns:
        df["betriebs_status"] = df["betriebs_status"].map(STATUS_MAP).fillna("unknown")

    # Step 5: Join with PLZ lookup for Bundesland
    plz_path = "reference/plz_bundesland.csv"
    if os.path.exists(plz_path):
        plz_df = pd.read_csv(plz_path, dtype=str)
        plz_df["plz"] = plz_df["plz"].astype(str).str.strip().str.zfill(5)

        before_cols = set(df.columns)
        df = df.merge(plz_df, left_on="postleitzahl", right_on="plz", how="left")

        # Clean up: use the joined columns
        if "bundesland" not in before_cols and "bundesland" in df.columns:
            pass  # Already from the join
        if "plz" in df.columns and "postleitzahl" in df.columns:
            df = df.drop(columns=["plz"], errors="ignore")

        no_match = df["bundesland"].isna().sum()
        df["bundesland"] = df["bundesland"].fillna("Unbekannt")
        df["bundesland_code"] = df["bundesland_code"].fillna("XX")
        print(f"\nPLZ join: {no_match} rows had no Bundesland match")
    else:
        print(f"\nWarning: PLZ lookup file not found at {plz_path}")
        df["bundesland"] = "Unbekannt"
        df["bundesland_code"] = "XX"

    # Step 6: Add source_id
    df["source_id"] = "mastr_wind"

    # Step 7: Print summary
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
