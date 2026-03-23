"""Tests for services/flashcard_reader.py."""

import pytest

from src.services.flashcard_reader import FlashcardReader


@pytest.fixture
def reader():
    return FlashcardReader()


class TestGetUserStats:
    async def test_returns_empty_when_db_is_none(self, mock_db_none, reader):
        stats = await reader.get_user_stats("user1")
        assert stats.total_reviews == 0
        assert stats.accuracy == 0.0

    async def test_returns_empty_when_no_doc(self, mock_db, reader):
        mock_db.flashcard_stats.find_one.return_value = None
        stats = await reader.get_user_stats("user1")
        assert stats.total_reviews == 0

    async def test_computes_accuracy_correctly(self, mock_db, reader):
        mock_db.flashcard_stats.find_one.return_value = {
            "user_id": "user1",
            "total_reviews": 100,
            "total_correct": 75,
            "total_time_ms": 150000,
            "unique_cards": 20,
        }
        stats = await reader.get_user_stats("user1")
        assert stats.accuracy == 75.0
        assert stats.avg_response_time_ms == 1500.0
        assert stats.total_cards == 20
        assert stats.total_reviews == 100

    async def test_handles_zero_reviews(self, mock_db, reader):
        mock_db.flashcard_stats.find_one.return_value = {
            "user_id": "user1",
            "total_reviews": 0,
            "total_correct": 0,
            "total_time_ms": 0,
            "unique_cards": 0,
        }
        stats = await reader.get_user_stats("user1")
        assert stats.accuracy == 0.0
        assert stats.avg_response_time_ms == 0.0


class TestGetWeaknessTags:
    async def test_returns_empty_when_db_is_none(self, mock_db_none, reader):
        tags = await reader.get_weakness_tags("user1")
        assert tags == []

    async def test_returns_empty_when_no_doc(self, mock_db, reader):
        mock_db.flashcard_stats.find_one.return_value = None
        tags = await reader.get_weakness_tags("user1")
        assert tags == []

    async def test_returns_empty_when_no_tags_field(self, mock_db, reader):
        mock_db.flashcard_stats.find_one.return_value = {"user_id": "user1"}
        tags = await reader.get_weakness_tags("user1")
        assert tags == []

    async def test_returns_sorted_tags(self, mock_db, reader):
        mock_db.flashcard_stats.find_one.return_value = {
            "user_id": "user1",
            "weakness_tags": {"tactics": 5, "endgame": 10, "opening": 3},
        }
        tags = await reader.get_weakness_tags("user1")
        assert len(tags) == 3
        assert tags[0] == {"tag": "endgame", "count": 10}
        assert tags[1] == {"tag": "tactics", "count": 5}
        assert tags[2] == {"tag": "opening", "count": 3}

    async def test_caps_at_20_tags(self, mock_db, reader):
        many_tags = {f"tag_{i}": i for i in range(25)}
        mock_db.flashcard_stats.find_one.return_value = {
            "user_id": "user1",
            "weakness_tags": many_tags,
        }
        tags = await reader.get_weakness_tags("user1")
        assert len(tags) == 20
        # Highest count should be first
        assert tags[0]["count"] == 24


class TestUpdateFromEvent:
    async def test_noop_when_db_is_none(self, mock_db_none, reader):
        await reader.update_from_event(
            user_id="user1", quality=4, response_time_ms=1000,
            is_new_card=False, weakness_tags=[], flashcard_id=None,
        )
        # Should not raise

    async def test_increments_correct_when_quality_gte_3(self, mock_db, reader):
        await reader.update_from_event(
            user_id="user1", quality=3, response_time_ms=1000,
            is_new_card=False, weakness_tags=[], flashcard_id=None,
        )
        call_args = mock_db.flashcard_stats.update_one.call_args_list[0]
        inc_ops = call_args[0][1]["$inc"]
        assert inc_ops["total_correct"] == 1
        assert inc_ops["total_reviews"] == 1

    async def test_does_not_increment_correct_when_quality_lt_3(self, mock_db, reader):
        await reader.update_from_event(
            user_id="user1", quality=2, response_time_ms=1000,
            is_new_card=False, weakness_tags=[], flashcard_id=None,
        )
        call_args = mock_db.flashcard_stats.update_one.call_args_list[0]
        inc_ops = call_args[0][1]["$inc"]
        assert inc_ops["total_correct"] == 0
        assert inc_ops["total_reviews"] == 1

    async def test_adds_to_set_when_flashcard_id(self, mock_db, reader):
        mock_db.flashcard_stats.find_one.return_value = {
            "card_ids": ["card1", "card2"],
        }
        await reader.update_from_event(
            user_id="user1", quality=4, response_time_ms=500,
            is_new_card=False, weakness_tags=[], flashcard_id="card3",
        )
        first_call = mock_db.flashcard_stats.update_one.call_args_list[0]
        assert "$addToSet" in first_call[0][1]
        assert first_call[0][1]["$addToSet"]["card_ids"] == "card3"

    async def test_updates_weakness_tags(self, mock_db, reader):
        await reader.update_from_event(
            user_id="user1", quality=4, response_time_ms=500,
            is_new_card=False, weakness_tags=["tactics", "endgame"],
            flashcard_id=None,
        )
        # Second call should be the weakness tag increment
        tag_call = mock_db.flashcard_stats.update_one.call_args_list[1]
        inc_ops = tag_call[0][1]["$inc"]
        assert inc_ops["weakness_tags.tactics"] == 1
        assert inc_ops["weakness_tags.endgame"] == 1

    async def test_updates_unique_cards_count(self, mock_db, reader):
        mock_db.flashcard_stats.find_one.return_value = {
            "card_ids": ["c1", "c2", "c3"],
        }
        await reader.update_from_event(
            user_id="user1", quality=4, response_time_ms=500,
            is_new_card=False, weakness_tags=[], flashcard_id="c3",
        )
        # Last update_one should set unique_cards
        last_call = mock_db.flashcard_stats.update_one.call_args_list[-1]
        assert last_call[0][1]["$set"]["unique_cards"] == 3
