from abc import ABC, abstractmethod
from typing import Any, List, Optional
from pydantic_models.document_models import RetrievedChunk


class BaseRetriever(ABC):
    """
    Abstract interface for document chunk retrieval.
    Phase 3 will add BM25Retriever and HybridRetriever implementing this interface.
    """

    @abstractmethod
    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        document_ids: Optional[List[str]] = None,
    ) -> List[RetrievedChunk]:
        """
        Retrieves top-k relevant chunks for the query, optionally isolated to document_ids.
        """
        pass
