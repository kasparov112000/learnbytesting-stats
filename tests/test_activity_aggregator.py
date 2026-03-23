"""Tests for analytics/activity_aggregator.py."""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from src.analytics.activity_aggregator import ActivityAggregator


@pytest.fixture
def agg():
    return ActivityAggregator()


class TestRecordFlashcardActivity:
    async def test_noop_when_db_is_none(self, mock_db_none, agg):
        await agg.record_flashcard_activity("user1", "2026-03-01")

    async def test_calls_upsert_with_correct_fields(self, mock_db, agg):
        await agg.record_flashcard_activity(
            "user1", "2026-03-01", reviews=1, correct=1, time_ms=1500,
        )
        mock_db.unified_daily_activity.update_one.assert_awaited_once()
        call_args = mock_db.unified_daily_activity.update_one.call_args
        assert call_args[0][0] == {"user_id": "user1", "date": "2026-03-01"}
        inc_ops = call_args[0][1]["$inc"]
        assert inc_ops["flashcard_reviews"] == 1
        assert inc_ops["flashcard_correct"] == 1
        assert inc_ops["flashcard_time_ms"] == 1500
        assert inc_ops["total_activities"] == 1
        assert inc_ops["total_correct"] == 1
        assert call_args[1]["upsert"] is True


class TestRecordOpeningActivity:
    async def test_calls_upsert_with_correct_fields(self, mock_db, agg):
        await agg.record_opening_activity(
            "user1", "2026-03-01", attempts=1, correct=0, time_ms=2000,
        )
        call_args = mock_db.unified_daily_activity.update_one.call_args
        inc_ops = call_args[0][1]["$inc"]
        assert inc_ops["opening_attempts"] == 1
        assert inc_ops["opening_correct"] == 0
        assert inc_ops["opening_time_ms"] == 2000
        assert inc_ops["total_activities"] == 1


class TestRecordChessPlayActivity:
    async def test_calls_upsert_with_correct_fields(self, mock_db, agg):
        await agg.record_chess_play_activity(
            "user1", "2026-03-01", games=1, correct=1, time_ms=3000,
        )
        call_args = mock_db.unified_daily_activity.update_one.call_args
        inc_ops = call_args[0][1]["$inc"]
        assert inc_ops["chess_play_games"] == 1
        assert inc_ops["chess_play_correct"] == 1
        assert inc_ops["chess_play_time_ms"] == 3000


class TestGetHeatmap:
    async def test_returns_empty_when_db_is_none(self, mock_db_none, agg):
        result = await agg.get_heatmap("user1")
        assert result == []

    async def test_returns_daily_activities(self, mock_db, agg):
        mock_db.unified_daily_activity._find_cursor.return_value = [
            {"user_id": "user1", "date": "2026-02-28", "flashcard_reviews": 5, "total_activities": 5},
            {"user_id": "user1", "date": "2026-03-01", "flashcard_reviews": 10, "total_activities": 10},
        ]
        result = await agg.get_heatmap("user1", days=30)
        assert len(result) == 2
        assert result[0].date == "2026-02-28"
        assert result[1].total_activities == 10


class TestComputeStreak:
    async def test_returns_zeros_when_db_is_none(self, mock_db_none, agg):
        result = await agg.compute_streak("user1")
        assert result == {"current": 0, "longest": 0}

    async def test_returns_zeros_when_no_data(self, mock_db, agg):
        mock_db.unified_daily_activity._find_cursor.return_value = []
        result = await agg.compute_streak("user1")
        assert result == {"current": 0, "longest": 0}

    async def test_computes_current_streak_ending_today(self, mock_db, agg):
        today = datetime.utcnow()
        dates = [
            (today - timedelta(days=i)).strftime("%Y-%m-%d")
            for i in range(5)
        ]
        mock_db.unified_daily_activity._find_cursor.return_value = [
            {"date": d} for d in dates
        ]
        result = await agg.compute_streak("user1")
        assert result["current"] == 5
        assert result["longest"] == 5

    async def test_computes_current_streak_ending_yesterday(self, mock_db, agg):
        today = datetime.utcnow()
        # Activity yesterday and day before, but not today
        dates = [
            (today - timedelta(days=i)).strftime("%Y-%m-%d")
            for i in range(1, 4)
        ]
        mock_db.unified_daily_activity._find_cursor.return_value = [
            {"date": d} for d in dates
        ]
        result = await agg.compute_streak("user1")
        assert result["current"] == 3

    async def test_no_current_streak_when_gap(self, mock_db, agg):
        today = datetime.utcnow()
        # Activity 3 and 4 days ago only
        dates = [
            (today - timedelta(days=3)).strftime("%Y-%m-%d"),
            (today - timedelta(days=4)).strftime("%Y-%m-%d"),
        ]
        mock_db.unified_daily_activity._find_cursor.return_value = [
            {"date": d} for d in dates
        ]
        result = await agg.compute_streak("user1")
        assert result["current"] == 0
        assert result["longest"] == 2

    async def test_longest_streak_across_gaps(self, mock_db, agg):
        today = datetime.utcnow()
        # Current: 2 days (today + yesterday)
        # Past: 4 consecutive days ending 10 days ago
        current_dates = [
            (today - timedelta(days=0)).strftime("%Y-%m-%d"),
            (today - timedelta(days=1)).strftime("%Y-%m-%d"),
        ]
        past_dates = [
            (today - timedelta(days=10 + i)).strftime("%Y-%m-%d")
            for i in range(4)
        ]
        all_dates = current_dates + past_dates
        mock_db.unified_daily_activity._find_cursor.return_value = [
            {"date": d} for d in all_dates
        ]
        result = await agg.compute_streak("user1")
        assert result["current"] == 2
        assert result["longest"] == 4
