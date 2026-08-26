from config import Settings
from tavily import TavilyClient

settings = Settings() #settings class instantiated to access the TAVILY_API_KEY from the .env file.
tavily_client = TavilyClient(api_key=settings.TAVILY_API_KEY)

class SearchService:
    def web_search(self, query: str):
        
        response = tavily_client.search(query, max_results=10)  # Perform a web search using the Tavily API with a maximum of 10 results
        #here the web_search(function) is used to search the web and return the results found in it.
        
        print(response.get("results", []))  # Print the search results to the console
      
    
# here the web_search(function) is used to search the web and return the results found in it. 