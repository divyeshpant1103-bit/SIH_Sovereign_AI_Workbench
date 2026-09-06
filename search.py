"""
Hybrid retrieval: meaning-based search + exact keyword search, fused.

Usage:
    python search.py "what is the action limit for bearing vibration"

Import from other code:
    from search import Retriever
    r = Retriever()
    result = r.search("...")
    if result.refused: ...
    for ev in result.evidence: print(ev.doc, ev.page_label, ev.text)

Why hybrid: refinery documents are full of equipment tags and standard codes
(P-101-A, SOP-PMP-114, NPSHR). Meaning-based search alone misses exact tokens.
Keyword search alone misses paraphrases. We need both.
"""

import pickle
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

INDEX_DIR = Path("data/index")
MODEL_NAME = "BAAI/bge-small-en-v1.5"

# bge-v1.5 models are trained with this prefix on the query side only.
# Leaving it out measurably hurts retrieval.
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

CANDIDATES = 20      # from each of the two searches, before fusion
TOP_K = 5            # what we hand to the model
RRF_K = 60           # standard reciprocal rank fusion constant
REFUSE_BELOW = 0.68  # cosine similarity of the best dense hit


@dataclass
class Evidence:
    id: str
    doc: str
    page_label: str
    pdf_page: int
    text: str
    score: float

    def cite(self) -> str:
        return f"{self.doc}, {self.page_label}"


@dataclass
class SearchResult:
    query: str
    evidence: list = field(default_factory=list)
    refused: bool = False
    reason: str = ""
    top_score: float = 0.0


def tokenize(text: str):
    return re.findall(r"[a-z0-9][a-z0-9\-\.]*", text.lower())


class Retriever:
    def __init__(self, index_dir: Path = INDEX_DIR):
        vec_path = index_dir / "vectors.npy"
        chunk_path = index_dir / "chunks.pkl"

        if not vec_path.exists():
            raise FileNotFoundError(
                f"No index at {index_dir.resolve()}. Run 'python ingest.py' first."
            )

        self.vectors = np.load(vec_path)
        with open(chunk_path, "rb") as f:
            self.chunks = pickle.load(f)

        self.model = SentenceTransformer(MODEL_NAME, device="cpu")
        self.bm25 = BM25Okapi([tokenize(c["text"]) for c in self.chunks])

    def _dense(self, query: str, n: int):
        q = self.model.encode(
            [QUERY_PREFIX + query], normalize_embeddings=True
        )[0].astype("float32")
        scores = self.vectors @ q          # vectors are normalized, so this is cosine
        idx = np.argsort(-scores)[:n]
        return [(int(i), float(scores[i])) for i in idx]

    def _sparse(self, query: str, n: int):
        scores = self.bm25.get_scores(tokenize(query))
        idx = np.argsort(-scores)[:n]
        return [(int(i), float(scores[i])) for i in idx]

    def search(self, query: str, top_k: int = TOP_K) -> SearchResult:
        dense = self._dense(query, CANDIDATES)
        sparse = self._sparse(query, CANDIDATES)

        best_cosine = dense[0][1] if dense else 0.0

        # Refusal gate. This is a feature, demo it deliberately.
        if best_cosine < REFUSE_BELOW:
            return SearchResult(
                query=query,
                refused=True,
                reason=(
                    "No sufficiently relevant passage found in the knowledge base. "
                    f"Best match scored {best_cosine:.2f}, below the {REFUSE_BELOW} threshold."
                ),
                top_score=best_cosine,
            )

        # Reciprocal rank fusion: combine two rankings without needing
        # their scores to be on the same scale.
        fused = {}
        for rank, (i, _) in enumerate(dense):
            fused[i] = fused.get(i, 0.0) + 1.0 / (RRF_K + rank + 1)
        for rank, (i, _) in enumerate(sparse):
            fused[i] = fused.get(i, 0.0) + 1.0 / (RRF_K + rank + 1)

        cosine_by_idx = dict(dense)
        ordered = sorted(fused.items(), key=lambda kv: -kv[1])[:top_k]

        evidence = []
        for i, fusion_score in ordered:
            c = self.chunks[i]
            evidence.append(Evidence(
                id=c["id"],
                doc=c["doc"],
                page_label=c["page_label"],
                pdf_page=c["pdf_page"],
                text=c["text"],
                score=cosine_by_idx.get(i, fusion_score),
            ))

        return SearchResult(
            query=query, evidence=evidence, top_score=best_cosine
        )


def main():
    if len(sys.argv) < 2:
        print('Usage: python search.py "your question here"')
        return

    query = " ".join(sys.argv[1:])
    r = Retriever()
    result = r.search(query)

    print(f"\nQuery: {query}")
    print("=" * 70)

    if result.refused:
        print("REFUSED")
        print(result.reason)
        return

    for n, ev in enumerate(result.evidence, 1):
        print(f"\n[{n}] {ev.cite()}   (score {ev.score:.3f})")
        print("-" * 70)
        body = ev.text[:420]
        print(body + ("..." if len(ev.text) > 420 else ""))


if __name__ == "__main__":
    main()