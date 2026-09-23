from typing import Optional
from services.retrievers.base_retriever import BaseRetriever
from services.retrievers.bm25_retriever import BM25Retriever
from services.retrievers.hybrid_retriever import HybridRetriever
from services.retrievers.vector_retriever import VectorRetriever


class RetrieverFactory:
    """
    Factory resolving the appropriate BaseRetriever instance based on mode.
    Supported modes: 'vector', 'bm25', 'hybrid'.
    """

    @staticmethod
    def create_retriever(
        mode: str = "hybrid",
        vector_retriever: Optional[VectorRetriever] = None,
        bm25_retriever: Optional[BM25Retriever] = None,
        vector_weight: float = 0.60,
        bm25_weight: float = 0.40,
        vector_candidate_k: int = 10,
        bm25_candidate_k: int = 10,
        final_top_k: int = 5,
    ) -> BaseRetriever:
        clean_mode = (mode or "hybrid").lower().strip()

        if clean_mode == "vector":
            if vector_retriever is None:
                raise ValueError("vector_retriever is required for mode 'vector'")
            return vector_retriever

        elif clean_mode == "bm25":
            if bm25_retriever is None:
                raise ValueError("bm25_retriever is required for mode 'bm25'")
            return bm25_retriever

        elif clean_mode == "hybrid":
            if vector_retriever is None or bm25_retriever is None:
                raise ValueError("Both vector_retriever and bm25_retriever are required for mode 'hybrid'")
            return HybridRetriever(
                vector_retriever=vector_retriever,
                bm25_retriever=bm25_retriever,
                vector_weight=vector_weight,
                bm25_weight=bm25_weight,
                vector_candidate_k=vector_candidate_k,
                bm25_candidate_k=bm25_candidate_k,
                final_top_k=final_top_k,
            )
        else:
            raise ValueError(f"Unknown retrieval mode: '{mode}'. Supported modes are: 'vector', 'bm25', 'hybrid'")
