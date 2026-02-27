"""Stats Microservice — Unified learning analytics for LearnByTesting.ai"""

from contextlib import asynccontextmanager
from datetime import datetime

import structlog
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.responses import JSONResponse

from . import __version__
from .config import settings
from .database import db
from .models import (
    ChessPlayEvent,
    CorrelationResponse,
    DomainComparisonResponse,
    EventAck,
    FlashcardReviewEvent,
    HeatmapResponse,
    HealthResponse,
    OpeningAttemptEvent,
    SuggestionResponse,
    TrendResponse,
    UnifiedUserAnalytics,
    WeaknessResponse,
)
from .services.unified_dashboard import dashboard_service
from .services.cache_manager import cache_manager
from .services.flashcard_reader import flashcard_reader
from .services.repertoire_reader import repertoire_reader
from .analytics.activity_aggregator import activity_aggregator
from .analytics.trend_calculator import trend_calculator
from .analytics.weakness_analyzer import weakness_analyzer

logger = structlog.get_logger()


# ── Lifespan ───────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Stats Microservice", port=settings.port)
    await db.connect()
    yield
    await db.disconnect()
    logger.info("Stats Microservice shutdown complete")


app = FastAPI(
    title="Stats Microservice",
    description="Unified learning analytics across flashcards, openings, and chess play",
    version=__version__,
    lifespan=lifespan,
)

# ── CORS ───────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
        "http://localhost:8080",
        "https://app.learnbytesting.ai",
        "https://orchestrator.learnbytesting.ai",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Error Handlers ─────────────────────────────────────────────

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    body = None
    try:
        body = await request.json()
    except Exception:
        try:
            raw = await request.body()
            body = raw.decode() if raw else None
        except Exception:
            pass

    logger.error(
        "Validation error",
        path=request.url.path,
        method=request.method,
        body=body,
        errors=exc.errors(),
    )
    return JSONResponse(
        status_code=422,
        content={
            "detail": exc.errors(),
            "body_received": str(body)[:500] if body else None,
        },
    )


# ── Health ─────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse)
async def health_check():
    db_status = "not_initialized"
    try:
        if db.client:
            await db.client.admin.command("ping")
            db_status = "connected"
    except Exception:
        db_status = "disconnected"

    return HealthResponse(
        status="healthy" if db_status == "connected" else "degraded",
        version=__version__,
        databases={"stats_db": db_status},
    )


# ── Unified Dashboard ─────────────────────────────────────────

@app.get("/dashboard/{user_id}", response_model=UnifiedUserAnalytics)
async def get_dashboard(user_id: str):
    """Get unified learning dashboard for a user."""
    return await dashboard_service.get_dashboard(user_id)


@app.get("/dashboard/{user_id}/heatmap", response_model=HeatmapResponse)
async def get_heatmap(
    user_id: str, days: int = Query(default=365, ge=1, le=730)
):
    """Get unified activity heatmap (all domains merged)."""
    activities = await activity_aggregator.get_heatmap(user_id, days)
    dates = [a.date for a in activities] if activities else []
    return HeatmapResponse(
        user_id=user_id,
        days=activities,
        period_start=min(dates) if dates else None,
        period_end=max(dates) if dates else None,
    )


@app.get("/dashboard/{user_id}/trends", response_model=TrendResponse)
async def get_trends(
    user_id: str, period: str = Query(default="30d", pattern="^(7d|30d|90d|365d)$")
):
    """Get cross-domain trend lines."""
    return await trend_calculator.get_trends(user_id, period)


@app.get("/dashboard/{user_id}/weaknesses", response_model=WeaknessResponse)
async def get_weaknesses(user_id: str):
    """Get synthesized weaknesses across all domains."""
    weaknesses = await weakness_analyzer.get_unified_weaknesses(user_id)
    return WeaknessResponse(user_id=user_id, weaknesses=weaknesses)


@app.get("/dashboard/{user_id}/suggestions", response_model=SuggestionResponse)
async def get_suggestions(user_id: str):
    """Get study suggestions based on cross-domain analysis."""
    analytics = await dashboard_service.get_dashboard(user_id)
    return SuggestionResponse(
        user_id=user_id, suggestions=analytics.study_suggestions
    )


# ── Event Ingestion (webhooks from other services) ─────────────

