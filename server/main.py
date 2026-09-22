import asyncio
import sys
import traceback
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from starlette.websockets import WebSocketState
from config import Settings
from pydantic_models.chat_body import ChatBody
from pydantic_models.conversation_models import (
    ConversationCreate,
    ConversationDetail,
    ConversationRename,
    ConversationSummary,
)
from repositories.conversation_repository import ConversationRepository
from services.conversation_service import ConversationService
from services.llm_service import LLMService
from services.search_service import SearchService
from services.sort_source_service import SortSourceService

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

app = FastAPI(title="AI-Powered Answer Engine API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

settings = Settings()

# Instantiate services
search_service = SearchService()
sort_source_service = SortSourceService()
llm_service = LLMService()
conversation_repository = ConversationRepository(db_path=settings.DATABASE_PATH)
conversation_service = ConversationService(repository=conversation_repository)


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


# ---------------------------------------------------------
# WebSocket Real-Time Chat Endpoint
# ---------------------------------------------------------

@app.websocket("/ws/chat")
async def websocket_chat_endpoint(websocket: WebSocket):
    await websocket.accept()

    try:
        while True:
            try:
                data = await websocket.receive_json()
            except WebSocketDisconnect:
                print("\n--- WebSocket client disconnected gracefully ---")
                break
            except Exception:
                # Disconnection or frame error
                break

            query = data.get("query")
            history = data.get("history", [])
            client_conv_id = data.get("conversation_id")

            if not query:
                await websocket.send_json({"error": "Query is required"})
                continue

            # Ensure conversation exists; auto-title deterministically on first turn
            active_conv = await asyncio.to_thread(
                conversation_service.get_or_create_conversation,
                client_conv_id,
                query,
            )
            active_conv_id = active_conv["id"]

            print(f"\n--- New Request: '{query}' (conv: {active_conv_id}, history: {len(history)} turns) ---")

            # Contextualize query for search if follow-up with history
            search_query = query
            if history:
                try:
                    search_query = await asyncio.to_thread(llm_service.contextualize_query, query, history)
                    print(f"--- Contextualized Search Query: '{search_query}' ---")
                except Exception as e:
                    print(f"Warning: contextualize query error: {e}")
                    search_query = query

            search_results = await asyncio.to_thread(search_service.web_search, search_query)
            sorted_results = await asyncio.to_thread(sort_source_service.sort_sources, search_query, search_results)
            
            print(f"\n--- Sorted Results ({len(sorted_results)} items) ---\n")
          
            await websocket.send_json(
                {
                    "type": "search_results",
                    "data": sorted_results,
                    "conversation_id": active_conv_id,
                }
            )

            full_response = ""
            for chunk in llm_service.generate_response(query, sorted_results, history=history):
                full_response += chunk
                await websocket.send_json(
                    {
                        "type": "content",
                        "data": chunk,
                        "conversation_id": active_conv_id,
                    }
                )

            await websocket.send_json({
                "type": "done",
                "conversation_id": active_conv_id,
            })
            print(f"\n--- Generated Response Complete ({len(full_response)} chars) ---\n")

            # Generate suggested follow-up questions
            follow_ups: list[str] = []
            try:
                follow_ups = await asyncio.to_thread(llm_service.generate_follow_ups, query, full_response)
                if follow_ups:
                    await websocket.send_json(
                        {
                            "type": "follow_ups",
                            "data": follow_ups,
                            "conversation_id": active_conv_id,
                        }
                    )
                    print(f"--- Sent Suggested Follow-ups: {follow_ups} ---")
            except Exception as e:
                print(f"Warning: follow-ups generation failed: {e}")

            # Persist completed turn atomically to SQLite
            try:
                await asyncio.to_thread(
                    conversation_service.save_completed_turn,
                    conversation_id=active_conv_id,
                    user_query=query,
                    assistant_answer=full_response,
                    sources=sorted_results,
                    follow_ups=follow_ups,
                )
                print(f"--- Successfully Persisted Turn to SQLite (conv: {active_conv_id}) ---")
            except Exception as e:
                print(f"Warning: Failed to persist completed turn to SQLite: {e}")

    except WebSocketDisconnect:
        print("\n--- WebSocket client disconnected gracefully ---")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        traceback.print_exc()
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_json({"type": "error", "data": str(e)})
        except Exception:
            pass

    finally:
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.close()
        except Exception:
            pass


# ---------------------------------------------------------
# Legacy HTTP Chat Endpoint
# ---------------------------------------------------------

@app.post("/chat")
def chat_endpoint(body: ChatBody):
    print(f"\n--- New HTTP Request: '{body.query}' ---")
    search_query = body.query
    if body.history:
        search_query = llm_service.contextualize_query(body.query, body.history)

    search_results = search_service.web_search(search_query)
    sorted_results = sort_source_service.sort_sources(search_query, search_results)

    response = "".join(llm_service.generate_response(body.query, sorted_results, history=body.history))
    print(f"\n--- Generated Response ---\n{response}\n--------------------------\n")

    return response
