"""Tests for analytics/trend_calculator.py."""

import pytest

from src.analytics.trend_calculator import TrendCalculator


@pytest.fixture
def tc():
    return TrendCalculator()


class TestGetTrends:
    async def test_returns_empty_when_db_is_none(self, mock_db_none, tc):
        result = await tc.get_trends("user1", "30d")
        assert result.user_id == "user1"
        assert result.period == "30d"
        assert result.accuracy_trend == []
        assert result.activity_trend == []

    async def test_returns_empty_when_no_docs(self, mock_db, tc):
        mock_db.unified_daily_activity._find_cursor.return_value = []
        result = await tc.get_trends("user1", "7d")
        assert result.accuracy_trend == []

    async def test_computes_activity_trend(self, mock_db, tc):
        mock_db.unified_daily_activity._find_cursor.return_value = [
            {"date": "2026-02-28", "total_activities": 10, "total_correct": 8,
             "flashcard_reviews": 5, "opening_attempts": 3, "chess_play_games": 2},
            {"date": "2026-03-01", "total_activities": 20, "total_correct": 15,
             "flashcard_reviews": 10, "opening_attempts": 5, "chess_play_games": 5},
        ]
        result = await tc.get_trends("user1", "30d")
        assert len(result.activity_trend) == 2
        assert result.activity_trend[0].date == "2026-02-28"
        assert result.activity_trend[0].value == 10.0
        assert result.activity_trend[1].value == 20.0

    async def test_computes_accuracy_trend(self, mock_db, tc):
        mock_db.unified_daily_activity._find_cursor.return_value = [
            {"date": "2026-02-28", "total_activities": 10, "total_correct": 8,
             "flashcard_reviews": 10},
            {"date": "2026-03-01", "total_activities": 20, "total_correct": 10,
             "flashcard_reviews": 20},
        ]
        result = await tc.get_trends("user1", "30d")
        assert len(result.accuracy_trend) == 2
        assert result.accuracy_trend[0].value == 80.0  # 8/10 * 100
        assert result.accuracy_trend[1].value == 50.0  # 10/20 * 100

    async def test_accuracy_zero_when_no_activities(self, mock_db, tc):
        mock_db.unified_daily_activity._find_cursor.return_value = [
            {"date": "2026-03-01", "total_activities": 0, "total_correct": 0,
             "flashcard_reviews": 0},
        ]
        result = await tc.get_trends("user1", "7d")
        assert result.accuracy_trend[0].value == 0.0

    async def test_computes_domain_breakdown(self, mock_db, tc):
        mock_db.unified_daily_activity._find_cursor.return_value = [
            {"date": "2026-02-28", "total_activities": 10, "total_correct": 5,
             "flashcard_reviews": 6, "opening_attempts": 3, "chess_play_games": 1},
            {"date": "2026-03-01", "total_activities": 10, "total_correct": 5,
             "flashcard_reviews": 4, "opening_attempts": 2, "chess_play_games": 4},
        ]
        result = await tc.get_trends("user1", "30d")
        assert "flashcards" in result.domain_breakdown
        assert result.domain_breakdown["flashcards"]["total"] == 10  # 6+4
        assert result.domain_breakdown["flashcards"]["daily_avg"] == 5.0
        assert "openings" in result.domain_breakdown
        assert result.domain_breakdown["openings"]["total"] == 5  # 3+2

    async def test_handles_all_period_values(self, mock_db, tc):
        mock_db.unified_daily_activity._find_cursor.return_value = []
        for period in ["7d", "30d", "90d", "365d"]:
            result = await tc.get_trends("user1", period)
            assert result.period == period

    async def test_defaults_to_30_for_unknown_period(self, mock_db, tc):
        mock_db.unified_daily_activity._find_cursor.return_value = []
        result = await tc.get_trends("user1", "unknown")
        assert result.period == "unknown"
