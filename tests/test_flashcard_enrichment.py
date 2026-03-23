"""Tests for services/flashcard_enrichment.py."""

from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from src.services.flashcard_enrichment import (
    fetch_flashcard_analytics,
    fetch_weakness_tags,
    fetch_opening_progress,
    FlashcardAnalyticsSummary,
    WeaknessTagStat,
)


class MockResponse:
    """Mock httpx response."""

    def __init__(self, json_data, status_code=200):
        self._json = json_data
        self.status_code = status_code

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


class TestFetchFlashcardAnalytics:
    async def test_parses_response_correctly(self):
        response_data = {
            "result": {
                "cardsToday": 5,
                "totalCards": 100,
                "masteredCards": 30,
                "studyingCards": 40,
                "newCards": 30,
                "dueCards": 12,
                "overallMastery": 0.3,
                "overallAccuracy": 85.5,
                "dailyGoal": 25,
                "ratingDistribution": {"again": 2, "hard": 5, "good": 15, "easy": 3},
                "currentStreak": 4,
                "longestStreak": 10,
                "totalReviews": 500,
                "todayProgress": {"cardsReviewed": 5, "goalProgress": 3},
            }
        }
        mock_resp = MockResponse(response_data)
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("src.services.flashcard_enrichment.httpx.AsyncClient", return_value=mock_client):
            result = await fetch_flashcard_analytics("user1")

        assert result is not None
        assert result.cards_today == 5
        assert result.total_cards == 100
        assert result.mastered_cards == 30
        assert result.overall_accuracy == 85.5
        assert result.current_streak == 4
        assert result.longest_streak == 10
        assert result.daily_goal == 25
        assert result.goal_progress == 3

    async def test_returns_none_on_http_error(self):
        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("Connection timeout")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("src.services.flashcard_enrichment.httpx.AsyncClient", return_value=mock_client):
            result = await fetch_flashcard_analytics("user1")

        assert result is None

    async def test_handles_unwrapped_response(self):
        response_data = {
            "cardsToday": 3,
            "totalCards": 50,
            "masteredCards": 10,
            "studyingCards": 20,
            "newCards": 20,
            "dueCards": 5,
            "overallAccuracy": 72.0,
            "totalReviews": 200,
        }
        mock_resp = MockResponse(response_data)
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("src.services.flashcard_enrichment.httpx.AsyncClient", return_value=mock_client):
            result = await fetch_flashcard_analytics("user1")

        assert result is not None
        assert result.total_cards == 50


class TestFetchWeaknessTags:
    async def test_parses_list_response(self):
        response_data = {
            "result": [
                {"tagId": "t1", "tagType": "opening", "tagSpecific": "Italian",
                 "displayName": "Italian Game", "cardsTotal": 10, "accuracy": 85.0},
                {"tagId": "t2", "tagType": "tactic", "tagSpecific": "fork",
                 "displayName": "Fork", "cardsTotal": 5, "accuracy": 60.0},
            ]
        }
        mock_resp = MockResponse(response_data)
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("src.services.flashcard_enrichment.httpx.AsyncClient", return_value=mock_client):
            result = await fetch_weakness_tags("user1")

        assert len(result) == 2
        assert isinstance(result[0], WeaknessTagStat)
        assert result[0].tagId == "t1"

    async def test_returns_empty_on_error(self):
        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("timeout")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("src.services.flashcard_enrichment.httpx.AsyncClient", return_value=mock_client):
            result = await fetch_weakness_tags("user1")

        assert result == []

    async def test_returns_empty_when_not_list(self):
        response_data = {"result": "not a list"}
        mock_resp = MockResponse(response_data)
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("src.services.flashcard_enrichment.httpx.AsyncClient", return_value=mock_client):
            result = await fetch_weakness_tags("user1")

        assert result == []


class TestFetchOpeningProgress:
    async def test_returns_openings_list(self):
        response_data = {
            "result": {
                "openings": [
                    {"name": "Italian Game", "mastery": 0.7},
                    {"name": "Sicilian Defense", "mastery": 0.4},
                ]
            }
        }
        mock_resp = MockResponse(response_data)
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("src.services.flashcard_enrichment.httpx.AsyncClient", return_value=mock_client):
            result = await fetch_opening_progress("user1")

        assert len(result) == 2
        assert result[0]["name"] == "Italian Game"

    async def test_returns_empty_on_error(self):
        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("500 Internal Server Error")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("src.services.flashcard_enrichment.httpx.AsyncClient", return_value=mock_client):
            result = await fetch_opening_progress("user1")

        assert result == []

    async def test_returns_empty_when_no_openings_key(self):
        response_data = {"result": {"other_data": True}}
        mock_resp = MockResponse(response_data)
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("src.services.flashcard_enrichment.httpx.AsyncClient", return_value=mock_client):
            result = await fetch_opening_progress("user1")

        assert result == []
