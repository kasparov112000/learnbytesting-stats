from typing import Optional

import structlog
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from .config import settings

logger = structlog.get_logger()


class Database:
    """Manages async connection to the stats-db (own database only)."""

    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None

    async def connect(self):
        """Connect to stats-db."""
        self.client = AsyncIOMotorClient(settings.stats_mongodb_url)
        self.db = self.client[settings.stats_mongodb_database]
        await self.client.admin.command("ping")
        logger.info("Connected to stats-db", database=settings.stats_mongodb_database)
        await self._ensure_indexes()

    async def _ensure_indexes(self):
        """Create indexes on stats-db collections."""
        # unified_user_analytics — one doc per user
        await self.db.unified_user_analytics.create_index("user_id", unique=True)
        await self.db.unified_user_analytics.create_index("user_email")

        # unified_daily_activity — one doc per user per day
        await self.db.unified_daily_activity.create_index(
            [("user_id", 1), ("date", 1)], unique=True
        )

        # Materialized views from events
        await self.db.flashcard_stats.create_index("user_id", unique=True)
        await self.db.opening_stats.create_index("user_id", unique=True)

        # chess_play_events
        await self.db.chess_play_events.create_index(
            [("user_id", 1), ("timestamp", -1)]
        )

        # event_log — webhook audit trail
        await self.db.event_log.create_index(
            [("event_type", 1), ("timestamp", -1)]
        )
        await self.db.event_log.create_index("user_id")

        logger.info("Stats DB indexes ensured")

    async def disconnect(self):
        """Disconnect from database."""
        if self.client:
            self.client.close()
            logger.info("Disconnected from stats-db")


db = Database()
