from pydantic import BaseModel
# pydantic here the query entered by the user is enters as a string instead of converting 
# it into any other thing

class ChatBody(BaseModel):
    query: str
    history: list[dict] = []