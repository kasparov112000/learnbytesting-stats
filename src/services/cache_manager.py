"""Cache management for unified analytics documents."""

from datetime import datetime
from typing import Optional

import structlog

from ..database import db
from ..models import UnifiedUserAnalytics

logger = structlog.get_logger()

# Cache TTL in seconds (5 minutes)
CACHE_TTL_SECONDS = 300


class CacheManager:
    """Manages the unified_user_analytics cache in stats-db."""

    async def get_cached(self, user_id: str) -> Optional[UnifiedUserAnalytics]:
        """Get cached analytics if still fresh."""
        sdb = db.db
        if not sdb:
            return None

        doc = await sdb.unified_user_analytics.find_one({"user_id": user_id})
        if not doc:
            return None

        doc.pop("_id", None)

        # Check freshness
        last_computed = doc.get("last_computed_at")
        if last_computed:
            age = (datetime.utcnow() - last_computed).total_seconds()
            if age < CACHE_TTL_SECONDS:
                return UnifiedUserAnalytics(**doc)

        return None

    async def save_cached(self, analytics: UnifiedUserAnalytics):
        """Save or update cached analytics."""
        sdb = db.db
        if not sdb:
            return

        data = analytics.model_dump()
        data["last_computed_at"] = datetime.utcnow()

        await sdb.unified_user_analytics.update_one(
            {"user_id": analytics.user_id},
            {"$set": data},
            upsert=True,
        )
        logger.debug("Analytics cache saved", user_id=analytics.user_id)

    async def invalidate(self, user_id: str):
        """Invalidate cache for a user (force recompute on next read)."""
        sdb = db.db
        if not sdb:
            return

        await sdb.unified_user_analytics.update_one(
            {"user_id": user_id},
            {"$set": {"last_computed_at": datetime(2000, 1, 1)}},
        )
        logger.debug("Analytics cache invalidated", user_id=user_id)


cache_manager = CacheManager()
