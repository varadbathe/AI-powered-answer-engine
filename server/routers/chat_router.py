import asyncio
import traceback
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState
from config import Settings
from pydantic_models.chat_body import ChatBody
from services.conversation_service import ConversationService
from services.llm_service import LLMService
from services.rag_service import RagService
from services.search_service import SearchService
from services.sort_source_service import SortSourceService

router = APIRouter(tags=["chat"])
settings = Settings()

# Services injected from main.py
_search_service: SearchService | None = None
_sort_source_service: SortSourceService | None = None
_llm_service: LLMService | None = None
_conversation_service: ConversationService | None = None
_rag_service: RagService | None = None


def set_chat_services(
    search_service: SearchService,
    sort_source_service: SortSourceService,
    llm_service: LLMService,
    conversation_service: ConversationService,
    rag_service: RagService,
) -> None:
    global _search_service, _sort_source_service, _llm_service, _conversation_service, _rag_service
    _search_service = search_service
    _sort_source_service = sort_source_service
    _llm_service = llm_service
    _conversation_service = conversation_service
    _rag_service = rag_service


@router.websocket("/ws/chat")
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
                break

            query = data.get("query")
            history = data.get("history", [])
            client_conv_id = data.get("conversation_id")
            mode = data.get("mode")  # "search" or "rag"
            document_ids = data.get("document_ids")  # list of doc IDs
            debug_requested = data.get("debug", False)

            if not query:
                await websocket.send_json({"error": "Query is required"})
                continue

            # Auto-detect mode: if document_ids provided or mode explicitly 'rag', use RAG
            if not mode:
                mode = "rag" if document_ids else "search"

            assert _conversation_service is not None
            assert _llm_service is not None

            # Get or create active conversation
            active_conv = await asyncio.to_thread(
                _conversation_service.get_or_create_conversation,
                client_conv_id,
                query,
            )
            active_conv_id = active_conv["id"]

            print(f"\n--- Request: '{query}' [Mode: {mode.upper()}] (conv: {active_conv_id}) ---")

            if mode == "rag":
                # ---------------------------------------------------------
                # DOCUMENT RAG PIPELINE
                # ---------------------------------------------------------
                assert _rag_service is not None

                # 1. Retrieve relevant chunks (filtered by document_ids if provided)
                chunks = await asyncio.to_thread(
                    _rag_service.retrieve,
                    query,
                    5,
                    document_ids,
                )

                # 2. Build structured context with stable evidence tags [DOC_CHUNK_X]
                context_str, evidence_map = _rag_service.build_context(chunks)

                # 3. Format sources and send immediately to UI
                client_sources = _rag_service.format_sources_for_client(chunks, evidence_map)
                await websocket.send_json(
                    {
                        "type": "search_results",
                        "data": client_sources,
                        "conversation_id": active_conv_id,
                        "mode": "rag",
                    }
                )

                # 4. Optional RAG Debug payload (only sent if RAG_DEBUG or requested)
                if _rag_service.debug_mode or debug_requested:
                    debug_payload = _rag_service.build_debug_info(chunks, context_str)
                    if debug_payload:
                        await websocket.send_json(
                            {
                                "type": "rag_debug",
                                "data": debug_payload.model_dump(),
                                "conversation_id": active_conv_id,
                            }
                        )

                # 5. Stream grounded answer from Gemini
                raw_response = ""
                for token in _llm_service.generate_rag_response(query, context_str, history=history):
                    raw_response += token
                    await websocket.send_json(
                        {
                            "type": "content",
                            "data": token,
                            "conversation_id": active_conv_id,
                        }
                    )

                # 6. Resolve citations: map [DOC_CHUNK_X] to human-readable document metadata
                resolved_text, cited_items = _rag_service.resolve_citations(raw_response, evidence_map)

                await websocket.send_json({
                    "type": "done",
                    "conversation_id": active_conv_id,
                    "citations": [c.model_dump() for c in cited_items],
                })
                print(f"\n--- RAG Response Complete ({len(raw_response)} chars, {len(cited_items)} citations) ---\n")

                final_answer_to_save = raw_response

            else:
                # ---------------------------------------------------------
                # WEB SEARCH PIPELINE (PRESERVED)
                # ---------------------------------------------------------
                assert _search_service is not None
                assert _sort_source_service is not None

                search_query = query
                if history:
                    try:
                        search_query = await asyncio.to_thread(_llm_service.contextualize_query, query, history)
                        print(f"--- Contextualized Search Query: '{search_query}' ---")
                    except Exception as e:
                        print(f"Warning: contextualize query error: {e}")
                        search_query = query

                search_results = await asyncio.to_thread(_search_service.web_search, search_query)
                sorted_results = await asyncio.to_thread(_sort_source_service.sort_sources, search_query, search_results)

                await websocket.send_json(
                    {
                        "type": "search_results",
                        "data": sorted_results,
                        "conversation_id": active_conv_id,
                        "mode": "search",
                    }
                )

                full_response = ""
                for chunk in _llm_service.generate_response(query, sorted_results, history=history):
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
                print(f"\n--- Search Response Complete ({len(full_response)} chars) ---\n")

                client_sources = sorted_results
                final_answer_to_save = full_response

            # Common follow-ups generation
            follow_ups: List[str] = []
            try:
                follow_ups = await asyncio.to_thread(_llm_service.generate_follow_ups, query, final_answer_to_save)
                if follow_ups:
                    await websocket.send_json(
                        {
                            "type": "follow_ups",
                            "data": follow_ups,
                            "conversation_id": active_conv_id,
                        }
                    )
            except Exception as e:
                print(f"Warning: follow-ups generation failed: {e}")

            # Atomically persist turn to SQLite
            try:
                await asyncio.to_thread(
                    _conversation_service.save_completed_turn,
                    conversation_id=active_conv_id,
                    user_query=query,
                    assistant_answer=final_answer_to_save,
                    sources=client_sources,
                    follow_ups=follow_ups,
                )
                print(f"--- Turn Persisted to SQLite (conv: {active_conv_id}) ---")
            except Exception as e:
                print(f"Warning: Failed to persist turn to SQLite: {e}")

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


@router.post("/chat")
def http_chat_endpoint(body: ChatBody):
    """
    Legacy HTTP chat endpoint with support for both web search and document RAG modes.
    """
    assert _llm_service is not None

    mode = getattr(body, "mode", None) or "search"
    document_ids = getattr(body, "document_ids", None)
    if document_ids:
        mode = "rag"

    if mode == "rag":
        assert _rag_service is not None
        chunks = _rag_service.retrieve(body.query, 5, document_ids)
        context_str, evidence_map = _rag_service.build_context(chunks)
        response = "".join(_llm_service.generate_rag_response(body.query, context_str, history=body.history))
        resolved, _ = _rag_service.resolve_citations(response, evidence_map)
        return resolved

    assert _search_service is not None
    assert _sort_source_service is not None

    search_query = body.query
    if body.history:
        search_query = _llm_service.contextualize_query(body.query, body.history)

    search_results = _search_service.web_search(search_query)
    sorted_results = _sort_source_service.sort_sources(search_query, search_results)

    response = "".join(_llm_service.generate_response(body.query, sorted_results, history=body.history))
    return response
