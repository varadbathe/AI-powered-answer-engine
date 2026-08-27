from fastapi import FastAPI
from pydantic_models.chat_body import ChatBody
from services.search_service import SearchService
from services.sort_source_service import SortSourceService

app = FastAPI()

# instantiate the search service
search_service = SearchService()
sort_source_service = SortSourceService()


# chat
@app.post("/chat")
def chat_endpoint(body: ChatBody):

    search_results = search_service.web_search(body.query)
    # here by using the search service we are searching the web for the query entered by the user and returning the results found in it.
    

    
    
    # sort the sources
    sorted_results = sort_source_service.sort_sources(body.query, search_results)
    
    
    # generate the response using the LLM
    

    return body.query
