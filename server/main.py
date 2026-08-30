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
        data = await websocket.receive_json()
        print(data)
        query = data.get("query")

        if not query:
            await websocket.send_json({"error": "Query is required"})
            return
        print(f"\n--- New Request: '{query}' ---")
        search_results = search_service.web_search(query)
        # here by using the search service we are searching the web for the query entered by the user and returning the results found in it.
        # sort the sources
        sorted_results = sort_source_service.sort_sources(query, search_results)
        
        print(f"\n--- Sorted Results ---\n{sorted_results}\n--------------------------\n")
      
        await websocket.send_json(
            {
                "type": "search_results",
                "data": sorted_results,
            }
        )
        full_response = ""
        for chunk in llm_service.generate_response(query, sorted_results):
            full_response += chunk
            await websocket.send_json(
                {
                    "type": "content",
                    "data": chunk,
                }
            )

        print(f"\n--- Generated Response ---\n{full_response}\n--------------------------\n")

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
    search_results = search_service.web_search(body.query)
    # here by using the search service we are searching the web for the query entered by the user and returning the results found in it.

    # sort the sources
    sorted_results = sort_source_service.sort_sources(body.query, search_results)

    response = "".join(llm_service.generate_response(body.query, sorted_results))
    print(f"\n--- Generated Response ---\n{response}\n--------------------------\n")

    return response
