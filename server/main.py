from fastapi import FastAPI
from pydantic_models.chat_body import ChatBody
from services.search_service import SearchService

app = FastAPI()

# instantiate the search service
search_service = SearchService()


# chat
@app.post("/chat")
def chat_endpoint(body: ChatBody):

    search_results = search_service.web_search(body.query)
    # here by using the search service we are searching the web for the query entered by the user and returning the results found in it.
    
    print(search_results)
    
    # sort the sources
    # generate the response using the LLM
    

    return body.query
