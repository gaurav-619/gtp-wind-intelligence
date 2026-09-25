"""
pipeline/translate_legal_citations.py
Automated statutory machine translation via DeepL API (free tier: api-free.deepl.com).
Translates official German statutory texts (official_text_de) to official_text_en,
applies a domain terminology glossary validation layer, runs back-translation diff checking,
and enforces translation_verified = FALSE until confirmed by human auditor.
"""

import os
import json
import difflib
import requests
import duckdb
from dotenv import load_dotenv
from pipeline.load import log_pipeline_run

env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path=env_path)
load_dotenv()

DEEPL_ENDPOINT = "https://api-free.deepl.com/v2/translate"

# Strict domain glossary for German energy/wind legal terminology
LEGAL_ENERGY_GLOSSARY = {
    "Einheiten": ["unit", "units"],
    "Inbetriebnahme": ["commissioning", "put into operation", "putting into operation", "commencement of operation", "operation"],
    "Marktstammdatenregister": ["core energy market data register", "market master data register", "market master data registry", "MaStR", "master data register"],
    "EEG-Anlagen": ["EEG installations", "EEG plants", "EEG systems", "EEG facilities", "renewable energy installations"],
    "KWK-Anlagen": ["CHP plants", "cogeneration plants", "CHP installations", "combined heat and power"],
    "Genehmigung": ["permit", "authorization", "approval", "licence", "license"],
    "Repowering": ["repowering", "re-powering"],
    "Ausbaupfade": ["expansion targets", "expansion pathways", "expansion paths", "expansion trajectories"],
    "Flächenbeitragswerte": ["area contribution values", "land contribution values", "area contribution quotas"],
    "Bundes-Immissionsschutzgesetz": ["Federal Immission Control Act", "BImSchG"],
    "Bundesnetzagentur": ["Federal Network Agency", "Federal Network"],
}


def translate_with_deepl(text: str, source_lang: str = "DE", target_lang: str = "EN-US", api_key: str = None) -> str:
    """
    Direct machine translation call to DeepL free-tier API.
    Zero generative LLM paraphrasing — stores raw MT output.
    """
    if not api_key:
        api_key = os.getenv("DEEPL_API_KEY")

    if not api_key or api_key == "your_deepl_api_key_here":
        raise ValueError(
            "DEEPL_API_KEY is not configured. Please set a valid DeepL API Free key "
            "in your .env file (e.g. DEEPL_API_KEY=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx:fx)."
        )

    headers = {
        "Authorization": f"DeepL-Auth-Key {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "GTP-Wind-Intelligence/1.0",
    }
    payload = {
        "text": [text],
        "source_lang": source_lang.upper(),
        "target_lang": target_lang.upper(),
    }

    resp = requests.post(DEEPL_ENDPOINT, headers=headers, json=payload, timeout=20)
    if resp.status_code != 200:
        raise RuntimeError(f"DeepL API returned HTTP {resp.status_code}: {resp.text}")

    data = resp.json()
    translations = data.get("translations", [])
    if not translations or "text" not in translations[0]:
        raise ValueError(f"Unexpected response structure from DeepL API: {data}")

    return translations[0]["text"]


def validate_legal_glossary(text_de: str, text_en: str) -> list[dict]:
    """
    Validation layer: checks if mandatory German statutory terms in text_de
    are correctly represented by approved domain translations in text_en.
    Returns list of terminology warnings/violations.
    """
    violations = []
    text_de_lower = text_de.lower()
    text_en_lower = text_en.lower()

    for de_term, approved_en_list in LEGAL_ENERGY_GLOSSARY.items():
        if de_term.lower() in text_de_lower:
            matched = any(en_term.lower() in text_en_lower for en_term in approved_en_list)
            if not matched:
                violations.append({
                    "german_term": de_term,
                    "expected_english_any_of": approved_en_list,
                    "status": "unmatched_in_translation",
                })
    return violations


def back_translate_and_diff(text_de: str, text_en: str, api_key: str = None) -> tuple[str, float, list[str]]:
    """
    Validation layer: Back-translates the DeepL EN output back to DE (EN -> DE)
    and computes character/word similarity against the original official_text_de.
    Returns (back_translation_de, similarity_score, unified_diff_lines).
    """
    back_de = translate_with_deepl(text_en, source_lang="EN", target_lang="DE", api_key=api_key)
    
    # Calculate SequenceMatcher ratio
    matcher = difflib.SequenceMatcher(None, text_de.strip(), back_de.strip())
    similarity_ratio = round(matcher.ratio(), 4)

    # Generate unified diff lines
    diff = list(difflib.unified_diff(
        text_de.strip().splitlines(keepends=True),
        back_de.strip().splitlines(keepends=True),
        fromfile="official_text_de",
        tofile="deepl_back_translated_de",
        n=1
    ))

    return back_de, similarity_ratio, diff


