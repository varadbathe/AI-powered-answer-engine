import os
import sys
import unittest

# Add server directory to path
server_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if server_dir not in sys.path:
    sys.path.insert(0, server_dir)

from repositories.conversation_repository import ConversationRepository
from services.conversation_service import ConversationService


class TestConversationRepositoryAndService(unittest.TestCase):
    def setUp(self):
        # Use in-memory SQLite database for test isolation
        self.repo = ConversationRepository(db_path=":memory:")
        self.service = ConversationService(repository=self.repo)

    def tearDown(self):
        self.repo.close()

    def test_create_and_get_conversation(self):
        conv = self.repo.create_conversation("Test Title")
        self.assertIsNotNone(conv["id"])
        self.assertEqual(conv["title"], "Test Title")

        fetched = self.repo.get_conversation(conv["id"])
        self.assertIsNotNone(fetched)
        assert fetched is not None
        self.assertEqual(fetched["id"], conv["id"])
        self.assertEqual(fetched["title"], "Test Title")

    def test_list_conversations_order(self):
        conv1 = self.repo.create_conversation("Conv 1")
        conv2 = self.repo.create_conversation("Conv 2")

        listed = self.repo.list_conversations()
        self.assertGreaterEqual(len(listed), 2)
        # Most recently created or updated should come first
        ids = [c["id"] for c in listed]
        self.assertIn(conv1["id"], ids)
        self.assertIn(conv2["id"], ids)

    def test_rename_conversation(self):
        conv = self.repo.create_conversation("Original Title")
        renamed = self.repo.rename_conversation(conv["id"], "Updated Title")
        self.assertIsNotNone(renamed)
        assert renamed is not None
        self.assertEqual(renamed["title"], "Updated Title")

        # Non-existent conversation rename returns None
        self.assertIsNone(self.repo.rename_conversation("non-existent-id", "Title"))

    def test_delete_conversation_cascade(self):
        conv = self.repo.create_conversation("To Delete")
        self.repo.save_turn_atomic(
            conversation_id=conv["id"],
            turn_index=0,
            user_query="What is quantum computing?",
            assistant_answer="Quantum computing is...",
            sources=[{"title": "Wiki", "url": "https://wiki.org"}],
            follow_ups=["How does it work?"],
        )

        messages = self.repo.get_messages(conv["id"])
        self.assertEqual(len(messages), 2)

        deleted = self.repo.delete_conversation(conv["id"])
        self.assertTrue(deleted)

        # Conversation should not exist
        self.assertIsNone(self.repo.get_conversation(conv["id"]))
        # Messages should be cascade deleted
        self.assertEqual(len(self.repo.get_messages(conv["id"])), 0)

    def test_deterministic_auto_titling(self):
        # Normal query
        self.assertEqual(
            self.service.generate_title_from_query("What is machine learning?"),
            "What is machine learning?",
        )
        # Query with extra spaces and newlines
        self.assertEqual(
            self.service.generate_title_from_query("  What   is \n  Python?   "),
            "What is Python?",
        )
        # Query exceeding 60 characters
        long_query = "This is an extremely long query that goes on and on about artificial intelligence algorithms and advanced neural networks"
        title = self.service.generate_title_from_query(long_query, max_length=50)
        self.assertTrue(title.endswith("..."))
        self.assertLessEqual(len(title), 53)
        # Empty query
        self.assertEqual(self.service.generate_title_from_query(""), "New Conversation")

    def test_get_or_create_conversation(self):
        # When id is None, creates a new one
        conv1 = self.service.get_or_create_conversation(None, "First search query")
        self.assertEqual(conv1["title"], "First search query")

        # When id exists, returns existing
        conv2 = self.service.get_or_create_conversation(conv1["id"], "Different query")
        self.assertEqual(conv2["id"], conv1["id"])
        self.assertEqual(conv2["title"], "First search query")

    def test_multiple_turns_consistency_and_detail(self):
        conv = self.repo.create_conversation("Multi-turn Thread")
        conv_id = conv["id"]

        # Turn 0
        idx0 = self.service.save_completed_turn(
            conversation_id=conv_id,
            user_query="Who founded Apple?",
            assistant_answer="Apple was founded by Steve Jobs, Steve Wozniak, and Ronald Wayne.",
            sources=[{"title": "Apple History", "url": "https://apple.com"}],
            follow_ups=["When was it founded?", "What was the first product?"],
        )
        self.assertEqual(idx0, 0)

        # Turn 1
        idx1 = self.service.save_completed_turn(
            conversation_id=conv_id,
            user_query="When was it founded?",
            assistant_answer="It was founded on April 1, 1976.",
            sources=[{"title": "Apple Inc.", "url": "https://en.wikipedia.org"}],
            follow_ups=["Where was it founded?"],
        )
        self.assertEqual(idx1, 1)

        # Check raw messages
        messages = self.repo.get_messages(conv_id)
        self.assertEqual(len(messages), 4)
        self.assertEqual(messages[0]["role"], "user")
        self.assertEqual(messages[0]["turn_index"], 0)
        self.assertEqual(messages[1]["role"], "assistant")
        self.assertEqual(messages[1]["turn_index"], 0)
        self.assertEqual(messages[2]["role"], "user")
        self.assertEqual(messages[2]["turn_index"], 1)
        self.assertEqual(messages[3]["role"], "assistant")
        self.assertEqual(messages[3]["turn_index"], 1)

        # Check detail compilation
        detail = self.service.get_conversation_detail(conv_id)
        self.assertIsNotNone(detail)
        assert detail is not None
        self.assertEqual(detail.id, conv_id)
        self.assertEqual(len(detail.turns), 2)

        # Turn 0 verification
        turn0 = detail.turns[0]
        self.assertEqual(turn0.turn_index, 0)
        self.assertEqual(turn0.question, "Who founded Apple?")
        self.assertIn("Steve Jobs", turn0.answer)
        self.assertEqual(len(turn0.sources), 1)
        self.assertEqual(len(turn0.follow_ups), 2)

        # Turn 1 verification
        turn1 = detail.turns[1]
        self.assertEqual(turn1.turn_index, 1)
        self.assertEqual(turn1.question, "When was it founded?")
        self.assertIn("1976", turn1.answer)
        self.assertEqual(len(turn1.sources), 1)
        self.assertEqual(len(turn1.follow_ups), 1)


if __name__ == "__main__":
    unittest.main()
