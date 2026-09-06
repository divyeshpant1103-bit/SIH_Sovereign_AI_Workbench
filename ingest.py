"""
Ingest PDFs into a searchable index.

Usage:
    python ingest.py

Reads every PDF in data/corpus/, extracts text page by page, pulls tables out
separately so their row structure survives, splits into chunks, embeds on CPU,
and saves to data/index/.

No vector database. For a few hundred chunks a numpy array is faster and has
fewer moving parts.
"""

import pickle
import re
from pathlib import Path

import numpy as np
import pymupdf
from sentence_transformers import SentenceTransformer

CORPUS_DIR = Path("data/corpus")
INDEX_DIR = Path("data/index")
MODEL_NAME = "BAAI/bge-small-en-v1.5"

CHUNK_WORDS = 320
OVERLAP_WORDS = 50
MIN_CHARS_PER_PAGE = 100


def clean(text):
    text = text.replace("\u00ad", "")
    text = re.sub(r"-\n(\w)", r"\1", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{2,}", "\n", text)
    return text.strip()


def page_label(page, fallback):
    text = page.get_text()
    m = re.search(r"(ME-\d\d|CH-\d\d|IC-\d\d)\s+.*?Page\s+(\d+)", text, re.S)
    if m:
        return f"{m.group(1)} p.{m.group(2)}"
    m = re.search(r"Page\s+(\d+)\s+(ME-\d\d|CH-\d\d|IC-\d\d)", text)
    if m:
        return f"{m.group(2)} p.{m.group(1)}"
    return f"p.{fallback}"


def table_text(page):
    """
    Pull tables out separately. Plain text extraction flattens a table into a
    word soup, which separates row labels from their numbers. Keeping each row
    on one line means 'Bearing vibration | 4.5 mm/s | 7.1 mm/s' stays together.
    """
    lines = []
    try:
        for tbl in page.find_tables():
            for row in tbl.extract():
                cells = [c.strip() for c in row if c and c.strip()]
                if cells:
                    lines.append(" | ".join(cells))
    except Exception:
        return ""
    if not lines:
        return ""
    return "\n\nTABLE:\n" + "\n".join(lines)


def chunk_words(words, size, overlap):
    step = size - overlap
    for start in range(0, max(len(words), 1), step):
        piece = words[start:start + size]
        if len(piece) < 30 and start > 0:
            break
        yield " ".join(piece)


def extract(pdf_path):
    if pdf_path.suffix == ".txt":
      text = pdf_path.read_text(encoding="utf-8")
      words = text.split()
      return [
           {"id": f"{pdf_path.stem}#0#{j}", "doc": pdf_path.stem,
            "pdf_page": 1, "page_label": "Section 2", "text": body}
           for j, body in enumerate(chunk_words(words, CHUNK_WORDS, OVERLAP_WORDS))
      ]
    doc = pymupdf.open(pdf_path)
    chunks = []
    skipped_pages = 0

    for i, page in enumerate(doc):
        raw = page.get_text()
        if len(raw.strip()) < MIN_CHARS_PER_PAGE:
            skipped_pages += 1
            continue

        text = clean(raw) + table_text(page)
        label = page_label(page, i + 1)
        words = text.split()

        for j, body in enumerate(chunk_words(words, CHUNK_WORDS, OVERLAP_WORDS)):
            chunks.append({
                "id": f"{pdf_path.stem}#{i}#{j}",
                "doc": pdf_path.stem,
                "pdf_page": i + 1,
                "page_label": label,
                "text": body,
            })

    doc.close()
    if skipped_pages:
        print(f"    {skipped_pages} page(s) had no text layer (scanned or blank) - skipped")
    return chunks


def main():
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    pdfs = sorted(CORPUS_DIR.glob("*.pdf")) + sorted(CORPUS_DIR.glob("*.txt"))

    if not pdfs:
        print(f"No PDFs found in {CORPUS_DIR.resolve()}")
        return

    all_chunks = []
    for pdf in pdfs:
        print(f"Reading {pdf.name}")
        got = extract(pdf)
        print(f"    {len(got)} chunks")
        all_chunks.extend(got)

    if not all_chunks:
        print("No text extracted. Are these scanned PDFs?")
        return

    print(f"\nTotal: {len(all_chunks)} chunks from {len(pdfs)} documents")
    print(f"Loading embedding model ({MODEL_NAME})")

    model = SentenceTransformer(MODEL_NAME, device="cpu")

    print("Embedding on CPU")
    vectors = model.encode(
        [c["text"] for c in all_chunks],
        batch_size=32,
        show_progress_bar=True,
        normalize_embeddings=True,
    )

    np.save(INDEX_DIR / "vectors.npy", vectors.astype("float32"))
    with open(INDEX_DIR / "chunks.pkl", "wb") as f:
        pickle.dump(all_chunks, f)

    print(f"\nSaved to {INDEX_DIR.resolve()}")
    print(f"  vectors.npy  shape {vectors.shape}")
    print(f"  chunks.pkl   {len(all_chunks)} chunks")


if __name__ == "__main__":
    main()