@app.post("/events/flashcard-review", response_model=EventAck)
async def ingest_flashcard_review(event: FlashcardReviewEvent):
    """Called by flashcards service (via orchestrator) after a review."""
    logger.info(
        "Flashcard review event",
        user_id=event.user_id,
        quality=event.quality,
    )

    sdb = db.db
    if sdb:
        # Log the raw event
        await sdb.event_log.insert_one(
            {
                "event_type": "flashcard_review",
                "user_id": event.user_id,
                "payload": event.model_dump(),
                "timestamp": event.timestamp,
            }
        )

    # Update materialized view
    await flashcard_reader.update_from_event(
        user_id=event.user_id,
        quality=event.quality,
        response_time_ms=event.response_time_ms or 0,
        is_new_card=event.is_new_card,
        weakness_tags=event.weakness_tags,
        flashcard_id=event.flashcard_id,
    )

    # Update daily activity
    date_str = event.timestamp.strftime("%Y-%m-%d")
    correct = 1 if event.quality >= 3 else 0
    await activity_aggregator.record_flashcard_activity(
        user_id=event.user_id,
        date_str=date_str,
        reviews=1,
        correct=correct,
        time_ms=event.response_time_ms or 0,
    )

    # Invalidate cache
    await cache_manager.invalidate(event.user_id)

    return EventAck(event_type="flashcard_review", user_id=event.user_id)


@app.post("/events/opening-attempt", response_model=EventAck)
async def ingest_opening_attempt(event: OpeningAttemptEvent):
    """Called by user-repertoire service (via orchestrator) after a move attempt."""
    logger.info(
        "Opening attempt event",
        user_id=event.user_id,
        was_correct=event.was_correct,
    )

    sdb = db.db
    if sdb:
        await sdb.event_log.insert_one(
            {
                "event_type": "opening_attempt",
                "user_id": event.user_id,
                "payload": event.model_dump(),
                "timestamp": event.timestamp,
            }
        )

    # Update materialized view
    await repertoire_reader.update_from_event(
        user_id=event.user_id,
        fen=event.fen,
        played_move=event.played_move,
        was_correct=event.was_correct,
        time_to_move=event.time_to_move,
        opening_name=event.opening_name,
        eco=event.eco,
    )

    # Update daily activity
    date_str = event.timestamp.strftime("%Y-%m-%d")
    await activity_aggregator.record_opening_activity(
        user_id=event.user_id,
        date_str=date_str,
        attempts=1,
        correct=1 if event.was_correct else 0,
        time_ms=event.time_to_move or 0,
    )

    await cache_manager.invalidate(event.user_id)

    return EventAck(event_type="opening_attempt", user_id=event.user_id)


@app.post("/events/chess-play", response_model=EventAck)
async def ingest_chess_play(event: ChessPlayEvent):
    """Called by mobile/chess-play (via orchestrator) after a game event."""
    logger.info(
        "Chess play event",
        user_id=event.user_id,
        was_correct=event.was_correct,
    )

    sdb = db.db
    if sdb:
        await sdb.chess_play_events.insert_one(event.model_dump())
        await sdb.event_log.insert_one(
            {
                "event_type": "chess_play",
                "user_id": event.user_id,
                "payload": event.model_dump(),
                "timestamp": event.timestamp,
            }
        )

    date_str = event.timestamp.strftime("%Y-%m-%d")
    await activity_aggregator.record_chess_play_activity(
        user_id=event.user_id,
        date_str=date_str,
        games=1,
        correct=1 if event.was_correct else 0,
        time_ms=event.time_to_answer_ms or 0,
    )

    await cache_manager.invalidate(event.user_id)

    return EventAck(event_type="chess_play", user_id=event.user_id)


# ── Cross-Domain Analysis ─────────────────────────────────────

@app.get("/analysis/{user_id}/correlations", response_model=CorrelationResponse)
async def get_correlations(user_id: str):
    """Get cross-domain correlation patterns."""
    analytics = await dashboard_service.get_dashboard(user_id)
    return CorrelationResponse(
        user_id=user_id, correlations=analytics.correlations
    )


@app.get(
    "/analysis/{user_id}/domain-comparison",
    response_model=DomainComparisonResponse,
)
async def get_domain_comparison(user_id: str):
    """Get side-by-side stats across all domains."""
    analytics = await dashboard_service.get_dashboard(user_id)
    return DomainComparisonResponse(
        user_id=user_id,
        flashcard_stats=analytics.flashcard_stats,
        opening_stats=analytics.opening_stats,
        chess_play_stats=analytics.chess_play_stats,
    )


# ── Admin ──────────────────────────────────────────────────────

@app.post("/admin/recompute/{user_id}", response_model=UnifiedUserAnalytics)
async def admin_recompute(user_id: str):
    """Force recompute unified analytics (bypasses cache)."""
    logger.info("Admin recompute requested", user_id=user_id)
    return await dashboard_service.compute_dashboard(user_id)
