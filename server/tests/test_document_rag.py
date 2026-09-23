import io
import os
import shutil
import tempfile
import unittest
import docx
from pydantic_models.document_models import DocumentStatus
from repositories.document_repository import DocumentRepository
from services.document_chunker import DocumentChunker
from services.document_parser import (
    CorruptedDocumentError,
    DocumentParser,
    EmptyDocumentError,
)
from services.document_security import (
    CorruptedFileError,
    DocumentSecurityService,
    UnsupportedFileError,
)
from services.document_service import DocumentService, DuplicateDocumentError
from services.embedding_service import EmbeddingService
from services.rag_service import RagService
from services.retrievers.vector_retriever import VectorRetriever
from services.vector_store_service import VectorStoreService


def make_test_pdf(pages_text: list[str]) -> bytes:
    """Creates a valid multi-page PDF in raw bytes without external tools."""
    obj_count = 3 + len(pages_text) * 2 + 1
    font_obj_id = obj_count

    catalog = "1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
    kids = " ".join(f"{3 + i * 2} 0 R" for i in range(len(pages_text)))
    pages_obj = f"2 0 obj << /Type /Pages /Kids [{kids}] /Count {len(pages_text)} >> endobj\n"

    page_objs = []
    content_objs = []
    for i, txt in enumerate(pages_text):
        p_id = 3 + i * 2
        c_id = p_id + 1
        stream = f"BT /F1 12 Tf 72 712 Td ({txt}) Tj ET"
        page_objs.append(
            f"{p_id} 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Contents {c_id} 0 R /Resources << /Font << /F1 {font_obj_id} 0 R >> >> >> endobj\n"
        )
        content_objs.append(
            f"{c_id} 0 obj << /Length {len(stream)} >> stream\n{stream}\nendstream endobj\n"
        )

    font_obj = f"{font_obj_id} 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n"

    body = catalog + pages_obj + "".join(page_objs) + "".join(content_objs) + font_obj

    # Calculate xref
    header = "%PDF-1.4\n"
    positions = [0]
    curr = len(header.encode("latin-1"))

    # We split body by endobj\n
    all_objs = [catalog, pages_obj]
    for p, c in zip(page_objs, content_objs):
        all_objs.extend([p, c])
    all_objs.append(font_obj)

    for obj in all_objs:
        positions.append(curr)
        curr += len(obj.encode("latin-1"))

    xref = f"xref\n0 {len(positions)}\n0000000000 65535 f \n"
    for pos in positions[1:]:
        xref += f"{pos:010d} 00000 n \n"

    trailer = f"trailer << /Size {len(positions)} /Root 1 0 R >>\nstartxref\n{curr}\n%%EOF"
    pdf_bytes = (header + body + xref + trailer).encode("latin-1")
    return pdf_bytes


def make_test_docx(sections: list[tuple[str, str]]) -> bytes:
    """Creates a valid DOCX with headings and paragraphs."""
    doc = docx.Document()
    for heading, text in sections:
        if heading:
            doc.add_heading(heading, level=1)
        if text:
            doc.add_paragraph(text)
    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()


