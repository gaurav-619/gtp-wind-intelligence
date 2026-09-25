"""
pipeline/extract_claims.py
Extract structured facts from document chunks using an LLM.
Tries Ollama first (local), falls back to OpenRouter (cloud).
Validates extracted claims against plausibility rules.
"""

import os
import re
import json
import yaml
import duckdb
import requests
from datetime import datetime
from dotenv import load_dotenv
from pipeline.load import log_pipeline_run
from pipeline.rag import retrieve_relevant_chunks

load_dotenv()


# --------------------------------------------------------------------------
# Extraction schema: what metrics to look for in press releases
# --------------------------------------------------------------------------
EXTRACTION_SCHEMA = {
    "order_intake_mw": {
        "description": "Total new orders received in megawatts",
        "german_terms": ["Auftragseingang", "Neuaufträge", "Bestelleingang"],
        "unit": "MW",
        "plausible_range": (0, 5000),
    },
    "capacity_installed_mw": {
        "description": "Total capacity commissioned in megawatts",
        "german_terms": ["Installierte Leistung", "Errichtete Leistung",
                         "Inbetriebnahme", "errichtet"],
        "unit": "MW",
        "plausible_range": (0, 3000),
    },
    "revenue_eur_millions": {
        "description": "Total revenue in EUR millions",
        "german_terms": ["Umsatz", "Erlöse", "Gesamtumsatz"],
        "unit": "EUR_M",
        "plausible_range": (0, 10000),
    },
}


# --------------------------------------------------------------------------
# LLM call: Ollama first, OpenRouter fallback
# --------------------------------------------------------------------------

def call_llm(prompt: str) -> tuple[str, str]:
    """
    Call an LLM to extract structured data.
    Tries Ollama (local) first, falls back to OpenRouter (cloud) with multiple fallback models.
    Returns (response_text, model_name).
    """
    # Attempt 1: Ollama (local)
    try:
        model = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=60,
        )
        if response.status_code == 200:
            result = response.json().get("response", "")
            print(f"  [LLM] Used Ollama ({model})")
            return result, model
    except Exception as e:
        print(f"  [LLM] Ollama unavailable: {e}")

    # Attempt 2: OpenRouter (cloud fallback)
    api_key = os.getenv("OPENROUTER_API_KEY")

    if not api_key or api_key == "your_key_here":
        raise ValueError(
            "No OPENROUTER_API_KEY set and Ollama unavailable. "
            "Set OPENROUTER_API_KEY in .env or install Ollama."
        )

    primary_model = os.getenv("OPENROUTER_MODEL", "inclusionai/ling-3.0-flash-fin:free")
    candidate_models = [
        primary_model,
        "liquid/lfm-2.5-2.6b:free",
        "qwen/qwen3.8-27b:free",
    ]
    # Remove duplicates while preserving order
    seen = set()
    candidate_models = [m for m in candidate_models if not (m in seen or seen.add(m))]

    last_error = None
    for model in candidate_models:
        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key.strip()}",
                    "HTTP-Referer": "https://github.com/gtp-wind",
                    "X-Title": "GTP Wind Intelligence",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=30,
            )
            data = response.json()
            if response.status_code == 200 and "choices" in data and data["choices"]:
                result = data["choices"][0]["message"]["content"]
                print(f"  [LLM] Used OpenRouter ({model})")
                return result, model
            else:
                err_msg = data.get("error", {}).get("message", f"HTTP {response.status_code}")
                print(f"  [LLM] OpenRouter model {model} failed: {err_msg}")
                last_error = err_msg
        except Exception as e:
            print(f"  [LLM] OpenRouter model {model} error: {e}")
            last_error = str(e)

    raise ValueError(f"Both Ollama and all OpenRouter models failed. Last error: {last_error}")


# --------------------------------------------------------------------------
# Prompt building
# --------------------------------------------------------------------------

# Regex matching German and English hedge, approximation, and estimation keywords
HEDGE_REGEX = re.compile(
    r"\b(rund|vorl(?:ä|ae)ufig\w*|gesch(?:ä|ae)tzt\w*|sch(?:ä|ae)tzung\w*|circa|ca\.?|etwa|ungef(?:ä|ae)hr\w*|preliminary|estimated|approx(?:imately)?|around|about)\b",
    re.IGNORECASE
)


def detect_hedge_language(text: str) -> bool:
    """Detect German or English hedge, approximation, and estimation keywords."""
    if not text:
        return False
    return bool(HEDGE_REGEX.search(text))


