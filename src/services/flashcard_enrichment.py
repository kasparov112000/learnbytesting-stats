"""Fetches live FSRS-derived flashcard analytics from the flashcards service via orchestrator."""

from typing import List, Optional

import httpx
import structlog
from pydantic import BaseModel

from ..config import settings

logger = structlog.get_logger()


class FlashcardAnalyticsSummary(BaseModel):
    cards_today: int = 0
    total_cards: int = 0
    mastered_cards: int = 0
    studying_cards: int = 0
    new_cards: int = 0
    due_cards: int = 0
    overall_mastery: float = 0.0
    overall_accuracy: float = 0.0
    daily_goal: int = 20
    goal_progress: int = 0
    rating_distribution: dict = {"again": 0, "hard": 0, "good": 0, "easy": 0}
    current_streak: int = 0
    longest_streak: int = 0
    total_reviews: int = 0


async def fetch_flashcard_analytics(user_id: str) -> Optional[FlashcardAnalyticsSummary]:
    """Call flashcards analytics endpoint via orchestrator. Returns None on failure."""
    url = f"{settings.orchestrator_url}/api/flashcards/analytics/{user_id}/summary"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            raw = resp.json()
            # Orchestrator wraps response in {"result": ...}
            data = raw.get("result", raw) if isinstance(raw, dict) else raw

        logger.debug("Flashcard enrichment fetched", user_id=user_id)

        today = data.get("todayProgress", {}) or {}

        return FlashcardAnalyticsSummary(
            cards_today=data.get("cardsToday", 0) or today.get("cardsReviewed", 0) or 0,
            total_cards=data.get("totalCards", 0) or 0,
            mastered_cards=data.get("masteredCards", 0) or 0,
            studying_cards=data.get("studyingCards", 0) or 0,
            new_cards=data.get("newCards", 0) or 0,
            due_cards=data.get("dueCards", 0) or 0,
            overall_mastery=data.get("overallMastery", 0.0) or 0.0,
            overall_accuracy=data.get("overallAccuracy", 0.0) or 0.0,
            daily_goal=data.get("dailyGoal", 20) or 20,
            goal_progress=today.get("goalProgress", 0) or 0,
            rating_distribution=data.get("ratingDistribution", {})
                or {"again": 0, "hard": 0, "good": 0, "easy": 0},
            current_streak=data.get("currentStreak", 0) or 0,
            longest_streak=data.get("longestStreak", 0) or 0,
            total_reviews=data.get("totalReviews", 0) or 0,
        )
    except Exception as e:
        logger.warning(
            "Flashcard enrichment failed, using defaults",
            user_id=user_id,
            error=str(e),
        )
        return None


class WeaknessTagStat(BaseModel):
    tagId: str = ""
    tagType: str = ""
    tagSpecific: str = ""
    displayName: str = ""
    cardsTotal: int = 0
    cardsMastered: int = 0
    cardsLearning: int = 0
    cardsNew: int = 0
    masteryPercent: float = 0.0
    accuracy: float = 0.0
    totalReviews: int = 0


async def fetch_weakness_tags(user_id: str) -> List[WeaknessTagStat]:
    """Fetch detailed weakness-tag stats from flashcards service via orchestrator."""
    url = f"{settings.orchestrator_url}/api/flashcards/analytics/{user_id}/weakness-tags"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            raw = resp.json()
            data = raw.get("result", raw) if isinstance(raw, dict) else raw

        if not isinstance(data, list):
            return []

        logger.debug("Weakness tags fetched", user_id=user_id, count=len(data))
        return [WeaknessTagStat(**item) for item in data]
    except Exception as e:
        logger.warning(
            "Weakness tags fetch failed",
            user_id=user_id,
            error=str(e),
        )
        return []
