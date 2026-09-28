"""
pipeline/aggregate.py
Build pre-aggregated snapshot table from wind_plants data.
Computes cumulative installed capacity, planned pipeline, and permitting speed
per Bundesland per year.
"""

import duckdb
import pandas as pd
from datetime import date
from pipeline.load import log_pipeline_run
from pipeline.fetch_tier1 import CODE_TO_BUNDESLAND


def build_snapshots(conn):
    """
    Build cumulative snapshots of installed and planned wind capacity
    by Bundesland and year. Also builds a national aggregate (Deutschland / DE).
    """
    print("Building snapshots...")

    # Drop existing snapshots for a clean rebuild
    conn.execute("DELETE FROM snapshots")

    today = date.today()

    # Get operating commissioning years up to current year (focus on 2000 to current year)
    years = conn.execute("""
        SELECT DISTINCT YEAR(inbetriebnahmedatum) as yr 
        FROM wind_plants 
        WHERE inbetriebnahmedatum IS NOT NULL
        AND YEAR(inbetriebnahmedatum) >= 2000
        AND YEAR(inbetriebnahmedatum) <= ?
        ORDER BY yr
    """, [today.year]).fetchdf()

    if years.empty:
        print("No data with commissioning dates found. Skipping snapshots.")
        log_pipeline_run(conn, "build_snapshots", 0, "mastr_wind", "failed",
                         "No commissioning dates in wind_plants")
        return

    year_list = [int(y) for y in years["yr"].tolist()]

    # Get all distinct Bundesländer
    states = conn.execute("""
        SELECT DISTINCT bundesland, bundesland_code 
        FROM wind_plants 
        WHERE bundesland IS NOT NULL AND bundesland != 'Unbekannt'
    """).fetchdf()

    all_snapshots = []

    for _, state_row in states.iterrows():
        bl_code = state_row["bundesland_code"]
        bl = CODE_TO_BUNDESLAND.get(bl_code, state_row["bundesland"])

        for yr in year_list:
            # Cumulative installed MW (sum of all operating plants commissioned up to this year)
            installed = conn.execute("""
                SELECT 
                    COALESCE(SUM(nettonennleistung_mw), 0) as total_mw,
                    COUNT(*) as plant_count
                FROM wind_plants
                WHERE betriebs_status = 'operating'
                AND bundesland_code = ?
                AND YEAR(inbetriebnahmedatum) <= ?
            """, [bl_code, yr]).fetchone()

            total_installed_mw = installed[0]
            plant_count = installed[1]

            # Planned MW (current snapshot of planned plants, not cumulative)
            planned = conn.execute("""
                SELECT 
                    COALESCE(SUM(nettonennleistung_mw), 0) as planned_mw,
                    COUNT(*) as planned_count
                FROM wind_plants
                WHERE betriebs_status = 'planned'
                AND bundesland_code = ?
            """, [bl_code]).fetchone()

            planned_mw = planned[0]
            planned_count = planned[1]

            # Median permit days (registration to commissioning)
            permit = conn.execute("""
                SELECT MEDIAN(
                    DATEDIFF('day', registrierungsdatum, inbetriebnahmedatum)
                ) as median_days
                FROM wind_plants
                WHERE bundesland_code = ?
                AND inbetriebnahmedatum IS NOT NULL
                AND registrierungsdatum IS NOT NULL
                AND DATEDIFF('day', registrierungsdatum, inbetriebnahmedatum) > 0
                AND DATEDIFF('day', registrierungsdatum, inbetriebnahmedatum) < 3650
                AND YEAR(inbetriebnahmedatum) <= ?
            """, [bl_code, yr]).fetchone()

            median_permit_days = permit[0] if permit[0] is not None else None
            snapshot_id = f"{bl_code}_{yr}"
            snapshot_dt = today if yr == today.year else date(yr, 12, 31)

            all_snapshots.append({
                "snapshot_id": snapshot_id,
                "snapshot_date": snapshot_dt,
                "bundesland": bl,
                "bundesland_code": bl_code,
                "energy_source": "Wind",
                "total_installed_mw": total_installed_mw,
                "plant_count": plant_count,
                "planned_mw": planned_mw,
                "planned_count": planned_count,
                "median_permit_days": median_permit_days,
                "source_id": "mastr_wind",
            })

    # Build national aggregate (Deutschland / DE) for each year
    for yr in year_list:
        installed = conn.execute("""
            SELECT 
                COALESCE(SUM(nettonennleistung_mw), 0) as total_mw,
                COUNT(*) as plant_count
            FROM wind_plants
            WHERE betriebs_status = 'operating'
            AND bundesland != 'Unbekannt'
            AND YEAR(inbetriebnahmedatum) <= ?
        """, [yr]).fetchone()

        planned = conn.execute("""
            SELECT 
                COALESCE(SUM(nettonennleistung_mw), 0) as planned_mw,
                COUNT(*) as planned_count
            FROM wind_plants
            WHERE betriebs_status = 'planned'
            AND bundesland != 'Unbekannt'
        """).fetchone()

        permit = conn.execute("""
            SELECT MEDIAN(
                DATEDIFF('day', registrierungsdatum, inbetriebnahmedatum)
            ) as median_days
            FROM wind_plants
            WHERE inbetriebnahmedatum IS NOT NULL
            AND registrierungsdatum IS NOT NULL
            AND DATEDIFF('day', registrierungsdatum, inbetriebnahmedatum) > 0
            AND DATEDIFF('day', registrierungsdatum, inbetriebnahmedatum) < 3650
            AND YEAR(inbetriebnahmedatum) <= ?
        """, [yr]).fetchone()

        snapshot_id = f"DE_{yr}"
        snapshot_dt = today if yr == today.year else date(yr, 12, 31)

        all_snapshots.append({
            "snapshot_id": snapshot_id,
            "snapshot_date": snapshot_dt,
            "bundesland": "Deutschland",
            "bundesland_code": "DE",
            "energy_source": "Wind",
            "total_installed_mw": installed[0],
            "plant_count": installed[1],
            "planned_mw": planned[0],
            "planned_count": planned[1],
            "median_permit_days": permit[0] if permit[0] is not None else None,
            "source_id": "mastr_wind",
        })

    # Insert all snapshots
    df = pd.DataFrame(all_snapshots)
    conn.execute("INSERT OR REPLACE INTO snapshots SELECT * FROM df")

    total = conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0]
    log_pipeline_run(conn, "build_snapshots", total, "mastr_wind", "success",
                     f"Built {total} snapshot rows")

    # Print summary
    print(f"\n{'=' * 60}")
    print("SNAPSHOT SUMMARY")
    print(f"{'=' * 60}")
    print(f"Total snapshot rows created: {total}")

    latest_year = conn.execute("""
        SELECT MAX(YEAR(snapshot_date)) FROM snapshots WHERE bundesland_code = 'DE'
    """).fetchone()[0]
    print(f"Latest year in data: {latest_year}")

    top3 = conn.execute("""
        SELECT bundesland, total_installed_mw
        FROM snapshots
        WHERE bundesland_code != 'DE'
        AND YEAR(snapshot_date) = ?
        ORDER BY total_installed_mw DESC
        LIMIT 3
    """, [latest_year]).fetchdf()

    print(f"\nTop 3 Bundesländer by installed MW ({latest_year}):")
    for _, row in top3.iterrows():
        print(f"  {row['bundesland']}: {row['total_installed_mw']:,.1f} MW")

    national = conn.execute("""
        SELECT total_installed_mw FROM snapshots
        WHERE bundesland_code = 'DE' AND YEAR(snapshot_date) = ?
    """, [latest_year]).fetchone()
    if national:
        print(f"\nNational total installed MW ({latest_year}): {national[0]:,.1f} MW")

    print(f"{'=' * 60}")


