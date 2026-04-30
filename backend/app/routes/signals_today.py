"""
Today's Signals — curated, decision-ready digest endpoint.

Surfaces the highest-conviction items from the most recent scan, plus
any open trades and freshly triggered alerts, so users see actionable
information at a glance without having to dig through full scan tables.
"""

from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Alert, ScanResult, Trade

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/signals", tags=["signals"])


def _serialize_scan(s: ScanResult) -> dict:
    return {
        "symbol": s.symbol,
        "price": s.price,
        "rsi": s.rsi,
        "recommendation": s.recommendation,
        "conviction": s.conviction,
        "conviction_score": s.conviction_score,
        "criteria_met": s.criteria_met,
        "primary_reason": s.primary_reason,
        "category_tag": s.category_tag,
        "entry_price": s.entry_price,
        "stop_loss_price": s.stop_loss_price,
        "target_1": s.target_1,
        "target_2": s.target_2,
        "risk_reward": s.risk_reward,
        "risk_warning": s.risk_warning,
    }


@router.get("/today")
async def todays_signals(
    limit: int = Query(8, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """
    Return the top BUY/RECOMMENDED candidates from the latest scan,
    plus a count of open trades and freshly triggered alerts.

    Frontend uses this for a single, glanceable "what should I do today"
    surface on the Dashboard.
    """
    # Latest scan date
    res = await db.execute(
        select(ScanResult.scan_date).order_by(desc(ScanResult.scan_date)).limit(1)
    )
    latest = res.scalar_one_or_none()

    top_signals: list[dict] = []
    if latest:
        res = await db.execute(
            select(ScanResult)
            .where(
                ScanResult.scan_date == latest,
                ScanResult.recommendation.in_(("BUY", "RECOMMENDED")),
            )
            .order_by(desc(ScanResult.conviction_score), desc(ScanResult.criteria_met))
            .limit(limit)
        )
        top_signals = [_serialize_scan(s) for s in res.scalars().all()]

    # Open trades count
    res = await db.execute(select(Trade).where(Trade.status == "OPEN"))
    open_trades = len(res.scalars().all())

    # Triggered alerts (last 24h)
    res = await db.execute(select(Alert).where(Alert.triggered.is_(True)))
    recent_triggered = [
        {
            "id": a.id,
            "symbol": a.symbol,
            "kind": a.kind,
            "value": a.value,
            "triggered_at": a.triggered_at.isoformat() if a.triggered_at else None,
            "triggered_price": a.triggered_price,
        }
        for a in res.scalars().all()
    ]

    return {
        "scan_date": latest.isoformat() if latest else None,
        "generated_at": datetime.utcnow().isoformat(),
        "top_signals": top_signals,
        "open_trades": open_trades,
        "triggered_alerts": recent_triggered[:5],
        "triggered_alerts_count": len(recent_triggered),
    }
