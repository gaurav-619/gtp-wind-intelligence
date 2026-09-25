"""
pipeline/rag.py
RAG pipeline: chunk documents, embed with sentence-transformers,
store embeddings in DuckDB with VSS extension for similarity search.
"""

import os
import re
import glob
import duckdb
import numpy as np
from datetime import datetime
from pipeline.load import log_pipeline_run


# Lazy-load the sentence transformer model (downloads on first use)
_model = None


def _get_model():
    """Load the multilingual sentence transformer model (cached)."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        print("Loading sentence-transformers model (paraphrase-multilingual-MiniLM-L12-v2)...")
        _model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
        print("Model loaded.")
    return _model


def chunk_document(text: str, chunk_size: int = 500, overlap: int = 50) -> list:
    """
    Split text into overlapping chunks.
    - Splits into sentences first (on ". " and ".\\n")
    - Builds chunks by accumulating sentences until chunk_size words
    - Overlap: includes last `overlap` words from the previous chunk
    """
    if not text or not text.strip():
        return []

    # Split into sentences
    sentences = re.split(r"(?<=\.)\s+|\n+", text)
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        return [text]

    chunks = []
    current_words = []

    for sentence in sentences:
        words = sentence.split()
        current_words.extend(words)

        if len(current_words) >= chunk_size:
            chunk_text = " ".join(current_words)
            chunks.append(chunk_text)

            # Keep overlap words for next chunk
            if overlap > 0 and len(current_words) > overlap:
                current_words = current_words[-overlap:]
            else:
                current_words = []

    # Don't forget remaining words
    if current_words:
        chunk_text = " ".join(current_words)
        if chunks and len(current_words) < overlap:
            # Too short, append to last chunk
            chunks[-1] = chunks[-1] + " " + chunk_text
        else:
            chunks.append(chunk_text)

    return chunks


def embed_chunks(chunks: list) -> list:
    """
    Embed text chunks using the multilingual sentence transformer.
    Returns a list of embedding vectors (list of floats).
    """
    if not chunks:
        return []

    model = _get_model()
    embeddings = model.encode(chunks, normalize_embeddings=True)
    return embeddings.tolist()


def store_chunks(doc: dict, chunks: list, embeddings: list, conn) -> int:
    """
    Store document chunks and their embeddings in DuckDB.
    Returns the count of chunks stored.
    """
    source_id = doc["source_id"]
    document_url = doc.get("url", "")
    document_date = doc.get("date")
    date_str = str(document_date) if document_date else "unknown"

    # Ensure VSS extension is loaded for this connection
    try:
        conn.execute("LOAD vss;")
    except Exception:
        pass

    stored_count = 0

    for i, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
        chunk_id = f"{source_id}_{date_str}_{i}"

        try:
            conn.execute("""
                INSERT OR REPLACE INTO document_chunks VALUES (
                    ?, ?, ?, ?, ?, ?, ?::FLOAT[384], NOW()
                )
            """, [chunk_id, source_id, document_url, document_date,
                  i, chunk_text, embedding])
            stored_count += 1
        except Exception as e:
            print(f"  Error storing chunk {chunk_id}: {e}")

    return stored_count


def retrieve_relevant_chunks(query: str, source_id: str, conn,
                              top_k: int = 3) -> list:
    """
    Retrieve the most relevant chunks for a query using vector similarity.
    Returns a list of dicts with chunk_text, score, and document_url.
    """
    # Ensure VSS extension is loaded
    try:
        conn.execute("LOAD vss;")
    except Exception:
        pass

    model = _get_model()
    query_embedding = model.encode([query], normalize_embeddings=True).tolist()[0]

    try:
        results = conn.execute("""
            SELECT chunk_id, chunk_text, document_url, document_date,
                   array_cosine_similarity(embedding, ?::FLOAT[384]) as score
            FROM document_chunks
            WHERE source_id = ?
            ORDER BY score DESC
            LIMIT ?
        """, [query_embedding, source_id, top_k]).fetchdf()

        if results.empty:
            return []

        return results.to_dict("records")

    except Exception as e:
        print(f"  Similarity search error: {e}")
        # Fallback: return most recent chunks without similarity
        try:
            results = conn.execute("""
                SELECT chunk_id, chunk_text, document_url, document_date,
                       0.5 as score
                FROM document_chunks
                WHERE source_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, [source_id, top_k]).fetchdf()
            return results.to_dict("records") if not results.empty else []
        except Exception:
            return []


def process_document_for_rag(doc: dict, conn) -> int:
    """
    Full RAG pipeline for a single document:
    chunk → embed → store.
    Returns number of chunks stored.
    """
    text = doc.get("text", "")
    source_id = doc.get("source_id", "unknown")

    if not text:
        print(f"  No text to process for {source_id}")
        return 0

    # Chunk
    chunks = chunk_document(text)
    print(f"  Chunked into {len(chunks)} segments")

    if not chunks:
        return 0

    # Embed
    embeddings = embed_chunks(chunks)
    print(f"  Generated {len(embeddings)} embeddings")

    # Store
    stored = store_chunks(doc, chunks, embeddings, conn)
    print(f"  Stored {stored} chunks in database")

    # Log
    log_pipeline_run(conn, "rag_process", stored, source_id, "success",
                     f"Processed document: {len(chunks)} chunks, {len(text)} chars")

    return stored


if __name__ == "__main__":
    import pdfplumber

    conn = duckdb.connect("db/gtp.duckdb")

    # Process all downloaded press release PDFs
    pdf_files = glob.glob("data/raw/*_press*.pdf") + glob.glob("data/raw/*nordex*.pdf")

    if not pdf_files:
        print("No press release PDFs found in data/raw/")
        print("Run fetch_tier2.py first to download documents.")
    else:
        total_chunks = 0
        for pdf_path in pdf_files:
            print(f"\nProcessing {pdf_path}...")

            try:
                full_text = ""
                with pdfplumber.open(pdf_path) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            full_text += page_text + "\n\n"

                if full_text.strip():
                    doc = {
                        "source_id": "nordex_press",
                        "url": pdf_path,
                        "date": datetime.now().date(),
                        "text": full_text,
                    }
                    chunks = process_document_for_rag(doc, conn)
                    total_chunks += chunks
                else:
                    print(f"  No text extracted from {pdf_path}")

            except Exception as e:
                print(f"  Error processing {pdf_path}: {e}")

        print(f"\nTotal chunks stored: {total_chunks}")

    conn.close()
