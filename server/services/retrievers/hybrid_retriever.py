import math
from typing import Any, Dict, List, Optional
from pydantic_models.document_models import RetrievedChunk
from services.retrievers.base_retriever import BaseRetriever
from services.retrievers.bm25_retriever import BM25Retriever
from services.retrievers.score_normalizer import ScoreNormalizer
from services.retrievers.vector_retriever import VectorRetriever


class HybridRetriever(BaseRetriever):
    """
    Hybrid retriever combining dense semantic retrieval (VectorRetriever)
    and lexical retrieval (BM25Retriever) with score normalization and weighted fusion.
    """

    def __init__(
        self,
        vector_retriever: VectorRetriever,
        bm25_retriever: BM25Retriever,
        vector_weight: float = 0.60,
        bm25_weight: float = 0.40,
        vector_candidate_k: int = 10,
        bm25_candidate_k: int = 10,
        final_top_k: int = 5,
    ):
        if not math.isclose(vector_weight + bm25_weight, 1.0, abs_tol=1e-5):
            raise ValueError(f"Vector weight ({vector_weight}) and BM25 weight ({bm25_weight}) must sum to 1.0")

        self.vector_retriever = vector_retriever
        self.bm25_retriever = bm25_retriever
        self.vector_weight = vector_weight
        self.bm25_weight = bm25_weight
        self.vector_candidate_k = vector_candidate_k
        self.bm25_candidate_k = bm25_candidate_k
        self.final_top_k = final_top_k

        # Development/Debug tracking of all candidates per turn
        self.last_debug_candidates: List[Dict[str, Any]] = []

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        document_ids: Optional[List[str]] = None,
    ) -> List[RetrievedChunk]:
        """
        Retrieves candidates from both retrievers, normalizes scores, fuses weights,
        deduplicates by chunk_id, and returns top-k ranked chunks.
        """
        self.last_debug_candidates = []
        k = top_k if top_k is not None else self.final_top_k

        if not query.strip():
            return []

        # 1. Retrieve candidates from both pools
        vector_candidates = self.vector_retriever.retrieve(
            query=query,
            top_k=self.vector_candidate_k,
            document_ids=document_ids,
        )

        bm25_candidates = self.bm25_retriever.retrieve(
            query=query,
            top_k=self.bm25_candidate_k,
            document_ids=document_ids,
        )

        if not vector_candidates and not bm25_candidates:
            return []

        # 2. Min-Max normalize vector candidates
        vector_map: Dict[str, tuple[RetrievedChunk, float, float]] = {}
        if vector_candidates:
            vec_scores = [c.relevance_score for c in vector_candidates]
            min_v = min(vec_scores)
            max_v = max(vec_scores)
            for c in vector_candidates:
                norm_v = ScoreNormalizer.normalize_single(c.relevance_score, min_v, max_v)
                raw_v = c.relevance_score
                vector_map[c.chunk_id] = (c, raw_v, norm_v)

        # 3. Min-Max normalize BM25 candidates
        bm25_map: Dict[str, tuple[RetrievedChunk, float, float]] = {}
        if bm25_candidates:
            b_scores = [c.relevance_score for c in bm25_candidates]
            min_b = min(b_scores)
            max_b = max(b_scores)
            for c in bm25_candidates:
                norm_b = ScoreNormalizer.normalize_single(c.relevance_score, min_b, max_b)
                raw_b = c.relevance_score
                bm25_map[c.chunk_id] = (c, raw_b, norm_b)

        # 4. Candidate union and deduplication by chunk_id
        all_chunk_ids = list(dict.fromkeys(list(vector_map.keys()) + list(bm25_map.keys())))
        fused_chunks: List[RetrievedChunk] = []

        for cid in all_chunk_ids:
            vec_entry = vector_map.get(cid)
            bm25_entry = bm25_map.get(cid)

            # Distinguish not retrieved vs retrieved with min normalized score
            vector_retrieved = vec_entry is not None
            bm25_retrieved = bm25_entry is not None

            raw_v = vec_entry[1] if vec_entry else None
            norm_v = vec_entry[2] if vec_entry else 0.0

            raw_b = bm25_entry[1] if bm25_entry else None
            norm_b = bm25_entry[2] if bm25_entry else 0.0

            # Base chunk metadata object from whichever retriever found it
            base_chunk = vec_entry[0] if vec_entry else bm25_entry[0]  # type: ignore

            # Weighted fusion formula
            hybrid_score = round(
                self.vector_weight * norm_v + self.bm25_weight * norm_b,
                4,
            )

            # Construct new RetrievedChunk copy with component and hybrid scores
            chunk_dict = base_chunk.model_dump()
            chunk_dict["relevance_score"] = hybrid_score
            chunk_dict["vector_score"] = raw_v
            chunk_dict["bm25_score"] = raw_b
            chunk_dict["normalized_vector_score"] = norm_v if vector_retrieved else None
            chunk_dict["normalized_bm25_score"] = norm_b if bm25_retrieved else None
            chunk_dict["hybrid_score"] = hybrid_score
            chunk_dict["vector_retrieved"] = vector_retrieved
            chunk_dict["bm25_retrieved"] = bm25_retrieved

            fused_chunk = RetrievedChunk(**chunk_dict)
            fused_chunks.append(fused_chunk)

            # Retain in debug candidate list
            self.last_debug_candidates.append({
                "chunk_id": fused_chunk.chunk_id,
                "document_id": fused_chunk.document_id,
                "document_name": fused_chunk.document_name,
                "vector_score": raw_v,
                "bm25_score": raw_b,
                "normalized_vector_score": norm_v if vector_retrieved else 0.0,
                "normalized_bm25_score": norm_b if bm25_retrieved else 0.0,
                "hybrid_score": hybrid_score,
                "vector_retrieved": vector_retrieved,
                "bm25_retrieved": bm25_retrieved,
            })

        # 5. Sort descending by hybrid_score (stable secondary sort by chunk_id)
        fused_chunks.sort(key=lambda x: (x.relevance_score, x.chunk_id), reverse=True)
        self.last_debug_candidates.sort(key=lambda x: (x["hybrid_score"], x["chunk_id"]), reverse=True)

        return fused_chunks[:k]
