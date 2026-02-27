from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


# ── Enums ──────────────────────────────────────────────────────

class EventType(str, Enum):
    FLASHCARD_REVIEW = "flashcard_review"
    OPENING_ATTEMPT = "opening_attempt"
    CHESS_PLAY = "chess_play"


class MasteryLevel(str, Enum):
    NEW = "new"
    LEARNING = "learning"
    FAMILIAR = "familiar"
    MASTERED = "mastered"


# ── Event Payloads (webhook ingestion) ─────────────────────────

class FlashcardReviewEvent(BaseModel):
    user_id: str
    session_id: Optional[str] = None
    flashcard_id: Optional[str] = None
    quality: int = Field(..., ge=0, le=5, description="FSRS rating 0-5")
    response_time_ms: Optional[int] = None
    category_id: Optional[str] = None
    category_name: Optional[str] = None
    is_new_card: bool = False
    weakness_tags: List[str] = []
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class OpeningAttemptEvent(BaseModel):
    user_id: str
    fen: str
    played_move: Optional[str] = None
    was_correct: bool
    time_to_move: Optional[int] = None
    opening_name: Optional[str] = None
    eco: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ChessPlayEvent(BaseModel):
    user_id: str
    difficulty: Optional[str] = None
    question_type: Optional[str] = None
    was_correct: bool
    time_to_answer_ms: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ── Sub-documents for unified analytics ────────────────────────

class FlashcardStats(BaseModel):
    total_cards: int = 0
    mastered: int = 0
    learning: int = 0
    new_cards: int = 0
    total_reviews: int = 0
    accuracy: float = 0.0
    avg_response_time_ms: float = 0.0
    due_today: int = 0


class OpeningStats(BaseModel):
    total_positions: int = 0
    mastered: int = 0
    familiar: int = 0
    learning: int = 0
    new_positions: int = 0
    accuracy: float = 0.0
    total_attempts: int = 0
    avg_time_to_move_ms: float = 0.0


class ChessPlayStats(BaseModel):
    total_games: int = 0
    accuracy: float = 0.0
    total_correct: int = 0
    avg_time_to_answer_ms: float = 0.0


class Weakness(BaseModel):
    tag: str
    domain: str  # "flashcards", "openings", "chess_play"
    mastery_pct: float = 0.0
    occurrences: int = 0


class Correlation(BaseModel):
    description: str
    domain_a: str
    domain_b: str
    metric: Optional[float] = None
    period: Optional[str] = None


class StudySuggestion(BaseModel):
    priority: int = 0
    suggestion: str
    domain: str
    reason: str


# ── Unified User Analytics (response model) ───────────────────

class UnifiedUserAnalytics(BaseModel):
    user_id: str
    user_email: Optional[str] = None
    total_activities: int = 0
    total_study_time_ms: int = 0
    overall_accuracy: float = 0.0
    current_streak: int = 0
    longest_streak: int = 0
    flashcard_stats: FlashcardStats = Field(default_factory=FlashcardStats)
    opening_stats: OpeningStats = Field(default_factory=OpeningStats)
    chess_play_stats: ChessPlayStats = Field(default_factory=ChessPlayStats)
    unified_weaknesses: List[Weakness] = []
    study_suggestions: List[StudySuggestion] = []
    correlations: List[Correlation] = []
    last_computed_at: Optional[datetime] = None
    computation_version: int = 1


# ── Daily Activity (heatmap) ──────────────────────────────────

class DailyActivity(BaseModel):
    user_id: str
    date: str  # "YYYY-MM-DD"
    flashcard_reviews: int = 0
    flashcard_correct: int = 0
    flashcard_time_ms: int = 0
    opening_attempts: int = 0
    opening_correct: int = 0
    opening_time_ms: int = 0
    chess_play_games: int = 0
    chess_play_correct: int = 0
    chess_play_time_ms: int = 0
    total_activities: int = 0
    total_correct: int = 0
    total_time_ms: int = 0


# ── Trend Data ─────────────────────────────────────────────────

class TrendPoint(BaseModel):
    date: str
    value: float
    domain: Optional[str] = None


class TrendResponse(BaseModel):
    user_id: str
    period: str  # "7d", "30d", "90d"
    accuracy_trend: List[TrendPoint] = []
    activity_trend: List[TrendPoint] = []
    domain_breakdown: dict = {}


# ── API Response Models ────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    service: str = "stats"
    version: str
    databases: dict = {}


class HeatmapResponse(BaseModel):
    user_id: str
    days: List[DailyActivity] = []
    period_start: Optional[str] = None
    period_end: Optional[str] = None


class WeaknessResponse(BaseModel):
    user_id: str
    weaknesses: List[Weakness] = []


class SuggestionResponse(BaseModel):
    user_id: str
    suggestions: List[StudySuggestion] = []


class DomainComparisonResponse(BaseModel):
    user_id: str
    flashcard_stats: FlashcardStats = Field(default_factory=FlashcardStats)
    opening_stats: OpeningStats = Field(default_factory=OpeningStats)
    chess_play_stats: ChessPlayStats = Field(default_factory=ChessPlayStats)


class CorrelationResponse(BaseModel):
    user_id: str
    correlations: List[Correlation] = []


class EventAck(BaseModel):
    status: str = "accepted"
    event_type: str
    user_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
