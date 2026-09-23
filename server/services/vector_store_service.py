import os
from pathlib import Path
from typing import Any, List, Optional
import chromadb
from chromadb.config import Settings as ChromaSettings


class VectorStoreService:
    """
    Local ChromaDB vector store wrapper supporting persistent collection storage,
    batch addition of precomputed embeddings, deletion by document_id, and
    isolated vector querying.
    """

    def __init__(self, chroma_dir: str, collection_name: str = "documents"):
        self.chroma_dir = chroma_dir
        self.collection_name = collection_name
        Path(self.chroma_dir).mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(
            path=self.chroma_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add_chunks(self, chunks: List[dict[str, Any]], embeddings: List[List[float]]) -> None:
        """
        Adds document chunks and pre-calculated embeddings to ChromaDB.
        """
        if not chunks:
            return

        ids = [c["chunk_id"] for c in chunks]
        documents = [c["text"] for c in chunks]
        metadatas = [
            {
                "document_id": str(c["document_id"]),
                "document_name": str(c["document_name"]),
                "chunk_index": int(c["chunk_index"]),
                "page_number": int(c["page_number"]) if c.get("page_number") is not None else -1,
                "section_title": str(c.get("section_title") or ""),
                "evidence_id": str(c.get("evidence_id") or ""),
            }
            for c in chunks
        ]

        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,  # type: ignore[arg-type]
            metadatas=metadatas,  # type: ignore[arg-type]
            documents=documents,
        )

    def delete_document_chunks(self, document_id: str) -> None:
        """
        Deletes all chunks belonging to a document from ChromaDB.
        """
        try:
            self.collection.delete(where={"document_id": document_id})
        except Exception as e:
            print(f"Warning: Failed to delete chunks for doc {document_id}: {e}")

    def query_similar(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        document_ids: Optional[List[str]] = None,
    ) -> List[dict[str, Any]]:
        """
        Queries top-k similar chunks with optional document isolation filter.
        Computes relevance_score = 1.0 - cosine_distance.
        """
        total_count = self.collection.count()
        if total_count == 0:
            return []

        # Chroma requires n_results <= collection count
        n_results = min(top_k, total_count)

        where_clause: Optional[dict[str, Any]] = None
        if document_ids:
            clean_ids = [d for d in document_ids if d]
            if len(clean_ids) == 1:
                where_clause = {"document_id": clean_ids[0]}
            elif len(clean_ids) > 1:
                where_clause = {"document_id": {"$in": clean_ids}}

        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where_clause,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as e:
            print(f"Error querying vector store: {e}")
            return []

        retrieved: List[dict[str, Any]] = []
        ids_list = results.get("ids")
        if not results or not ids_list or not ids_list[0]:
            return []

        ids = ids_list[0]
        docs_list = results.get("documents")
        docs = docs_list[0] if docs_list is not None else []
        metas_list = results.get("metadatas")
        metas = metas_list[0] if metas_list is not None else []
        dist_list = results.get("distances")
        distances = dist_list[0] if dist_list is not None else []

        for i, chunk_id in enumerate(ids):
            meta = metas[i] if i < len(metas) else {}
            text = docs[i] if i < len(docs) else ""
            dist = distances[i] if i < len(distances) else 1.0

            # Cosine distance to similarity: 1.0 - distance
            score = max(0.0, min(1.0, round(1.0 - float(dist), 4)))

            page_num = meta.get("page_number")
            if page_num == -1:
                page_num = None

            section = meta.get("section_title")
            if not section:
                section = None

            retrieved.append({
                "chunk_id": chunk_id,
                "document_id": meta.get("document_id", ""),
                "document_name": meta.get("document_name", ""),
                "chunk_index": meta.get("chunk_index", 0),
                "page_number": page_num,
                "section_title": section,
                "evidence_id": meta.get("evidence_id", ""),
                "text": text,
                "relevance_score": score,
            })

        # Sort by relevance_score descending
        retrieved.sort(key=lambda x: x["relevance_score"], reverse=True)
        return retrieved
