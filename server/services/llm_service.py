from google import genai

from config import Settings

settings = Settings()


class LLMService:
    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.models = ["gemini-3.6-flash", "gemini-3.5-flash", "gemini-3.5-flash-lite"]

    def generate_response(self, query: str, search_results: list[dict]):
        # Format sources
        context = "\n\n".join(
            [
                f"Source {i+1} : {result['url']}\n{result['content']}"
                for i, result in enumerate(search_results)
            ]
        )

        full_prompt = f"""
        Context from web search:
        {context}
        
        Query: {query}
        
        please provide a comprehensive, detailed, well-cited accurate response using the above context. Think and reason deeply. Ensure it answers the query the user is asking. do not use your knowledge until its absolutly necessary.
        """

        last_error = None
        for model in self.models:
            try:
                response = self.client.models.generate_content_stream(
                    model=model,
                    contents=full_prompt,
                )
                for chunk in response:
                    if chunk.text:
                        yield chunk.text
                return  # Successfully generated response
            except Exception as e:
                print(f"Warning: Model {model} failed with: {e}. Trying fallback if available...")
                last_error = e

        if last_error:
            raise last_error

