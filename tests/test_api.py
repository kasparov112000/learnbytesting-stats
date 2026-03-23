"""Tests for FastAPI endpoints in api.py."""

from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from httpx import AsyncClient, ASGITransport

from src.models import (
    UnifiedUserAnalytics,
    HeatmapResponse,
    DailyActivity,
    TrendResponse,
    TrendPoint,
    WeaknessResponse,
    Weakness,
    SuggestionResponse,
    StudySuggestion,
)


@pytest.fixture
def mock_lifespan():
    """Patch the lifespan to skip DB connection."""
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def noop_lifespan(app):
        yield

    with patch("src.api.lifespan", noop_lifespan):
        # Re-import to get fresh app with patched lifespan
        import importlib
        import src.api
        importlib.reload(src.api)
        yield src.api.app
    # Reload again to restore original
    importlib.reload(src.api)


@pytest.fixture
async def client(mock_lifespan):
    transport = ASGITransport(app=mock_lifespan)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestHealthEndpoint:
    async def test_health_connected(self, client):
        mock_client = AsyncMock()
        mock_client.admin.command = AsyncMock(return_value=True)
        with patch("src.api.db.client", mock_client):
            resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["service"] == "stats"

    async def test_health_no_db(self, client):
        with patch("src.api.db.client", None):
            resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "degraded"


class TestDashboardEndpoint:
    async def test_get_dashboard(self, client):
        analytics = UnifiedUserAnalytics(user_id="user1", total_activities=42)
        with patch(
            "src.api.dashboard_service.get_dashboard",
            new_callable=AsyncMock, return_value=analytics,
        ):
            resp = await client.get("/dashboard/user1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == "user1"
        assert data["total_activities"] == 42


class TestHeatmapEndpoint:
    async def test_get_heatmap(self, client):
        activities = [
            DailyActivity(user_id="user1", date="2026-03-01", total_activities=5),
        ]
        with patch(
            "src.api.activity_aggregator.get_heatmap",
            new_callable=AsyncMock, return_value=activities,
        ):
            resp = await client.get("/dashboard/user1/heatmap?days=30")
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == "user1"
        assert len(data["days"]) == 1

    async def test_heatmap_empty(self, client):
        with patch(
            "src.api.activity_aggregator.get_heatmap",
            new_callable=AsyncMock, return_value=[],
        ):
            resp = await client.get("/dashboard/user1/heatmap")
        assert resp.status_code == 200
        data = resp.json()
        assert data["days"] == []
        assert data["period_start"] is None


class TestTrendsEndpoint:
    async def test_get_trends(self, client):
        trend = TrendResponse(
            user_id="user1", period="30d",
            activity_trend=[TrendPoint(date="2026-03-01", value=10.0)],
        )
        with patch(
            "src.api.trend_calculator.get_trends",
            new_callable=AsyncMock, return_value=trend,
        ):
            resp = await client.get("/dashboard/user1/trends?period=30d")
        assert resp.status_code == 200
        data = resp.json()
        assert data["period"] == "30d"
        assert len(data["activity_trend"]) == 1

    async def test_invalid_period_rejected(self, client):
        resp = await client.get("/dashboard/user1/trends?period=15d")
        assert resp.status_code == 422


class TestWeaknessesEndpoint:
    async def test_get_weaknesses(self, client):
        weaknesses = [Weakness(tag="tactics", domain="flashcards", occurrences=10)]
        with patch(
            "src.api.weakness_analyzer.get_unified_weaknesses",
            new_callable=AsyncMock, return_value=weaknesses,
        ):
            resp = await client.get("/dashboard/user1/weaknesses")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["weaknesses"]) == 1
        assert data["weaknesses"][0]["tag"] == "tactics"


class TestFlashcardReviewEvent:
    async def test_ingest_valid_event(self, client):
        with patch("src.api.db.db", MagicMock()) as mock_sdb, \
             patch("src.api.flashcard_reader.update_from_event", new_callable=AsyncMock), \
             patch("src.api.activity_aggregator.record_flashcard_activity", new_callable=AsyncMock), \
             patch("src.api.cache_manager.invalidate", new_callable=AsyncMock):
            mock_sdb.event_log.insert_one = AsyncMock()
            resp = await client.post("/events/flashcard-review", json={
                "user_id": "user1",
                "quality": 4,
                "response_time_ms": 1500,
            })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "accepted"
        assert data["event_type"] == "flashcard_review"

    async def test_validation_error_on_invalid_quality(self, client):
        resp = await client.post("/events/flashcard-review", json={
            "user_id": "user1",
            "quality": 10,
        })
        assert resp.status_code == 422

    async def test_requires_user_id_or_session_id(self, client):
        with patch("src.api.db.db", MagicMock()) as mock_sdb, \
             patch("src.api.flashcard_reader.update_from_event", new_callable=AsyncMock), \
             patch("src.api.activity_aggregator.record_flashcard_activity", new_callable=AsyncMock), \
             patch("src.api.cache_manager.invalidate", new_callable=AsyncMock):
            mock_sdb.event_log.insert_one = AsyncMock()
            resp = await client.post("/events/flashcard-review", json={
                "quality": 3,
            })
        assert resp.status_code == 422


class TestOpeningAttemptEvent:
    async def test_ingest_valid_event(self, client):
        with patch("src.api.db.db", MagicMock()) as mock_sdb, \
             patch("src.api.repertoire_reader.update_from_event", new_callable=AsyncMock), \
             patch("src.api.activity_aggregator.record_opening_activity", new_callable=AsyncMock), \
             patch("src.api.cache_manager.invalidate", new_callable=AsyncMock):
            mock_sdb.event_log.insert_one = AsyncMock()
            resp = await client.post("/events/opening-attempt", json={
                "user_id": "user1",
                "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR",
                "was_correct": True,
                "time_to_move": 2000,
            })
        assert resp.status_code == 200
        data = resp.json()
        assert data["event_type"] == "opening_attempt"

    async def test_validation_error_missing_fen(self, client):
        resp = await client.post("/events/opening-attempt", json={
            "user_id": "user1",
            "was_correct": True,
        })
        assert resp.status_code == 422


class TestChessPlayEvent:
    async def test_ingest_valid_event(self, client):
        with patch("src.api.db.db", MagicMock()) as mock_sdb, \
             patch("src.api.activity_aggregator.record_chess_play_activity", new_callable=AsyncMock), \
             patch("src.api.cache_manager.invalidate", new_callable=AsyncMock):
            mock_sdb.chess_play_events.insert_one = AsyncMock()
            mock_sdb.event_log.insert_one = AsyncMock()
            resp = await client.post("/events/chess-play", json={
                "user_id": "user1",
                "was_correct": False,
                "time_to_answer_ms": 5000,
            })
        assert resp.status_code == 200
        data = resp.json()
        assert data["event_type"] == "chess_play"

    async def test_validation_error_missing_user_id(self, client):
        resp = await client.post("/events/chess-play", json={
            "was_correct": True,
        })
        assert resp.status_code == 422
