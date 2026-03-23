"""Shared fixtures for stats microservice tests."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class MockCollection:
    """A mock MongoDB collection with all common methods as AsyncMocks."""

    def __init__(self):
        self.find_one = AsyncMock(return_value=None)
        self.update_one = AsyncMock()
        self.insert_one = AsyncMock()
        self.delete_one = AsyncMock()
        self.create_index = AsyncMock()
        self._find_cursor = AsyncMock()
        self._aggregate_cursor = AsyncMock()

    def find(self, *args, **kwargs):
        cursor = MagicMock()
        cursor.sort = MagicMock(return_value=cursor)
        cursor.to_list = self._find_cursor
        return cursor

    def aggregate(self, *args, **kwargs):
        cursor = MagicMock()
        cursor.to_list = self._aggregate_cursor
        return cursor


class MockDatabase:
    """A mock Motor database with pre-configured collections."""

    def __init__(self):
        self.unified_user_analytics = MockCollection()
        self.unified_daily_activity = MockCollection()
        self.flashcard_stats = MockCollection()
        self.opening_stats = MockCollection()
        self.chess_play_events = MockCollection()
        self.event_log = MockCollection()


@pytest.fixture
def mock_db():
    """Patch src.database.db.db with a MockDatabase and return it."""
    mdb = MockDatabase()
    with patch("src.database.db.db", mdb):
        yield mdb


@pytest.fixture
def mock_db_none():
    """Patch src.database.db.db to None (simulates no DB connection)."""
    with patch("src.database.db.db", None):
        yield


@pytest.fixture
def mock_settings():
    """Patch settings with test values."""
    with patch("src.config.settings") as s:
        s.orchestrator_url = "http://test-orchestrator:8080"
        s.stats_mongodb_url = "mongodb://localhost:27017"
        s.stats_mongodb_database = "test-stats-db"
        s.env_name = "TEST"
        s.port = 3038
        yield s
