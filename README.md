# ⚡ ResearchOS

[![Flutter](https://img.shields.io/badge/Flutter-02569B?style=for-the-badge&logo=flutter&logoColor=white)](https://flutter.dev/)
[![Dart](https://img.shields.io/badge/Dart-0175C2?style=for-the-badge&logo=dart&logoColor=white)](https://dart.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Google Gemini](https://img.shields.io/badge/Google_Gemini-8E75B2?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev/)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-FF6600?style=for-the-badge&logo=databricks&logoColor=white)](https://www.trychroma.com/)
[![BM25](https://img.shields.io/badge/BM25_Lexical-007ACC?style=for-the-badge&logo=elastic&logoColor=white)](https://pypi.org/project/rank-bm25/)
[![Sentence Transformers](https://img.shields.io/badge/Sentence--Transformers-FFD21E?style=for-the-badge&logo=huggingface&logoColor=black)](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)
[![SQLite](https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![WebSockets](https://img.shields.io/badge/WebSockets-010101?style=for-the-badge&logo=socket.io&logoColor=white)](https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

**ResearchOS** is a full-stack, real-time conversational answer and generative research engine. It features dual operating modes:

1. **🌐 Live Web Search Mode**: Live web grounding via Tavily, local semantic vector re-ranking (`all-MiniLM-L6-v2`), conversational query contextualization, streaming generative answers with multi-model fallback cascades, and automated follow-up suggestions.
2. **📚 Document RAG & Hybrid Retrieval Engine (Phases 2 & 3)**: Full multi-format document management (`.pdf`, `.docx`, `.txt`, `.md`), SHA-256 duplicate detection, page/section-aware chunking, **dense semantic retrieval** (ChromaDB) fused with **lexical retrieval** (BM25 with technical term preservation), min-max score normalization, query-specific evidence grounding (`[DOC_CHUNK_X]`), and strict human-readable citation resolution (`[filename.pdf, p. 1]`).
3. **💾 Persistent Conversations**: SQLite database maintaining threaded chat histories, auto-titling, renaming, and cascade deletions.

---

## 🌟 Key Features

### 1. Hybrid Retrieval Engine (Phase 3)
* **Dense + Lexical Fusion**: Combines deep semantic similarity from SentenceTransformers + ChromaDB with exact keyword matching from BM25 (`rank-bm25`).
* **Technical Term Preservation**: Custom tokenizer guarantees zero loss for hyphenated terms, alphanumeric symbols, and versioning: `CYP3A4`, `IL-6`, `B12`, `COVID-19`, `GPT-5.6`.
* **Per-Query Min-Max Score Normalization**: Normalizes vector and BM25 scores to a standardized scale `[0.0, 1.0]` with division-by-zero protection.
* **Weighted Score Fusion**: Configurable weighted ranking (`0.60 * norm_vector + 0.40 * norm_bm25`) with candidate pool deduplication.
* **Candidate Pool Tracking**: Distinguishes unretrieved chunks (`retrieved: false`) from chunks with lowest relative scores.
* **Deterministic Local Persistence**: BM25 chunks and metadata are stored in JSON (`bm25_index/bm25_chunks.json`) with atomic writes — zero dependency on Python `pickle`.
* **Safe Reindexing Lifecycle**: Validates new document parsing, chunking, and embedding before replacing previous ChromaDB and BM25 indices.

### 2. Document RAG Engine (Phase 2)
* **Multi-Format Ingestion**: Ingests `.pdf`, `.docx`, `.txt`, and `.md` with automated metadata extraction (pages, section headings).
* **SHA-256 Duplicate Detection**: Prevents redundant storage and re-indexing of identical documents.
* **Document Isolation**: Queries can be filtered to specific documents or searched across the entire collection.
* **Evidence Grounding & Citation Resolution**: Tags each retrieved chunk with an ephemeral turn evidence ID (`[DOC_CHUNK_1]`), instructing Gemini to cite specific claims, which the server resolves back to `[annual_report.pdf, p. 4]`.
* **Grounded "No Relevant Context" Handling**: Strictly avoids hallucination and prevents silent fallback to web search when document information is insufficient.

### 3. Agentic Live Web Search
* **Real-Time Web Retrieval**: Powered by Tavily Search API.
* **Local Semantic Re-Ranking**: Filters out noisy web snippets using cosine similarity computed via normalized vector dot products.
* **Conversational Contextualization**: Rewrites multi-turn pronouns and implicit entity references into standalone queries using Gemini.
* **Dynamic Follow-Ups**: Proposes 3 clickable follow-up research questions after each completion.

### 4. Cross-Platform Flutter Client
* Native support for **Web**, **Windows Desktop**, **macOS**, **Linux**, and **Mobile**.
* Modern dark-mode interface with collapsible drawer navigation.
* Interactive document manager modal (upload, preview, delete, reindex, select).
* Skeleton shimmer loaders with `skeletonizer` and streaming Markdown rendering.

---

## 🏗️ End-to-End Architecture & Data Flow

```mermaid
flowchart TD
    subgraph Client["Flutter Frontend Client"]
        UI[Search & Chat UI]
        DM[Document Management Dialog]
    end

    subgraph Backend["FastAPI Backend (server/)"]
        Router[Chat Router: /ws/chat & /chat]
        DocRouter[Document Router: /api/documents]
        
        subgraph ModeDetect{"Mode Detection"}
            IsDoc{Documents Selected?}
        end

        subgraph WebSearchEngine["Web Search Engine"]
            Context[LLM Query Contextualizer]
            Tavily[Tavily Web Search]
            ReRank[SentenceTransformer Cosine Re-Ranker]
        end

        subgraph HybridRAG["Hybrid Retrieval Engine (Phase 3)"]
            subgraph Retrievers["Parallel Candidate Retrieval"]
                VecRet[VectorRetriever: ChromaDB Top 10]
                BM25Ret[BM25Retriever: Lexical Top 10]
            end
            Norm[ScoreNormalizer: Min-Max]
            Fusion["Weighted Fusion: 0.60 Vec + 0.40 BM25"]
            Dedup[Deduplication & Top 5 Selection]
        end

        subgraph IngestionPipeline["Document Ingestion & Storage"]
            Parser[DocumentParser: PDF, DOCX, TXT, MD]
            Chunker[DocumentChunker: Page/Section Aware]
            Embedder[EmbeddingService: all-MiniLM-L6-v2]
            ChromaDB[(ChromaDB Persistent)]
            BM25Store[(BM25 JSON Store)]
            SQLite[(SQLite: conversations.db)]
        end

        subgraph LLMGeneration["Grounded Synthesis"]
            LLM[Google Gemini Streaming]
            CiteResolve[Citation & Evidence Resolver]
        end
    end

    UI -->|WebSocket JSON| Router
    DM -->|REST API| DocRouter
    DocRouter --> IngestionPipeline
    Parser --> Chunker --> Embedder
    Embedder --> ChromaDB & BM25Store

    Router --> ModeDetect
    IsDoc -->|No: Web Search| Context --> Tavily --> ReRank --> LLM
    IsDoc -->|Yes: Document RAG| VecRet & BM25Ret
    VecRet --> Norm
    BM25Ret --> Norm
    Norm --> Fusion --> Dedup --> LLM

    LLM --> CiteResolve -->|Stream Tokens + Citations| UI
```

---

## 💻 Tech Stack & Dependencies

### Frontend (Flutter)
| Technology | Package / Version | Role & Description |
| :--- | :--- | :--- |
| **Framework** | Flutter 3 (Dart SDK `^3.12.2`) | Cross-platform client for Web, Windows Desktop, and Mobile. |
| **Networking** | `web_socket_client: ^0.2.1` | Low-latency persistent WebSocket client with broadcast streams. |
| **Markdown** | `flutter_markdown: ^0.7.7+1` | Rich Markdown rendering with code blocks, tables, and clickable links. |
| **Shimmer UI** | `skeletonizer: ^2.1.3` | Bone-style skeleton placeholders during retrieval and synthesis. |
| **Typography** | `google_fonts: ^8.2.1` | Typography using `Inter` and `IBM Plex Mono`. |

### Backend (Python)
| Technology | Package | Role & Description |
| :--- | :--- | :--- |
| **Framework** | `fastapi`, `uvicorn`, `fastapi-cli` | Asynchronous REST & WebSocket server. |
| **LLM Engine** | `google-genai` | Official Google GenAI SDK for Gemini streaming and generation. |
| **Vector DB** | `chromadb` | Local persistent vector database with cosine distance space. |
| **Lexical Engine** | `rank-bm25` | Local BM25Okapi scoring with non-negative Lucene IDF smoothing. |
| **Embeddings & ML** | `sentence-transformers`, `numpy` | Local dense sentence embeddings (`all-MiniLM-L6-v2`). |
| **Document Parsing**| `pypdf`, `python-docx` | Extraction from multi-page PDFs, Word documents, text, and markdown. |
| **Database** | `sqlite3` | Local persistent storage for conversations, turns, and document metadata. |
| **Web Search** | `tavily-python` | Search API optimized for LLMs and factual source retrieval. |

---

## 📂 Repository Blueprint

```text
ResearchOS/
├── lib/                               # Flutter Client
│   ├── main.dart                      # Bootstrap & dark theme configuration
│   ├── pages/
│   │   ├── home_page.dart             # Hero search view with sidebar navigation
│   │   └── chat_page.dart             # Multi-turn conversation thread manager
│   ├── services/
│   │   ├── chat_web_services.dart     # WebSocket service with broadcast controllers
│   │   ├── conversation_service.dart  # REST client for conversation threads
│   │   └── document_service.dart      # REST client for document uploads/management
│   ├── theme/
│   │   └── colors.dart                # AppColors design system tokens
│   └── widget/
│       ├── answer_section.dart        # Markdown renderer with token streaming & copy
│       ├── document_management_dialog.dart # Ingestion, status tracking, selection modal
│       ├── follow_up_section.dart     # Suggested questions and thread continuation
│       ├── search_section.dart        # Main query input bar
│       ├── side_bar.dart              # Collapsible conversation drawer
│       └── sources_section.dart       # Horizontal citation cards
├── server/                            # Python Backend Server
│   ├── config.py                      # Pydantic BaseSettings & configuration
│   ├── main.py                        # FastAPI app, service wiring & dependency injection
│   ├── requirements.txt               # Pinned Python dependencies
│   ├── bm25_index/                    # Deterministic local BM25 JSON storage
│   ├── chroma_db/                     # Persistent ChromaDB vector index
│   ├── uploads/                       # Stored uploaded files (.pdf, .docx, .txt, .md)
│   ├── pydantic_models/
│   │   ├── chat_body.py               # ChatBody schemas & retrieval mode
│   │   ├── conversation_models.py     # Conversation & turn schemas
│   │   └── document_models.py         # Document, RetrievedChunk, and RagDebugInfo
│   ├── repositories/
│   │   ├── conversation_repository.py # SQLite conversation & turn persistence
│   │   └── document_repository.py     # SQLite document metadata & state tracking
│   ├── routers/
│   │   ├── chat_router.py             # /ws/chat and /chat routing
│   │   └── document_router.py         # /api/documents upload, reindex, delete
│   ├── services/
│   │   ├── bm25_store_service.py      # BM25 store, tokenization & JSON persistence
│   │   ├── document_chunker.py        # Sentence & paragraph-aware chunking
│   │   ├── document_parser.py         # PDF, DOCX, TXT, MD parsers
│   │   ├── document_security.py       # SHA-256 duplicate detection & sanitization
│   │   ├── document_service.py        # Ingestion pipeline, sync & safe reindexing
│   │   ├── embedding_service.py       # SentenceTransformers singleton wrapper
│   │   ├── llm_service.py             # Gemini streaming, prompts & fallback cascade
│   │   ├── rag_service.py             # Context formulation, evidence IDs & citations
│   │   ├── search_service.py          # Tavily search wrapper
│   │   ├── sort_source_service.py     # Web search vector re-ranking
│   │   ├── vector_store_service.py    # ChromaDB wrapper
│   │   └── retrievers/
│   │       ├── base_retriever.py      # Abstract BaseRetriever interface
│   │       ├── bm25_retriever.py      # Lexical BM25 retriever
│   │       ├── hybrid_retriever.py    # Fused dense + lexical hybrid retriever
│   │       ├── retriever_factory.py   # Mode factory ('hybrid', 'vector', 'bm25')
│   │       ├── score_normalizer.py    # Reusable Min-Max score normalization
│   │       └── vector_retriever.py    # Dense vector retriever
│   └── tests/
│       ├── test_conversation_repository.py # 7 tests
│       ├── test_document_rag.py            # 12 tests
│       └── test_hybrid_retrieval.py        # 21 tests (40 tests total)
└── README.md
```

---

## 📡 Wire Protocol & API Contracts

### WebSocket Endpoint: `ws://localhost:8000/ws/chat`

#### Client &rarr; Server Payload
```json
{
  "query": "What clinical indicators suggest CYP3A4 inhibition?",
  "history": [],
  "mode": "rag",
  "document_ids": ["doc_0195e2f7_a82b_74dc"],
  "retrieval_mode": "hybrid",
  "debug": false
}
```

| Field | Type | Description |
| :--- | :---: | :--- |
| `query` | `string` | **Required**. The user's query. |
| `history` | `array[object]` | Optional prior conversation turns (`query`, `answer`). |
| `mode` | `string` | `"rag"` (documents selected) or `"search"` (web search). |
| `document_ids` | `array[string]` | Optional document isolation filter. |
| `retrieval_mode` | `string` | Optional: `"hybrid"` (default), `"vector"`, or `"bm25"`. |
| `debug` | `boolean` | When `true`, server emits an additional `rag_debug` payload. |

#### Server &rarr; Client Message Flow
1. **`search_results`**: Formatted document chunks or web sources sent immediately.
2. **`rag_debug`** *(optional, only if debug enabled)*: Emits candidate breakdown, vector scores, BM25 scores, normalized scores, and final hybrid scores.
3. **`content`**: Real-time token chunks streamed from Gemini.
4. **`done`**: Stream termination signal with resolved human-readable citations.
5. **`follow_ups`**: 3 suggested next queries.

---

## ⚙️ Configuration Matrix

Create `server/.env` based on `server/.env.example`:

```env
# Required API Keys
TAVILY_API_KEY=tvly-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GEMINI_API_KEY=AIzaxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Local Storage Paths
DATABASE_PATH=conversations.db
CHROMA_DIR=chroma_db
BM25_DIR=bm25_index
UPLOADS_DIR=uploads

# Chunking & Document Ingestion
DEFAULT_CHUNK_SIZE=600
DEFAULT_CHUNK_OVERLAP=120
MAX_FILE_SIZE_MB=50

# Hybrid Retrieval Settings
RETRIEVAL_MODE=hybrid
HYBRID_VECTOR_WEIGHT=0.60
HYBRID_BM25_WEIGHT=0.40
HYBRID_VECTOR_CANDIDATE_K=10
HYBRID_BM25_CANDIDATE_K=10
HYBRID_FINAL_TOP_K=5
RAG_RELEVANCE_THRESHOLD=0.0
RAG_DEBUG=false
```

---

## 🚀 Quickstart & Developer Runbook

### 1. Prerequisites
- **Flutter SDK**: `^3.12.2` ([Install Guide](https://docs.flutter.dev/get-started/install))
- **Python**: `3.10` or `3.11` ([Python Downloads](https://www.python.org/downloads/))
- **Google Gemini API Key** ([Google AI Studio](https://aistudio.google.com/))
- **Tavily Search API Key** ([Tavily](https://app.tavily.com/))

---

### 2. Backend Setup

```powershell
cd server

# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install pinned dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env and paste your GEMINI_API_KEY and TAVILY_API_KEY

# Start backend server
fastapi dev main.py
```
*Backend runs on `http://127.0.0.1:8000` (Swagger UI: `http://127.0.0.1:8000/docs`).*

---

### 3. Frontend Setup

In a new terminal window:
```powershell
# Get dependencies
flutter pub get

# Launch on Windows Desktop
flutter run -d windows

# Or launch on Web
flutter run -d chrome
```

---

### 4. Running Automated Tests

Run the complete test suite across all Phase 1, Phase 2, and Phase 3 suites:

```powershell
server\venv\Scripts\python -m unittest discover -s server/tests -v
```

**Result**: All 40 unit and integration tests execute and pass:
```text
Ran 40 tests in 22.007s
OK
```

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
