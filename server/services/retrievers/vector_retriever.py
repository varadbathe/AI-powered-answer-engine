from typing import List, Optional
from pydantic_models.document_models import RetrievedChunk
from services.embedding_service import EmbeddingService
from services.retrievers.base_retriever import BaseRetriever
from services.vector_store_service import VectorStoreService


class VectorRetriever(BaseRetriever):
    """
    Dense vector retriever using local all-MiniLM-L6-v2 embeddings and ChromaDB.
    """

    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_store_service: VectorStoreService,
    ):
        self.embedding_service = embedding_service
        self.vector_store = vector_store_service

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        document_ids: Optional[List[str]] = None,
    ) -> List[RetrievedChunk]:
        """
        Embeds the query and queries ChromaDB for top-k similar chunks with optional document isolation.
        """
        if not query.strip():
            return []

        query_embedding = self.embedding_service.embed_query(query)
        raw_chunks = self.vector_store.query_similar(
            query_embedding=query_embedding,
            top_k=top_k,
            document_ids=document_ids,
        )

        return [RetrievedChunk(**c) for c in raw_chunks]
