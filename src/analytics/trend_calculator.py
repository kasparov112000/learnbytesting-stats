"""Pandas-based trend analysis across domains."""

from datetime import datetime, timedelta
from typing import List, Optional

import structlog

try:
    import pandas as pd
    import numpy as np
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

from ..database import db
from ..models import TrendPoint, TrendResponse

logger = structlog.get_logger()


class TrendCalculator:
    """Calculates trend lines using pandas DataFrames."""

    async def get_trends(
        self, user_id: str, period: str = "30d"
    ) -> TrendResponse:
        """Compute trend data over a given period."""
        days = {"7d": 7, "30d": 30, "90d": 90, "365d": 365}.get(period, 30)

        sdb = db.db
        if not sdb:
            return TrendResponse(user_id=user_id, period=period)

        since = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")

        cursor = sdb.unified_daily_activity.find(
            {"user_id": user_id, "date": {"$gte": since}},
            {"_id": 0},
        ).sort("date", 1)
        docs = await cursor.to_list(days)

        if not docs or not PANDAS_AVAILABLE:
            return TrendResponse(user_id=user_id, period=period)

        df = pd.DataFrame(docs)

        # Activity trend (total activities per day)
        activity_trend = [
            TrendPoint(date=row["date"], value=float(row.get("total_activities", 0)))
            for _, row in df.iterrows()
        ]

        # Accuracy trend (total_correct / total_activities per day)
        accuracy_trend = []
        for _, row in df.iterrows():
            total = row.get("total_activities", 0)
            correct = row.get("total_correct", 0)
            acc = (correct / total * 100) if total > 0 else 0.0
            accuracy_trend.append(
                TrendPoint(date=row["date"], value=round(acc, 1))
            )

        # Domain breakdown (avg daily for period)
        domain_breakdown = {}
        for domain, prefix in [
            ("flashcards", "flashcard"),
            ("openings", "opening"),
            ("chess_play", "chess_play"),
        ]:
            col = f"{prefix}_reviews" if domain == "flashcards" else (
                f"{prefix}_attempts" if domain == "openings" else f"{prefix}_games"
            )
            if col in df.columns:
                domain_breakdown[domain] = {
                    "total": int(df[col].sum()),
                    "daily_avg": round(float(df[col].mean()), 1),
                }

        return TrendResponse(
            user_id=user_id,
            period=period,
            accuracy_trend=accuracy_trend,
            activity_trend=activity_trend,
            domain_breakdown=domain_breakdown,
        )


trend_calculator = TrendCalculator()
