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


def build_snapshots(conn):
    """
    Build cumulative snapshots of installed and planned wind capacity
    by Bundesland and year. Also builds a national aggregate (Deutschland / DE).
    """
    print("Building snapshots...")

    # Drop existing snapshots for a clean rebuild
    conn.execute("DELETE FROM snapshots")

    # Get all distinct years from wind_plants
    years = conn.execute("""
        SELECT DISTINCT YEAR(inbetriebnahmedatum) as yr 
        FROM wind_plants 
        WHERE inbetriebnahmedatum IS NOT NULL
        ORDER BY yr
    """).fetchdf()

    if years.empty:
        print("No data with commissioning dates found. Skipping snapshots.")
        log_pipeline_run(conn, "build_snapshots", 0, "mastr_wind", "failed",
                         "No commissioning dates in wind_plants")
        return

    year_list = years["yr"].tolist()

    # Get all distinct Bundesländer
    states = conn.execute("""
        SELECT DISTINCT bundesland, bundesland_code 
        FROM wind_plants 
        WHERE bundesland IS NOT NULL AND bundesland != 'Unbekannt'
    """).fetchdf()

    all_snapshots = []
    today = date.today()

    for _, state_row in states.iterrows():
        bl = state_row["bundesland"]
        bl_code = state_row["bundesland_code"]

        for yr in year_list:
            yr = int(yr)

            # Cumulative installed MW (sum of all operating plants commissioned up to this year)
            installed = conn.execute("""
                SELECT 
                    COALESCE(SUM(nettonennleistung_mw), 0) as total_mw,
                    COUNT(*) as plant_count
                FROM wind_plants
                WHERE betriebs_status = 'operating'
                AND bundesland = ?
                AND YEAR(inbetriebnahmedatum) <= ?
            """, [bl, yr]).fetchone()

            total_installed_mw = installed[0]
            plant_count = installed[1]

            # Planned MW (current snapshot of planned plants, not cumulative)
            planned = conn.execute("""
                SELECT 
                    COALESCE(SUM(nettonennleistung_mw), 0) as planned_mw,
                    COUNT(*) as planned_count
                FROM wind_plants
                WHERE betriebs_status = 'planned'
                AND bundesland = ?
            """, [bl]).fetchone()

            planned_mw = planned[0]
            planned_count = planned[1]

            # Median permit days (registration to commissioning)
            permit = conn.execute("""
                SELECT MEDIAN(
                    DATEDIFF('day', registrierungsdatum, inbetriebnahmedatum)
                ) as median_days
                FROM wind_plants
                WHERE bundesland = ?
                AND inbetriebnahmedatum IS NOT NULL
                AND registrierungsdatum IS NOT NULL
                AND DATEDIFF('day', registrierungsdatum, inbetriebnahmedatum) > 0
                AND DATEDIFF('day', registrierungsdatum, inbetriebnahmedatum) < 3650
                AND YEAR(inbetriebnahmedatum) <= ?
            """, [bl, yr]).fetchone()

            median_permit_days = permit[0] if permit[0] is not None else None

            snapshot_id = f"{bl_code}_{yr}"

            all_snapshots.append({
                "snapshot_id": snapshot_id,
                "snapshot_date": date(yr, 12, 31) if yr < today.year else today,
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
        yr = int(yr)

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

        all_snapshots.append({
            "snapshot_id": snapshot_id,
            "snapshot_date": date(yr, 12, 31) if yr < today.year else today,
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


if __name__ == "__main__":
    import duckdb as ddb
    conn = ddb.connect("db/gtp.duckdb")
    build_snapshots(conn)
    conn.close()
