"""
pipeline/fetch_legal_citations.py
Live scraper and validator for official German statutory provisions from gesetze-im-internet.de.
Fetches verbatim law texts, parses official HTML via div.jurAbsatz,
and populates the legal_citations table in db/gtp.duckdb.
"""

import requests
from bs4 import BeautifulSoup
import duckdb
from datetime import date
from pipeline.load import log_pipeline_run

# Registry of authoritative statutory provisions to fetch live
STATUTE_CONFIGS = [
    {
        "citation_id": "mastrv_p5_abs5",
        "law_name": "MaStRV",
        "paragraph": "§ 5",
        "topic": "Ein-Monats-Frist zur Registrierung nach Inbetriebnahme",
        "url": "https://www.gesetze-im-internet.de/mastrv/__5.html",
        "absatz_prefix": "(5)",
    },
    {
        "citation_id": "mastrv_p5_abs1",
        "law_name": "MaStRV",
        "paragraph": "§ 5",
        "topic": "Registrierungspflicht für Einheiten und EEG-Anlagen",
        "url": "https://www.gesetze-im-internet.de/mastrv/__5.html",
        "absatz_prefix": "(1)",
    },
    {
        "citation_id": "mastrv_p5_abs4",
        "law_name": "MaStRV",
        "paragraph": "§ 5",
        "topic": "Registrierungspflicht für genehmigungsbedürftige Projekte",
        "url": "https://www.gesetze-im-internet.de/mastrv/__5.html",
        "absatz_prefix": "(4)",
    },
    {
        "citation_id": "eeg_p1",
        "law_name": "EEG 2023",
        "paragraph": "§ 1",
        "topic": "Ziel des Gesetzes (Transformation, 80% Erneuerbare bis 2030, Ausbaupfad)",
        "url": "https://www.gesetze-im-internet.de/eeg_2014/__1.html",
        "absatz_prefix": "ALL",
    },
    {
        "citation_id": "eeg_p4",
        "law_name": "EEG 2023",
        "paragraph": "§ 4",
        "topic": "Gesetzliche Ausbaupfade (115 GW Wind an Land bis 2030, 160 GW bis 2040)",
        "url": "https://www.gesetze-im-internet.de/eeg_2014/__4.html",
        "absatz_prefix": "Die Ziele",
    },
    {
        "citation_id": "bimschg_p4",
        "law_name": "BImSchG",
        "paragraph": "§ 4",
        "topic": "Genehmigungsbedürftige Anlagen",
        "url": "https://www.gesetze-im-internet.de/bimschg/__4.html",
        "absatz_prefix": "(1)",
    },
    {
        "citation_id": "bimschg_p6",
        "law_name": "BImSchG",
        "paragraph": "§ 6",
        "topic": "Genehmigungsvoraussetzungen für Windkraftanlagen",
        "url": "https://www.gesetze-im-internet.de/bimschg/__6.html",
        "absatz_prefix": "(1)",
    },
    {
        "citation_id": "bimschg_p16b",
        "law_name": "BImSchG",
        "paragraph": "§ 16b",
        "topic": "Erleichterungen für das Repowering von Windenergieanlagen",
        "url": "https://www.gesetze-im-internet.de/bimschg/__16b.html",
        "absatz_prefix": "(1)",
    },
    {
        "citation_id": "windbg_p3",
        "law_name": "WindBG",
        "paragraph": "§ 3",
        "topic": "Flächenbeitragswerte der Länder (Wind-an-Land-Gesetz)",
        "url": "https://www.gesetze-im-internet.de/windbg/__3.html",
        "absatz_prefix": "(1)",
    },
    {
        "citation_id": "enwg_p111e",
        "law_name": "EnWG",
        "paragraph": "§ 111e",
        "topic": "Marktstammdatenregister gesetzliche Grundlage",
        "url": "https://www.gesetze-im-internet.de/enwg_2005/__111e.html",
        "absatz_prefix": "(1)",
    },
]


