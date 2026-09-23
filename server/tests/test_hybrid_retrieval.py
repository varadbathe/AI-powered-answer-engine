import math
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure server directory is on sys.path
SERVER_DIR = Path(__file__).resolve().parent.parent
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

from pydantic_models.document_models import DocumentStatus, RetrievedChunk
from repositories.document_repository import DocumentRepository
from services.bm25_store_service import BM25StoreService, bm25_tokenize
from services.document_service import DocumentService
from services.embedding_service import EmbeddingService
from services.rag_service import RagService
from services.retrievers.bm25_retriever import BM25Retriever
from services.retrievers.hybrid_retriever import HybridRetriever
from services.retrievers.retriever_factory import RetrieverFactory
from services.retrievers.score_normalizer import ScoreNormalizer
from services.retrievers.vector_retriever import VectorRetriever
from services.vector_store_service import VectorStoreService
from tests.test_document_rag import make_test_pdf



class TestHybridRetrieval(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_conversations.db")
        self.chroma_dir = os.path.join(self.temp_dir, "test_chroma")
        self.bm25_dir = os.path.join(self.temp_dir, "test_bm25")
        self.uploads_dir = os.path.join(self.temp_dir, "test_uploads")

        self.repository = DocumentRepository(db_path=self.db_path)
        self.vector_store = VectorStoreService(chroma_dir=self.chroma_dir, collection_name="test_hybrid_col")
        self.bm25_store = BM25StoreService(persistence_dir=self.bm25_dir)
        self.embedding_service = EmbeddingService()

        self.vector_retriever = VectorRetriever(self.embedding_service, self.vector_store)
        self.bm25_retriever = BM25Retriever(self.bm25_store)

        self.hybrid_retriever = HybridRetriever(
            vector_retriever=self.vector_retriever,
            bm25_retriever=self.bm25_retriever,
            vector_weight=0.60,
            bm25_weight=0.40,
            vector_candidate_k=10,
            bm25_candidate_k=10,
            final_top_k=5,
        )

        self.rag_service = RagService(self.hybrid_retriever, debug_mode=True)

        self.document_service = DocumentService(
            repository=self.repository,
            vector_store=self.vector_store,
            embedding_service=self.embedding_service,
            bm25_store=self.bm25_store,
            uploads_dir=self.uploads_dir,
            chunk_size=300,
            chunk_overlap=50,
        )

    def tearDown(self):
        self.repository.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # -------------------------------------------------------------------------
    # 1. test_bm25_retrieval
    # -------------------------------------------------------------------------
    def test_bm25_retrieval(self):
        """Verifies basic BM25 keyword retrieval finds relevant chunk."""
        chunks = [
            {
                "chunk_id": "c1",
                "document_id": "d1",
                "document_name": "astronomy.txt",
                "chunk_index": 0,
                "page_number": 1,
                "section_title": None,
                "evidence_id": "c1",
                "text": "The James Webb Space Telescope observes deep infrared galaxies and cosmic nebulae.",
            },
            {
                "chunk_id": "c2",
                "document_id": "d2",
                "document_name": "culinary.txt",
                "chunk_index": 0,
                "page_number": 1,
                "section_title": None,
                "evidence_id": "c2",
                "text": "Baking sourdough bread requires fermented starter and high hydration dough.",
            },
        ]
        self.bm25_store.add_chunks(chunks)

        results = self.bm25_retriever.retrieve("James Webb telescope infrared", top_k=2)
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0].chunk_id, "c1")
        self.assertTrue(results[0].bm25_retrieved)
        self.assertGreater(results[0].relevance_score, 0.0)

    # -------------------------------------------------------------------------
    # 2. test_exact_keyword_retrieval
    # -------------------------------------------------------------------------
    def test_exact_keyword_retrieval(self):
        """Verifies technical terms preservation: CYP3A4, IL-6, B12, COVID-19, GPT-5.6."""
        technical_chunks = [
            {
                "chunk_id": "c_cyp",
                "document_id": "doc_med",
                "document_name": "pharma.txt",
                "chunk_index": 0,
                "evidence_id": "c_cyp",
                "text": "Strong CYP3A4 inhibition elevates plasma levels of co-administered substrates.",
            },
            {
                "chunk_id": "c_il6",
                "document_id": "doc_med",
                "document_name": "pharma.txt",
                "chunk_index": 1,
                "evidence_id": "c_il6",
                "text": "In patients with acute COVID-19 infection, severe pulmonary damage is mediated by IL-6.",
            },
            {
                "chunk_id": "c_b12",
                "document_id": "doc_med",
                "document_name": "pharma.txt",
                "chunk_index": 2,
                "evidence_id": "c_b12",
                "text": "Methylcobalamin is a bioactive form of vitamin B12 essential for nerve sheath health.",
            },
            {
                "chunk_id": "c_gpt",
                "document_id": "doc_tech",
                "document_name": "tech.txt",
                "chunk_index": 0,
                "evidence_id": "c_gpt",
                "text": "The release of GPT-5.6 improved complex multimodal reasoning benchmarks significantly.",
            },
        ]
        self.bm25_store.add_chunks(technical_chunks)

        # Test CYP3A4
        res_cyp = self.bm25_retriever.retrieve("CYP3A4 inhibition", top_k=1)
        self.assertEqual(len(res_cyp), 1)
        self.assertEqual(res_cyp[0].chunk_id, "c_cyp")

        # Test IL-6 and COVID-19
        res_il6 = self.bm25_retriever.retrieve("IL-6 COVID-19", top_k=1)
        self.assertEqual(len(res_il6), 1)
        self.assertEqual(res_il6[0].chunk_id, "c_il6")

        # Test B12
        res_b12 = self.bm25_retriever.retrieve("B12 vitamin", top_k=1)
        self.assertEqual(len(res_b12), 1)
        self.assertEqual(res_b12[0].chunk_id, "c_b12")

        # Test GPT-5.6
        res_gpt = self.bm25_retriever.retrieve("GPT-5.6 reasoning", top_k=1)
        self.assertEqual(len(res_gpt), 1)
        self.assertEqual(res_gpt[0].chunk_id, "c_gpt")

    # -------------------------------------------------------------------------
    # 3. test_semantic_retrieval_regression
    # -------------------------------------------------------------------------
    def test_semantic_retrieval_regression(self):
        """Verifies vector retrieval finds conceptually similar text without exact keywords."""
        doc = self.document_service.upload_and_ingest(
            "cardiology.txt",
            b"Myocardial infarction occurs when coronary blood supply is interrupted causing cardiac tissue death.",
        )
        # Query using synonyms/paraphrase without mentioning 'myocardial infarction'
        results = self.vector_retriever.retrieve("heart attack and blocked arteries", top_k=1)
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0].document_id, doc.document_id)
        self.assertTrue(results[0].vector_retrieved)
        self.assertGreater(results[0].relevance_score, 0.4)

    # -------------------------------------------------------------------------
    # 4. test_hybrid_retrieval
    # -------------------------------------------------------------------------
    def test_hybrid_retrieval(self):
        """Verifies hybrid retriever fuses semantic and lexical candidate signals."""
        doc1 = self.document_service.upload_and_ingest(
            "enzyme_research.txt",
            b"CYP3A4 is a key enzyme in the liver. Inhibiting CYP3A4 causes toxicity with statins.",
        )
        doc2 = self.document_service.upload_and_ingest(
            "general_biology.txt",
            b"Photosynthesis in plant leaves converts solar photons into chemical carbohydrates.",
        )

        results = self.hybrid_retriever.retrieve("CYP3A4 liver enzyme inhibition", top_k=2)
        self.assertGreater(len(results), 0)
        top = results[0]
        self.assertEqual(top.document_id, doc1.document_id)
        self.assertIsNotNone(top.hybrid_score)
        self.assertEqual(top.relevance_score, top.hybrid_score)

    # -------------------------------------------------------------------------
    # 5. test_score_normalization
    # -------------------------------------------------------------------------
    def test_score_normalization(self):
        """Verifies Min-Max normalization scales values to [0.0, 1.0]."""
        raw_scores = [10.0, 20.0, 30.0]
        normalized = ScoreNormalizer.min_max_normalize(raw_scores)
        self.assertEqual(normalized, [0.0, 0.5, 1.0])

        single_norm = ScoreNormalizer.normalize_single(20.0, 10.0, 30.0)
        self.assertEqual(single_norm, 0.5)

    # -------------------------------------------------------------------------
    # 6. test_equal_scores_no_division_by_zero
    # -------------------------------------------------------------------------
    def test_equal_scores_no_division_by_zero(self):
        """Verifies safe handling when max_score == min_score."""
        # Non-zero equal scores
        equal_pos = [15.0, 15.0, 15.0]
        norm_pos = ScoreNormalizer.min_max_normalize(equal_pos)
        self.assertEqual(norm_pos, [1.0, 1.0, 1.0])

        # Zero equal scores
        equal_zero = [0.0, 0.0]
        norm_zero = ScoreNormalizer.min_max_normalize(equal_zero)
        self.assertEqual(norm_zero, [0.0, 0.0])

        # Single element
        self.assertEqual(ScoreNormalizer.min_max_normalize([5.0]), [1.0])
        self.assertEqual(ScoreNormalizer.min_max_normalize([]), [])

    # -------------------------------------------------------------------------
    # 7. test_candidate_deduplication
    # -------------------------------------------------------------------------
    def test_candidate_deduplication(self):
        """Verifies chunks present in both candidate pools are deduplicated by chunk_id."""
        doc = self.document_service.upload_and_ingest(
            "dedup.txt",
            b"Kubernetes container orchestration deploys pods across worker nodes.",
        )
        results = self.hybrid_retriever.retrieve("Kubernetes container pods", top_k=5)

        # Check unique chunk IDs
        chunk_ids = [r.chunk_id for r in results]
        self.assertEqual(len(chunk_ids), len(set(chunk_ids)))

        # Find the matching chunk and check both flags
        matching = [r for r in results if r.document_id == doc.document_id]
        if matching:
            self.assertTrue(matching[0].vector_retrieved)
            self.assertTrue(matching[0].bm25_retrieved)

    # -------------------------------------------------------------------------
    # 8. test_document_isolation_bm25
    # -------------------------------------------------------------------------
    def test_document_isolation_bm25(self):
        """Verifies BM25 queries strictly respect document_ids filter."""
        doc_a = self.document_service.upload_and_ingest("doc_a.txt", b"Alpha protocol details.")
        doc_b = self.document_service.upload_and_ingest("doc_b.txt", b"Beta protocol details.")

        # Search for 'protocol' isolated to doc_a
        results_a = self.bm25_retriever.retrieve("protocol", top_k=5, document_ids=[doc_a.document_id])
        for r in results_a:
            self.assertEqual(r.document_id, doc_a.document_id)

        # Search for 'protocol' isolated to doc_b
        results_b = self.bm25_retriever.retrieve("protocol", top_k=5, document_ids=[doc_b.document_id])
        for r in results_b:
            self.assertEqual(r.document_id, doc_b.document_id)

    # -------------------------------------------------------------------------
    # 9. test_document_isolation_hybrid
    # -------------------------------------------------------------------------
    def test_document_isolation_hybrid(self):
        """Verifies hybrid queries strictly respect document_ids filter."""
        doc_a = self.document_service.upload_and_ingest("doc_a.txt", b"Quantum mechanics superposition states.")
        doc_b = self.document_service.upload_and_ingest("doc_b.txt", b"Classical thermodynamics heat transfer.")

        # Search for 'quantum superposition' isolated to doc_b (must NOT return doc_a)
        results = self.hybrid_retriever.retrieve("quantum superposition", top_k=5, document_ids=[doc_b.document_id])
        for r in results:
            self.assertEqual(r.document_id, doc_b.document_id)

    # -------------------------------------------------------------------------
    # 10. test_empty_bm25_results
    # -------------------------------------------------------------------------
    def test_empty_bm25_results(self):
        """Verifies that queries with no lexical overlap return an empty list safely."""
        self.document_service.upload_and_ingest("sample.txt", b"Medical radiology scans and diagnosis.")
        results = self.bm25_retriever.retrieve("xylophone zookeeper astronaut", top_k=5)
        self.assertEqual(results, [])

    # -------------------------------------------------------------------------
    # 11. test_empty_vector_results
    # -------------------------------------------------------------------------
    def test_empty_vector_results(self):
        """Verifies empty vector retrieval handles empty queries safely."""
        results = self.vector_retriever.retrieve("", top_k=5)
        self.assertEqual(results, [])

    # -------------------------------------------------------------------------
    # 12. test_hybrid_empty_results
    # -------------------------------------------------------------------------
    def test_hybrid_empty_results(self):
        """Verifies that when both retrievers return empty, hybrid retriever returns []."""
        results = self.hybrid_retriever.retrieve("", top_k=5)
        self.assertEqual(results, [])

        # Non-matching query against empty corpus
        empty_bm25 = BM25StoreService(persistence_dir=os.path.join(self.temp_dir, "empty_bm25"))
        empty_vector_store = VectorStoreService(chroma_dir=os.path.join(self.temp_dir, "empty_chroma"), collection_name="empty")
        empty_hybrid = HybridRetriever(
            VectorRetriever(self.embedding_service, empty_vector_store),
            BM25Retriever(empty_bm25),
        )
        self.assertEqual(empty_hybrid.retrieve("anything", top_k=5), [])

    # -------------------------------------------------------------------------
    # 13. test_hybrid_score_formula
    # -------------------------------------------------------------------------
    def test_hybrid_score_formula(self):
        """Verifies exact weighted formula: vector_weight * norm_vec + bm25_weight * norm_bm25."""
        mock_vec_retriever = MagicMock()
        mock_bm25_retriever = MagicMock()

        chunk = RetrievedChunk(
            chunk_id="test_c1",
            document_id="doc1",
            document_name="doc.txt",
            chunk_index=0,
            evidence_id="test_c1",
            text="Synthetic text for formula verification",
            relevance_score=0.80,
        )

        mock_vec_retriever.retrieve.return_value = [chunk]
        mock_bm25_retriever.retrieve.return_value = [chunk]

        custom_hybrid = HybridRetriever(
            vector_retriever=mock_vec_retriever,
            bm25_retriever=mock_bm25_retriever,
            vector_weight=0.60,
            bm25_weight=0.40,
        )

        results = custom_hybrid.retrieve("query", top_k=1)
        self.assertEqual(len(results), 1)

        # Single candidate in each pool normalizes to 1.0
        # 0.60 * 1.0 + 0.40 * 1.0 = 1.0
        self.assertAlmostEqual(results[0].relevance_score, 1.0, places=3)
        self.assertAlmostEqual(results[0].hybrid_score, 1.0, places=3)

    # -------------------------------------------------------------------------
    # 14. test_citation_preservation
    # -------------------------------------------------------------------------
    def test_citation_preservation(self):
        """Verifies that evidence IDs and citations resolve correctly using HybridRetriever."""
        pdf_bytes = make_test_pdf(["The survival rate exceeded ninety percent."])
        doc = self.document_service.upload_and_ingest("clinical_trial.pdf", pdf_bytes)

        chunks = self.rag_service.retrieve("survival rate exceeded", top_k=1)
        self.assertEqual(len(chunks), 1)

        context_str, evidence_map = self.rag_service.build_context(chunks)
        self.assertIn("[DOC_CHUNK_1]", context_str)
        self.assertIn("DOC_CHUNK_1", evidence_map)

        mock_llm_response = "The clinical trial showed positive outcomes [DOC_CHUNK_1]."
        resolved_text, cited_items = self.rag_service.resolve_citations(mock_llm_response, evidence_map)

        self.assertIn("[clinical_trial.pdf", resolved_text)
        self.assertEqual(len(cited_items), 1)
        self.assertEqual(cited_items[0].filename, "clinical_trial.pdf")


    # -------------------------------------------------------------------------
    # 15. test_chroma_persistence_regression
    # -------------------------------------------------------------------------
    def test_chroma_persistence_regression(self):
        """Verifies ChromaDB retains indexed chunks after vector store re-instantiation."""
        doc = self.document_service.upload_and_ingest("persist_vector.txt", b"Persistent vector embeddings text content.")
        
        # Re-instantiate VectorStoreService pointing to same directory
        reloaded_vector_store = VectorStoreService(chroma_dir=self.chroma_dir, collection_name="test_hybrid_col")
        reloaded_retriever = VectorRetriever(self.embedding_service, reloaded_vector_store)

        results = reloaded_retriever.retrieve("vector embeddings text", top_k=1)
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0].document_id, doc.document_id)

    # -------------------------------------------------------------------------
    # 16. test_bm25_persistence_after_restart
    # -------------------------------------------------------------------------
    def test_bm25_persistence_after_restart(self):
        """Verifies BM25 chunks and index reload deterministically after restart without pickle."""
        doc = self.document_service.upload_and_ingest("persist_bm25.txt", b"Persisted BM25 keywords for engine test.")

        # Re-instantiate BM25StoreService pointing to same directory
        reloaded_bm25_store = BM25StoreService(persistence_dir=self.bm25_dir)
        self.assertGreater(reloaded_bm25_store.count(), 0)

        reloaded_retriever = BM25Retriever(reloaded_bm25_store)
        results = reloaded_retriever.retrieve("keywords engine test", top_k=1)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].document_id, doc.document_id)

    # -------------------------------------------------------------------------
    # 17. test_bm25_document_deletion
    # -------------------------------------------------------------------------
    def test_bm25_document_deletion(self):
        """Verifies that deleting a document removes its chunks from the BM25 index."""
        doc = self.document_service.upload_and_ingest("to_delete.txt", b"UniqueDeletablePhraseBM25 content.")
        self.assertGreater(len(self.bm25_retriever.retrieve("UniqueDeletablePhraseBM25")), 0)

        # Delete document
        deleted = self.document_service.delete_document(doc.document_id)
        self.assertTrue(deleted)

        # BM25 should now return empty
        results = self.bm25_retriever.retrieve("UniqueDeletablePhraseBM25")
        self.assertEqual(results, [])

    # -------------------------------------------------------------------------
    # 18. test_bm25_reindex
    # -------------------------------------------------------------------------
    def test_bm25_reindex(self):
        """Verifies that reindexing updates the BM25 index and chunk contents."""
        doc = self.document_service.upload_and_ingest("reindex_doc.txt", b"Initial pre-reindex content.")

        # Reindex
        updated = self.document_service.reindex_document(doc.document_id)
        self.assertEqual(updated.status, DocumentStatus.READY)

        # Retrieve via BM25
        results = self.bm25_retriever.retrieve("pre-reindex", top_k=1)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].document_id, doc.document_id)

    # -------------------------------------------------------------------------
    # 19. test_no_relevant_context
    # -------------------------------------------------------------------------
    def test_no_relevant_context(self):
        """
        Verifies grounded behavior when:
        1. Zero candidates retrieved.
        2. Candidates exist but are all below the configured relevance threshold.
        In both cases, context is empty and no web fallback occurs.
        """
        # Case 1: Zero candidates retrieved
        zero_chunks = self.rag_service.retrieve("completely_unrelated_query_12345", top_k=5)
        ctx, evidence_map = self.rag_service.build_context(zero_chunks)
        self.assertEqual(ctx, "")
        self.assertEqual(evidence_map, {})
        client_sources = self.rag_service.format_sources_for_client(zero_chunks, evidence_map)
        self.assertEqual(client_sources, [])

        # Case 2: Candidates exist but are below relevance_threshold
        doc = self.document_service.upload_and_ingest("threshold_test.txt", b"Some general document content.")
        threshold_rag_service = RagService(
            retriever=self.hybrid_retriever,
            debug_mode=True,
            relevance_threshold=1.5,  # Unattainable threshold (max normalized score is 1.0)
        )
        filtered_chunks = threshold_rag_service.retrieve("general document content", top_k=5)
        self.assertEqual(filtered_chunks, [])
        ctx_filtered, evidence_filtered = threshold_rag_service.build_context(filtered_chunks)
        self.assertEqual(ctx_filtered, "")
        self.assertEqual(evidence_filtered, {})


    # -------------------------------------------------------------------------
    # 20. test_web_search_regression
    # -------------------------------------------------------------------------
    def test_web_search_regression(self):
        """Verifies that web search pipeline remains functional and separate from RAG."""
        from services.search_service import SearchService
        from services.sort_source_service import SortSourceService

        search_service = SearchService()
        sort_service = SortSourceService()

        # Mock tavily search call to test pipeline isolation without network/API key
        with patch.object(search_service, "web_search", return_value=[{"title": "Web Title", "url": "https://example.com", "content": "Web search content"}]):
            raw_results = search_service.web_search("Python news")
            self.assertEqual(len(raw_results), 1)

            sorted_results = sort_service.sort_sources("Python news", raw_results)
            self.assertEqual(len(sorted_results), 1)
            self.assertEqual(sorted_results[0]["title"], "Web Title")

    # -------------------------------------------------------------------------
    # 21. test_reindex_failure_preserves_previous_index (Correction 2)
    # -------------------------------------------------------------------------
    def test_reindex_failure_preserves_previous_index(self):
        """
        Verifies that if reindexing fails during parsing/chunking/embedding,
        the previous successful ChromaDB and BM25 index are NOT destroyed.
        """
        doc = self.document_service.upload_and_ingest(
            "safe_reindex.txt",
            b"Original working document content before failed reindex.",
        )

        # Verify initial retrieval succeeds
        initial_bm25 = self.bm25_retriever.retrieve("working document content", top_k=1)
        self.assertEqual(len(initial_bm25), 1)
        initial_vec = self.vector_retriever.retrieve("working document content", top_k=1)
        self.assertEqual(len(initial_vec), 1)

        # Corrupt file on disk to simulate parsing failure during reindexing
        with open(doc.storage_path, "wb") as f:
            f.write(b"")  # 0 bytes, causes EmptyDocumentError or CorruptedFileError

        with self.assertRaises(Exception):
            self.document_service.reindex_document(doc.document_id)

        # Verify document status marked FAILED in repository
        failed_doc = self.document_service.get_document(doc.document_id)
        self.assertIsNotNone(failed_doc)
        self.assertEqual(failed_doc.status, DocumentStatus.FAILED)

        # Verify previous working index in ChromaDB and BM25 still exists!
        after_bm25 = self.bm25_retriever.retrieve("working document content", top_k=1)
        self.assertEqual(len(after_bm25), 1, "Previous BM25 index must be preserved on reindex failure")

        after_vec = self.vector_retriever.retrieve("working document content", top_k=1)
        self.assertEqual(len(after_vec), 1, "Previous ChromaDB index must be preserved on reindex failure")


if __name__ == "__main__":
    unittest.main()
