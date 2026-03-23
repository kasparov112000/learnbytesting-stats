"""Tests for services/repertoire_reader.py."""

import pytest

from src.services.repertoire_reader import RepertoireReader


@pytest.fixture
def reader():
    return RepertoireReader()


class TestGetUserStats:
    async def test_returns_empty_when_db_is_none(self, mock_db_none, reader):
        stats = await reader.get_user_stats("user1")
        assert stats.total_attempts == 0
        assert stats.accuracy == 0.0

    async def test_returns_empty_when_no_doc(self, mock_db, reader):
        mock_db.opening_stats.find_one.return_value = None
        stats = await reader.get_user_stats("user1")
        assert stats.total_attempts == 0

    async def test_computes_accuracy_correctly(self, mock_db, reader):
        mock_db.opening_stats.find_one.return_value = {
            "user_id": "user1",
            "total_attempts": 200,
            "total_correct": 150,
            "total_time_ms": 400000,
            "unique_positions": 30,
        }
        stats = await reader.get_user_stats("user1")
        assert stats.accuracy == 75.0
        assert stats.avg_time_to_move_ms == 2000.0
        assert stats.total_positions == 30
        assert stats.total_attempts == 200

    async def test_handles_zero_attempts(self, mock_db, reader):
        mock_db.opening_stats.find_one.return_value = {
            "user_id": "user1",
            "total_attempts": 0,
            "total_correct": 0,
            "total_time_ms": 0,
            "unique_positions": 0,
        }
        stats = await reader.get_user_stats("user1")
        assert stats.accuracy == 0.0
        assert stats.avg_time_to_move_ms == 0.0


class TestGetMistakePatterns:
    async def test_returns_empty_when_db_is_none(self, mock_db_none, reader):
        patterns = await reader.get_mistake_patterns("user1")
        assert patterns == []

    async def test_returns_empty_when_no_doc(self, mock_db, reader):
        mock_db.opening_stats.find_one.return_value = None
        patterns = await reader.get_mistake_patterns("user1")
        assert patterns == []

    async def test_returns_empty_when_no_patterns_field(self, mock_db, reader):
        mock_db.opening_stats.find_one.return_value = {"user_id": "user1"}
        patterns = await reader.get_mistake_patterns("user1")
        assert patterns == []

    async def test_returns_sorted_patterns(self, mock_db, reader):
        mock_db.opening_stats.find_one.return_value = {
            "user_id": "user1",
            "mistake_patterns": {
                "fen1::e4": {"count": 3, "fen": "fen1", "played_move": "e4", "opening_name": "Italian"},
                "fen2::d4": {"count": 7, "fen": "fen2", "played_move": "d4", "opening_name": "QGD"},
                "fen3::c4": {"count": 1, "fen": "fen3", "played_move": "c4", "opening_name": "English"},
            },
        }
        patterns = await reader.get_mistake_patterns("user1")
        assert len(patterns) == 3
        assert patterns[0]["count"] == 7
        assert patterns[0]["wrong_move"] == "d4"
        assert patterns[0]["opening"] == "QGD"
        assert patterns[1]["count"] == 3
        assert patterns[2]["count"] == 1

    async def test_caps_at_20_patterns(self, mock_db, reader):
        many_patterns = {
            f"fen{i}::move{i}": {"count": i, "fen": f"fen{i}", "played_move": f"move{i}", "opening_name": f"Opening{i}"}
            for i in range(25)
        }
        mock_db.opening_stats.find_one.return_value = {
            "user_id": "user1",
            "mistake_patterns": many_patterns,
        }
        patterns = await reader.get_mistake_patterns("user1")
        assert len(patterns) == 20
        assert patterns[0]["count"] == 24


class TestUpdateFromEvent:
    async def test_noop_when_db_is_none(self, mock_db_none, reader):
        await reader.update_from_event(
            user_id="user1", fen="some_fen", played_move="e4",
            was_correct=True, time_to_move=1000,
            opening_name="Italian", eco="C50",
        )

    async def test_increments_correct_when_was_correct(self, mock_db, reader):
        mock_db.opening_stats.find_one.return_value = {"position_fens": ["fen1"]}
        await reader.update_from_event(
            user_id="user1", fen="fen1", played_move="e4",
            was_correct=True, time_to_move=500,
            opening_name="Italian", eco="C50",
        )
        first_call = mock_db.opening_stats.update_one.call_args_list[0]
        inc_ops = first_call[0][1]["$inc"]
        assert inc_ops["total_correct"] == 1
        assert inc_ops["total_attempts"] == 1

    async def test_does_not_increment_correct_when_incorrect(self, mock_db, reader):
        mock_db.opening_stats.find_one.return_value = {"position_fens": ["fen1"]}
        await reader.update_from_event(
            user_id="user1", fen="fen1", played_move="e4",
            was_correct=False, time_to_move=500,
            opening_name="Italian", eco="C50",
        )
        first_call = mock_db.opening_stats.update_one.call_args_list[0]
        inc_ops = first_call[0][1]["$inc"]
        assert inc_ops["total_correct"] == 0

    async def test_records_mistake_pattern_for_incorrect(self, mock_db, reader):
        mock_db.opening_stats.find_one.return_value = {"position_fens": ["fen1"]}
        await reader.update_from_event(
            user_id="user1", fen="fen1_long_fen_string_here_padding", played_move="e4",
            was_correct=False, time_to_move=500,
            opening_name="Italian", eco="C50",
        )
        # Should have 3 update_one calls: main upsert, unique_positions set, mistake pattern
        assert mock_db.opening_stats.update_one.await_count == 3
        mistake_call = mock_db.opening_stats.update_one.call_args_list[2]
        update_op = mistake_call[0][1]
        assert "$inc" in update_op
        assert "$set" in update_op

    async def test_no_mistake_pattern_for_correct(self, mock_db, reader):
        mock_db.opening_stats.find_one.return_value = {"position_fens": ["fen1"]}
        await reader.update_from_event(
            user_id="user1", fen="fen1", played_move="e4",
            was_correct=True, time_to_move=500,
            opening_name="Italian", eco="C50",
        )
        # Should have only 2 update_one calls: main upsert + unique_positions set
        assert mock_db.opening_stats.update_one.await_count == 2

    async def test_adds_position_to_set(self, mock_db, reader):
        mock_db.opening_stats.find_one.return_value = {"position_fens": ["fen1"]}
        await reader.update_from_event(
            user_id="user1", fen="fen2", played_move="d4",
            was_correct=True, time_to_move=300,
            opening_name=None, eco=None,
        )
        first_call = mock_db.opening_stats.update_one.call_args_list[0]
        assert first_call[0][1]["$addToSet"]["position_fens"] == "fen2"
