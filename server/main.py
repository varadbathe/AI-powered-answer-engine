import asyncio
import sys
import traceback
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState
from pydantic_models.chat_body import ChatBody
from services.llm_service import LLMService
from services.search_service import SearchService
from services.sort_source_service import SortSourceService

# Ensure stdout and stderr use UTF-8 encoding on Windows to prevent UnicodeEncodeError with emojis/special characters
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

app = FastAPI()

# instantiate the search service
search_service = SearchService()
sort_source_service = SortSourceService()
llm_service = LLMService()


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
            except Exception as e:
                # Disconnection or frame error
                break

            query = data.get("query")
            history = data.get("history", [])

            if not query:
                await websocket.send_json({"error": "Query is required"})
                continue

            print(f"\n--- New Request: '{query}' (history: {len(history)} turns) ---")

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
                }
            )

            full_response = ""
            for chunk in llm_service.generate_response(query, sorted_results, history=history):
                full_response += chunk
                await websocket.send_json(
                    {
                        "type": "content",
                        "data": chunk,
                    }
                )

            await websocket.send_json({"type": "done"})
            print(f"\n--- Generated Response Complete ({len(full_response)} chars) ---\n")

            # Generate suggested follow-up questions
            try:
                follow_ups = await asyncio.to_thread(llm_service.generate_follow_ups, query, full_response)
                if follow_ups:
                    await websocket.send_json(
                        {
                            "type": "follow_ups",
                            "data": follow_ups,
                        }
                    )
                    print(f"--- Sent Suggested Follow-ups: {follow_ups} ---")
            except Exception as e:
                print(f"Warning: follow-ups generation failed: {e}")

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


# chat
@app.post("/chat")
def chat_endpoint(body: ChatBody):
    print(f"\n--- New Request: '{body.query}' ---")
    search_query = body.query
    if body.history:
        search_query = llm_service.contextualize_query(body.query, body.history)

    search_results = search_service.web_search(search_query)
    sorted_results = sort_source_service.sort_sources(search_query, search_results)

    response = "".join(llm_service.generate_response(body.query, sorted_results, history=body.history))
    print(f"\n--- Generated Response ---\n{response}\n--------------------------\n")

    return response

