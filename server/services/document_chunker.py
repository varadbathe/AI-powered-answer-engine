import re
from typing import Any


class DocumentChunker:
    """
    Sentence- and paragraph-aware text chunker that strictly preserves page boundaries
    and supports configurable chunk_size and chunk_overlap.
    """

    @classmethod
    def split_into_semantic_units(cls, text: str) -> list[str]:
        """
        Splits text by paragraphs first, then by sentences within paragraphs.
        """
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        units: list[str] = []

        sentence_pattern = re.compile(r"(?<=[.!?])\s+")
        for para in paragraphs:
            # If paragraph contains multiple sentences, split them
            sentences = sentence_pattern.split(para)
            para_sentences = [s.strip() for s in sentences if s.strip()]
            if para_sentences:
                units.extend(para_sentences)
            else:
                units.append(para)

        return units

    @classmethod
    def chunk_segment(
        cls,
        text: str,
        chunk_size: int,
        chunk_overlap: int,
    ) -> list[str]:
        """
        Chunks text within a single page/segment up to chunk_size with chunk_overlap.
        """
        if len(text) <= chunk_size:
            return [text]

        units = cls.split_into_semantic_units(text)
        if not units:
            return [text]

        chunks: list[str] = []
        current_chunk_parts: list[str] = []
        current_len = 0

        for unit in units:
            unit_len = len(unit)

            # If a single unit exceeds chunk_size, split it into word-level windows
            if unit_len > chunk_size:
                if current_chunk_parts:
                    chunks.append(" ".join(current_chunk_parts))
                    current_chunk_parts = []
                    current_len = 0

                words = unit.split()
                w_start = 0
                while w_start < len(words):
                    sub_words = []
                    sub_len = 0
                    while w_start < len(words) and (sub_len + len(words[w_start]) + 1) <= chunk_size:
                        sub_words.append(words[w_start])
                        sub_len += len(words[w_start]) + 1
                        w_start += 1
                    if sub_words:
                        chunks.append(" ".join(sub_words))
                    else:
                        # Extremely long single word: take prefix
                        chunks.append(words[w_start][:chunk_size])
                        w_start += 1
                continue

            if current_len + unit_len + 1 <= chunk_size:
                current_chunk_parts.append(unit)
                current_len += unit_len + 1
            else:
                if current_chunk_parts:
                    chunk_text = " ".join(current_chunk_parts)
                    chunks.append(chunk_text)

                    # Build overlap from the end of current_chunk_parts
                    overlap_parts: list[str] = []
                    overlap_len = 0
                    for part in reversed(current_chunk_parts):
                        if overlap_len + len(part) + 1 <= chunk_overlap:
                            overlap_parts.insert(0, part)
                            overlap_len += len(part) + 1
                        else:
                            break
                    current_chunk_parts = overlap_parts + [unit]
                    current_len = sum(len(p) + 1 for p in current_chunk_parts)
                else:
                    current_chunk_parts = [unit]
                    current_len = unit_len

        if current_chunk_parts:
            chunks.append(" ".join(current_chunk_parts))

        return chunks

    @classmethod
    def chunk_document(
        cls,
        segments: list[dict[str, Any]],
        document_id: str,
        document_name: str,
        chunk_size: int = 600,
        chunk_overlap: int = 120,
    ) -> list[dict[str, Any]]:
        """
        Chunks all segments of a document.
        Preserves page boundaries: chunks never cross page boundaries.
        Returns list of structured chunk dicts.
        """
        if chunk_size <= 0:
            chunk_size = 600
        if chunk_overlap >= chunk_size:
            chunk_overlap = max(0, chunk_size // 4)

        all_chunks: list[dict[str, Any]] = []
        global_chunk_idx = 0

        for seg in segments:
            seg_text = seg["text"]
            page_num = seg.get("page_number")
            section_title = seg.get("section_title")

            page_chunks = cls.chunk_segment(
                text=seg_text,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )

            for chunk_str in page_chunks:
                chunk_str = chunk_str.strip()
                if not chunk_str:
                    continue

                chunk_id = f"{document_id}_chunk_{global_chunk_idx}"
                evidence_id = f"DOC_CHUNK_{global_chunk_idx + 1}"

                all_chunks.append({
                    "chunk_id": chunk_id,
                    "document_id": document_id,
                    "document_name": document_name,
                    "chunk_index": global_chunk_idx,
                    "page_number": page_num,
                    "section_title": section_title,
                    "evidence_id": evidence_id,
                    "text": chunk_str,
                })
                global_chunk_idx += 1

        return all_chunks
