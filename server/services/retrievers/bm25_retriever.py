from typing import List, Optional
from pydantic_models.document_models import RetrievedChunk
from services.bm25_store_service import BM25StoreService
from services.retrievers.base_retriever import BaseRetriever


class BM25Retriever(BaseRetriever):
    """
    Lexical BM25 retriever utilizing BM25StoreService.
    Conforms to the BaseRetriever interface.
    """

    def __init__(self, bm25_store: BM25StoreService):
        self.bm25_store = bm25_store

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        document_ids: Optional[List[str]] = None,
    ) -> List[RetrievedChunk]:
        """
        Retrieves top-k lexical matches using BM25 with optional document isolation.
        """
        if not query.strip():
            return []

        raw_chunks = self.bm25_store.query(
            query=query,
            top_k=top_k,
            document_ids=document_ids,
        )

        results: List[RetrievedChunk] = []
        for c in raw_chunks:
            chunk = RetrievedChunk(**c)
            chunk.bm25_score = c.get("bm25_score", chunk.relevance_score)
            chunk.bm25_retrieved = True
            results.append(chunk)

        return results
