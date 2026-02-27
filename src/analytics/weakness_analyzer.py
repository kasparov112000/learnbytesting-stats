"""Cross-domain weakness detection and study suggestion engine."""

from typing import List

import structlog

from ..models import (
    FlashcardStats,
    OpeningStats,
    ChessPlayStats,
    StudySuggestion,
    Weakness,
)
from ..services.flashcard_reader import flashcard_reader
from ..services.repertoire_reader import repertoire_reader

logger = structlog.get_logger()


class WeaknessAnalyzer:
    """Synthesizes weaknesses from flashcards + openings into a unified profile."""

    async def get_unified_weaknesses(self, user_id: str) -> List[Weakness]:
        """Merge weakness sources from flashcard tags and opening mistakes."""
        weaknesses: List[Weakness] = []

        # Flashcard weakness tags
        fc_tags = await flashcard_reader.get_weakness_tags(user_id)
        for tag_info in fc_tags:
            weaknesses.append(
                Weakness(
                    tag=tag_info["tag"],
                    domain="flashcards",
                    occurrences=tag_info["count"],
                    mastery_pct=0.0,
                )
            )

        # Opening mistake patterns
        mistakes = await repertoire_reader.get_mistake_patterns(user_id)
        for m in mistakes:
            tag = m.get("opening") or f"position:{m.get('fen', 'unknown')[:20]}"
            weaknesses.append(
                Weakness(
                    tag=f"opening:{tag}",
                    domain="openings",
                    occurrences=m["count"],
                    mastery_pct=0.0,
                )
            )

        # Sort by occurrences descending
        weaknesses.sort(key=lambda w: w.occurrences, reverse=True)
        return weaknesses[:30]

    async def generate_suggestions(
        self,
        user_id: str,
        fc_stats: FlashcardStats,
        op_stats: OpeningStats,
        cp_stats: ChessPlayStats,
        weaknesses: List[Weakness],
    ) -> List[StudySuggestion]:
        """Rule-based study recommendations."""
        suggestions: List[StudySuggestion] = []
        priority = 0

        # 1. Due cards piling up
        if fc_stats.due_today > 10:
            priority += 1
            suggestions.append(
                StudySuggestion(
                    priority=priority,
                    suggestion=f"Review {fc_stats.due_today} due flashcards",
                    domain="flashcards",
                    reason="Due cards are piling up — review them to maintain retention.",
                )
            )

        # 2. Opening mistakes with no flashcards
        opening_weaknesses = [w for w in weaknesses if w.domain == "openings"]
        flashcard_weaknesses = [w for w in weaknesses if w.domain == "flashcards"]
        fc_tags_set = {w.tag for w in flashcard_weaknesses}

        for ow in opening_weaknesses[:3]:
            if ow.tag not in fc_tags_set:
                priority += 1
                suggestions.append(
                    StudySuggestion(
                        priority=priority,
                        suggestion=f"Create flashcards for {ow.tag}",
                        domain="flashcards",
                        reason="You make mistakes in this opening but have no flashcards to reinforce it.",
                    )
                )

        # 3. Flashcard mastery high but opening accuracy low
        if (
            fc_stats.accuracy > 80
            and op_stats.total_attempts > 10
            and op_stats.accuracy < 60
        ):
            priority += 1
            suggestions.append(
                StudySuggestion(
                    priority=priority,
                    suggestion="Practice your openings",
                    domain="openings",
                    reason="Your flashcard accuracy is good but opening practice accuracy is low — time to apply what you know.",
                )
            )

        # 4. Low overall activity
        if fc_stats.total_reviews == 0 and op_stats.total_attempts == 0:
            priority += 1
            suggestions.append(
                StudySuggestion(
                    priority=priority,
                    suggestion="Start studying to build your streak",
                    domain="flashcards",
                    reason="No activity recorded yet — begin with flashcards to get started.",
                )
            )

        # 5. Weakness with lowest mastery
        if weaknesses:
            worst = min(weaknesses, key=lambda w: w.mastery_pct)
            priority += 1
            suggestions.append(
                StudySuggestion(
                    priority=priority,
                    suggestion=f"Focus on {worst.tag}",
                    domain=worst.domain,
                    reason=f"This is your weakest area with {worst.occurrences} occurrences.",
                )
            )

        return suggestions


weakness_analyzer = WeaknessAnalyzer()
