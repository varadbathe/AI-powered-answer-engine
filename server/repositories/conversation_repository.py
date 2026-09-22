from contextlib import contextmanager
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class ConversationRepository:
    """
    SQLite repository for persistent conversation and message storage.
    Provides atomic transactions, foreign keys with cascade deletion,
    and thread-safe database connections.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._shared_conn: sqlite3.Connection | None = None
        if self.db_path == ":memory:":
            self._shared_conn = sqlite3.connect(":memory:")
            self._shared_conn.row_factory = sqlite3.Row
            self._shared_conn.execute("PRAGMA foreign_keys = ON;")
        else:
            self._ensure_db_dir()
        self.init_db()

    def _ensure_db_dir(self) -> None:
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def _get_connection(self):
        if self._shared_conn is not None:
            with self._shared_conn:
                yield self._shared_conn
        else:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.execute("PRAGMA journal_mode = WAL;")
            try:
                with conn:
                    yield conn
            finally:
                conn.close()

    def close(self) -> None:
        if self._shared_conn is not None:
            self._shared_conn.close()
            self._shared_conn = None

    @staticmethod
    def _utc_now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def init_db(self) -> None:
        """Initializes conversations and messages tables with indexes."""
        with self._get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    turn_index INTEGER NOT NULL,
                    metadata TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);
                CREATE INDEX IF NOT EXISTS idx_messages_turn ON messages(conversation_id, turn_index);
                CREATE INDEX IF NOT EXISTS idx_conversations_updated_at ON conversations(updated_at DESC);
            """)

    def create_conversation(self, title: str, conversation_id: str | None = None) -> dict[str, Any]:
        """Creates a new conversation record."""
        conv_id = conversation_id or str(uuid.uuid4())
        now = self._utc_now_iso()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO conversations (id, title, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (conv_id, title, now, now),
            )
        return {
            "id": conv_id,
            "title": title,
            "created_at": now,
            "updated_at": now,
        }

    def get_conversation(self, conversation_id: str) -> dict[str, Any] | None:
        """Retrieves a single conversation metadata record."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT id, title, created_at, updated_at FROM conversations WHERE id = ?",
                (conversation_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return dict(row)

    def list_conversations(self, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        """Lists conversations sorted by updated_at descending."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT id, title, created_at, updated_at
                FROM conversations
                ORDER BY updated_at DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            )
            return [dict(row) for row in cursor.fetchall()]

    def rename_conversation(self, conversation_id: str, new_title: str) -> dict[str, Any] | None:
        """Renames a conversation title and updates updated_at."""
        now = self._utc_now_iso()
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                UPDATE conversations
                SET title = ?, updated_at = ?
                WHERE id = ?
                """,
                (new_title, now, conversation_id),
            )
            if cursor.rowcount == 0:
                return None
        return self.get_conversation(conversation_id)

    def delete_conversation(self, conversation_id: str) -> bool:
        """Deletes a conversation and its messages (via ON DELETE CASCADE)."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM conversations WHERE id = ?",
                (conversation_id,),
            )
            return cursor.rowcount > 0

    def get_messages(self, conversation_id: str) -> list[dict[str, Any]]:
        """
        Retrieves all messages for a conversation ordered deterministically
        by turn_index ASC and created_at ASC.
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT id, conversation_id, role, content, turn_index, metadata, created_at
                FROM messages
                WHERE conversation_id = ?
                ORDER BY turn_index ASC,
                         CASE role WHEN 'user' THEN 0 WHEN 'assistant' THEN 1 ELSE 2 END,
                         created_at ASC
                """,
                (conversation_id,),
            )
            messages = []
            for row in cursor.fetchall():
                msg = dict(row)
                if msg["metadata"]:
                    try:
                        msg["metadata"] = json.loads(msg["metadata"])
                    except Exception:
                        pass
                else:
                    msg["metadata"] = None
                messages.append(msg)
            return messages

    def get_max_turn_index(self, conversation_id: str) -> int:
        """Returns the highest turn_index in the conversation, or -1 if empty."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT MAX(turn_index) AS max_idx FROM messages WHERE conversation_id = ?",
                (conversation_id,),
            )
            row = cursor.fetchone()
            if row and row["max_idx"] is not None:
                return int(row["max_idx"])
            return -1

    def save_turn_atomic(
        self,
        conversation_id: str,
        turn_index: int,
        user_query: str,
        assistant_answer: str,
        sources: list[dict[str, Any]] | None = None,
        follow_ups: list[str] | None = None,
    ) -> None:
        """
        Atomically saves both user message and assistant message for a completed turn
        within a single transaction, ensuring consistent turn_index and updating conversation timestamp.
        """
        now = self._utc_now_iso()
        user_msg_id = str(uuid.uuid4())
        assistant_msg_id = str(uuid.uuid4())

        assistant_metadata = {
            "sources": sources or [],
            "follow_ups": follow_ups or [],
        }
        metadata_json = json.dumps(assistant_metadata)

        with self._get_connection() as conn:
            # Insert user message
            conn.execute(
                """
                INSERT INTO messages (id, conversation_id, role, content, turn_index, metadata, created_at)
                VALUES (?, ?, 'user', ?, ?, NULL, ?)
                """,
                (user_msg_id, conversation_id, user_query, turn_index, now),
            )

            # Insert assistant message
            conn.execute(
                """
                INSERT INTO messages (id, conversation_id, role, content, turn_index, metadata, created_at)
                VALUES (?, ?, 'assistant', ?, ?, ?, ?)
                """,
                (assistant_msg_id, conversation_id, assistant_answer, turn_index, metadata_json, now),
            )

            # Update conversation timestamp
            conn.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (now, conversation_id),
            )