def build_extraction_prompt(chunks: list, metric: str, schema: dict) -> str:
    """
    Build a structured extraction prompt for the LLM.
    """
    combined_text = "\n\n".join([c.get("chunk_text", "") for c in chunks])

    prompt = f"""You are extracting structured data from a German wind energy press release.

Extract this specific metric if present:
Metric: {metric}
Description: {schema['description']}
Unit: {schema['unit']}
German terms to look for: {', '.join(schema['german_terms'])}

Return ONLY a valid JSON object with exactly these fields:
{{
  "found": true or false,
  "value": numeric value as integer or float (or null),
  "period": the time period (e.g. "Q1-2024") or null,
  "source_sentence_de": "the exact original German sentence containing the value",
  "source_sentence_en": "your English translation of that sentence",
  "confidence": a float between 0 and 1,
  "is_preliminary": true or false
}}

Rules:
1. German formatting uses dots for thousands and commas for decimals (e.g. 1.680 MW is 1680 MW; 0,89 is 0.89). Convert to standard JSON number.
2. If the metric is not mentioned or no clear value exists, return {{"found": false}}.
3. Do not invent values. Only extract what is explicitly stated in the text.
4. Output raw JSON only. Do not add markdown commentary or extra text outside the JSON.
5. Confidence scoring tiers:
   - Tier 1 (Definitive, exact figure): If a single specific, finalized numeric value is stated (e.g. "Auftragseingang von 1.680 MW"), confidence must be 0.85-1.0 and is_preliminary: false.
   - Tier 2 (Preliminary / Hedged figure): If a specific numeric value is present but explicitly qualified by hedge or estimate language (e.g. "rund 1.700 MW", "vorläufig", "geschätzt", "circa", "etwa"), confidence must be 0.55-0.65 and is_preliminary: true.
   - Tier 3 (No isolated value / Range / General discussion): If you cannot isolate one exact number (e.g. the source gives a range like "1.500 bis 1.800 MW", an estimate without a number, or no figure at all), set "value": null, "confidence": 0.0-0.2, and is_preliminary: false.

Text to extract from:
{combined_text}"""

    return prompt


# --------------------------------------------------------------------------
# Claim validation
# --------------------------------------------------------------------------

def validate_claim(result: dict, schema: dict, full_text: str) -> bool:
    """
    Validate an extracted claim against plausibility rules.
    Returns True only if ALL checks pass.
    """
    # Hard enforcement: confidence must be 0.0 if no definitive value exists or not found
    if not result.get("found", False) or result.get("value") is None:
        result["confidence"] = 0.0
        result["is_preliminary"] = False
        return False

    value = result.get("value")
    if isinstance(value, str):
        try:
            cleaned_val = value.strip().replace(" ", "")
            if "." in cleaned_val and "," in cleaned_val:
                cleaned_val = cleaned_val.replace(".", "").replace(",", ".")
            elif "." in cleaned_val and len(cleaned_val.split(".")[-1]) == 3:
                cleaned_val = cleaned_val.replace(".", "")
            else:
                cleaned_val = cleaned_val.replace(",", ".")
            value = float(cleaned_val)
            result["value"] = value
        except Exception:
            result["confidence"] = 0.0
            result["is_preliminary"] = False
            return False

    if value is None or not isinstance(value, (int, float)) or value <= 0:
        result["confidence"] = 0.0
        result["is_preliminary"] = False
        return False

    low, high = schema["plausible_range"]
    if value < low or value > high:
        return False

    source_de = result.get("source_sentence_de", "")
    source_en = result.get("source_sentence_en", "")
    if not source_de or not source_de.strip():
        return False

    # At least one German term must appear in the full text (case-insensitive)
    text_lower = full_text.lower()
    term_found = any(term.lower() in text_lower for term in schema["german_terms"])
    if not term_found:
        return False

    confidence = result.get("confidence", 0)
    if isinstance(confidence, str):
        try:
            confidence = float(confidence)
        except Exception:
            confidence = 0.0

    if not isinstance(confidence, (int, float)):
        confidence = 0.0

    # Hedge language detection
    is_hedged = (
        detect_hedge_language(source_de) or
        detect_hedge_language(source_en) or
        bool(result.get("is_preliminary", False))
    )

    # 3-Tier Confidence & Preliminary Flag Enforcement:
    # Tier 2: Real specific value present, but hedged with preliminary wording
    if is_hedged:
        result["is_preliminary"] = True
        # Set / clamp confidence to mid-range (0.55-0.60) so it passes validation (> 0.5)
        # and enters extracted_claims for human review rather than being discarded
        if not (0.50 < confidence <= 0.65):
            result["confidence"] = 0.55
        else:
            result["confidence"] = round(confidence, 2)
    else:
        result["is_preliminary"] = False
        result["confidence"] = confidence

    # Rejection threshold: claims with confidence <= 0.5 are rejected
    if result["confidence"] <= 0.5:
        return False

    return True


