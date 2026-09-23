from pydantic import BaseModel
# pydantic here the query entered by the user is enters as a string instead of converting 
# it into any other thing

class ChatBody(BaseModel):
    query: str
    history: list[dict] = []
    mode: str | None = None
    document_ids: list[str] | None = None
    retrieval_mode: str | None = None
