import os
from pathlib import Path
from typing import Any, List, Optional
from config import Settings
from pydantic_models.document_models import DocumentDetail, DocumentStatus, DocumentSummary
from repositories.document_repository import DocumentRepository
from services.document_chunker import DocumentChunker
from services.document_parser import DocumentParser, DocumentParserError, EmptyDocumentError
from services.document_security import (
    DocumentSecurityError,
    DocumentSecurityService,
)
from services.embedding_service import EmbeddingService
from services.vector_store_service import VectorStoreService

settings = Settings()


class DuplicateDocumentError(Exception):
    def __init__(self, message: str, existing_document: dict[str, Any]):
        super().__init__(message)
        self.existing_document = existing_document


class DocumentService:
    """
    Coordinates document ingestion pipeline, duplicate detection, metadata tracking,
    re-indexing, and deletion.
    """

    def __init__(
        self,
        repository: DocumentRepository,
        vector_store: VectorStoreService,
        embedding_service: EmbeddingService,
        uploads_dir: Optional[str] = None,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
    ):
        self.repository = repository
        self.vector_store = vector_store
        self.embedding_service = embedding_service
        self.uploads_dir = Path(uploads_dir or settings.UPLOADS_DIR)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.chunk_size = chunk_size or settings.DEFAULT_CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.DEFAULT_CHUNK_OVERLAP

    def list_documents(self, limit: int = 100, offset: int = 0) -> list[DocumentSummary]:
        """Lists documents sorted by updated_at descending."""
        rows = self.repository.list_documents(limit=limit, offset=offset)
        return [DocumentSummary(**r) for r in rows]

    def count_documents(self) -> int:
        return self.repository.count_documents()

    def get_document(self, document_id: str) -> Optional[DocumentDetail]:
        """Retrieves a document by ID."""
        row = self.repository.get_document_by_id(document_id)
        if not row:
            return None
        return DocumentDetail(**row)

    def upload_and_ingest(
        self,
        filename: str,
        file_bytes: bytes,
    ) -> DocumentDetail:
        """
        Executes full ingestion pipeline:
        1. Duplicate detection via SHA-256 hash.
        2. File validation & sanitization.
        3. Local file persistence.
        4. State machine: UPLOADING -> PROCESSING -> CHUNKING -> EMBEDDING -> INDEXING -> READY.
        """
        # 1. Compute SHA-256 hash
        file_hash = DocumentSecurityService.calculate_sha256(file_bytes)

        # 2. Check for duplicate document
        existing = self.repository.get_document_by_hash(file_hash)
        if existing and existing.get("status") == DocumentStatus.READY.value:
            raise DuplicateDocumentError(
                f"Document with identical content already exists: '{existing.get('filename')}'",
                existing_document=existing,
            )

        # 3. Security validation & filename sanitization
        sanitized_filename, file_type = DocumentSecurityService.validate_file(
            filename=filename,
            file_bytes=file_bytes,
            max_size_mb=settings.MAX_FILE_SIZE_MB,
        )

        # 4. Generate server-side document ID
        document_id = DocumentSecurityService.generate_document_id()
        storage_filename = f"{document_id}_{sanitized_filename}"
        storage_path = str(self.uploads_dir / storage_filename)

        # Save file to disk
        with open(storage_path, "wb") as f:
            f.write(file_bytes)

        # 5. Insert initial record in SQLite
        doc_record = self.repository.create_document(
            document_id=document_id,
            filename=sanitized_filename,
            file_type=file_type,
            file_size=len(file_bytes),
            file_hash=file_hash,
            storage_path=storage_path,
            status=DocumentStatus.UPLOADING.value,
            progress=0.1,
        )

        try:
            # 6. PROCESSING: Parse and extract text per page/section
            self.repository.update_status(document_id, DocumentStatus.PROCESSING.value, 0.3)
            segments = DocumentParser.parse(file_bytes=file_bytes, file_type=file_type)

            # 7. CHUNKING: Sentence- and paragraph-aware chunking preserving page boundaries
            self.repository.update_status(document_id, DocumentStatus.CHUNKING.value, 0.5)
            chunks = DocumentChunker.chunk_document(
                segments=segments,
                document_id=document_id,
                document_name=sanitized_filename,
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
            )

            if not chunks:
                raise EmptyDocumentError("No text chunks could be generated from document")

            # 8. EMBEDDING: Generate local all-MiniLM-L6-v2 embeddings
            self.repository.update_status(document_id, DocumentStatus.EMBEDDING.value, 0.7)
            chunk_texts = [c["text"] for c in chunks]
            embeddings = self.embedding_service.embed_texts(chunk_texts)

            # 9. INDEXING: Store chunks and vectors into ChromaDB
            self.repository.update_status(document_id, DocumentStatus.INDEXING.value, 0.9)
            self.vector_store.add_chunks(chunks=chunks, embeddings=embeddings)

            # 10. READY: Ingestion complete
            updated = self.repository.update_metadata(
                document_id=document_id,
                chunk_count=len(chunks),
                status=DocumentStatus.READY.value,
                progress=1.0,
            )
            return DocumentDetail(**(updated or {}))

        except Exception as e:
            # Transition to FAILED status
            self.repository.update_status(
                document_id=document_id,
                status=DocumentStatus.FAILED.value,
                progress=0.0,
                error_message=str(e),
            )
            raise

    def reindex_document(self, document_id: str) -> DocumentDetail:
        """
        Re-indexes an existing document from its stored file on disk:
        1. Deletes old chunks from ChromaDB.
        2. Re-parses, re-chunks, re-embeds, and updates ChromaDB and SQLite.
        """
        doc = self.repository.get_document_by_id(document_id)
        if not doc:
            raise FileNotFoundError(f"Document {document_id} not found")

        storage_path = doc["storage_path"]
        if not os.path.exists(storage_path):
            raise FileNotFoundError(f"Stored file not found on disk at {storage_path}")

        with open(storage_path, "rb") as f:
            file_bytes = f.read()

        file_type = doc["file_type"]
        filename = doc["filename"]

        try:
            # Delete old chunks from ChromaDB
            self.vector_store.delete_document_chunks(document_id)

            # Ingestion steps
            self.repository.update_status(document_id, DocumentStatus.PROCESSING.value, 0.3)
            segments = DocumentParser.parse(file_bytes=file_bytes, file_type=file_type)

            self.repository.update_status(document_id, DocumentStatus.CHUNKING.value, 0.5)
            chunks = DocumentChunker.chunk_document(
                segments=segments,
                document_id=document_id,
                document_name=filename,
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
            )

            if not chunks:
                raise EmptyDocumentError("No text chunks generated during re-indexing")

            self.repository.update_status(document_id, DocumentStatus.EMBEDDING.value, 0.7)
            chunk_texts = [c["text"] for c in chunks]
            embeddings = self.embedding_service.embed_texts(chunk_texts)

            self.repository.update_status(document_id, DocumentStatus.INDEXING.value, 0.9)
            self.vector_store.add_chunks(chunks=chunks, embeddings=embeddings)

            updated = self.repository.update_metadata(
                document_id=document_id,
                chunk_count=len(chunks),
                status=DocumentStatus.READY.value,
                progress=1.0,
            )
            return DocumentDetail(**(updated or {}))

        except Exception as e:
            self.repository.update_status(
                document_id=document_id,
                status=DocumentStatus.FAILED.value,
                progress=0.0,
                error_message=str(e),
            )
            raise

    def delete_document(self, document_id: str) -> bool:
        """
        Deletes document from SQLite, ChromaDB, and disk storage.
        """
        doc = self.repository.get_document_by_id(document_id)
        if not doc:
            return False

        # 1. Delete chunks from ChromaDB
        self.vector_store.delete_document_chunks(document_id)

        # 2. Delete file from disk
        storage_path = doc.get("storage_path")
        if storage_path and os.path.exists(storage_path):
            try:
                os.remove(storage_path)
            except Exception as e:
                print(f"Warning: Failed to remove file {storage_path}: {e}")

        # 3. Delete record from SQLite
        return self.repository.delete_document(document_id)
