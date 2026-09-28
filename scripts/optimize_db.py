"""
scripts/optimize_db.py
Builds a production-ready, lean DuckDB file (<5MB) suitable for GitHub and Streamlit Cloud deployment.
Prunes redundant residential rooftop home batteries from storage_units, preserving only wind-relevant units.
"""
import duckdb
import os
import shutil

DB_ORIG = os.path.join(os.path.dirname(__file__), "..", "db", "gtp.duckdb")
DB_OPT = os.path.join(os.path.dirname(__file__), "..", "db", "gtp_optimized.duckdb")

if os.path.exists(DB_OPT):
    os.remove(DB_OPT)

conn = duckdb.connect(DB_OPT)
conn.execute(f"ATTACH '{DB_ORIG}' AS src (READ_ONLY)")

tables = [r[0] for r in conn.execute('SHOW TABLES FROM src').fetchall()]
print(f"Transferring {len(tables)} tables to lean production database...")

for t in tables:
    if t == 'storage_units':
        conn.execute('CREATE TABLE storage_units AS SELECT * FROM src.storage_units WHERE co_located_wind = TRUE')
        cnt = conn.execute('SELECT count(*) FROM storage_units').fetchone()[0]
        print(f"  - {t}: pruned to {cnt:,} co-located rows")
    else:
        conn.execute(f'CREATE TABLE {t} AS SELECT * FROM src.{t}')
        cnt = conn.execute(f'SELECT count(*) FROM {t}').fetchone()[0]
        print(f"  - {t}: {cnt:,} rows")

conn.execute('DETACH src')
conn.close()

sz_mb = os.path.getsize(DB_OPT) / (1024 * 1024)
print(f"\n[DONE] Lean database created at {DB_OPT} ({sz_mb:.2f} MB)")
