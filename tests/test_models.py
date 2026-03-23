"""Tests for Pydantic models validation."""

import pytest
from datetime import datetime

from src.models import (
    EventType,
    MasteryLevel,
    FlashcardReviewEvent,
    OpeningAttemptEvent,
    ChessPlayEvent,
    FlashcardStats,
    OpeningStats,
    ChessPlayStats,
    Weakness,
    StudySuggestion,
    UnifiedUserAnalytics,
    DailyActivity,
    TrendPoint,
    TrendResponse,
    HealthResponse,
    HeatmapResponse,
    WeaknessResponse,
    SuggestionResponse,
    EventAck,
    Correlation,
)
from pydantic import ValidationError


class TestEnums:
    def test_event_type_values(self):
        assert EventType.FLASHCARD_REVIEW == "flashcard_review"
        assert EventType.OPENING_ATTEMPT == "opening_attempt"
        assert EventType.CHESS_PLAY == "chess_play"

    def test_mastery_level_values(self):
        assert MasteryLevel.NEW == "new"
        assert MasteryLevel.LEARNING == "learning"
        assert MasteryLevel.FAMILIAR == "familiar"
        assert MasteryLevel.MASTERED == "mastered"


class TestFlashcardReviewEvent:
    def test_valid_event(self):
        event = FlashcardReviewEvent(quality=4, user_id="user1")
        assert event.quality == 4
        assert event.user_id == "user1"
        assert event.is_new_card is False
        assert event.weakness_tags == []
        assert isinstance(event.timestamp, datetime)

    def test_quality_min_boundary(self):
        event = FlashcardReviewEvent(quality=0)
        assert event.quality == 0

    def test_quality_max_boundary(self):
        event = FlashcardReviewEvent(quality=5)
        assert event.quality == 5

    def test_quality_below_min_rejected(self):
        with pytest.raises(ValidationError):
            FlashcardReviewEvent(quality=-1)

    def test_quality_above_max_rejected(self):
        with pytest.raises(ValidationError):
            FlashcardReviewEvent(quality=6)

    def test_optional_fields_default_none(self):
        event = FlashcardReviewEvent(quality=3)
        assert event.user_id is None
        assert event.session_id is None
        assert event.flashcard_id is None
        assert event.response_time_ms is None
        assert event.category_id is None


class TestOpeningAttemptEvent:
    def test_valid_event(self):
        event = OpeningAttemptEvent(user_id="u1", fen="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR", was_correct=True)
        assert event.user_id == "u1"
        assert event.was_correct is True
        assert event.played_move is None

    def test_missing_required_fields(self):
        with pytest.raises(ValidationError):
            OpeningAttemptEvent(fen="some_fen", was_correct=True)  # missing user_id


class TestChessPlayEvent:
    def test_valid_event(self):
        event = ChessPlayEvent(user_id="u1", was_correct=False)
        assert event.was_correct is False
        assert event.difficulty is None

    def test_missing_required_fields(self):
        with pytest.raises(ValidationError):
            ChessPlayEvent(was_correct=True)  # missing user_id


class TestStatsModels:
    def test_flashcard_stats_defaults(self):
        stats = FlashcardStats()
        assert stats.total_cards == 0
        assert stats.mastered == 0
        assert stats.accuracy == 0.0
        assert stats.due_today == 0
        assert stats.daily_goal == 20
        assert stats.rating_distribution == {"again": 0, "hard": 0, "good": 0, "easy": 0}

    def test_opening_stats_defaults(self):
        stats = OpeningStats()
        assert stats.total_positions == 0
        assert stats.accuracy == 0.0
        assert stats.total_attempts == 0

    def test_chess_play_stats_defaults(self):
        stats = ChessPlayStats()
        assert stats.total_games == 0
        assert stats.accuracy == 0.0
        assert stats.total_correct == 0


class TestUnifiedUserAnalytics:
    def test_defaults(self):
        analytics = UnifiedUserAnalytics(user_id="u1")
        assert analytics.user_id == "u1"
        assert analytics.total_activities == 0
        assert analytics.overall_accuracy == 0.0
        assert analytics.current_streak == 0
        assert analytics.longest_streak == 0
        assert isinstance(analytics.flashcard_stats, FlashcardStats)
        assert isinstance(analytics.opening_stats, OpeningStats)
        assert isinstance(analytics.chess_play_stats, ChessPlayStats)
        assert analytics.unified_weaknesses == []
        assert analytics.study_suggestions == []
        assert analytics.correlations == []
        assert analytics.computation_version == 1

    def test_nested_defaults_independent(self):
        """Ensure default_factory creates independent instances."""
        a1 = UnifiedUserAnalytics(user_id="u1")
        a2 = UnifiedUserAnalytics(user_id="u2")
        a1.flashcard_stats.total_cards = 99
        assert a2.flashcard_stats.total_cards == 0


class TestResponseModels:
    def test_daily_activity(self):
        day = DailyActivity(user_id="u1", date="2026-03-01")
        assert day.flashcard_reviews == 0
        assert day.total_activities == 0

    def test_trend_point(self):
        tp = TrendPoint(date="2026-03-01", value=85.5)
        assert tp.domain is None

    def test_trend_response(self):
        tr = TrendResponse(user_id="u1", period="30d")
        assert tr.accuracy_trend == []
        assert tr.domain_breakdown == {}

    def test_health_response(self):
        hr = HealthResponse(status="healthy", version="0.1.0")
        assert hr.service == "stats"

    def test_event_ack(self):
        ack = EventAck(event_type="flashcard_review", user_id="u1")
        assert ack.status == "accepted"

    def test_weakness(self):
        w = Weakness(tag="tactics", domain="flashcards", occurrences=5)
        assert w.mastery_pct == 0.0

    def test_correlation(self):
        c = Correlation(description="test", domain_a="flashcards", domain_b="openings")
        assert c.metric is None

    def test_heatmap_response(self):
        hr = HeatmapResponse(user_id="u1")
        assert hr.days == []
        assert hr.period_start is None
