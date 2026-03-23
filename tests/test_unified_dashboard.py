"""Tests for services/unified_dashboard.py."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from src.models import (
    FlashcardStats,
    OpeningStats,
    ChessPlayStats,
    UnifiedUserAnalytics,
    Weakness,
    StudySuggestion,
)
from src.services.unified_dashboard import UnifiedDashboardService
from src.services.flashcard_enrichment import FlashcardAnalyticsSummary


@pytest.fixture
def svc():
    return UnifiedDashboardService()


class TestGetDashboard:
    async def test_returns_cached_when_fresh(self, svc):
        cached = UnifiedUserAnalytics(user_id="user1", total_activities=42)
        with patch(
            "src.services.unified_dashboard.cache_manager.get_cached",
            new_callable=AsyncMock, return_value=cached,
        ):
            result = await svc.get_dashboard("user1")
        assert result.total_activities == 42

    async def test_computes_fresh_when_no_cache(self, svc):
        with patch(
            "src.services.unified_dashboard.cache_manager.get_cached",
            new_callable=AsyncMock, return_value=None,
        ), patch.object(
            svc, "compute_dashboard",
            new_callable=AsyncMock,
            return_value=UnifiedUserAnalytics(user_id="user1", total_activities=99),
        ) as mock_compute:
            result = await svc.get_dashboard("user1")
        mock_compute.assert_awaited_once_with("user1")
        assert result.total_activities == 99


class TestComputeDashboard:
    @pytest.fixture
    def mock_deps(self, mock_db):
        """Patch all dependencies for compute_dashboard."""
        fc = FlashcardStats(total_reviews=100, accuracy=80.0, avg_response_time_ms=1500.0)
        op = OpeningStats(total_attempts=50, accuracy=70.0, avg_time_to_move_ms=2000.0)
        cp = ChessPlayStats(total_games=30, accuracy=60.0, total_correct=18, avg_time_to_answer_ms=3000.0)

        # Set up chess_play_events aggregate to return matching data for cp
        mock_db.chess_play_events._aggregate_cursor.return_value = [
            {"_id": None, "total": 30, "correct": 18, "avg_time": 3000.0}
        ]

        patches = {
            "fc": patch(
                "src.services.unified_dashboard.flashcard_reader.get_user_stats",
                new_callable=AsyncMock, return_value=fc,
            ),
            "op": patch(
                "src.services.unified_dashboard.repertoire_reader.get_user_stats",
                new_callable=AsyncMock, return_value=op,
            ),
            "streak": patch(
                "src.services.unified_dashboard.activity_aggregator.compute_streak",
                new_callable=AsyncMock, return_value={"current": 3, "longest": 7},
            ),
            "enrichment": patch(
                "src.services.unified_dashboard.fetch_flashcard_analytics",
                new_callable=AsyncMock, return_value=None,
            ),
            "weaknesses": patch(
                "src.services.unified_dashboard.weakness_analyzer.get_unified_weaknesses",
                new_callable=AsyncMock, return_value=[],
            ),
            "suggestions": patch(
                "src.services.unified_dashboard.weakness_analyzer.generate_suggestions",
                new_callable=AsyncMock, return_value=[],
            ),
            "cache_save": patch(
                "src.services.unified_dashboard.cache_manager.save_cached",
                new_callable=AsyncMock,
            ),
        }
        mocks = {}
        for key, p in patches.items():
            mocks[key] = p.start()
        yield mocks, fc, op, cp
        for p in patches.values():
            p.stop()

    async def test_aggregates_total_activities(self, svc, mock_deps):
        mocks, fc, op, cp = mock_deps
        result = await svc.compute_dashboard("user1")
        assert result.total_activities == 100 + 50 + 30  # fc + op + cp

    async def test_computes_weighted_accuracy(self, svc, mock_deps):
        mocks, fc, op, cp = mock_deps
        result = await svc.compute_dashboard("user1")
        # Weighted: (80*100 + 70*50 + 60*30) / (100+50+30) = (8000+3500+1800)/180 = 73.9
        assert abs(result.overall_accuracy - 73.9) < 0.2

    async def test_total_study_time(self, svc, mock_deps):
        mocks, fc, op, cp = mock_deps
        result = await svc.compute_dashboard("user1")
        expected_time = int(1500.0 * 100 + 2000.0 * 50 + 3000.0 * 30)
        assert result.total_study_time_ms == expected_time

    async def test_streak_from_activity_aggregator(self, svc, mock_deps):
        mocks, fc, op, cp = mock_deps
        result = await svc.compute_dashboard("user1")
        assert result.current_streak == 3
        assert result.longest_streak == 7

    async def test_enrichment_applied_to_fc_stats(self, svc, mock_deps):
        mocks, fc, op, cp = mock_deps

        enrichment = FlashcardAnalyticsSummary(
            total_cards=200, mastered_cards=50, studying_cards=30,
            new_cards=20, due_cards=15, cards_today=10,
            daily_goal=25, goal_progress=8,
            overall_accuracy=92.0, total_reviews=500,
            current_streak=5, longest_streak=10,
            rating_distribution={"again": 1, "hard": 2, "good": 10, "easy": 5},
        )
        mocks["enrichment"].return_value = enrichment

        result = await svc.compute_dashboard("user1")
        assert result.flashcard_stats.total_cards == 200
        assert result.flashcard_stats.mastered == 50
        assert result.flashcard_stats.due_today == 15
        assert result.flashcard_stats.accuracy == 92.0
        assert result.flashcard_stats.total_reviews == 500

    async def test_streak_reconciliation_with_enrichment(self, svc, mock_deps):
        mocks, fc, op, cp = mock_deps

        enrichment = FlashcardAnalyticsSummary(
            current_streak=5, longest_streak=10,
        )
        mocks["enrichment"].return_value = enrichment

        result = await svc.compute_dashboard("user1")
        # max(activity=3, enrichment=5) = 5
        assert result.current_streak == 5
        # max(activity=7, enrichment=10) = 10
        assert result.longest_streak == 10

    async def test_saves_to_cache(self, svc, mock_deps):
        mocks, fc, op, cp = mock_deps
        await svc.compute_dashboard("user1")
        mocks["cache_save"].assert_awaited_once()

    async def test_zero_accuracy_when_no_activities(self, mock_db, svc):
        mock_db.chess_play_events._aggregate_cursor.return_value = []
        with patch(
            "src.services.unified_dashboard.flashcard_reader.get_user_stats",
            new_callable=AsyncMock, return_value=FlashcardStats(),
        ), patch(
            "src.services.unified_dashboard.repertoire_reader.get_user_stats",
            new_callable=AsyncMock, return_value=OpeningStats(),
        ), patch(
            "src.services.unified_dashboard.activity_aggregator.compute_streak",
            new_callable=AsyncMock, return_value={"current": 0, "longest": 0},
        ), patch(
            "src.services.unified_dashboard.fetch_flashcard_analytics",
            new_callable=AsyncMock, return_value=None,
        ), patch(
            "src.services.unified_dashboard.weakness_analyzer.get_unified_weaknesses",
            new_callable=AsyncMock, return_value=[],
        ), patch(
            "src.services.unified_dashboard.weakness_analyzer.generate_suggestions",
            new_callable=AsyncMock, return_value=[],
        ), patch(
            "src.services.unified_dashboard.cache_manager.save_cached",
            new_callable=AsyncMock,
        ):
            result = await svc.compute_dashboard("user1")
        assert result.overall_accuracy == 0.0
        assert result.total_activities == 0


class TestGetChessPlayStats:
    async def test_returns_empty_when_db_is_none(self, mock_db_none, svc):
        result = await svc._get_chess_play_stats("user1")
        assert result.total_games == 0

    async def test_returns_empty_when_no_data(self, mock_db, svc):
        mock_db.chess_play_events._aggregate_cursor.return_value = []
        result = await svc._get_chess_play_stats("user1")
        assert result.total_games == 0

    async def test_aggregates_correctly(self, mock_db, svc):
        mock_db.chess_play_events._aggregate_cursor.return_value = [
            {"_id": None, "total": 50, "correct": 35, "avg_time": 2500.0}
        ]
        result = await svc._get_chess_play_stats("user1")
        assert result.total_games == 50
        assert result.total_correct == 35
        assert result.accuracy == 70.0
        assert result.avg_time_to_answer_ms == 2500.0