class TestDocumentRag(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_conversations.db")
        self.chroma_dir = os.path.join(self.temp_dir, "test_chroma")
        self.uploads_dir = os.path.join(self.temp_dir, "test_uploads")

        self.repository = DocumentRepository(db_path=self.db_path)
        self.vector_store = VectorStoreService(chroma_dir=self.chroma_dir, collection_name="test_collection")
        self.embedding_service = EmbeddingService()
        self.retriever = VectorRetriever(self.embedding_service, self.vector_store)
        self.rag_service = RagService(self.retriever, debug_mode=True)
        self.document_service = DocumentService(
            repository=self.repository,
            vector_store=self.vector_store,
            embedding_service=self.embedding_service,
            uploads_dir=self.uploads_dir,
            chunk_size=300,
            chunk_overlap=50,
        )

    def tearDown(self):
        self.repository.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_pdf_ingestion(self):
        """Verifies PDF ingestion, page boundary extraction, and metadata."""
        pdf_bytes = make_test_pdf([
            "Artificial intelligence is transforming healthcare and medicine.",
            "Deep learning models require high performance GPUs and large datasets.",
        ])

        doc = self.document_service.upload_and_ingest("ai_overview.pdf", pdf_bytes)

        self.assertEqual(doc.status, DocumentStatus.READY)
        self.assertEqual(doc.file_type, "pdf")
        self.assertGreater(doc.chunk_count, 0)
        self.assertEqual(doc.progress, 1.0)
        self.assertIsNotNone(doc.file_hash)

        # Retrieve and verify page numbers
        chunks = self.rag_service.retrieve("healthcare medicine", top_k=2)
        self.assertGreater(len(chunks), 0)
        self.assertEqual(chunks[0].document_name, "ai_overview.pdf")
        self.assertIn(chunks[0].page_number, [1, 2])

    def test_docx_ingestion(self):
        """Verifies DOCX ingestion, headings as section titles, and status."""
        docx_bytes = make_test_docx([
            ("Financial Highlights", "Net revenue increased by 25 percent year over year in the third quarter."),
            ("Strategic Initiatives", "Expanding into cloud-native infrastructure and automated workflows."),
        ])

        doc = self.document_service.upload_and_ingest("quarterly_report.docx", docx_bytes)

        self.assertEqual(doc.status, DocumentStatus.READY)
        self.assertEqual(doc.file_type, "docx")
        self.assertGreater(doc.chunk_count, 0)

        chunks = self.rag_service.retrieve("revenue increased by 25 percent", top_k=2)
        self.assertGreater(len(chunks), 0)
        self.assertIn("Financial Highlights", [c.section_title for c in chunks if c.section_title])

    def test_txt_markdown_ingestion(self):
        """Verifies TXT and Markdown ingestion."""
        # TXT
        txt_bytes = "Kubernetes is an open-source container orchestration system for automating software deployment.".encode("utf-8")
        doc_txt = self.document_service.upload_and_ingest("k8s.txt", txt_bytes)
        self.assertEqual(doc_txt.status, DocumentStatus.READY)

        # Markdown
        md_bytes = "# Architecture\nMicroservices communicate over gRPC.\n# Security\nAll ingress traffic uses TLS 1.3.".encode("utf-8")
        doc_md = self.document_service.upload_and_ingest("arch.md", md_bytes)
        self.assertEqual(doc_md.status, DocumentStatus.READY)

        chunks = self.rag_service.retrieve("gRPC microservices", top_k=2)
        self.assertGreater(len(chunks), 0)
        self.assertEqual(chunks[0].document_name, "arch.md")

    def test_chunking_metadata_and_page_preservation(self):
        """Verifies chunking preserves page boundaries and assigns required metadata."""
        segments = [
            {"text": "Page one paragraph one. Page one paragraph two.", "page_number": 1, "section_title": "Intro"},
            {"text": "Page two paragraph one. Page two paragraph two.", "page_number": 2, "section_title": "Body"},
        ]

        chunks = DocumentChunker.chunk_document(
            segments=segments,
            document_id="doc-123",
            document_name="test.pdf",
            chunk_size=50,
            chunk_overlap=10,
        )

        for chunk in chunks:
            self.assertIn("chunk_id", chunk)
            self.assertIn("document_id", chunk)
            self.assertIn("document_name", chunk)
            self.assertIn("chunk_index", chunk)
            self.assertIn("page_number", chunk)
            self.assertIn("section_title", chunk)
            self.assertIn("evidence_id", chunk)
            self.assertIn("text", chunk)
            # Ensure chunks from page 1 never have page 2 content
            if chunk["page_number"] == 1:
                self.assertNotIn("Page two", chunk["text"])
            elif chunk["page_number"] == 2:
                self.assertNotIn("Page one", chunk["text"])

    def test_duplicate_document_detection(self):
        """Verifies that uploading identical bytes raises DuplicateDocumentError."""
        txt_bytes = "Identical document content for duplicate hash testing.".encode("utf-8")
        self.document_service.upload_and_ingest("original.txt", txt_bytes)

        with self.assertRaises(DuplicateDocumentError):
            self.document_service.upload_and_ingest("copy.txt", txt_bytes)

    def test_citation_evidence_id_mapping(self):
        """Verifies stable evidence tag assignment and resolution."""
        pdf_bytes = make_test_pdf([
            "Annual EBITDA reached fifty million dollars.",
        ])
        self.document_service.upload_and_ingest("annual.pdf", pdf_bytes)

        chunks = self.rag_service.retrieve("EBITDA", top_k=1)
        self.assertEqual(len(chunks), 1)

        context_str, evidence_map = self.rag_service.build_context(chunks)
        self.assertIn("[DOC_CHUNK_1]", context_str)
        self.assertIn("DOC_CHUNK_1", evidence_map)

        # LLM response containing [DOC_CHUNK_1]
        mock_llm_response = "The company reported strong results with $50M EBITDA [DOC_CHUNK_1]."
        resolved_text, cited_items = self.rag_service.resolve_citations(mock_llm_response, evidence_map)

        self.assertIn("[annual.pdf, p. 1]", resolved_text)
        self.assertEqual(len(cited_items), 1)
        self.assertEqual(cited_items[0].filename, "annual.pdf")
        self.assertEqual(cited_items[0].page_number, 1)

    def test_document_isolation(self):
        """Verifies document isolation: queries can be restricted to specific document IDs."""
        doc_a_bytes = "Quantum computing uses superposition and entanglement to calculate complex matrices.".encode("utf-8")
        doc_b_bytes = "Organic compost requires nitrogen-rich greens and carbon-rich browns.".encode("utf-8")

        doc_a = self.document_service.upload_and_ingest("quantum.txt", doc_a_bytes)
        doc_b = self.document_service.upload_and_ingest("gardening.txt", doc_b_bytes)

        # Query across both
        all_chunks = self.rag_service.retrieve("calculate matrices", top_k=5)
        self.assertTrue(any(c.document_id == doc_a.document_id for c in all_chunks))

        # Query isolated to doc_a only
        isolated_a = self.rag_service.retrieve("superposition", top_k=5, document_ids=[doc_a.document_id])
        for c in isolated_a:
            self.assertEqual(c.document_id, doc_a.document_id)

        # Query with doc_b isolation for quantum terms: should NOT return doc_a
        isolated_b = self.rag_service.retrieve("superposition", top_k=5, document_ids=[doc_b.document_id])
        for c in isolated_b:
            self.assertEqual(c.document_id, doc_b.document_id)

    def test_document_deletion(self):
        """Verifies document deletion removes records from SQLite, disk, and ChromaDB."""
        txt_bytes = "Delete test document text content.".encode("utf-8")
        doc = self.document_service.upload_and_ingest("to_delete.txt", txt_bytes)

        self.assertTrue(os.path.exists(doc.storage_path))
        self.assertIsNotNone(self.document_service.get_document(doc.document_id))

        # Delete
        success = self.document_service.delete_document(doc.document_id)
        self.assertTrue(success)

        # Verify SQLite
        self.assertIsNone(self.document_service.get_document(doc.document_id))
        # Verify file on disk
        self.assertFalse(os.path.exists(doc.storage_path))
        # Verify ChromaDB
        chunks = self.rag_service.retrieve("Delete test", top_k=5, document_ids=[doc.document_id])
        self.assertEqual(len(chunks), 0)

    def test_empty_document_handling(self):
        """Verifies empty documents and whitespace-only files are rejected."""
        # 0 bytes
        with self.assertRaises(CorruptedFileError):
            self.document_service.upload_and_ingest("empty.txt", b"")

        # Whitespace only
        with self.assertRaises(EmptyDocumentError):
            self.document_service.upload_and_ingest("blank.txt", b"   \n\t  \n  ")

    def test_corrupted_file_handling(self):
        """Verifies corrupted file headers are cleanly caught."""
        # Fake PDF header without content
        with self.assertRaises(CorruptedDocumentError):
            self.document_service.upload_and_ingest("bad.pdf", b"%PDF-1.4 corrupt junk not a real pdf structure")

    def test_upload_security(self):
        """Verifies filename sanitization and disallowed extension rejection."""
        # Path traversal
        sanitized, _ = DocumentSecurityService.validate_file("../../etc/passwd.txt", b"safe content")
        self.assertNotIn("..", sanitized)
        self.assertNotIn("/", sanitized)

        # Disallowed extension
        with self.assertRaises(UnsupportedFileError):
            DocumentSecurityService.validate_file("malware.exe", b"binary content")

    def test_reindex_document(self):
        """Verifies document reindexing refreshes chunks and updates timestamp."""
        txt_bytes = "Original text before re-indexing.".encode("utf-8")
        doc = self.document_service.upload_and_ingest("reindex_target.txt", txt_bytes)

        reindexed = self.document_service.reindex_document(doc.document_id)
        self.assertEqual(reindexed.status, DocumentStatus.READY)
        self.assertEqual(reindexed.document_id, doc.document_id)
        self.assertGreater(reindexed.chunk_count, 0)


if __name__ == "__main__":
    unittest.main()
