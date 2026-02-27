"""Unified daily/weekly/monthly activity aggregation."""

from datetime import datetime, timedelta
from typing import Optional

import structlog

from ..database import db
from ..models import DailyActivity

logger = structlog.get_logger()


class ActivityAggregator:
    """Aggregates activity from all domains into unified daily records."""

    async def record_flashcard_activity(
        self, user_id: str, date_str: str, reviews: int = 1,
        correct: int = 0, time_ms: int = 0,
    ):
        """Increment flashcard counters in unified daily activity."""
        sdb = db.stats_db
        if not sdb:
            return

        await sdb.unified_daily_activity.update_one(
            {"user_id": user_id, "date": date_str},
            {
                "$inc": {
                    "flashcard_reviews": reviews,
                    "flashcard_correct": correct,
                    "flashcard_time_ms": time_ms,
                    "total_activities": reviews,
                    "total_correct": correct,
                    "total_time_ms": time_ms,
                },
                "$setOnInsert": {"user_id": user_id, "date": date_str},
            },
            upsert=True,
        )

    async def record_opening_activity(
        self, user_id: str, date_str: str, attempts: int = 1,
        correct: int = 0, time_ms: int = 0,
    ):
        """Increment opening counters in unified daily activity."""
        sdb = db.stats_db
        if not sdb:
            return

        await sdb.unified_daily_activity.update_one(
            {"user_id": user_id, "date": date_str},
            {
                "$inc": {
                    "opening_attempts": attempts,
                    "opening_correct": correct,
                    "opening_time_ms": time_ms,
                    "total_activities": attempts,
                    "total_correct": correct,
                    "total_time_ms": time_ms,
                },
                "$setOnInsert": {"user_id": user_id, "date": date_str},
            },
            upsert=True,
        )

    async def record_chess_play_activity(
        self, user_id: str, date_str: str, games: int = 1,
        correct: int = 0, time_ms: int = 0,
    ):
        """Increment chess play counters in unified daily activity."""
        sdb = db.stats_db
        if not sdb:
            return

        await sdb.unified_daily_activity.update_one(
            {"user_id": user_id, "date": date_str},
            {
                "$inc": {
                    "chess_play_games": games,
                    "chess_play_correct": correct,
                    "chess_play_time_ms": time_ms,
                    "total_activities": games,
                    "total_correct": correct,
                    "total_time_ms": time_ms,
                },
                "$setOnInsert": {"user_id": user_id, "date": date_str},
            },
            upsert=True,
        )

    async def get_heatmap(
        self, user_id: str, days: int = 365
    ) -> list[DailyActivity]:
        """Get unified daily activity for heatmap display."""
        sdb = db.stats_db
        if not sdb:
            return []

        since = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
        cursor = sdb.unified_daily_activity.find(
            {"user_id": user_id, "date": {"$gte": since}},
            {"_id": 0},
        ).sort("date", 1)

        docs = await cursor.to_list(days)
        return [DailyActivity(**doc) for doc in docs]

    async def compute_streak(self, user_id: str) -> dict:
        """Compute current and longest streak across all domains."""
        sdb = db.stats_db
        if not sdb:
            return {"current": 0, "longest": 0}

        # Get all activity days sorted descending
        cursor = sdb.unified_daily_activity.find(
            {"user_id": user_id, "total_activities": {"$gt": 0}},
            {"_id": 0, "date": 1},
        ).sort("date", -1)

        docs = await cursor.to_list(1000)
        if not docs:
            return {"current": 0, "longest": 0}

        dates = sorted([doc["date"] for doc in docs], reverse=True)
        today = datetime.utcnow().strftime("%Y-%m-%d")
        yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")

        # Current streak: count consecutive days ending today or yesterday
        current = 0
        if dates and dates[0] in (today, yesterday):
            current = 1
            for i in range(1, len(dates)):
                prev_date = datetime.strptime(dates[i - 1], "%Y-%m-%d")
                curr_date = datetime.strptime(dates[i], "%Y-%m-%d")
                if (prev_date - curr_date).days == 1:
                    current += 1
                else:
                    break

        # Longest streak: scan all dates
        longest = 0
        if dates:
            streak = 1
            for i in range(1, len(dates)):
                prev_date = datetime.strptime(dates[i - 1], "%Y-%m-%d")
                curr_date = datetime.strptime(dates[i], "%Y-%m-%d")
                if (prev_date - curr_date).days == 1:
                    streak += 1
                else:
                    longest = max(longest, streak)
                    streak = 1
            longest = max(longest, streak)

        return {"current": current, "longest": longest}


activity_aggregator = ActivityAggregator()
