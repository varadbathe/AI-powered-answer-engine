import re
from typing import Any, Dict, List, Optional, Tuple
from config import Settings
from pydantic_models.document_models import CitationItem, RagDebugInfo, RetrievedChunk
from services.retrievers.base_retriever import BaseRetriever

settings = Settings()


class RagService:
    """
    Coordinates document retrieval, context construction with stable evidence tags,
    grounded prompt formulation, citation resolution, and RAG debug payload creation.
    """

    def __init__(self, retriever: BaseRetriever, debug_mode: bool = False):
        self.retriever = retriever
        self.debug_mode = debug_mode or settings.RAG_DEBUG

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        document_ids: Optional[List[str]] = None,
    ) -> List[RetrievedChunk]:
        """
        Retrieves top-k relevant document chunks using the injected BaseRetriever.
        """
        return self.retriever.retrieve(
            query=query,
            top_k=top_k,
            document_ids=document_ids,
        )

    def build_context(
        self,
        chunks: List[RetrievedChunk],
    ) -> Tuple[str, Dict[str, CitationItem]]:
        """
        Builds structured context where each chunk is labeled with a stable evidence ID.
        Returns context string and evidence_map {evidence_id: CitationItem}.
        """
        if not chunks:
            return "", {}

        context_parts: List[str] = []
        evidence_map: Dict[str, CitationItem] = {}

        for i, chunk in enumerate(chunks):
            # Stable evidence ID for this retrieval turn
            tag = f"DOC_CHUNK_{i + 1}"

            citation = CitationItem(
                evidence_id=tag,
                filename=chunk.document_name,
                page_number=chunk.page_number,
                section_title=chunk.section_title,
                relevance_score=chunk.relevance_score,
            )
            evidence_map[tag] = citation

            header_info = [f"Source: {chunk.document_name}"]
            if chunk.page_number is not None:
                header_info.append(f"Page: {chunk.page_number}")
            if chunk.section_title:
                header_info.append(f"Section: {chunk.section_title}")

            context_parts.append(
                f"[{tag}] ({', '.join(header_info)})\n{chunk.text}"
            )

        context_str = "\n\n".join(context_parts)
        return context_str, evidence_map

    def resolve_citations(
        self,
        response_text: str,
        evidence_map: Dict[str, CitationItem],
    ) -> Tuple[str, List[CitationItem]]:
        """
        Resolves evidence tags (e.g. [DOC_CHUNK_1]) in the LLM response to human-readable
        citation labels like '[quarterly_report.pdf, Page 3]' or '[annual_plan.docx]'.
        Returns (resolved_text, list_of_cited_items).
        """
        cited_items: List[CitationItem] = []
        seen_tags = set()

        def replace_tag(match: re.Match) -> str:
            tag = match.group(1)
            if tag in evidence_map:
                if tag not in seen_tags:
                    seen_tags.add(tag)
                    cited_items.append(evidence_map[tag])

                item = evidence_map[tag]
                parts = [item.filename]
                if item.page_number is not None:
                    parts.append(f"p. {item.page_number}")
                elif item.section_title:
                    parts.append(item.section_title)
                return f"[{', '.join(parts)}]"
            return match.group(0)

        # Replace tags like [DOC_CHUNK_1]
        pattern = re.compile(r"\[(DOC_CHUNK_\d+)\]")
        resolved_text = pattern.sub(replace_tag, response_text)

        return resolved_text, cited_items

    def format_sources_for_client(
        self,
        chunks: List[RetrievedChunk],
        evidence_map: Dict[str, CitationItem],
    ) -> List[Dict[str, Any]]:
        """
        Formats retrieved document chunks into source items compatible with the Flutter UI.
        """
        sources = []
        for i, chunk in enumerate(chunks):
            tag = f"DOC_CHUNK_{i + 1}"
            subtitle = f"Page {chunk.page_number}" if chunk.page_number is not None else "Document"
            if chunk.section_title:
                subtitle += f" • {chunk.section_title}"

            sources.append({
                "title": chunk.document_name,
                "url": subtitle,
                "content": chunk.text,
                "type": "document",
                "document_id": chunk.document_id,
                "evidence_id": tag,
                "page_number": chunk.page_number,
                "section_title": chunk.section_title,
                "score": chunk.relevance_score,
            })
        return sources

    def build_debug_info(
        self,
        chunks: List[RetrievedChunk],
        final_context_prompt: str,
    ) -> Optional[RagDebugInfo]:
        """
        Builds development-only debug payload. Returns None if debug mode is disabled.
        """
        if not self.debug_mode:
            return None

        return RagDebugInfo(
            retrieved_chunks=[c.model_dump() for c in chunks],
            retrieval_scores=[c.relevance_score for c in chunks],
            document_ids=[c.document_id for c in chunks],
            page_numbers=[c.page_number for c in chunks],
            final_context_prompt=final_context_prompt,
        )
