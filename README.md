# ⚡ ResearchOS

[![Flutter](https://img.shields.io/badge/Flutter-02569B?style=for-the-badge&logo=flutter&logoColor=white)](https://flutter.dev/)
[![Dart](https://img.shields.io/badge/Dart-0175C2?style=for-the-badge&logo=dart&logoColor=white)](https://dart.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Google Gemini](https://img.shields.io/badge/Google_Gemini-8E75B2?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev/)
[![Tavily](https://img.shields.io/badge/Tavily_Search-0A84FF?style=for-the-badge&logo=google-chrome&logoColor=white)](https://tavily.com/)
[![Hugging Face](https://img.shields.io/badge/Sentence--Transformers-FFD21E?style=for-the-badge&logo=huggingface&logoColor=black)](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)
[![WebSockets](https://img.shields.io/badge/WebSockets-010101?style=for-the-badge&logo=socket.io&logoColor=white)](https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

A full-stack, real-time conversational search and generative research engine — **ResearchOS**. 

It integrates live web search, local semantic vector re-ranking, multi-turn query contextualization, streaming generative answers with multi-model fallback cascades, dynamic follow-up recommendations, and a dark-mode Flutter interface across Web, Desktop, and Mobile.

---

## 🤖 AI Assistant & Bot Developer Guide (System Context)

> [!NOTE]
> **To AI Chatbots, LLMs, and Autonomous Coding Agents reading this repository:**
> This section is your architectural index. Use this mental model to understand project conventions, state flows, invariant constraints, and component boundaries before proposing changes.

### Core Architectural Paradigm
- **Full-Stack Decoupling**: The project is split into a **Flutter Client** (`lib/`) and a **Python FastAPI Backend** (`server/`).
- **Real-Time Communication**: Primary client-backend communication uses a persistent bidirectional **WebSocket connection** (`ws://localhost:8000/ws/chat`). An HTTP fallback endpoint (`POST /chat`) is also maintained.
- **RAG & Agentic Web Search Flow**:
  1. **User Query & History Ingestion**: Client submits the current prompt and past conversation turns (`[{"query": "...", "answer": "..."}]`).
  2. **Conversational Contextualization**: If prior conversation history exists, `LLMService.contextualize_query()` uses Gemini to rewrite contextual references and pronouns (e.g., *"How old is he?"* &rarr; *"How old is Sundar Pichai?"*) into a self-contained search query.
  3. **Live Web Retrieval**: `SearchService.web_search()` queries the **Tavily API** for up to 10 web sources containing raw titles, URLs, and text snippets.
  4. **Local Vector Re-Ranking**: `SortSourceService.sort_sources()` encodes the query and source contents using `sentence-transformers` (`all-MiniLM-L6-v2`). Cosine similarity is computed via normalized vector dot products. Documents with similarity scores `<= 0.3` are pruned, and the remainder are sorted descending by relevance score.
  5. **Streaming Source Cards**: Filtered sources are transmitted immediately to the client as a `search_results` JSON frame, allowing the UI to render source cards while synthesis begins.
  6. **Grounded Answer Streaming**: `LLMService.generate_response()` streams synthesized markdown content token-by-token over WebSockets (`content` frames) with source citations.
  7. **Stream Finalization & Follow-Ups**: Upon completion (`done` frame), `LLMService.generate_follow_ups()` prompts Gemini to generate 3 logical follow-up questions, emitted as a `follow_ups` JSON frame.

### Key Invariants & Design Decisions
1. **Frontend State & Streams**:
   - `ChatWebService` is a singleton with `StreamController<Map<String, dynamic>>.broadcast()` streams (`searchResultStream`, `contentStream`, `followUpStream`). Broadcast streams prevent `Bad state: Stream has already been listened to` errors during screen transitions.
   - `ChatPage` tracks multi-turn state via a list of `ChatTurn` objects. Each turn encapsulates its own question, sources, answer buffer, loading flags, and suggested follow-ups.
2. **Backend Concurrency & Thread Offloading**:
   - FastAPI handles WebSocket frames asynchronously. Blocking, CPU-heavy, or synchronous I/O operations (Tavily search, SentenceTransformer embedding calculation, Gemini API calls) are wrapped with `asyncio.to_thread(...)` to ensure the event loop remains unblocked.
3. **Multi-Model LLM Cascade & Resilience**:
   - `LLMService` utilizes a fallback cascade list: `["gemini-3.6-flash", "gemini-3.5-flash", "gemini-3.5-flash-lite"]`.
   - If an upstream model is deprecated, throttled, or rate-limited, the service automatically logs a warning and attempts generation with the next model in the cascade before failing.
4. **Normalized Vector Dot-Product**:
   - Vectors are encoded with `normalize_embeddings=True`. Cosine similarity between the query and documents is calculated via `np.dot(doc_embeddings, query_embedding)`, eliminating manual vector norm divisions and maximizing CPU throughput.
5. **Windows Terminal UTF-8 Safety**:
   - `server/main.py` explicitly reconfigures `sys.stdout` and `sys.stderr` to UTF-8 on launch to prevent `UnicodeEncodeError` crashes on Windows when printing emoji characters or non-ASCII web text.
6. **Centralized Frontend Logging**:
   - The Flutter client uses `AppLogger` (`lib/utils/app_logger.dart`) with level-based logging (`debug`, `info`, `warn`, `error`), dual-routing to `dart:developer.log` (for VS Code Debug Console & DevTools) and `debugPrint` (for terminal and browser console).

---

## 🌟 Key Features

- ⚡ **Token-by-Token Streaming**: Low-latency WebSocket streaming delivers perceived instant response times.
- 🌐 **Live Web Grounding**: Live search powered by Tavily Search API, providing real-time data beyond LLM training cutoff dates.
- 🧬 **Local Semantic Vector Re-Ranking**: Edge-based sentence embedding scoring (`all-MiniLM-L6-v2`) eliminates noisy search snippets and ranks sources by relevance.
- 🔄 **Multi-Turn Contextual Search**: Context-aware query rewriting preserves entity references and pronouns throughout continuous conversation threads.
- 💡 **Dynamic Suggested Follow-Ups**: Automatically generates 3 relevant, clickable follow-up queries after each answer completion.
- 🎨 **ResearchOS Dark UI**:
  - Collapsible navigation sidebar
  - Smooth shimmer loaders with `skeletonizer`
  - Horizontal scrolling source citation cards displaying domain, title, and direct external links
  - Full Markdown rendering with syntax highlighting, lists, and formatted tables
  - Threaded multi-turn conversation layout
- 🛡️ **Graceful Multi-Model Failover**: Cascades across Gemini models to maximize uptime under API constraints.
- 🪵 **Centralized App Logging**: Unified, tagged logging across both client and server layers.

---

## 🏗️ End-to-End Architecture & Data Flow

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Flutter as Flutter Frontend (Client)
    participant WS as FastAPI WebSocket (/ws/chat)
    participant LLM as Google Gemini (LLMService)
    participant Tavily as Tavily Search Engine
    participant ReRank as Sentence Transformers (Local)

    User->>Flutter: Enters query or selects follow-up chip
    Flutter->>WS: Sends JSON {"query": "...", "history": [...]}
    
    alt Follow-up Turn with Conversation History
        WS->>LLM: Contextualize query with prior history
        LLM-->>WS: Returns standalone search query
    end

    WS->>Tavily: Search web for top results (max_results=10)
    Tavily-->>WS: Returns raw search results (urls, titles, snippets)
    
    WS->>ReRank: Vector encode & compute cosine similarity (dot product)
    ReRank-->>WS: Filtered & ranked sources (similarity > 0.3)
    
    WS-->>Flutter: {"type": "search_results", "data": [...]}
    Note over Flutter: Renders source citation cards; ends shimmer skeleton

    WS->>LLM: Stream grounded answer with cited context
    loop Token Streaming
        LLM-->>WS: Content chunk
        WS-->>Flutter: {"type": "content", "data": chunk}
        Note over Flutter: Appends chunk to active ChatTurn & auto-scrolls
    end

    WS-->>Flutter: {"type": "done"}
    Note over Flutter: Marks turn streaming as complete; enables copy actions

    WS->>LLM: Generate 3 suggested follow-up questions
    LLM-->>WS: JSON array of follow-up strings
    WS-->>Flutter: {"type": "follow_ups", "data": [...]}
    Note over Flutter: Renders clickable follow-up suggestion pills
```

---

## 💻 Tech Stack & Dependencies

### Frontend (Flutter)
| Technology | Package / Version | Role & Description |
| :--- | :--- | :--- |
| **Framework** | Flutter 3 (Dart SDK `^3.12.2`) | Cross-platform UI toolkit targeting Web, Desktop, and Mobile. |
| **Networking** | `web_socket_client: ^0.2.1` | Low-level WebSocket client with automatic reconnection and state streams. |
| **Markdown** | `flutter_markdown: ^0.7.7+1` | Rich Markdown rendering supporting code blocks, hyperlinks, and tables. |
| **Shimmer UI** | `skeletonizer: ^2.1.3` | Bone-style skeleton loading placeholder during search and answer synthesis. |
| **Typography** | `google_fonts: ^8.2.1` | Modern Google Fonts typography (`Inter`, `IBM Plex Mono`). |
| **Logging** | Custom `AppLogger` | Tagged logging routing to `dart:developer` and standard debug output. |

### Backend (Python)
| Technology | Package | Role & Description |
| :--- | :--- | :--- |
| **Framework** | `fastapi`, `uvicorn`, `fastapi-cli` | High-performance asynchronous REST & WebSocket server. |
| **LLM Engine** | `google-genai` | Official Google GenAI SDK for Gemini streaming and content generation. |
| **Embeddings & ML** | `sentence-transformers`, `numpy` | Local dense embedding inference (`all-MiniLM-L6-v2`) for cosine re-ranking. |
| **Web Search** | `tavily-python` | Search API optimized for LLMs, RAG applications, and source retrieval. |
| **Web Scraping** | `trafilatura` | Robust HTML parsing, article text extraction, and boilerplate removal. |
| **Configuration** | `pydantic`, `pydantic-settings`, `python-dotenv` | Type-safe environment variable validation and configuration loading. |

---

## 📂 Repository Blueprint & Component Catalog

```text
ResearchOS/
├── .vscode/
│   └── launch.json                    # Pre-configured debug targets (Full Stack, Chrome, Windows, FastAPI)
├── lib/                               # Flutter Frontend Client
│   ├── main.dart                      # App bootstrap, dark theme configuration, and root routing
│   ├── pages/
│   │   ├── home_page.dart             # ResearchOS hero search view with side navigation
│   │   └── chat_page.dart             # Multi-turn conversation thread manager and turn coordinator
│   ├── services/
│   │   └── chat_web_services.dart     # Singleton WebSocket service managing broadcast streams
│   ├── theme/
│   │   └── colors.dart                # Design system color tokens (AppColors)
│   ├── utils/
│   │   └── app_logger.dart            # Multi-level tagged logger (debug, info, warn, error)
│   └── widget/
│       ├── answer_section.dart        # Markdown renderer with token streaming and clipboard copy
│       ├── follow_up_section.dart     # Clickable suggestion chips and follow-up query input box
│       ├── search_bar_button.dart     # Focus & Attach action chips on home screen
│       ├── search_section.dart        # Centered hero search input bar
│       ├── side_bar.dart              # Collapsible navigation drawer
│       ├── side_bar_buttons.dart      # Navigation icon and label buttons
│       └── sources_section.dart       # Horizontal scrolling source citation cards
├── server/                            # Python Backend Server
│   ├── .env.example                   # Environment variable template
│   ├── config.py                      # Pydantic BaseSettings loading API keys
│   ├── main.py                        # FastAPI application with /ws/chat and /chat endpoints
│   ├── requirements.txt               # Pinned Python package dependencies
│   ├── pydantic_models/
│   │   └── chat_body.py               # Pydantic schema for ChatBody request validation
│   └── services/
│       ├── llm_service.py             # Gemini streaming, prompt templates, contextualization & follow-ups
│       ├── search_service.py          # Tavily search client wrapper
│       └── sort_source_service.py     # SentenceTransformers vector re-ranking and cosine scoring
├── test/                              # Automated Unit & Widget Tests
│   ├── follow_up_widget_test.dart     # Widget tests for FollowUpSection interaction
│   └── widget_test.dart               # Baseline Flutter widget smoke test
├── pubspec.yaml                       # Flutter project dependencies and metadata
├── pyrightconfig.json                 # Python static type analysis configuration
└── README.md                          # Comprehensive project documentation
```

### Component Responsibility Breakdown

#### Frontend (`lib/`)
- **[main.dart](lib/main.dart)**: Sets up the Flutter application root, configures the dark `ThemeData` using `AppColors.background`, and defines the initial route to `HomePage`.
- **[home_page.dart](lib/pages/home_page.dart)**: Presents the hero search experience with the collapsible `SideBar`, centered `SearchSection`, and category focus buttons (`Search`, `Attach`). When a query is submitted, it initializes the WebSocket connection and pushes to `ChatPage`.
- **[chat_page.dart](lib/pages/chat_page.dart)**: Coordinates the conversation lifecycle. Maintains `List<ChatTurn> _turns`. Subscribes to `searchResultStream`, `contentStream`, and `followUpStream`. Handles auto-scrolling as tokens arrive.
- **[chat_web_services.dart](lib/services/chat_web_services.dart)**: Singleton service encapsulating the `WebSocket` client. Exposes three broadcast streams: `searchResultStream`, `contentStream`, and `followUpStream`. Encodes query and history payloads.
- **[app_logger.dart](lib/utils/app_logger.dart)**: Centralized logging utility with timestamps, tags, and severity levels (`debug`, `info`, `warn`, `error`). Dispatches to `dart:developer.log` and `debugPrint`.
- **[answer_section.dart](lib/widget/answer_section.dart)**: Renders the markdown answer using `MarkdownBody`. Displays a shimmer placeholder while waiting for the first token, and provides copy-to-clipboard functionality upon completion.
- **[sources_section.dart](lib/widget/sources_section.dart)**: Renders horizontal cards for verified search sources with domain favicons/initials, titles, and similarity scores. Opens URLs in the default browser.
- **[follow_up_section.dart](lib/widget/follow_up_section.dart)**: Displays 3 suggested follow-up chips and a bottom query input bar for continuing the multi-turn thread.
- **[colors.dart](lib/theme/colors.dart)**: Color palette tokens (`background: #131415`, `sideNav: #171819`, `searchBar: #1C1E20`, `submitButton: #20B8CD`, etc.).

#### Backend (`server/`)
- **[main.py](server/main.py)**: FastAPI entrypoint. Establishes the WebSocket endpoint `/ws/chat` and HTTP endpoint `/chat`. Coordinates async workflow across `SearchService`, `SortSourceService`, and `LLMService`.
- **[config.py](server/config.py)**: Pydantic `BaseSettings` reading `TAVILY_API_KEY` and `GEMINI_API_KEY` from `.env`.
- **[chat_body.py](server/pydantic_models/chat_body.py)**: Request validation model with fields `query: str` and `history: list[dict] = []`.
- **[llm_service.py](server/services/llm_service.py)**: Wraps Google GenAI SDK. Implements `contextualize_query()`, `generate_response()`, and `generate_follow_ups()` with multi-model fallback cascade.
- **[search_service.py](server/services/search_service.py)**: Executes web searches via `TavilyClient`, extracting `title`, `url`, and `content`.
- **[sort_source_service.py](server/services/sort_source_service.py)**: Loads `all-MiniLM-L6-v2`, computes vector dot products for cosine similarity, filters results below `0.3`, and sorts by relevance.

---

## 📡 Wire Protocol & Network Contracts

### WebSocket Endpoint: `ws://localhost:8000/ws/chat`

#### 1. Inbound Client Message (Flutter &rarr; Backend)
Sent as a JSON text frame when the user submits a query or clicks a follow-up chip:

```json
{
  "query": "Who is the CEO of Google and what is their background?",
  "history": [
    {
      "query": "What companies belong to Alphabet?",
      "answer": "Alphabet Inc. is a multinational conglomerate comprising Google, Waymo, DeepMind, Verily, and Calico..."
    }
  ]
}
```

| Field | Type | Required | Description |
| :--- | :---: | :---: | :--- |
| `query` | `string` | **Yes** | The user's latest question or follow-up query. |
| `history` | `array[object]` | No | Chronological list of prior turns (`query` and `answer`) used for contextualization. |

---

#### 2. Outbound Server Messages (Backend &rarr; Flutter)

##### A. `search_results` (Emitted once search & re-ranking finish)
```json
{
  "type": "search_results",
  "data": [
    {
      "title": "Sundar Pichai - Wikipedia",
      "url": "https://en.wikipedia.org/wiki/Sundar_Pichai",
      "content": "Pichai Sundararajan is an American business executive who is the chief executive officer of Alphabet and Google...",
      "score": 0.784
    },
    {
      "title": "Alphabet Leadership: Sundar Pichai",
      "url": "https://abc.xyz/investor/management/",
      "content": "Sundar Pichai joined Google in 2004 where he led the development of Google Chrome, ChromeOS, and Google Drive...",
      "score": 0.692
    }
  ]
}
```

##### B. `content` (Emitted repeatedly as LLM generates tokens)
```json
{
  "type": "content",
  "data": "Sundar Pichai is an American business executive currently serving as the CEO of both Alphabet and Google... "
}
```

##### C. `done` (Emitted once generation concludes)
```json
{
  "type": "done"
}
```

##### D. `follow_ups` (Emitted with 3 suggested follow-up questions)
```json
{
  "type": "follow_ups",
  "data": [
    "What university degrees did Sundar Pichai earn?",
    "When did Sundar Pichai become CEO of Google?",
    "What major products did he manage before becoming CEO?"
  ]
}
```

##### E. `error` (Emitted if an unhandled exception occurs)
```json
{
  "type": "error",
  "data": "Detailed error message string"
}
```

---

### HTTP REST Fallback: `POST /chat`

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "What is Flutter?", "history": []}'
```
Returns a single complete markdown response string upon completion.

---

## ⚙️ Configuration & Environment Matrix

The backend requires the following keys defined in `server/.env`:

| Variable | Required | Default | Description |
| :--- | :---: | :---: | :--- |
| `TAVILY_API_KEY` | **Yes** | `"your_tavily_api_key"` | API key for Tavily AI Web Search. Obtain from [app.tavily.com](https://app.tavily.com/). |
| `GEMINI_API_KEY` | **Yes** | `"your_gemini_api_key"` | Google Gemini API key for contextualization and generation. Obtain from [Google AI Studio](https://aistudio.google.com/). |

### Example `server/.env`:
```env
TAVILY_API_KEY=tvly-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GEMINI_API_KEY=AIzaxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

## 🚀 Developer Runbook & CLI Workflows

### 1. Prerequisites
- **Flutter SDK**: `^3.12.2` or later ([Flutter Install Guide](https://docs.flutter.dev/get-started/install))
- **Python**: `3.10` or `3.11` ([Python Downloads](https://www.python.org/downloads/))
- **Google Gemini API Key**
- **Tavily Search API Key**

---

### 2. Backend Setup & Startup

1. **Open a terminal and navigate to the `server/` folder**:
   ```bash
   cd server
   ```

2. **Create and activate a virtual environment**:
   - **Windows (PowerShell)**:
     ```powershell
     python -m venv venv
     .\venv\Scripts\Activate.ps1
     ```
   - **macOS / Linux**:
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

3. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   > [!TIP]
   > On the first startup, `sentence-transformers` downloads `all-MiniLM-L6-v2` (~90MB) to the Hugging Face local cache (`~/.cache/huggingface/hub`).

4. **Set environment variables**:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` to include your valid `TAVILY_API_KEY` and `GEMINI_API_KEY`.

5. **Start the server**:
   ```bash
   fastapi dev main.py
   ```
   *The server will start listening at `http://127.0.0.1:8000`, with WebSockets ready at `ws://127.0.0.1:8000/ws/chat`.*

---

### 3. Frontend Setup & Startup

1. **Open a second terminal and navigate to the project root**:
   ```bash
   cd ..
   ```

2. **Fetch Flutter dependencies**:
   ```bash
   flutter pub get
   ```

3. **Launch the application on your desired platform**:
   - **Web (Chrome)**:
     ```bash
     flutter run -d chrome
     ```
   - **Windows Desktop**:
     ```bash
     flutter run -d windows
     ```
   - **Mobile (Android / iOS)**:
     ```bash
     flutter run
     ```

---

### 4. VS Code 1-Click Debugging
The repository includes [.vscode/launch.json](.vscode/launch.json) with pre-configured compound targets:
- Select **`Full Stack (Backend + Chrome)`** from the Run & Debug panel to launch both the FastAPI backend and Chrome Flutter frontend simultaneously.
- Select **`Full Stack (Backend + Windows Desktop)`** for native Windows desktop development.

---

### 5. Testing & Static Analysis

- **Run Flutter Widget Tests**:
  ```bash
  flutter test
  ```
  Runs tests including [test/follow_up_widget_test.dart](test/follow_up_widget_test.dart).

- **Run Flutter Analyzer**:
  ```bash
  flutter analyze
  ```

- **Python Type Checking**:
  Configured via [pyrightconfig.json](pyrightconfig.json) pointing to the `server/venv` environment:
  ```bash
  pyright server
  ```

---

## 🛠️ Extensibility & Future Roadmap

For AI chatbots and developers implementing extensions:

1. **Adding Alternative Search Providers**:
   - `SearchService` in [search_service.py](server/services/search_service.py) outputs standard dictionaries `[{"title": "...", "url": "...", "content": "..."}]`. You can add providers like **SearXNG**, **DuckDuckGo**, or **Google Custom Search** by implementing the same schema.
2. **Swapping LLMs or Local Inference**:
   - `LLMService` in [llm_service.py](server/services/llm_service.py) provides clean separation. Integrate local LLMs via **Ollama**, **vLLM**, or OpenAI-compatible endpoints by modifying `generate_response()` to yield chunks from an async generator.
3. **Customizing Re-Ranking Thresholds**:
   - The cosine similarity filtering threshold is set to `0.3` in [sort_source_service.py](server/services/sort_source_service.py). Adjust this value to calibrate the trade-off between recall (lower threshold) and precision (higher threshold).
4. **Persistent Conversation History**:
   - Currently, conversation turns are retained in Flutter memory across `ChatTurn` items. SQLite, Hive, or a backend database (e.g. Supabase, PostgreSQL) can be integrated to persist threads across application sessions.

---
