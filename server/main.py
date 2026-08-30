from fastapi import FastAPI
from pydantic_models.chat_body import ChatBody
from services.llm_service import LLMService
from services.search_service import SearchService
from services.sort_source_service import SortSourceService

app = FastAPI()

# instantiate the search service
search_service = SearchService()
sort_source_service = SortSourceService()
llm_service = LLMService()


# chat
@app.post("/chat")
def chat_endpoint(body: ChatBody):
    print(f"\n--- New Request: '{body.query}' ---")
    search_results = search_service.web_search(body.query)
    # here by using the search service we are searching the web for the query entered by the user and returning the results found in it.
    
    # sort the sources
    sorted_results = sort_source_service.sort_sources(body.query, search_results)
    
    response = llm_service.generate_response(body.query, sorted_results)
    print(f"\n--- Generated Response ---\n{response}\n--------------------------\n")
    
    return response

