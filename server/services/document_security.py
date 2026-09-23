import hashlib
import os
import re
import uuid
from typing import Tuple


class DocumentSecurityError(Exception):
    pass


class UnsupportedFileError(DocumentSecurityError):
    pass


class FileTooLargeError(DocumentSecurityError):
    pass


class CorruptedFileError(DocumentSecurityError):
    pass


class DocumentSecurityService:
    ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}

    @classmethod
    def calculate_sha256(cls, file_bytes: bytes) -> str:
        """Calculates SHA-256 hash of file bytes."""
        hasher = hashlib.sha256()
        hasher.update(file_bytes)
        return hasher.hexdigest()

    @classmethod
    def generate_document_id(cls) -> str:
        """Generates a secure server-side UUIDv4 document ID."""
        return str(uuid.uuid4())

    @classmethod
    def sanitize_filename(cls, filename: str) -> str:
        """
        Sanitizes filename against path traversal, null bytes, and unsafe characters.
        Preserves original extension.
        """
        if not filename:
            return "document.txt"

        # Remove null bytes
        cleaned = filename.replace("\x00", "")

        # Extract only the base name (handling both forward and backward slashes)
        cleaned = cleaned.replace("\\", "/").rstrip("/")
        cleaned = cleaned.split("/")[-1].strip()

        # Remove any lingering path traversal '..'
        while ".." in cleaned:
            cleaned = cleaned.replace("..", "")

        # Separate name and ext
        name, ext = os.path.splitext(cleaned)
        # Normalize extension
        ext = ext.lower()

        # Sanitize name
        sanitized_name = re.sub(r"[^a-zA-Z0-9_\-\. ]", "", name).strip()
        if not sanitized_name:
            sanitized_name = "document"

        # Truncate to reasonable length (max 100 chars)
        sanitized_name = sanitized_name[:100]
        return f"{sanitized_name}{ext}"

    @classmethod
    def validate_file(
        cls,
        filename: str,
        file_bytes: bytes,
        max_size_mb: int = 50,
    ) -> Tuple[str, str]:
        """
        Validates file extension, size, and header magic bytes.
        Returns tuple of (sanitized_filename, file_type).
        Raises DocumentSecurityError subclasses on failure.
        """
        sanitized_name = cls.sanitize_filename(filename)
        _, ext = os.path.splitext(sanitized_name)
        ext = ext.lower()

        if ext not in cls.ALLOWED_EXTENSIONS:
            raise UnsupportedFileError(
                f"Unsupported file type '{ext}'. Allowed types: {', '.join(sorted(cls.ALLOWED_EXTENSIONS))}"
            )

        # File size check
        max_bytes = max_size_mb * 1024 * 1024
        if len(file_bytes) > max_bytes:
            raise FileTooLargeError(
                f"File size ({len(file_bytes) / (1024 * 1024):.1f}MB) exceeds maximum limit of {max_size_mb}MB"
            )

        if len(file_bytes) == 0:
            raise CorruptedFileError("Uploaded file is empty (0 bytes)")

        # Magic byte & structure inspection
        if ext == ".pdf":
            if not file_bytes.startswith(b"%PDF-"):
                raise CorruptedFileError("Invalid PDF header: Missing '%PDF-' signature")
            file_type = "pdf"
        elif ext == ".docx":
            if not file_bytes.startswith(b"PK\x03\x04"):
                raise CorruptedFileError("Invalid DOCX format: Missing ZIP package header")
            file_type = "docx"
        elif ext == ".txt":
            file_type = "txt"
        elif ext == ".md":
            file_type = "md"
        else:
            file_type = ext.lstrip(".")

        return sanitized_name, file_type
