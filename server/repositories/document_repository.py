from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
from typing import Any


class DocumentRepository:
    """
    SQLite repository for document metadata, ingestion status, and duplicate detection.
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
        """Initializes the documents table with indexes."""
        with self._get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    file_hash TEXT NOT NULL,
                    status TEXT NOT NULL,
                    progress REAL NOT NULL DEFAULT 0.0,
                    error_message TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    chunk_count INTEGER NOT NULL DEFAULT 0,
                    storage_path TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_documents_hash ON documents(file_hash);
                CREATE INDEX IF NOT EXISTS idx_documents_updated_at ON documents(updated_at DESC);
            """)

    def create_document(
        self,
        document_id: str,
        filename: str,
        file_type: str,
        file_size: int,
        file_hash: str,
        storage_path: str,
        status: str = "UPLOADING",
        progress: float = 0.0,
    ) -> dict[str, Any]:
        """Creates a new document record."""
        now = self._utc_now_iso()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO documents (
                    id, filename, file_type, file_size, file_hash,
                    status, progress, error_message, created_at, updated_at,
                    chunk_count, storage_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, 0, ?)
                """,
                (
                    document_id,
                    filename,
                    file_type,
                    file_size,
                    file_hash,
                    status,
                    progress,
                    now,
                    now,
                    storage_path,
                ),
            )
        return self.get_document_by_id(document_id) or {}

    def get_document_by_id(self, document_id: str) -> dict[str, Any] | None:
        """Retrieves a single document record by ID."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT id, filename, file_type, file_size, file_hash,
                       status, progress, error_message, created_at, updated_at,
                       chunk_count, storage_path
                FROM documents WHERE id = ?
                """,
                (document_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            doc = dict(row)
            doc["document_id"] = doc["id"]
            return doc

    def get_document_by_hash(self, file_hash: str) -> dict[str, Any] | None:
        """Retrieves a document by SHA-256 file hash for duplicate detection."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT id, filename, file_type, file_size, file_hash,
                       status, progress, error_message, created_at, updated_at,
                       chunk_count, storage_path
                FROM documents WHERE file_hash = ?
                ORDER BY updated_at DESC LIMIT 1
                """,
                (file_hash,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            doc = dict(row)
            doc["document_id"] = doc["id"]
            return doc

    def list_documents(self, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        """Lists documents sorted by updated_at descending."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT id, filename, file_type, file_size, file_hash,
                       status, progress, error_message, created_at, updated_at,
                       chunk_count, storage_path
                FROM documents
                ORDER BY updated_at DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            )
            results = []
            for row in cursor.fetchall():
                doc = dict(row)
                doc["document_id"] = doc["id"]
                results.append(doc)
            return results

    def count_documents(self) -> int:
        """Returns the total number of documents."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) AS total FROM documents")
            row = cursor.fetchone()
            return int(row["total"]) if row else 0

    def update_status(
        self,
        document_id: str,
        status: str,
        progress: float,
        error_message: str | None = None,
    ) -> dict[str, Any] | None:
        """Updates document status, progress, and optional error message."""
        now = self._utc_now_iso()
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE documents
                SET status = ?, progress = ?, error_message = ?, updated_at = ?
                WHERE id = ?
                """,
                (status, progress, error_message, now, document_id),
            )
        return self.get_document_by_id(document_id)

    def update_metadata(
        self,
        document_id: str,
        chunk_count: int,
        status: str = "READY",
        progress: float = 1.0,
    ) -> dict[str, Any] | None:
        """Updates document chunk count, status, and progress on ingestion completion."""
        now = self._utc_now_iso()
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE documents
                SET chunk_count = ?, status = ?, progress = ?, error_message = NULL, updated_at = ?
                WHERE id = ?
                """,
                (chunk_count, status, progress, now, document_id),
            )
        return self.get_document_by_id(document_id)

    def delete_document(self, document_id: str) -> bool:
        """Deletes a document record from SQLite."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM documents WHERE id = ?",
                (document_id,),
            )
            return cursor.rowcount > 0
