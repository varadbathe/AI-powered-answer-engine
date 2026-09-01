import json
from google import genai

from config import Settings

settings = Settings()


class LLMService:
    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.models = ["gemini-3.6-flash", "gemini-3.5-flash", "gemini-3.5-flash-lite"]

    def contextualize_query(self, query: str, history: list[dict]) -> str:
        """
        Rewrites a follow-up query to include conversational context for search engines.
        """
        if not history:
            return query

        history_snippets = []
        for turn in history[-3:]:
            q = turn.get("query", "")
            a = turn.get("answer", "")
            if q:
                history_snippets.append(f"User: {q}")
            if a:
                history_snippets.append(f"Assistant: {a[:250]}")

        history_text = "\n".join(history_snippets)
        prompt = f"""Given the following conversation history and the latest follow-up question, rewrite the follow-up question as a clear, standalone search query that preserves all necessary context (e.g., resolve pronouns like 'he', 'it', 'they', 'the first one'). Output ONLY the standalone search query text, without explanations, quotes, or markdown.

Conversation History:
{history_text}

Follow-up Question: {query}
Standalone Search Query:"""

        for model in self.models:
            try:
                response = self.client.models.generate_content(
                    model=model,
                    contents=prompt,
                )
                if response.text and response.text.strip():
                    cleaned = response.text.strip().strip('"').strip("'")
                    return cleaned
            except Exception as e:
                print(f"Warning: contextualize_query with model {model} failed: {e}")
                continue

        return query

    def generate_response(self, query: str, search_results: list[dict], history: list[dict] = None):
        # Format sources
        context = "\n\n".join(
            [
                f"Source {i+1} : {result.get('url', '')}\n{result.get('content', '')}"
                for i, result in enumerate(search_results)
            ]
        )

        history_context = ""
        if history:
            history_lines = []
            for item in history:
                q = item.get("query", "")
                a = item.get("answer", "")
                if q:
                    history_lines.append(f"User: {q}")
                if a:
                    history_lines.append(f"Assistant: {a}")
            if history_lines:
                history_context = "Previous Conversation History:\n" + "\n".join(history_lines) + "\n\n"

        full_prompt = f"""
        {history_context}Context from web search:
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

    def generate_follow_ups(self, query: str, response_text: str) -> list[str]:
        """
        Generates 3 concise, relevant suggested follow-up questions for the user to explore next.
        """
        prompt = f"""Based on the following query and answer, generate exactly 3 brief, logical follow-up questions that the user might want to ask next.
Return ONLY a valid JSON array of strings, for example: ["Question 1?", "Question 2?", "Question 3?"].
Do not include markdown codeblocks, comments, or any other surrounding text.

Query: {query}
Answer Summary: {response_text[:1200]}"""

        for model in self.models:
            try:
                response = self.client.models.generate_content(
                    model=model,
                    contents=prompt,
                )
                text = (response.text or "").strip()
                if text.startswith("```"):
                    lines = text.splitlines()
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines and lines[-1].startswith("```"):
                        lines = lines[:-1]
                    text = "\n".join(lines).strip()

                parsed = json.loads(text)
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed if str(item).strip()][:3]
            except Exception as e:
                print(f"Warning: generate_follow_ups with model {model} failed: {e}")
                continue

        return []


