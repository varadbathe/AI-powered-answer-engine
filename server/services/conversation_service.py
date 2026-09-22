from typing import Any
from pydantic_models.conversation_models import (
    ConversationDetail,
    ConversationMessage,
    ConversationSummary,
    ConversationTurn,
)
from repositories.conversation_repository import ConversationRepository


class ConversationService:
    """
    Domain service for conversation management.
    Encapsulates deterministic titling, turn structure compilation, and repository delegation.
    """

    def __init__(self, repository: ConversationRepository):
        self.repository = repository

    @staticmethod
    def generate_title_from_query(query: str, max_length: int = 60) -> str:
        """
        Deterministically produces a clean conversation title from the first user query
        without invoking an external LLM.
        """
        cleaned = " ".join(query.strip().split())
        if not cleaned:
            return "New Conversation"
        if len(cleaned) <= max_length:
            return cleaned
        return cleaned[:max_length].rstrip() + "..."

    def create_conversation(
        self,
        title: str | None = None,
        conversation_id: str | None = None,
    ) -> ConversationSummary:
        safe_title = (title or "").strip() or "New Conversation"
        record = self.repository.create_conversation(safe_title, conversation_id)
        return ConversationSummary(**record)

    def get_or_create_conversation(
        self,
        conversation_id: str | None,
        first_query: str,
    ) -> dict[str, Any]:
        """
        Ensures a conversation exists. If conversation_id is provided and valid, returns it;
        otherwise creates a new conversation with a title derived from first_query.
        """
        if conversation_id:
            existing = self.repository.get_conversation(conversation_id)
            if existing:
                return existing

        title = self.generate_title_from_query(first_query)
        return self.repository.create_conversation(title=title, conversation_id=conversation_id)

    def list_conversations(self, limit: int = 50, offset: int = 0) -> list[ConversationSummary]:
        records = self.repository.list_conversations(limit=limit, offset=offset)
        return [ConversationSummary(**rec) for rec in records]

    def rename_conversation(self, conversation_id: str, new_title: str) -> ConversationSummary | None:
        safe_title = new_title.strip()
        record = self.repository.rename_conversation(conversation_id, safe_title)
        if not record:
            return None
        return ConversationSummary(**record)

    def delete_conversation(self, conversation_id: str) -> bool:
        return self.repository.delete_conversation(conversation_id)

    def save_completed_turn(
        self,
        conversation_id: str,
        user_query: str,
        assistant_answer: str,
        sources: list[dict[str, Any]] | None = None,
        follow_ups: list[str] | None = None,
    ) -> int:
        """
        Determines the next sequential turn_index and persists both the user query
        and assistant response in an atomic transaction.
        """
        current_max = self.repository.get_max_turn_index(conversation_id)
        next_turn_index = current_max + 1

        self.repository.save_turn_atomic(
            conversation_id=conversation_id,
            turn_index=next_turn_index,
            user_query=user_query,
            assistant_answer=assistant_answer,
            sources=sources or [],
            follow_ups=follow_ups or [],
        )
        return next_turn_index

    def get_conversation_detail(self, conversation_id: str) -> ConversationDetail | None:
        """
        Loads the conversation, its raw messages, and compiles deterministic paired ConversationTurns
        for direct frontend ChatTurn restoration.
        """
        conv = self.repository.get_conversation(conversation_id)
        if not conv:
            return None

        raw_messages = self.repository.get_messages(conversation_id)
        message_models = [ConversationMessage(**msg) for msg in raw_messages]

        # Group messages by turn_index to form paired ConversationTurns
        turns_by_index: dict[int, dict[str, Any]] = {}
        for msg in message_models:
            idx = msg.turn_index
            if idx not in turns_by_index:
                turns_by_index[idx] = {
                    "turn_index": idx,
                    "question": "",
                    "answer": "",
                    "sources": [],
                    "follow_ups": [],
                    "created_at": msg.created_at,
                }

            if msg.role == "user":
                turns_by_index[idx]["question"] = msg.content
                turns_by_index[idx]["created_at"] = msg.created_at
            elif msg.role == "assistant":
                turns_by_index[idx]["answer"] = msg.content
                if msg.metadata:
                    turns_by_index[idx]["sources"] = msg.metadata.get("sources", [])
                    turns_by_index[idx]["follow_ups"] = msg.metadata.get("follow_ups", [])

        # Sort turns deterministically by turn_index
        sorted_turns = [
            ConversationTurn(**turns_by_index[idx])
            for idx in sorted(turns_by_index.keys())
        ]

        return ConversationDetail(
            id=conv["id"],
            title=conv["title"],
            created_at=conv["created_at"],
            updated_at=conv["updated_at"],
            messages=message_models,
            turns=sorted_turns,
        )
