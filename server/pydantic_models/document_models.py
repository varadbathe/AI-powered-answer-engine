from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class DocumentStatus(str, Enum):
    UPLOADING = "UPLOADING"
    PROCESSING = "PROCESSING"
    CHUNKING = "CHUNKING"
    EMBEDDING = "EMBEDDING"
    INDEXING = "INDEXING"
    READY = "READY"
    FAILED = "FAILED"


class DocumentSummary(BaseModel):
    document_id: str
    filename: str
    file_type: str
    file_size: int
    file_hash: str
    status: DocumentStatus
    progress: float = 0.0
    error_message: str | None = None
    created_at: str
    updated_at: str
    chunk_count: int = 0


class DocumentDetail(DocumentSummary):
    storage_path: str


class DocumentListResponse(BaseModel):
    documents: list[DocumentSummary]
    total: int


class ChunkMetadata(BaseModel):
    chunk_id: str
    document_id: str
    document_name: str
    chunk_index: int
    page_number: int | None = None
    section_title: str | None = None
    evidence_id: str
    text: str


class RetrievedChunk(ChunkMetadata):
    relevance_score: float = 0.0


class CitationItem(BaseModel):
    evidence_id: str
    filename: str
    page_number: int | None = None
    section_title: str | None = None
    relevance_score: float = 0.0


class RagDebugInfo(BaseModel):
    retrieved_chunks: list[dict[str, Any]]
    retrieval_scores: list[float]
    document_ids: list[str]
    page_numbers: list[int | None]
    final_context_prompt: str
