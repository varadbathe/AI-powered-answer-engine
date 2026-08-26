# here the web_search(function) is used to search the web and return the results found in it.

from config import Settings

from tavily import TavilyClient

import trafilatura

settings = (
    Settings()
)  # settings class instantiated to access the TAVILY_API_KEY from the .env file.
tavily_client = TavilyClient(api_key=settings.TAVILY_API_KEY)


class SearchService:
    def web_search(self, query: str):
        results = []

        response = tavily_client.search(
            query, max_results=10
        )  # Perform a web search using the Tavily API with a maximum of 10 results
        # here the web_search(function) is used to search the web and return the results found in it.
        search_results = response.get(
            "results", []
        )  # Print the search results to the console

        for result in search_results:
            downloaded = trafilatura.fetch_url(
                result.get("url")
            )  # Fetch the content of a specific URL using trafilatura
            content = trafilatura.extract(
                downloaded, include_comments=False
            )  # Extract the content from the downloaded URL using trafilatura
            results.append(
                {
                    "title": result.get("title", ""),
                    "url": result.get("url"),
                    "content": content,
                }
                # it is appending the extracted content to the results list, which contains the title, url, and content of each search result.
            )  # Append the extracted content to the results list

        return results  # Return the list of extracted content from the search results
