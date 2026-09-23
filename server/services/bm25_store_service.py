import json
import math
import os
import re
from pathlib import Path
from typing import Any, List, Optional
import numpy as np
from rank_bm25 import BM25Okapi


def bm25_tokenize(text: str) -> List[str]:
    """
    Consistent tokenizer preserving technical terms, hyphens, and versioning:
    e.g. CYP3A4, IL-6, B12, COVID-19, GPT-5.6.
    """
    if not text:
        return []
    return re.findall(r"[A-Za-z0-9]+(?:[-._][A-Za-z0-9]+)*", text.lower())


class LuceneBM25(BM25Okapi):
    """
    BM25 with non-negative Lucene-style IDF smoothing:
    idf = log(1 + (N - n + 0.5) / (n + 0.5))
    Guarantees non-negative IDFs even on small corpora or test collections.
    """

    def _calc_idf(self, nd):
        for word, freq in nd.items():
            self.idf[word] = math.log(1.0 + (self.corpus_size - freq + 0.5) / (freq + 0.5))


class BM25StoreService:
    """
    Local BM25 lexical store service maintaining chunk texts and metadata.
    Provides deterministic local persistence (JSON), query scoring,
    document isolation, and safe index lifecycle management without pickle.
    """

    def __init__(self, persistence_dir: str):
        self.persistence_dir = Path(persistence_dir)
        self.persistence_dir.mkdir(parents=True, exist_ok=True)
        self.storage_file = self.persistence_dir / "bm25_chunks.json"

        self.chunks: List[dict[str, Any]] = []
        self.index: Optional[LuceneBM25] = None

        self._load()

    def _load(self) -> None:
        """Loads chunks from persistent JSON file and reconstructs BM25 index."""
        if self.storage_file.exists():
            try:
                with open(self.storage_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self.chunks = data
                        self._rebuild_index()
            except Exception as e:
                print(f"Warning: Failed to load BM25 store from {self.storage_file}: {e}")
                self.chunks = []
                self.index = None

    def _save(self) -> None:
        """Atomically saves chunks to persistent JSON file."""
        temp_file = self.persistence_dir / f"bm25_chunks.tmp_{os.getpid()}"
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(self.chunks, f, ensure_ascii=False, indent=2)
            temp_file.replace(self.storage_file)
        except Exception as e:
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception:
                    pass
            raise IOError(f"Failed to persist BM25 chunks to {self.storage_file}: {e}")

    def _rebuild_index(self) -> None:
        """Rebuilds the LuceneBM25 index from currently loaded chunks."""
        if not self.chunks:
            self.index = None
            return

        tokenized_corpus = [bm25_tokenize(c.get("text", "")) for c in self.chunks]
        self.index = LuceneBM25(tokenized_corpus)

    def add_chunks(self, chunks: List[dict[str, Any]]) -> None:
        """Adds new chunks, persists them, and updates the BM25 index."""
        if not chunks:
            return

        # Sanitize metadata fields
        sanitized = []
        for c in chunks:
            sanitized.append({
                "chunk_id": str(c["chunk_id"]),
                "document_id": str(c["document_id"]),
                "document_name": str(c["document_name"]),
                "chunk_index": int(c.get("chunk_index", 0)),
                "page_number": int(c["page_number"]) if c.get("page_number") is not None and c.get("page_number") != -1 else None,
                "section_title": str(c.get("section_title") or "") if c.get("section_title") else None,
                "evidence_id": str(c.get("evidence_id") or ""),
                "text": str(c.get("text", "")),
            })

        self.chunks.extend(sanitized)
        self._save()
        self._rebuild_index()

    def delete_document_chunks(self, document_id: str) -> None:
        """Removes all chunks belonging to document_id, persists, and rebuilds."""
        self.chunks = [c for c in self.chunks if str(c.get("document_id")) != str(document_id)]
        self._save()
        self._rebuild_index()

    def reindex_document_chunks(self, document_id: str, new_chunks: List[dict[str, Any]]) -> None:
        """Atomically replaces chunks for document_id with new_chunks."""
        retained = [c for c in self.chunks if str(c.get("document_id")) != str(document_id)]
        sanitized = []
        for c in new_chunks:
            sanitized.append({
                "chunk_id": str(c["chunk_id"]),
                "document_id": str(c["document_id"]),
                "document_name": str(c["document_name"]),
                "chunk_index": int(c.get("chunk_index", 0)),
                "page_number": int(c["page_number"]) if c.get("page_number") is not None and c.get("page_number") != -1 else None,
                "section_title": str(c.get("section_title") or "") if c.get("section_title") else None,
                "evidence_id": str(c.get("evidence_id") or ""),
                "text": str(c.get("text", "")),
            })

        self.chunks = retained + sanitized
        self._save()
        self._rebuild_index()

    def query(
        self,
        query: str,
        top_k: int = 5,
        document_ids: Optional[List[str]] = None,
    ) -> List[dict[str, Any]]:
        """
        Queries the BM25 index with optional document filtering.
        Returns matching chunks with BM25 scores.
        """
        if not self.chunks or self.index is None or not query.strip():
            return []

        tokens = bm25_tokenize(query)
        if not tokens:
            return []

        scores = self.index.get_scores(tokens)

        clean_doc_ids = set(str(d) for d in document_ids) if document_ids else None

        candidates = []
        for i, chunk in enumerate(self.chunks):
            if clean_doc_ids is not None and str(chunk.get("document_id")) not in clean_doc_ids:
                continue

            score = float(scores[i])
            if score <= 0.0:
                continue

            candidate = dict(chunk)
            candidate["relevance_score"] = round(score, 4)
            candidate["bm25_score"] = round(score, 4)
            candidates.append(candidate)

        # Sort descending by BM25 score
        candidates.sort(key=lambda x: x["relevance_score"], reverse=True)
        return candidates[:top_k]

    def count(self) -> int:
        return len(self.chunks)
