from typing import List
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic_models.document_models import (
    DocumentDetail,
    DocumentListResponse,
    DocumentSummary,
)
from services.document_parser import CorruptedDocumentError, DocumentParserError, EmptyDocumentError
from services.document_security import (
    CorruptedFileError,
    DocumentSecurityError,
    FileTooLargeError,
    UnsupportedFileError,
)
from services.document_service import DocumentService, DuplicateDocumentError

router = APIRouter(prefix="/api/documents", tags=["documents"])

# Global service instance will be injected from main.py
_document_service: DocumentService | None = None


def get_document_service() -> DocumentService:
    if _document_service is None:
        raise RuntimeError("DocumentService has not been initialized.")
    return _document_service


def set_document_service(service: DocumentService) -> None:
    global _document_service
    _document_service = service


@router.post("", response_model=DocumentDetail, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    service: DocumentService = Depends(get_document_service),
):
    """
    Upload and ingest a document (.pdf, .docx, .txt, .md).
    Validates file, performs SHA-256 duplicate detection, extracts text,
    chunks, embeds with all-MiniLM-L6-v2, and indexes into ChromaDB.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename cannot be empty")

    try:
        content = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read uploaded file: {e}")

    try:
        doc = service.upload_and_ingest(filename=file.filename, file_bytes=content)
        return doc
    except DuplicateDocumentError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": str(e),
                "existing_document": e.existing_document,
            },
        )
    except UnsupportedFileError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except (FileTooLargeError, CorruptedFileError, EmptyDocumentError, CorruptedDocumentError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except (DocumentSecurityError, DocumentParserError) as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document ingestion failed: {str(e)}",
        )


@router.get("", response_model=List[DocumentSummary])
def list_documents(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    service: DocumentService = Depends(get_document_service),
):
    """
    Lists all documents sorted by updated_at descending.
    """
    return service.list_documents(limit=limit, offset=offset)


@router.get("/{document_id}", response_model=DocumentDetail)
def get_document(
    document_id: str,
    service: DocumentService = Depends(get_document_service),
):
    """
    Retrieves full metadata for a single document.
    """
    doc = service.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document '{document_id}' not found")
    return doc


@router.delete("/{document_id}")
def delete_document(
    document_id: str,
    service: DocumentService = Depends(get_document_service),
):
    """
    Deletes a document from SQLite, ChromaDB, and disk storage.
    """
    deleted = service.delete_document(document_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Document '{document_id}' not found")
    return {"status": "deleted", "id": document_id}


@router.post("/{document_id}/reindex", response_model=DocumentDetail)
def reindex_document(
    document_id: str,
    service: DocumentService = Depends(get_document_service),
):
    """
    Re-indexes an existing document from its original file on disk.
    Deletes old chunks from ChromaDB and creates fresh chunks and embeddings.
    """
    try:
        updated = service.reindex_document(document_id)
        return updated
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Re-indexing failed: {str(e)}",
        )
