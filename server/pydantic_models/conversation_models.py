from typing import Any
from pydantic import BaseModel, Field


class ConversationSummary(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str


class ConversationCreate(BaseModel):
    title: str | None = None
    id: str | None = None


class ConversationRename(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)


class ConversationMessage(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    turn_index: int
    metadata: dict[str, Any] | None = None
    created_at: str


class ConversationTurn(BaseModel):
    turn_index: int
    question: str
    answer: str
    sources: list[dict[str, Any]] = Field(default_factory=list)
    follow_ups: list[str] = Field(default_factory=list)
    created_at: str


class ConversationDetail(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    messages: list[ConversationMessage] = Field(default_factory=list)
    turns: list[ConversationTurn] = Field(default_factory=list)
