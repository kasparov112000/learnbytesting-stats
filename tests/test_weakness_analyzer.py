"""Tests for analytics/weakness_analyzer.py."""

from unittest.mock import AsyncMock, patch

import pytest

from src.analytics.weakness_analyzer import WeaknessAnalyzer
from src.models import FlashcardStats, OpeningStats, ChessPlayStats, Weakness


@pytest.fixture
def analyzer():
    return WeaknessAnalyzer()


class TestGetUnifiedWeaknesses:
    async def test_merges_flashcard_tags_and_opening_mistakes(self, analyzer):
        with patch(
            "src.analytics.weakness_analyzer.flashcard_reader.get_weakness_tags",
            new_callable=AsyncMock,
            return_value=[
                {"tag": "tactics", "count": 10},
                {"tag": "endgame", "count": 5},
            ],
        ), patch(
            "src.analytics.weakness_analyzer.repertoire_reader.get_mistake_patterns",
            new_callable=AsyncMock,
            return_value=[
                {"count": 8, "opening": "Italian Game", "fen": "fen1", "wrong_move": "e4"},
                {"count": 3, "opening": None, "fen": "fen_long_string_here", "wrong_move": "d4"},
            ],
        ):
            result = await analyzer.get_unified_weaknesses("user1")

        assert len(result) == 4
        # Should be sorted by occurrences descending
        assert result[0].tag == "tactics"
        assert result[0].occurrences == 10
        assert result[0].domain == "flashcards"
        assert result[1].tag == "opening:Italian Game"
        assert result[1].occurrences == 8
        assert result[1].domain == "openings"

    async def test_caps_at_30(self, analyzer):
        fc_tags = [{"tag": f"tag{i}", "count": 30 - i} for i in range(20)]
        op_mistakes = [{"count": 20 - i, "opening": f"op{i}", "fen": f"fen{i}", "wrong_move": "m"} for i in range(15)]

        with patch(
            "src.analytics.weakness_analyzer.flashcard_reader.get_weakness_tags",
            new_callable=AsyncMock, return_value=fc_tags,
        ), patch(
            "src.analytics.weakness_analyzer.repertoire_reader.get_mistake_patterns",
            new_callable=AsyncMock, return_value=op_mistakes,
        ):
            result = await analyzer.get_unified_weaknesses("user1")

        assert len(result) == 30

    async def test_empty_when_no_data(self, analyzer):
        with patch(
            "src.analytics.weakness_analyzer.flashcard_reader.get_weakness_tags",
            new_callable=AsyncMock, return_value=[],
        ), patch(
            "src.analytics.weakness_analyzer.repertoire_reader.get_mistake_patterns",
            new_callable=AsyncMock, return_value=[],
        ):
            result = await analyzer.get_unified_weaknesses("user1")

        assert result == []

    async def test_opening_without_name_uses_fen(self, analyzer):
        with patch(
            "src.analytics.weakness_analyzer.flashcard_reader.get_weakness_tags",
            new_callable=AsyncMock, return_value=[],
        ), patch(
            "src.analytics.weakness_analyzer.repertoire_reader.get_mistake_patterns",
            new_callable=AsyncMock,
            return_value=[
                {"count": 5, "opening": None, "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR", "wrong_move": "e5"},
            ],
        ):
            result = await analyzer.get_unified_weaknesses("user1")

        assert len(result) == 1
        assert "position:" in result[0].tag


