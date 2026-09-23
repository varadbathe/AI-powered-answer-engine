import sys
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from config import Settings
from pydantic_models.conversation_models import (
    ConversationCreate,
    ConversationDetail,
    ConversationRename,
    ConversationSummary,
)
from repositories.conversation_repository import ConversationRepository
from repositories.document_repository import DocumentRepository
from routers.chat_router import router as chat_router, set_chat_services
from routers.document_router import router as document_router, set_document_service
from services.bm25_store_service import BM25StoreService
from services.conversation_service import ConversationService
from services.document_service import DocumentService
from services.embedding_service import EmbeddingService
from services.llm_service import LLMService
from services.rag_service import RagService
from services.retrievers.bm25_retriever import BM25Retriever
from services.retrievers.hybrid_retriever import HybridRetriever
from services.retrievers.retriever_factory import RetrieverFactory
from services.retrievers.vector_retriever import VectorRetriever
from services.search_service import SearchService
from services.sort_source_service import SortSourceService
from services.vector_store_service import VectorStoreService


# Ensure stdout and stderr use UTF-8 encoding on Windows to prevent UnicodeEncodeError with emojis/special characters
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8")  # type: ignore
    except Exception:
        pass

app = FastAPI(title="ResearchOS API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

settings = Settings()

# ---------------------------------------------------------
# Service Instantiations
# ---------------------------------------------------------
search_service = SearchService()
sort_source_service = SortSourceService()
llm_service = LLMService()

# Conversation services
conversation_repository = ConversationRepository(db_path=settings.DATABASE_PATH)
conversation_service = ConversationService(repository=conversation_repository)

# Document RAG services
document_repository = DocumentRepository(db_path=settings.DATABASE_PATH)
embedding_service = EmbeddingService()
vector_store_service = VectorStoreService(chroma_dir=settings.CHROMA_DIR)
bm25_store_service = BM25StoreService(persistence_dir=settings.BM25_DIR)

vector_retriever = VectorRetriever(
    embedding_service=embedding_service,
    vector_store_service=vector_store_service,
)
bm25_retriever = BM25Retriever(bm25_store=bm25_store_service)

active_retriever = RetrieverFactory.create_retriever(
    mode=settings.RETRIEVAL_MODE,
    vector_retriever=vector_retriever,
    bm25_retriever=bm25_retriever,
    vector_weight=settings.HYBRID_VECTOR_WEIGHT,
    bm25_weight=settings.HYBRID_BM25_WEIGHT,
    vector_candidate_k=settings.HYBRID_VECTOR_CANDIDATE_K,
    bm25_candidate_k=settings.HYBRID_BM25_CANDIDATE_K,
    final_top_k=settings.HYBRID_FINAL_TOP_K,
)

document_service = DocumentService(
    repository=document_repository,
    vector_store=vector_store_service,
    embedding_service=embedding_service,
    bm25_store=bm25_store_service,
    uploads_dir=settings.UPLOADS_DIR,
    chunk_size=settings.DEFAULT_CHUNK_SIZE,
    chunk_overlap=settings.DEFAULT_CHUNK_OVERLAP,
)
rag_service = RagService(
    retriever=active_retriever,
    debug_mode=settings.RAG_DEBUG,
    relevance_threshold=settings.RAG_RELEVANCE_THRESHOLD,
)

# Inject services into routers
set_document_service(document_service)
set_chat_services(
    search_service=search_service,
    sort_source_service=sort_source_service,
    llm_service=llm_service,
    conversation_service=conversation_service,
    rag_service=rag_service,
    vector_retriever=vector_retriever,
    bm25_retriever=bm25_retriever,
)


# Register routers
app.include_router(document_router)
app.include_router(chat_router)


# ---------------------------------------------------------
# Conversation Management REST Endpoints
# ---------------------------------------------------------

@app.get("/api/conversations", response_model=list[ConversationSummary])
def list_conversations(limit: int = 50, offset: int = 0):
    return conversation_service.list_conversations(limit=limit, offset=offset)


@app.post("/api/conversations", response_model=ConversationSummary)
def create_conversation(body: ConversationCreate):
    return conversation_service.create_conversation(title=body.title, conversation_id=body.id)


@app.get("/api/conversations/{conversation_id}", response_model=ConversationDetail)
def get_conversation(conversation_id: str):
    detail = conversation_service.get_conversation_detail(conversation_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return detail


@app.patch("/api/conversations/{conversation_id}", response_model=ConversationSummary)
def rename_conversation(conversation_id: str, body: ConversationRename):
    updated = conversation_service.rename_conversation(conversation_id, body.title)
    if not updated:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return updated


@app.delete("/api/conversations/{conversation_id}")
def delete_conversation(conversation_id: str):
    deleted = conversation_service.delete_conversation(conversation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"status": "deleted", "id": conversation_id}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=False)
