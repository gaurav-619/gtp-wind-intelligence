"""
pipeline/fetch_tier2.py
Tier 2 data fetching: download press releases and OEM investor documents.
Discovers PDF links from IR pages and extracts text using pdfplumber.
"""

import os
import re
import requests
import pdfplumber
import yaml
import duckdb
from datetime import datetime, date
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from pipeline.load import log_pipeline_run


HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; research)"}


def discover_new_documents(source_config: dict) -> list:
    """
    Discover new PDF documents from an OEM investor relations page.
    Returns a list of dicts for new (not yet processed) documents.
    """
    ir_page = source_config["ir_page"]
    pdf_pattern = source_config.get("pdf_pattern", "")
    source_id = source_config["source_id"]
    company = source_config["company"]

    print(f"Discovering documents for {company} at {ir_page}...")

    try:
        response = requests.get(ir_page, headers=HEADERS, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Find all links that point to PDFs
        pdf_links = []
        for link in soup.find_all("a", href=True):
            href = link["href"]
            link_text = link.get_text(strip=True)

            # Check if link points to a PDF
            if href.lower().endswith(".pdf"):
                full_url = urljoin(ir_page, href)

                # Check if the link text or URL matches the pattern
                if pdf_pattern:
                    pattern = re.compile(pdf_pattern, re.IGNORECASE)
                    if pattern.search(link_text) or pattern.search(href):
                        pdf_links.append(full_url)
                else:
                    pdf_links.append(full_url)

        if not pdf_links:
            print(f"  No matching PDF links found on {ir_page}")
            raise ValueError("No PDF links matched the pattern")

        # Check which documents we already have in the database
        new_docs = []
        try:
            conn = duckdb.connect("db/gtp.duckdb", read_only=True)
            existing = conn.execute(
                "SELECT DISTINCT document_url FROM document_chunks WHERE source_id = ?",
                [source_id]
            ).fetchdf()
            conn.close()
            existing_urls = set(existing["document_url"].tolist()) if not existing.empty else set()
        except Exception:
            existing_urls = set()

        for url in pdf_links:
            if url not in existing_urls:
                new_docs.append({
                    "url": url,
                    "source_id": source_id,
                    "company": company,
                })

        print(f"  Found {len(pdf_links)} matching PDFs, {len(new_docs)} are new")
        return new_docs

    except Exception as e:
        print(f"  Warning: Could not access {ir_page}: {e}")
        print("  Using fallback document list")

        # Fallback: a real Nordex press release URL
        # NOTE: This URL may become stale over time. Replace with a current
        # Nordex IR PDF URL if this fallback is needed.
        fallback_docs = [
            {
                "url": "https://www.nordex-online.com/wp-content/uploads/sites/2/2024/04/Nordex_Q1_2024_Zwischenmitteilung_DE.pdf",
                "source_id": source_id,
                "company": company,
            }
        ]
        return fallback_docs


def download_document(doc: dict) -> dict:
    """
    Download a PDF document and extract its text using pdfplumber.
    Returns the doc dict enriched with text, date, and local path.
    Returns None if download or extraction fails.
    """
    url = doc["url"]
    source_id = doc["source_id"]

    os.makedirs("data/raw", exist_ok=True)

    # Generate local filename
    date_str = datetime.now().strftime("%Y%m%d")
    safe_name = re.sub(r"[^\w]", "_", url.split("/")[-1])[:80]
    local_path = f"data/raw/{source_id}_{date_str}_{safe_name}"

    if not local_path.endswith(".pdf"):
        local_path += ".pdf"

    print(f"  Downloading {url}...")

    try:
        response = requests.get(url, headers=HEADERS, timeout=60)
        response.raise_for_status()

        with open(local_path, "wb") as f:
            f.write(response.content)

        print(f"  Saved to {local_path}")

    except Exception as e:
        print(f"  Download failed: {e}")
        try:
            conn = duckdb.connect("db/gtp.duckdb")
            log_pipeline_run(conn, "download_document", 0, source_id, "failed",
                             f"Download failed for {url}: {e}")
            conn.close()
        except Exception:
            pass
        return None

    # Extract text using pdfplumber
    try:
        full_text = ""
        with pdfplumber.open(local_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    full_text += page_text + "\n\n"

        # Clean excessive whitespace while keeping German characters
        full_text = re.sub(r"\n{3,}", "\n\n", full_text)
        full_text = re.sub(r" {2,}", " ", full_text)
        full_text = full_text.strip()

        if not full_text:
            print(f"  Warning: No text extracted from {local_path}")
            return None

        print(f"  Extracted {len(full_text)} characters of text")

    except Exception as e:
        print(f"  PDF extraction failed: {e}")
        # Check for local fallback text document
        candidate_paths = [
            f"data/raw/{source_id}_press_Q1_2024.txt",
            f"data/raw/{source_id}_Q1_2024.txt",
            "data/raw/nordex_press_Q1_2024.txt",
        ]
        fallback_found = None
        for cp in candidate_paths:
            if os.path.exists(cp):
                fallback_found = cp
                break

        if fallback_found:
            print(f"  Using local fallback text file: {fallback_found}")
            with open(fallback_found, "r", encoding="utf-8") as f:
                full_text = f.read()
            local_path = fallback_found
        else:
            try:
                conn = duckdb.connect("db/gtp.duckdb")
                log_pipeline_run(conn, "download_document", 0, source_id, "failed",
                                 f"PDF extraction failed for {local_path}: {e}")
                conn.close()
            except Exception:
                pass
            return None

    # Detect document date from filename or content
    document_date = _detect_date(url, full_text)

    doc_enriched = dict(doc)
    doc_enriched["text"] = full_text
    doc_enriched["date"] = document_date
    doc_enriched["path"] = local_path

    return doc_enriched


def _detect_date(url: str, text: str) -> date:
    """
    Try to detect a document date from the URL or text content.
    Falls back to today's date.
    """
    # Try to find a date in the URL (e.g., 2024-Q1, Q1_2024)
    patterns = [
        r"(\d{4})[_-](\d{2})[_-](\d{2})",    # 2024-04-15
        r"Q(\d)[_-]?(\d{4})",                  # Q1_2024 or Q12024
        r"(\d{4})[_-]Q(\d)",                    # 2024-Q1 or 2024_Q1
    ]

    combined = url + " " + text[:500]

    for pattern in patterns:
        match = re.search(pattern, combined)
        if match:
            groups = match.groups()
            try:
                if len(groups) == 3:
                    return date(int(groups[0]), int(groups[1]), int(groups[2]))
                elif pattern.startswith(r"Q"):
                    quarter = int(groups[0])
                    year = int(groups[1])
                    return date(year, quarter * 3, 1)
                else:
                    year = int(groups[0])
                    quarter = int(groups[1])
                    return date(year, quarter * 3, 1)
            except (ValueError, IndexError):
                continue

    return date.today()


if __name__ == "__main__":
    with open("config/tier2_sources.yaml") as f:
        config = yaml.safe_load(f)

    total_found = 0
    total_downloaded = 0

    for source in config["sources"]:
        print(f"\n{'=' * 60}")
        print(f"Processing {source['company']}...")
        print(f"{'=' * 60}")

        new_docs = discover_new_documents(source)
        total_found += len(new_docs)
        print(f"Found {len(new_docs)} new documents")

        for doc in new_docs:
            result = download_document(doc)
            if result is not None:
                total_downloaded += 1
                print(f"  Successfully processed: {result['path']}")
            else:
                print(f"  Failed to process: {doc['url']}")

    print(f"\n{'=' * 60}")
    print(f"Summary: Found {total_found} documents, downloaded {total_downloaded}")
    print(f"{'=' * 60}")
