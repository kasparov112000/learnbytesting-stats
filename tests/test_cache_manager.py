"""Tests for services/cache_manager.py."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from src.services.cache_manager import CacheManager, CACHE_TTL_SECONDS


@pytest.fixture
def cm():
    return CacheManager()


class TestGetCached:
    async def test_returns_none_when_db_is_none(self, mock_db_none, cm):
        result = await cm.get_cached("user1")
        assert result is None

    async def test_returns_none_when_no_doc(self, mock_db, cm):
        mock_db.unified_user_analytics.find_one.return_value = None
        result = await cm.get_cached("user1")
        assert result is None

    async def test_returns_none_when_stale(self, mock_db, cm):
        stale_time = datetime.utcnow() - timedelta(seconds=CACHE_TTL_SECONDS + 60)
        mock_db.unified_user_analytics.find_one.return_value = {
            "user_id": "user1",
            "last_computed_at": stale_time,
        }
        result = await cm.get_cached("user1")
        assert result is None

    async def test_returns_none_when_no_last_computed(self, mock_db, cm):
        mock_db.unified_user_analytics.find_one.return_value = {
            "user_id": "user1",
        }
        result = await cm.get_cached("user1")
        assert result is None

    async def test_returns_analytics_when_fresh(self, mock_db, cm):
        fresh_time = datetime.utcnow() - timedelta(seconds=10)
        mock_db.unified_user_analytics.find_one.return_value = {
            "user_id": "user1",
            "last_computed_at": fresh_time,
            "total_activities": 42,
        }
        result = await cm.get_cached("user1")
        assert result is not None
        assert result.user_id == "user1"
        assert result.total_activities == 42

    async def test_strips_mongo_id(self, mock_db, cm):
        fresh_time = datetime.utcnow() - timedelta(seconds=10)
        mock_db.unified_user_analytics.find_one.return_value = {
            "_id": "mongo_obj_id",
            "user_id": "user1",
            "last_computed_at": fresh_time,
        }
        result = await cm.get_cached("user1")
        assert result is not None


class TestSaveCached:
    async def test_noop_when_db_is_none(self, mock_db_none, cm):
        from src.models import UnifiedUserAnalytics
        analytics = UnifiedUserAnalytics(user_id="user1")
        await cm.save_cached(analytics)
        # No exception raised — just silently returns

    async def test_calls_update_one_with_upsert(self, mock_db, cm):
        from src.models import UnifiedUserAnalytics
        analytics = UnifiedUserAnalytics(user_id="user1", total_activities=10)
        await cm.save_cached(analytics)

        mock_db.unified_user_analytics.update_one.assert_awaited_once()
        call_args = mock_db.unified_user_analytics.update_one.call_args
        assert call_args[0][0] == {"user_id": "user1"}
        assert "$set" in call_args[0][1]
        assert call_args[1]["upsert"] is True


class TestInvalidate:
    async def test_noop_when_db_is_none(self, mock_db_none, cm):
        await cm.invalidate("user1")

    async def test_sets_last_computed_to_year_2000(self, mock_db, cm):
        await cm.invalidate("user1")

        mock_db.unified_user_analytics.update_one.assert_awaited_once()
        call_args = mock_db.unified_user_analytics.update_one.call_args
        assert call_args[0][0] == {"user_id": "user1"}
        set_op = call_args[0][1]["$set"]
        assert set_op["last_computed_at"] == datetime(2000, 1, 1)