# --------------------------------------------------------------------------
# Legal & Regulatory Citation Verification Layer
# --------------------------------------------------------------------------

CITATION_REGEX = re.compile(
    r"(§+\s*\d+[a-z]?(?:\s*(?:Absatz|Abs\.)\s*\d+)?(?:\s*(?:Satz|S\.)\s*\d+)?)\s+([A-Za-zÄÖÜäöü\-]+(?:\s+\d{4})?)",
    re.IGNORECASE
)


def detect_legal_citations(text: str) -> list[dict]:
    """
    Detect regulatory and statutory citations in text using regex.
    Catches patterns like '§ 5 Absatz 5 MaStRV', '§ 5 MaStRV', '§ 4 EEG 2023', '§ 4 BImSchG'.
    """
    if not text:
        return []

    matches = []
    for m in CITATION_REGEX.finditer(text):
        raw_match = m.group(0).strip()
        para_part = m.group(1).strip()
        law_part = m.group(2).strip()

        # Normalize base paragraph, e.g. "§ 5 Absatz 1" -> "§ 5"
        base_para = re.match(r"(§+\s*\d+[a-z]?)", para_part)
        norm_para = base_para.group(1).replace(" ", "") if base_para else para_part
        if norm_para.startswith("§") and not norm_para.startswith("§ "):
            norm_para = "§ " + norm_para.lstrip("§")

        matches.append({
            "raw_text": raw_match,
            "paragraph_full": para_part,
            "paragraph": norm_para,
            "law_name": law_part,
            "start": m.start(),
            "end": m.end()
        })
    return matches


def validate_legal_citation(citation: dict, conn=None) -> tuple[bool, dict | None]:
    """
    Validate a detected legal citation against the authoritative legal_citations table.
    Never auto-passes: must match an authentic row in legal_citations.
    Returns (is_valid, record_or_none).
    """
    close_conn = False
    if conn is None:
        conn = duckdb.connect("db/gtp.duckdb", read_only=True)
        close_conn = True

    try:
        law = citation.get("law_name", "")
        para = citation.get("paragraph", "")

        row = conn.execute("""
            SELECT citation_id, law_name, paragraph, topic, official_text_de, source_url, verified_at
            FROM legal_citations
            WHERE (law_name ILIKE ? OR law_name ILIKE ?)
              AND paragraph = ?
        """, [law, f"{law}%", para]).fetchone()

        if row:
            record = {
                "citation_id": row[0],
                "law_name": row[1],
                "paragraph": row[2],
                "topic": row[3],
                "official_text_de": row[4],
                "source_url": row[5],
                "verified_at": str(row[6]),
            }
            return True, record
        else:
            return False, None
    finally:
        if close_conn:
            conn.close()


def verify_and_annotate_text_citations(text: str, conn=None, replace_inline: bool = True) -> tuple[str, list[dict], int]:
    """
    Scan text for legal citations, validate against legal_citations table,
    and flag/replace unverified citations inline with '[UNVERIFIED CITATION - needs manual check]'.
    Logs step='citation_check' to pipeline_runs table.
    Returns (annotated_text, results, n_unverified).
    """
    citations = detect_legal_citations(text)
    if not citations:
        return text, [], 0

    close_conn = False
    if conn is None:
        conn = duckdb.connect("db/gtp.duckdb")
        close_conn = True

    try:
        results = []
        n_unverified = 0

        # Replace in reverse order of appearance to maintain string character offsets
        annotated_text = text
        for cit in sorted(citations, key=lambda x: x["start"], reverse=True):
            is_valid, matched_record = validate_legal_citation(cit, conn)
            item = {
                "citation_text": cit["raw_text"],
                "paragraph": cit["paragraph"],
                "law_name": cit["law_name"],
                "is_verified": is_valid,
                "matched_record": matched_record,
            }
            results.append(item)

            if not is_valid:
                n_unverified += 1
                if replace_inline:
                    annotated_text = (
                        annotated_text[:cit["start"]] +
                        f"{cit['raw_text']} [UNVERIFIED CITATION - needs manual check]" +
                        annotated_text[cit["end"]:]
                    )

        results.reverse()

        # Log to pipeline_runs
        log_pipeline_run(
            conn,
            step="citation_check",
            records_processed=len(citations),
            source_id="legal_citations",
            status="success" if n_unverified == 0 else "flagged",
            notes=f"{n_unverified} unverified citations found in report",
        )

        return annotated_text, results, n_unverified
    finally:
        if close_conn:
            conn.close()