def translate_all_legal_citations(conn=None, api_key: str = None, run_back_translation: bool = True) -> list[dict]:
    """
    Processes all rows in legal_citations:
    1. Fetches official_text_de
    2. Calls DeepL API for translation to official_text_en
    3. Runs terminology glossary check
    4. Runs back-translation check
    5. Saves raw DeepL output, keeps translation_verified = FALSE
    """
    close_conn = False
    if conn is None:
        conn = duckdb.connect("db/gtp.duckdb")
        close_conn = True

    # Ensure schema has translation columns
    conn.execute("ALTER TABLE legal_citations ADD COLUMN IF NOT EXISTS official_text_en VARCHAR")
    conn.execute("ALTER TABLE legal_citations ADD COLUMN IF NOT EXISTS translation_verified BOOLEAN DEFAULT FALSE")
    conn.execute("ALTER TABLE legal_citations ADD COLUMN IF NOT EXISTS translation_model VARCHAR")
    conn.execute("ALTER TABLE legal_citations ADD COLUMN IF NOT EXISTS back_translation_de VARCHAR")
    conn.execute("ALTER TABLE legal_citations ADD COLUMN IF NOT EXISTS back_translation_similarity DOUBLE")
    conn.execute("ALTER TABLE legal_citations ADD COLUMN IF NOT EXISTS glossary_violations VARCHAR")

    rows = conn.execute("""
        SELECT citation_id, law_name, paragraph, topic, official_text_de 
        FROM legal_citations 
        ORDER BY citation_id
    """).fetchall()

    print("=" * 70)
    print("DEEPL MACHINE TRANSLATION PIPELINE FOR LEGAL CITATIONS")
    print("=" * 70)
    print(f"Found {len(rows)} provisions to translate. DeepL Endpoint: {DEEPL_ENDPOINT}")

    results = []
    for r in rows:
        cid, law, para, topic, text_de = r
        print(f"\nProcessing {cid} ({law} {para})...")
        try:
            # 1. Forward MT (DE -> EN)
            raw_en = translate_with_deepl(text_de, source_lang="DE", target_lang="EN-US", api_key=api_key)
            print(f"  [OK] DeepL EN translation received ({len(raw_en)} chars)")

            # 2. Terminology Glossary Validation
            violations = validate_legal_glossary(text_de, raw_en)
            if violations:
                print(f"  [WARN] Glossary validation warnings ({len(violations)} terms):")
                for v in violations:
                    print(f"         - '{v['german_term']}' expected one of: {v['expected_english_any_of']}")
            else:
                print("  [OK] Glossary check passed (100% domain terminology compliance)")

            # 3. Back-Translation & Diff Check
            back_de = None
            sim_score = None
            if run_back_translation:
                back_de, sim_score, diff = back_translate_and_diff(text_de, raw_en, api_key=api_key)
                print(f"  [OK] Back-translation similarity: {sim_score * 100:.1f}%")

            # 4. Store in DuckDB (Strictly FALSE for translation_verified)
            conn.execute("""
                UPDATE legal_citations
                SET official_text_en = ?,
                    translation_verified = FALSE,
                    translation_model = 'DeepL-API-Free',
                    back_translation_de = ?,
                    back_translation_similarity = ?,
                    glossary_violations = ?
                WHERE citation_id = ?
            """, [
                raw_en,
                back_de,
                sim_score,
                json.dumps(violations, ensure_ascii=False) if violations else "[]",
                cid
            ])

            results.append({
                "citation_id": cid,
                "law_name": law,
                "paragraph": para,
                "official_text_en": raw_en,
                "glossary_violations": violations,
                "back_translation_similarity": sim_score,
                "translation_verified": False,
            })

        except Exception as e:
            print(f"  [ERROR] Translation failed for {cid}: {e}")

    # Log to pipeline_runs
    log_pipeline_run(
        conn,
        step="legal_citation_deepl_translation",
        records_processed=len(results),
        source_id="deepl_api_free",
        status="success" if results else "warning",
        notes=f"Translated {len(results)}/{len(rows)} provisions using DeepL API. All translation_verified=FALSE pending human audit."
    )

    print("\n" + "=" * 70)
    print(f"COMPLETED: {len(results)}/{len(rows)} provisions translated and validated.")
    print("All rows set to translation_verified = FALSE awaiting human confirmation.")
    print("=" * 70)

    if close_conn:
        conn.close()

    return results


if __name__ == "__main__":
    translate_all_legal_citations()