class TestGenerateSuggestions:
    async def test_due_cards_suggestion(self, analyzer):
        fc = FlashcardStats(due_today=15, total_reviews=50, accuracy=70.0)
        op = OpeningStats(total_attempts=10, accuracy=60.0)
        cp = ChessPlayStats()
        weaknesses = [Weakness(tag="tactics", domain="flashcards", occurrences=5)]

        suggestions = await analyzer.generate_suggestions("user1", fc, op, cp, weaknesses)
        due_suggestions = [s for s in suggestions if "due flashcards" in s.suggestion]
        assert len(due_suggestions) == 1
        assert "15" in due_suggestions[0].suggestion

    async def test_no_due_cards_suggestion_when_low(self, analyzer):
        fc = FlashcardStats(due_today=5, total_reviews=50, accuracy=70.0)
        op = OpeningStats()
        cp = ChessPlayStats()

        suggestions = await analyzer.generate_suggestions("user1", fc, op, cp, [])
        due_suggestions = [s for s in suggestions if "due flashcards" in s.suggestion]
        assert len(due_suggestions) == 0

    async def test_create_flashcards_for_opening_weaknesses(self, analyzer):
        fc = FlashcardStats(total_reviews=50, accuracy=70.0)
        op = OpeningStats(total_attempts=20, accuracy=50.0)
        cp = ChessPlayStats()
        weaknesses = [
            Weakness(tag="opening:Italian Game", domain="openings", occurrences=8),
        ]

        suggestions = await analyzer.generate_suggestions("user1", fc, op, cp, weaknesses)
        create_suggestions = [s for s in suggestions if "Create flashcards" in s.suggestion]
        assert len(create_suggestions) == 1

    async def test_no_create_flashcards_when_already_exists(self, analyzer):
        fc = FlashcardStats(total_reviews=50, accuracy=70.0)
        op = OpeningStats(total_attempts=20, accuracy=50.0)
        cp = ChessPlayStats()
        weaknesses = [
            Weakness(tag="opening:Italian Game", domain="openings", occurrences=8),
            Weakness(tag="opening:Italian Game", domain="flashcards", occurrences=3),
        ]

        suggestions = await analyzer.generate_suggestions("user1", fc, op, cp, weaknesses)
        create_suggestions = [s for s in suggestions if "Create flashcards" in s.suggestion]
        assert len(create_suggestions) == 0

    async def test_practice_openings_suggestion(self, analyzer):
        fc = FlashcardStats(total_reviews=100, accuracy=85.0)
        op = OpeningStats(total_attempts=50, accuracy=45.0)
        cp = ChessPlayStats()

        suggestions = await analyzer.generate_suggestions("user1", fc, op, cp, [])
        practice_suggestions = [s for s in suggestions if "Practice your openings" in s.suggestion]
        assert len(practice_suggestions) == 1

    async def test_no_practice_openings_when_both_high(self, analyzer):
        fc = FlashcardStats(total_reviews=100, accuracy=85.0)
        op = OpeningStats(total_attempts=50, accuracy=75.0)
        cp = ChessPlayStats()

        suggestions = await analyzer.generate_suggestions("user1", fc, op, cp, [])
        practice_suggestions = [s for s in suggestions if "Practice your openings" in s.suggestion]
        assert len(practice_suggestions) == 0

    async def test_start_studying_suggestion(self, analyzer):
        fc = FlashcardStats()  # 0 reviews
        op = OpeningStats()  # 0 attempts
        cp = ChessPlayStats()

        suggestions = await analyzer.generate_suggestions("user1", fc, op, cp, [])
        start_suggestions = [s for s in suggestions if "Start studying" in s.suggestion]
        assert len(start_suggestions) == 1

    async def test_focus_on_worst_weakness(self, analyzer):
        fc = FlashcardStats(total_reviews=50, accuracy=70.0)
        op = OpeningStats(total_attempts=20, accuracy=60.0)
        cp = ChessPlayStats()
        weaknesses = [
            Weakness(tag="tactics", domain="flashcards", occurrences=10, mastery_pct=20.0),
            Weakness(tag="endgame", domain="flashcards", occurrences=5, mastery_pct=50.0),
        ]

        suggestions = await analyzer.generate_suggestions("user1", fc, op, cp, weaknesses)
        focus_suggestions = [s for s in suggestions if "Focus on" in s.suggestion]
        assert len(focus_suggestions) == 1
        assert "tactics" in focus_suggestions[0].suggestion

    async def test_priorities_are_incremental(self, analyzer):
        fc = FlashcardStats(due_today=15, total_reviews=0)
        op = OpeningStats()
        cp = ChessPlayStats()
        weaknesses = [Weakness(tag="test", domain="flashcards", occurrences=1)]

        suggestions = await analyzer.generate_suggestions("user1", fc, op, cp, weaknesses)
        priorities = [s.priority for s in suggestions]
        # Each priority should be unique and incrementing
        assert priorities == sorted(priorities)
        assert len(priorities) == len(set(priorities))