def extract_claims_from_document(doc: dict, conn) -> list:
    """
    Extract all defined metrics from a document's chunks.
    Returns a list of successfully extracted and validated claims.
    """
    source_id = doc.get("source_id", "unknown")
    company = doc.get("company", "Unknown")
    document_url = doc.get("url", "")
    full_text = doc.get("text", "")

    extracted = []

    for metric, schema in EXTRACTION_SCHEMA.items():
        print(f"\n  Extracting: {metric}...")

        try:
            # Retrieve relevant chunks via similarity search
            chunks = retrieve_relevant_chunks(
                schema["description"], source_id, conn, top_k=3
            )

            if not chunks:
                print(f"    No relevant chunks found for {metric}")
                continue

            # Build prompt and call LLM
            prompt = build_extraction_prompt(chunks, metric, schema)
            llm_response, used_model = call_llm(prompt)

            # Parse JSON response (handle malformed JSON)
            result = _parse_json_response(llm_response)

            if result is None:
                print(f"    Could not parse LLM response for {metric}")
                continue

            # Validate
            if validate_claim(result, schema, full_text):
                period = result.get("period", "unknown")
                claim_id = f"{source_id}_{metric}_{period}"
                chunk_id = chunks[0].get("chunk_id", None) if chunks else None

                source_de = result.get("source_sentence_de", "")
                source_en = result.get("source_sentence_en", "")

                # Scan and verify legal citations in source sentences
                source_de_annotated, _, n_unverified_de = verify_and_annotate_text_citations(
                    source_de, conn, replace_inline=True
                )
                source_en_annotated, _, n_unverified_en = verify_and_annotate_text_citations(
                    source_en, conn, replace_inline=True
                )

                claim_confidence = result.get("confidence", 0.0)
                if n_unverified_de > 0 or n_unverified_en > 0:
                    claim_confidence = min(claim_confidence, 0.4)

                is_preliminary = bool(result.get("is_preliminary", False))

                # Store in extracted_claims
                conn.execute("""
                    INSERT OR REPLACE INTO extracted_claims VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NOW(), ?,
                        FALSE, NULL, ?, ?
                    )
                """, [
                    claim_id, source_id, company, metric, period,
                    result["value"], schema["unit"],
                    source_de_annotated,
                    source_en_annotated,
                    document_url, chunk_id, used_model,
                    claim_confidence,
                    is_preliminary
                ])

                extracted.append({
                    "claim_id": claim_id,
                    "metric": metric,
                    "value": result["value"],
                    "period": period,
                    "confidence": claim_confidence,
                    "is_preliminary": is_preliminary,
                })

                print(f"    ✓ Found: {result['value']} {schema['unit']} ({period})")
            else:
                print(f"    ✗ Validation failed for {metric}")

        except Exception as e:
            print(f"    Error extracting {metric}: {e}")

    # Log results
    log_pipeline_run(conn, "extract_claims", len(extracted), source_id,
                     "success" if extracted else "no_claims",
                     f"Extracted {len(extracted)} claims from {company}")

    print(f"\n  Summary for {company}: {len(extracted)} claims extracted")
    return extracted


def _parse_json_response(response: str) -> dict:
    """Parse JSON from LLM response, handling common formatting issues."""
    if not response:
        return None

    # 1. First look for ```json ... ``` code fence
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response, re.DOTALL)
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except json.JSONDecodeError:
            pass

    # 2. Direct parse
    try:
        return json.loads(response.strip())
    except json.JSONDecodeError:
        pass

    # 3. Find outermost { ... }
    first_brace = response.find("{")
    last_brace = response.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        candidate = response[first_brace:last_brace + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    return None


if __name__ == "__main__":
    with open("config/tier2_sources.yaml") as f:
        config = yaml.safe_load(f)

    conn = duckdb.connect("db/gtp.duckdb")

    for source in config["sources"]:
        source_id = source["source_id"]
        company = source["company"]

        print(f"\n{'=' * 60}")
        print(f"Extracting claims for {company} (source: {source_id})")
        print(f"{'=' * 60}")

        # Check if we have any chunks for this source
        chunk_count = conn.execute("""
            SELECT COUNT(*) FROM document_chunks WHERE source_id = ?
        """, [source_id]).fetchone()[0]

        if chunk_count == 0:
            print(f"No document chunks found for {source_id}. "
                  f"Run the RAG pipeline first.")
            continue

        # Get the full text from chunks for validation
        chunks_df = conn.execute("""
            SELECT chunk_text FROM document_chunks 
            WHERE source_id = ? ORDER BY chunk_index
        """, [source_id]).fetchdf()

        full_text = "\n".join(chunks_df["chunk_text"].tolist())

        doc = {
            "source_id": source_id,
            "company": company,
            "url": "",
            "text": full_text,
        }

        claims = extract_claims_from_document(doc, conn)
        print(f"\nTotal claims for {company}: {len(claims)}")

    conn.close()