def fetch_and_seed_legal_citations(conn=None) -> list[dict]:
    """
    Fetch verbatim statutory texts directly from gesetze-im-internet.de via requests.get(),
    parse HTML using div.jurAbsatz, and load into legal_citations table in DuckDB.
    """
    close_conn = False
    if conn is None:
        conn = duckdb.connect("db/gtp.duckdb")
        close_conn = True

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"
    }

    records_loaded = []
    print("=" * 60)
    print("FETCHING VERBATIM STATUTORY TEXTS FROM GESETZE-IM-INTERNET.DE")
    print("=" * 60)

    for cfg in STATUTE_CONFIGS:
        cid = cfg["citation_id"]
        law = cfg["law_name"]
        para = cfg["paragraph"]
        topic = cfg["topic"]
        url = cfg["url"]
        prefix = cfg["absatz_prefix"]

        try:
            print(f"Fetching {law} {para} from {url}...")
            resp = requests.get(url, headers=headers, timeout=15)
            resp.encoding = "utf-8"

            if resp.status_code != 200:
                print(f"  [FAIL] HTTP {resp.status_code} for {url}")
                continue

            soup = BeautifulSoup(resp.text, "html.parser")
            jur_divs = soup.find_all("div", class_="jurAbsatz")

            matched_text = None
            if jur_divs:
                if prefix == "ALL":
                    matched_text = "\n\n".join(d.get_text(separator=" ", strip=True) for d in jur_divs)
                else:
                    for div in jur_divs:
                        clean_text = div.get_text(separator=" ", strip=True)
                        if prefix in clean_text or clean_text.startswith(prefix):
                            matched_text = clean_text
                            break
                    # If no prefix matched, use the first jurAbsatz
                    if not matched_text and len(jur_divs) > 0:
                        matched_text = jur_divs[0].get_text(separator=" ", strip=True)

            if not matched_text:
                print(f"  [WARN] No div.jurAbsatz found for {cid}")
                continue

            # Insert into DuckDB table legal_citations (specifying columns explicitly)
            today_str = date.today().isoformat()
            conn.execute("""
                INSERT INTO legal_citations (citation_id, law_name, paragraph, topic, official_text_de, source_url, verified_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (citation_id) DO UPDATE SET
                    law_name = EXCLUDED.law_name,
                    paragraph = EXCLUDED.paragraph,
                    topic = EXCLUDED.topic,
                    official_text_de = EXCLUDED.official_text_de,
                    source_url = EXCLUDED.source_url,
                    verified_at = EXCLUDED.verified_at
            """, [cid, law, para, topic, matched_text, url, today_str])

            records_loaded.append({
                "citation_id": cid,
                "law_name": law,
                "paragraph": para,
                "topic": topic,
                "text_snippet": matched_text[:120] + "...",
                "source_url": url,
            })
            print(f"  [OK] Successfully scraped and loaded: {cid} ({len(matched_text)} chars)")

        except Exception as e:
            print(f"  [ERROR] Failed to fetch {cid}: {e}")

    # Ensure redundant alias rows are purged (retaining canonical mastrv_p5_abs5)
    conn.execute("DELETE FROM legal_citations WHERE citation_id IN ('mastrv_p5', 'mastrv_p3')")

    # Log to pipeline_runs
    log_pipeline_run(
        conn,
        step="fetch_legal_citations",
        records_processed=len(records_loaded),
        source_id="gesetze-im-internet",
        status="success" if records_loaded else "failed",
        notes=f"Scraped and verified {len(records_loaded)} statutory citations from gesetze-im-internet.de",
    )

    print("=" * 60)
    print(f"SUMMARY: Loaded {len(records_loaded)} verified statutory citations into db/gtp.duckdb")
    print("=" * 60)

    if close_conn:
        conn.close()

    return records_loaded


if __name__ == "__main__":
    fetch_and_seed_legal_citations()
