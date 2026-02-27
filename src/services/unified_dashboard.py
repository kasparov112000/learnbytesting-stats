"""Main dashboard aggregation service — unifies stats from all domains."""

from datetime import datetime

import structlog

from ..database import db
from ..models import ChessPlayStats, UnifiedUserAnalytics
from .cache_manager import cache_manager
from .flashcard_reader import flashcard_reader
from .flashcard_enrichment import fetch_flashcard_analytics
from .repertoire_reader import repertoire_reader
from ..analytics.weakness_analyzer import weakness_analyzer
from ..analytics.activity_aggregator import activity_aggregator

logger = structlog.get_logger()


class UnifiedDashboardService:
    """Aggregates stats from event-sourced materialized views."""

    async def get_dashboard(self, user_id: str) -> UnifiedUserAnalytics:
        """Get unified dashboard stats, using cache when fresh."""
        cached = await cache_manager.get_cached(user_id)
        if cached:
            logger.debug("Returning cached dashboard", user_id=user_id)
            return cached

        return await self.compute_dashboard(user_id)

    async def compute_dashboard(self, user_id: str) -> UnifiedUserAnalytics:
        """Force-compute fresh unified stats from materialized views."""
        logger.info("Computing unified dashboard", user_id=user_id)

        # Read from materialized views (all in stats-db)
        fc_stats = await flashcard_reader.get_user_stats(user_id)
        op_stats = await repertoire_reader.get_user_stats(user_id)
        cp_stats = await self._get_chess_play_stats(user_id)

        # Unified activity totals
        total_activities = (
            fc_stats.total_reviews + op_stats.total_attempts + cp_stats.total_games
        )
        total_time = int(
            fc_stats.avg_response_time_ms * fc_stats.total_reviews
            + op_stats.avg_time_to_move_ms * op_stats.total_attempts
            + cp_stats.avg_time_to_answer_ms * cp_stats.total_games
        )

        # Weighted overall accuracy
        total_weighted = 0.0
        total_weight = 0
        if fc_stats.total_reviews > 0:
            total_weighted += fc_stats.accuracy * fc_stats.total_reviews
            total_weight += fc_stats.total_reviews
        if op_stats.total_attempts > 0:
            total_weighted += op_stats.accuracy * op_stats.total_attempts
            total_weight += op_stats.total_attempts
        if cp_stats.total_games > 0:
            total_weighted += cp_stats.accuracy * cp_stats.total_games
            total_weight += cp_stats.total_games
        overall_accuracy = (total_weighted / total_weight) if total_weight > 0 else 0.0

        # Unified streak
        streak_info = await activity_aggregator.compute_streak(user_id)

        # Enrich with live FSRS data from flashcards service
        enrichment = await fetch_flashcard_analytics(user_id)
        if enrichment:
            logger.info("Applying flashcard enrichment", user_id=user_id)
            fc_stats.total_cards = enrichment.total_cards or fc_stats.total_cards
            fc_stats.mastered = enrichment.mastered_cards or fc_stats.mastered
            fc_stats.learning = enrichment.studying_cards or fc_stats.learning
            fc_stats.new_cards = enrichment.new_cards or fc_stats.new_cards
            fc_stats.due_today = enrichment.due_cards or fc_stats.due_today
            fc_stats.cards_today = enrichment.cards_today
            fc_stats.daily_goal = enrichment.daily_goal
            fc_stats.daily_goal_progress = enrichment.goal_progress
            fc_stats.rating_distribution = enrichment.rating_distribution
            if enrichment.total_cards > 0:
                fc_stats.mastered_pct = round(
                    enrichment.mastered_cards / enrichment.total_cards * 100, 1
                )
            if enrichment.overall_accuracy > 0:
                fc_stats.accuracy = enrichment.overall_accuracy
            if enrichment.total_reviews > 0:
                fc_stats.total_reviews = enrichment.total_reviews

        # Reconcile streaks: use max of stats-service (cross-domain) vs flashcards-service
        current_streak = streak_info["current"]
        longest_streak = streak_info["longest"]
        if enrichment:
            current_streak = max(current_streak, enrichment.current_streak)
            longest_streak = max(longest_streak, enrichment.longest_streak)

        # Weaknesses
        weaknesses = await weakness_analyzer.get_unified_weaknesses(user_id)

        # Study suggestions
        suggestions = await weakness_analyzer.generate_suggestions(
            user_id, fc_stats, op_stats, cp_stats, weaknesses
        )

        analytics = UnifiedUserAnalytics(
            user_id=user_id,
            total_activities=total_activities,
            total_study_time_ms=total_time,
            overall_accuracy=round(overall_accuracy, 1),
            current_streak=current_streak,
            longest_streak=longest_streak,
            flashcard_stats=fc_stats,
            opening_stats=op_stats,
            chess_play_stats=cp_stats,
            unified_weaknesses=weaknesses,
            study_suggestions=suggestions,
            last_computed_at=datetime.utcnow(),
            # Top-level convenience fields
            cards_today=fc_stats.cards_today,
            mastered_pct=fc_stats.mastered_pct,
            daily_goal=fc_stats.daily_goal,
            daily_goal_progress=fc_stats.daily_goal_progress,
            rating_distribution=fc_stats.rating_distribution,
        )

        await cache_manager.save_cached(analytics)
        return analytics

    async def _get_chess_play_stats(self, user_id: str) -> ChessPlayStats:
        """Aggregate chess play stats from event collection."""
        sdb = db.db
        if sdb is None:
            return ChessPlayStats()

        try:
            pipeline = [
                {"$match": {"user_id": user_id}},
                {
                    "$group": {
                        "_id": None,
                        "total": {"$sum": 1},
                        "correct": {"$sum": {"$cond": ["$was_correct", 1, 0]}},
                        "avg_time": {"$avg": "$time_to_answer_ms"},
                    }
                },
            ]
            result = await sdb.chess_play_events.aggregate(pipeline).to_list(1)
            data = result[0] if result else {}

            total = data.get("total", 0)
            correct = data.get("correct", 0)

            return ChessPlayStats(
                total_games=total,
                accuracy=(correct / total * 100) if total > 0 else 0.0,
                total_correct=correct,
                avg_time_to_answer_ms=data.get("avg_time", 0.0) or 0.0,
            )
        except Exception as e:
            logger.error("Error reading chess play stats", user_id=user_id, error=str(e))
            return ChessPlayStats()


dashboard_service = UnifiedDashboardService()