def aggregate_bess(conn):
    """
    Produce state-level and national BESS co-location summaries.
    Computes:
      - Total operating wind MW
      - Co-located BESS MW (operating)
      - Co-located BESS unit count
      - Co-location rate (% of wind MW paired with battery storage)
      - Average battery capacity (MW)
      - Top operators co-locating BESS
    Saves results into the bess_summary table.
    """
    print("\nAggregating BESS co-location summaries...")
    # Recreate table with clean schema
    conn.execute("DROP TABLE IF EXISTS bess_summary")
    conn.execute("""
        CREATE TABLE bess_summary (
            bundesland              TEXT PRIMARY KEY,
            bundesland_code         TEXT NOT NULL,
            total_wind_mw           DOUBLE,
            wind_plant_count        INTEGER,
            colocated_bess_mw       DOUBLE,
            colocated_bess_count    INTEGER,
            bess_share_pct          DOUBLE,
            colocation_mw_share_pct DOUBLE,
            avg_bess_mw             DOUBLE,
            top_operators           TEXT,
            updated_at              DATE
        )
    """)

    # 1. State-level summary
    states_df = conn.execute("""
        SELECT DISTINCT bundesland, bundesland_code 
        FROM wind_plants 
        WHERE bundesland IS NOT NULL AND bundesland != 'Unbekannt'
        ORDER BY bundesland
    """).fetchdf()

    today = date.today()
    rows = []

    for _, srow in states_df.iterrows():
        bl_code = srow["bundesland_code"]
        bl = CODE_TO_BUNDESLAND.get(bl_code, srow["bundesland"])

        # Wind stats for operating
        w_stats = conn.execute("""
            SELECT 
                COALESCE(SUM(nettonennleistung_mw), 0) as wind_mw,
                COUNT(*) as wind_count
            FROM wind_plants
            WHERE betriebs_status = 'operating'
            AND bundesland_code = ?
        """, [bl_code]).fetchone()

        # Co-located BESS stats
        b_stats = conn.execute("""
            SELECT 
                COALESCE(SUM(nettonennleistung_mw), 0) as bess_mw,
                COUNT(*) as bess_count
            FROM storage_units
            WHERE co_located_wind = TRUE
            AND betriebs_status = 'operating'
            AND bundesland_code = ?
        """, [bl_code]).fetchone()

        wind_mw = round(float(w_stats[0]), 2)
        wind_count = int(w_stats[1])
        bess_mw = round(float(b_stats[0]), 2)
        bess_count = int(b_stats[1])
        share_pct = round((bess_mw / wind_mw * 100.0), 4) if wind_mw > 0 else 0.0
        avg_bess = round((bess_mw / bess_count), 2) if bess_count > 0 else 0.0

        # Top operators for this state
        top_ops = conn.execute("""
            SELECT operator_name, SUM(nettonennleistung_mw) as op_mw
            FROM storage_units
            WHERE co_located_wind = TRUE
            AND betriebs_status = 'operating'
            AND bundesland_code = ?
            AND operator_name IS NOT NULL
            GROUP BY operator_name
            ORDER BY op_mw DESC
            LIMIT 3
        """, [bl_code]).fetchdf()

        top_op_str = ", ".join([f"{r['operator_name']} ({r['op_mw']:.1f} MW)" for _, r in top_ops.iterrows()]) if not top_ops.empty else "N/A"

        rows.append({
            "bundesland": bl,
            "bundesland_code": bl_code,
            "total_wind_mw": wind_mw,
            "wind_plant_count": wind_count,
            "colocated_bess_mw": bess_mw,
            "colocated_bess_count": bess_count,
            "bess_share_pct": share_pct,
            "colocation_mw_share_pct": share_pct,
            "avg_bess_mw": avg_bess,
            "top_operators": top_op_str,
            "updated_at": today
        })

    # 2. National summary (Deutschland / DE)
    w_nat = conn.execute("""
        SELECT 
            COALESCE(SUM(nettonennleistung_mw), 0) as wind_mw,
            COUNT(*) as wind_count
        FROM wind_plants
        WHERE betriebs_status = 'operating'
        AND bundesland != 'Unbekannt'
    """).fetchone()

    b_nat = conn.execute("""
        SELECT 
            COALESCE(SUM(nettonennleistung_mw), 0) as bess_mw,
            COUNT(*) as bess_count
        FROM storage_units
        WHERE co_located_wind = TRUE
        AND betriebs_status = 'operating'
    """).fetchone()

    nat_wind_mw = round(float(w_nat[0]), 2)
    nat_wind_cnt = int(w_nat[1])
    nat_bess_mw = round(float(b_nat[0]), 2)
    nat_bess_cnt = int(b_nat[1])
    nat_share = round((nat_bess_mw / nat_wind_mw * 100.0), 4) if nat_wind_mw > 0 else 0.0
    nat_avg = round((nat_bess_mw / nat_bess_cnt), 2) if nat_bess_cnt > 0 else 0.0

    nat_top_ops = conn.execute("""
        SELECT operator_name, SUM(nettonennleistung_mw) as op_mw
        FROM storage_units
        WHERE co_located_wind = TRUE
        AND betriebs_status = 'operating'
        AND operator_name IS NOT NULL
        GROUP BY operator_name
        ORDER BY op_mw DESC
        LIMIT 5
    """).fetchdf()
    nat_top_op_str = ", ".join([f"{r['operator_name']} ({r['op_mw']:.1f} MW)" for _, r in nat_top_ops.iterrows()]) if not nat_top_ops.empty else "N/A"

    rows.append({
        "bundesland": "Deutschland",
        "bundesland_code": "DE",
        "total_wind_mw": nat_wind_mw,
        "wind_plant_count": nat_wind_cnt,
        "colocated_bess_mw": nat_bess_mw,
        "colocated_bess_count": nat_bess_cnt,
        "bess_share_pct": nat_share,
        "colocation_mw_share_pct": nat_share,
        "avg_bess_mw": nat_avg,
        "top_operators": nat_top_op_str,
        "updated_at": today
    })

    bess_df = pd.DataFrame(rows)
    cols_str = ", ".join(bess_df.columns)
    conn.execute(f"INSERT OR REPLACE INTO bess_summary ({cols_str}) SELECT {cols_str} FROM bess_df")
    print(f"Stored {len(bess_df)} rows in bess_summary (National: {nat_bess_mw:,.2f} MW co-located across {nat_bess_cnt:,} assets).")

    # Export to CSV with unit convention note
    import os
    os.makedirs("data/exports", exist_ok=True)
    export_path = "data/exports/bess_summary_export.csv"
    unit_note = "# Unit convention: All *_pct columns are percentages (0.35 = 0.35%), all *_mw columns are megawatts.\n"
    csv_content = bess_df.to_csv(index=False)
    with open(export_path, "w", encoding="utf-8") as f:
        f.write(unit_note + csv_content)
    print(f"Exported BESS co-location summary to {export_path}")

    log_pipeline_run(conn, "aggregate_bess", len(bess_df), "mastr_storage", "success",
                     f"National co-located BESS: {nat_bess_mw:,.2f} MW ({nat_share:.2f}% of wind capacity)")
    return bess_df


if __name__ == "__main__":
    import duckdb as ddb
    conn = ddb.connect("db/gtp.duckdb")
    build_snapshots(conn)
    aggregate_bess(conn)
    conn.close()
