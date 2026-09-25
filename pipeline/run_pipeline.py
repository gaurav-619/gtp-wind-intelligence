"""
pipeline/run_pipeline.py
Orchestrates the full data pipeline.
- run_tier1(): Official data (MaStR, PLZ)
- run_tier2(): Company sources (press releases, RAG, LLM extraction)
- run_all(): Both tiers in sequence
"""

import sys
import time
import duckdb
import yaml

from pipeline.load import init_db, load_wind_plants
from pipeline.fetch_tier1 import fetch_plz_lookup, load_plz_lookup, fetch_mastr_wind
from pipeline.parse import parse_wind_plants
from pipeline.aggregate import build_snapshots


def run_tier1():
    """Run all Tier 1 pipeline steps in order with error handling."""
    start = time.time()
    results = {}

    conn = duckdb.connect("db/gtp.duckdb")

    steps = [
        ("init_db", lambda: init_db()),
        ("plz_fetch", lambda: fetch_plz_lookup()),
        ("plz_load", lambda: load_plz_lookup(conn)),
        ("mastr_fetch", lambda: fetch_mastr_wind()),
        ("mastr_parse", lambda: parse_wind_plants()),
        ("mastr_load", lambda: load_wind_plants(parse_wind_plants(), conn)),
        ("aggregate", lambda: build_snapshots(conn)),
    ]

    for step_name, step_fn in steps:
        try:
            step_fn()
            results[step_name] = "success"
            print(f"[OK] {step_name}")
        except Exception as e:
            results[step_name] = f"failed: {e}"
            print(f"[FAIL] {step_name}: {e}")

    elapsed = time.time() - start
    print(f"\nTier 1 pipeline complete in {elapsed:.1f}s")
    print(f"Results: {results}")
    conn.close()


def run_tier2():
    """Run all Tier 2 pipeline steps: discover, download, chunk, embed, extract."""
    from pipeline.fetch_tier2 import discover_new_documents, download_document
    from pipeline.rag import process_document_for_rag
    from pipeline.extract_claims import extract_claims_from_document

    conn = duckdb.connect("db/gtp.duckdb")

    with open("config/tier2_sources.yaml") as f:
        config = yaml.safe_load(f)

    for source in config["sources"]:
        print(f"\nProcessing {source['company']}...")

        try:
            new_docs = discover_new_documents(source)
            print(f"Found {len(new_docs)} new documents")
        except Exception as e:
            print(f"Discovery failed: {e}")
            continue

        for doc in new_docs:
            try:
                doc = download_document(doc)
                if doc is None:
                    continue

                chunk_count = process_document_for_rag(doc, conn)
                print(f"Stored {chunk_count} chunks")

                claims = extract_claims_from_document(doc, conn)
                print(f"Extracted {len(claims)} claims")

            except Exception as e:
                print(f"Failed processing {doc.get('url')}: {e}")

    conn.close()


def run_all():
    """Run both Tier 1 and Tier 2 pipelines."""
    print("=== Tier 1: Official Data ===")
    run_tier1()
    print("\n=== Tier 2: Company Sources ===")
    run_tier2()
    print("\n=== Pipeline complete ===")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "tier1":
        run_tier1()
    elif len(sys.argv) > 1 and sys.argv[1] == "tier2":
        run_tier2()
    else:
        run_all()
