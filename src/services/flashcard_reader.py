"""Reads flashcard stats from event-sourced materialized views in stats-db."""

import structlog

from ..database import db
from ..models import FlashcardStats

logger = structlog.get_logger()


class FlashcardReader:
    """Reads flashcard data from materialized views built by incoming events."""

    async def get_user_stats(self, user_id: str) -> FlashcardStats:
        """Get flashcard stats from the materialized view in stats-db."""
        sdb = db.db
        if not sdb:
            return FlashcardStats()

        try:
            doc = await sdb.flashcard_stats.find_one({"user_id": user_id})
            if not doc:
                return FlashcardStats()

            total = doc.get("total_reviews", 0)
            correct = doc.get("total_correct", 0)
            total_time = doc.get("total_time_ms", 0)

            return FlashcardStats(
                total_cards=doc.get("unique_cards", 0),
                mastered=0,
                learning=0,
                new_cards=0,
                total_reviews=total,
                accuracy=(correct / total * 100) if total > 0 else 0.0,
                avg_response_time_ms=(total_time / total) if total > 0 else 0.0,
                due_today=0,
            )
        except Exception as e:
            logger.error("Error reading flashcard stats", user_id=user_id, error=str(e))
            return FlashcardStats()

    async def get_weakness_tags(self, user_id: str) -> list[dict]:
        """Get weakness tags from materialized flashcard events."""
        sdb = db.db
        if not sdb:
            return []

        try:
            doc = await sdb.flashcard_stats.find_one({"user_id": user_id})
            if not doc or not doc.get("weakness_tags"):
                return []

            tags = doc["weakness_tags"]
            # tags is stored as { "tag_name": count, ... }
            return [
                {"tag": tag, "count": count}
                for tag, count in sorted(tags.items(), key=lambda x: -x[1])
            ][:20]
        except Exception as e:
            logger.error("Error reading weakness tags", user_id=user_id, error=str(e))
            return []

    async def update_from_event(
        self, user_id: str, quality: int, response_time_ms: int,
        is_new_card: bool, weakness_tags: list[str], flashcard_id: str | None,
    ):
        """Update materialized view from a flashcard review event."""
        sdb = db.db
        if not sdb:
            return

        correct = 1 if quality >= 3 else 0
        inc_ops = {
            "total_reviews": 1,
            "total_correct": correct,
            "total_time_ms": response_time_ms or 0,
        }

        # Track unique cards via addToSet
        update: dict = {
            "$inc": inc_ops,
            "$setOnInsert": {"user_id": user_id, "weakness_tags": {}},
        }

        if flashcard_id:
            update["$addToSet"] = {"card_ids": flashcard_id}

        await sdb.flashcard_stats.update_one(
            {"user_id": user_id}, update, upsert=True,
        )

        # Update weakness tags separately (can't mix $inc on nested with $setOnInsert)
        if weakness_tags:
            tag_inc = {f"weakness_tags.{tag}": 1 for tag in weakness_tags}
            await sdb.flashcard_stats.update_one(
                {"user_id": user_id}, {"$inc": tag_inc},
            )

        # Update unique_cards count from card_ids array
        if flashcard_id:
            doc = await sdb.flashcard_stats.find_one({"user_id": user_id}, {"card_ids": 1})
            if doc and doc.get("card_ids"):
                await sdb.flashcard_stats.update_one(
                    {"user_id": user_id},
                    {"$set": {"unique_cards": len(doc["card_ids"])}},
                )


flashcard_reader = FlashcardReader()
