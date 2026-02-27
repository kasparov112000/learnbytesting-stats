"""Reads opening stats from event-sourced materialized views in stats-db."""

import structlog

from ..database import db
from ..models import OpeningStats

logger = structlog.get_logger()


class RepertoireReader:
    """Reads opening data from materialized views built by incoming events."""

    async def get_user_stats(self, user_id: str) -> OpeningStats:
        """Get opening stats from the materialized view in stats-db."""
        sdb = db.db
        if sdb is None:
            return OpeningStats()

        try:
            doc = await sdb.opening_stats.find_one({"user_id": user_id})
            if not doc:
                return OpeningStats()

            total = doc.get("total_attempts", 0)
            correct = doc.get("total_correct", 0)
            total_time = doc.get("total_time_ms", 0)

            return OpeningStats(
                total_positions=doc.get("unique_positions", 0),
                mastered=0,
                familiar=0,
                learning=0,
                new_positions=0,
                accuracy=(correct / total * 100) if total > 0 else 0.0,
                total_attempts=total,
                avg_time_to_move_ms=(total_time / total) if total > 0 else 0.0,
            )
        except Exception as e:
            logger.error("Error reading opening stats", user_id=user_id, error=str(e))
            return OpeningStats()

    async def get_mistake_patterns(self, user_id: str) -> list[dict]:
        """Get mistake patterns from materialized opening events."""
        sdb = db.db
        if sdb is None:
            return []

        try:
            doc = await sdb.opening_stats.find_one({"user_id": user_id})
            if not doc or not doc.get("mistake_patterns"):
                return []

            patterns = doc["mistake_patterns"]
            # patterns is stored as { "fen::move": { count, opening_name, ... }, ... }
            result = []
            for key, info in sorted(patterns.items(), key=lambda x: -x[1].get("count", 0)):
                result.append({
                    "wrong_move": info.get("played_move"),
                    "correct_move": None,
                    "count": info.get("count", 0),
                    "fen": info.get("fen"),
                    "opening": info.get("opening_name"),
                })
            return result[:20]
        except Exception as e:
            logger.error("Error reading mistake patterns", user_id=user_id, error=str(e))
            return []

    async def update_from_event(
        self, user_id: str, fen: str, played_move: str | None,
        was_correct: bool, time_to_move: int | None,
        opening_name: str | None, eco: str | None,
    ):
        """Update materialized view from an opening attempt event."""
        sdb = db.db
        if sdb is None:
            return

        correct = 1 if was_correct else 0
        inc_ops = {
            "total_attempts": 1,
            "total_correct": correct,
            "total_time_ms": time_to_move or 0,
        }

        update: dict = {
            "$inc": inc_ops,
            "$addToSet": {"position_fens": fen},
            "$setOnInsert": {"user_id": user_id, "mistake_patterns": {}},
        }

        await sdb.opening_stats.update_one(
            {"user_id": user_id}, update, upsert=True,
        )

        # Update unique_positions count
        doc = await sdb.opening_stats.find_one({"user_id": user_id}, {"position_fens": 1})
        if doc and doc.get("position_fens"):
            await sdb.opening_stats.update_one(
                {"user_id": user_id},
                {"$set": {"unique_positions": len(doc["position_fens"])}},
            )

        # Record mistake patterns for incorrect moves
        if not was_correct and played_move:
            key = f"{fen[:30]}::{played_move}"
            await sdb.opening_stats.update_one(
                {"user_id": user_id},
                {
                    "$inc": {f"mistake_patterns.{key}.count": 1},
                    "$set": {
                        f"mistake_patterns.{key}.fen": fen,
                        f"mistake_patterns.{key}.played_move": played_move,
                        f"mistake_patterns.{key}.opening_name": opening_name,
                    },
                },
            )


repertoire_reader = RepertoireReader()
