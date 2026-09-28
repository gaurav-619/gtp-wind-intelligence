"""
pipeline/parse.py
Parse, clean, and standardize official MaStR wind plant data.
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


def resolve_operator_names(wind_df: pd.DataFrame, market_df: pd.DataFrame) -> pd.DataFrame:
    """
    Join wind_plants.operator_name (currently the ABR ID) against the market actors
    table's MaStR-Nr. column (MastrNummer), replacing operator_name with the resolved
    company name (Firmenname / Name des Marktakteurs) wherever a match exists.
    Where no match exists, keep the original ABR ID and flag rows in
    operator_name_resolved (True/False).
    """
    wind_df = wind_df.copy()

    # Find the ID column (MaStR-Nr. / MastrNummer)
    id_col = None
    for c in ["MastrNummer", "MaStR-Nr.", "mastr_nummer", "mastr_id"]:
        if c in market_df.columns:
            id_col = c
            break
    if not id_col:
        for c in market_df.columns:
            if re.search(r"mastr.*(nr|nummer|id)", c, re.IGNORECASE):
                id_col = c
                break

    # Find the company / legal name column
    name_col = None
    for c in ["Firmenname", "Name des Marktakteurs", "MarktakteurName", "name", "firmenname"]:
        if c in market_df.columns:
            name_col = c
            break
    if not name_col:
        for c in market_df.columns:
            if re.search(r"(firmenname|name.*marktakteur|marktakteur.*name)", c, re.IGNORECASE):
                name_col = c
                break

    if not id_col or not name_col:
        raise ValueError(
            f"Could not identify ID and Name columns in market_df. Available: {list(market_df.columns[:10])}"
        )

    # Filter market_df to non-null IDs
    clean_market = market_df[[id_col, name_col]].dropna(subset=[id_col]).copy()
    clean_market[id_col] = clean_market[id_col].astype(str).str.strip()
    clean_market[name_col] = clean_market[name_col].astype(str).str.strip().str.replace('\uff06', '&', regex=False)

    # Drop empty or literal 'nan'/'none' values
    valid_mask = (
        clean_market[name_col].notna() &
        (clean_market[name_col] != "") &
        (clean_market[name_col].str.lower() != "nan") &
        (clean_market[name_col].str.lower() != "none")
    )
    clean_market = clean_market[valid_mask].drop_duplicates(subset=[id_col], keep="first")

    id_to_name = dict(zip(clean_market[id_col], clean_market[name_col]))

    original_op = wind_df["operator_name"].fillna("").astype(str).str.strip().str.replace('\uff06', '&', regex=False)
    resolved_name = original_op.map(id_to_name)

    is_resolved = resolved_name.notna() & (resolved_name != "")
    if "operator_mastr_id" not in wind_df.columns:
        wind_df["operator_mastr_id"] = original_op
    wind_df["operator_name_resolved"] = is_resolved
    wind_df["operator_name"] = np.where(is_resolved, resolved_name, original_op)
    wind_df["operator_name"] = wind_df["operator_name"].str.replace('\uff06', '&', regex=False)

    n_resolved = int(is_resolved.sum())
    n_total = len(wind_df)
    pct = (n_resolved / n_total * 100) if n_total > 0 else 0.0
    print(f"\nOperator Name Resolution Summary:")
    print(f"  Total rows:     {n_total:,}")
    print(f"  Resolved names: {n_resolved:,} ({pct:.1f}%)")
    print(f"  Unresolved IDs: {n_total - n_resolved:,} ({100 - pct:.1f}%)")

    return wind_df


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
    from pipeline.fetch_tier1 import CODE_TO_BUNDESLAND
    if "bundesland" in df.columns:
        df["bundesland_code"] = df["bundesland"].map(BUNDESLAND_CODES).fillna("XX")
    else:
        df["bundesland_code"] = "XX"

    # If any Bundesland is missing or Unbekannt, join with reference PLZ
    missing_bl = (df["bundesland_code"] == "XX") | df["bundesland"].isna() | (df["bundesland"] == "Unbekannt")
    plz_path = "reference/plz_bundesland.csv"
    if os.path.exists(plz_path):
        plz_df = pd.read_csv(plz_path, dtype=str)
        plz_df["plz"] = plz_df["plz"].astype(str).str.strip().str.zfill(5)
        code_map = dict(zip(plz_df["plz"], plz_df["bundesland_code"]))
        df.loc[missing_bl, "bundesland_code"] = df.loc[missing_bl, "postleitzahl"].map(code_map).fillna("XX")

    # Standardize Bundesland names to clean UTF-8 German names
    df["bundesland"] = df["bundesland_code"].map(CODE_TO_BUNDESLAND).fillna(df.get("bundesland", "Unbekannt"))

    # Step 7: Resolve operator names if market actors export exists
    market_csv = "data/raw/market_actors_raw.csv"
    if os.path.exists(market_csv):
        print(f"\nResolving operator names using {market_csv}...")
        header_df = pd.read_csv(market_csv, nrows=1, dtype=str)
        cols_needed = [c for c in header_df.columns if c in ["MastrNummer", "Firmenname", "Name des Marktakteurs", "MaStR-Nr."]]
        market_df = pd.read_csv(market_csv, usecols=cols_needed if cols_needed else None, dtype=str)
        df = resolve_operator_names(df, market_df)
    elif "operator_name_resolved" not in df.columns:
        df["operator_name_resolved"] = False

    # Step 8: Ensure standard output columns match DuckDB wind_plants schema
    df["source_id"] = "mastr_wind"

    expected_cols = [
        "mastr_id", "display_name", "operator_mastr_id", "operator_name", "operator_name_resolved", "betriebs_status",
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


def parse_storage_units():
    """
    Read, clean and transform MaStR storage units data.
    Standardizes kW to MW, parses dates, normalizes postal codes,
    maps statuses to operating/planned/decommissioned, and resolves operator names.
    Uses DuckDB's vectorized reader for fast, memory-safe transformation.
    Returns a cleaned DataFrame ready for loading into DuckDB storage_units.
    """
    csv_path = "data/raw/storage_units_raw.csv"

    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Raw storage data file not found: {csv_path}")

    print(f"Reading and transforming {csv_path} via DuckDB...")
    import duckdb
    conn = duckdb.connect()

    market_csv = "data/raw/market_actors_raw.csv"
    has_market = os.path.exists(market_csv)

    market_join = f"LEFT JOIN (SELECT MastrNummer, Firmenname FROM read_csv_auto('{market_csv}')) m ON s.AnlagenbetreiberMastrNummer = m.MastrNummer" if has_market else ""
    op_name_col = "COALESCE(REPLACE(m.Firmenname, '\uff06', '&'), s.AnlagenbetreiberMastrNummer)" if has_market else "s.AnlagenbetreiberMastrNummer"
    op_res_col = "(m.Firmenname IS NOT NULL AND m.Firmenname != '')" if has_market else "FALSE"

    df = conn.execute(f"""
        SELECT 
            s.EinheitMastrNummer as mastr_id,
            s.NameStromerzeugungseinheit as display_name,
            s.AnlagenbetreiberMastrNummer as operator_mastr_id,
            {op_name_col} as operator_name,
            {op_res_col} as operator_name_resolved,
            CASE 
                WHEN s.EinheitBetriebsstatus IN ('In Betrieb', 'Betrieb') THEN 'operating'
                WHEN s.EinheitBetriebsstatus IN ('In Planung', 'Geplant') THEN 'planned'
                ELSE 'decommissioned'
            END as betriebs_status,
            TRY_CAST(COALESCE(s.Inbetriebnahmedatum, s.GeplantesInbetriebnahmedatum) AS DATE) as inbetriebnahmedatum,
            TRY_CAST(s.Registrierungsdatum AS DATE) as registrierungsdatum,
            LPAD(TRIM(REPLACE(COALESCE(s.Postleitzahl, ''), '.0', '')), 5, '0') as postleitzahl,
            COALESCE(s.Bundesland, 'Unbekannt') as bundesland,
            'XX' as bundesland_code,
            TRY_CAST(s.Bruttoleistung AS DOUBLE) / 1000.0 as bruttoleistung_mw,
            TRY_CAST(s.Nettonennleistung AS DOUBLE) / 1000.0 as nettonennleistung_mw,
            COALESCE(s.Batterietechnologie, 'Unbekannt') as batterietechnologie,
            'mastr_storage' as source_id,
            TRY_CAST(s.DatumLetzteAktualisierung AS DATE) as last_updated
        FROM read_csv_auto('{csv_path}') s
        {market_join}
        WHERE s.EinheitBetriebsstatus IN ('In Betrieb', 'Betrieb', 'In Planung', 'Geplant')
        AND s.EinheitMastrNummer IS NOT NULL
    """).df()
    conn.close()

    # Deduplicate by mastr_id
    if "last_updated" in df.columns:
        df = df.sort_values("last_updated", ascending=False).drop_duplicates(subset=["mastr_id"], keep="first")
    else:
        df = df.drop_duplicates(subset=["mastr_id"], keep="first")

    # Map Bundesland code
    df["bundesland_code"] = df["bundesland"].map(BUNDESLAND_CODES).fillna("XX")

    # If any Bundesland is missing or Unbekannt, look up from reference/plz_bundesland.csv
    missing_bl = (df["bundesland"] == "Unbekannt") | (df["bundesland_code"] == "XX")
    if missing_bl.any():
        plz_path = "reference/plz_bundesland.csv"
        if os.path.exists(plz_path):
            plz_df = pd.read_csv(plz_path, dtype=str)
            plz_df["plz"] = plz_df["plz"].astype(str).str.strip().str.zfill(5)
            plz_map = dict(zip(plz_df["plz"], plz_df["bundesland"]))
            code_map = dict(zip(plz_df["plz"], plz_df["bundesland_code"]))
            df.loc[missing_bl, "bundesland"] = df.loc[missing_bl, "postleitzahl"].map(plz_map).fillna("Unbekannt")
            df.loc[missing_bl, "bundesland_code"] = df.loc[missing_bl, "postleitzahl"].map(code_map).fillna("XX")

    df["source_id"] = "mastr_storage"

    # Standard columns
    expected_cols = [
        "mastr_id", "display_name", "operator_mastr_id", "operator_name", "operator_name_resolved",
        "betriebs_status", "inbetriebnahmedatum", "registrierungsdatum",
        "postleitzahl", "bruttoleistung_mw", "nettonennleistung_mw", "batterietechnologie",
        "bundesland", "bundesland_code", "source_id", "last_updated"
    ]
    for col in expected_cols:
        if col not in df.columns:
            df[col] = np.nan
    df = df[expected_cols]

    print("\n" + "=" * 60)
    print("STORAGE PARSE SUMMARY")
    print("=" * 60)
    print(f"Total storage units after cleaning: {len(df):,}")
    operating = df[df["betriebs_status"] == "operating"]
    print(f"Operating storage units:            {len(operating):,}")
    print(f"Total operating storage capacity:   {operating['nettonennleistung_mw'].sum():,.2f} MW")
    print("=" * 60)
    return df


if __name__ == "__main__":
    df = parse_wind_plants()
    print(f"\nParsed DataFrame shape: {df.shape}")

