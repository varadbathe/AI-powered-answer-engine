from google import genai

from config import Settings

settings = Settings()


class LLMService:
    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model = "gemini-3.6-flash"

    def generate_response(self, query: str, search_results: list[dict]):
        # source 1 : <url>
        # <content>
        # source 2 : <url>
        # <content>
        # Query:
        context = "\n\n".join(
            [
                f"Source {i+1} : {result['url']}\n{result['content']}"
                for i, result in enumerate(search_results)
            ]
        )
        # for every element in the search_results list, we are creating a string that contains the source number, the url and the content of the result. We are then joining all these strings with two new lines in between each source.

        full_prompt = f"""
        Context from web search:
        {context}
        
        Query: {query}
        
        please provide a comprehensive, detailed, well-cited accurate response using the above context. Think and reason deeply. Ensure it answers the query the user is asking. do not use your knowledge until its absolutly necessary.
        """
        
        response = self.client.models.generate_content(
            model=self.model,
            contents=full_prompt,
        )
        
        return response.text

