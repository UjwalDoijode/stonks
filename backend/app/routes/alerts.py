"""
Alerts CRUD + evaluation.

Persistent server-side alerts. Each call to GET /alerts also evaluates
active alerts against fresh market data (price + RSI) and marks any
condition that has been met as triggered.

This means alerts work even if the user closes the browser — the next
time anyone hits the endpoint, alerts are evaluated.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

import numpy as np
import yfinance as yf
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Alert

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/alerts", tags=["alerts"])


VALID_KINDS = {"above", "below", "rsi_above", "rsi_below"}


# ─── Schemas ──────────────────────────────────────────


class AlertCreate(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=30)
    kind: str
    value: float
    note: Optional[str] = Field(None, max_length=200)

    @field_validator("kind")
    @classmethod
    def kind_valid(cls, v: str) -> str:
        v = v.lower().strip()
        if v not in VALID_KINDS:
            raise ValueError(f"kind must be one of {sorted(VALID_KINDS)}")
        return v

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, v: str) -> str:
        return v.upper().strip().replace(" ", "")


class AlertOut(BaseModel):
    id: int
    symbol: str
    kind: str
    value: float
    note: Optional[str]
    triggered: bool
    triggered_at: Optional[datetime]
    triggered_price: Optional[float]
    triggered_value: Optional[float]
    active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Pure logic (testable) ────────────────────────────


def should_fire(kind: str, threshold: float, *, price: Optional[float], rsi: Optional[float]) -> bool:
    """
    Pure evaluator — given a snapshot, decide if an alert should fire.

    Used both by the API and by tests.
    """
    if kind == "above":
        return price is not None and price >= threshold
    if kind == "below":
        return price is not None and price <= threshold
    if kind == "rsi_above":
        return rsi is not None and rsi >= threshold
    if kind == "rsi_below":
        return rsi is not None and rsi <= threshold
    return False


def _resolve_symbol(sym: str) -> str:
    s = sym.strip().upper().replace(" ", "")
    if s in {"NIFTY", "NIFTY50"}:
        return "^NSEI"
    if s == "BANKNIFTY":
        return "^NSEBANK"
    if s == "SENSEX":
        return "^BSESN"
    if s.startswith("^") or "=" in s or s.endswith(".NS") or s.endswith(".BO"):
        return s
    return f"{s}.NS"


def _snapshot(symbol: str) -> dict:
    """
    Fetch a small market snapshot for one symbol.

    Returns dict with 'price' and 'rsi' (may be None on failure).
    """
    out: dict = {"price": None, "rsi": None}
    try:
        ticker = yf.Ticker(_resolve_symbol(symbol))
        hist = ticker.history(period="3mo")
        if hist is None or hist.empty:
            return out
        out["price"] = float(hist["Close"].iloc[-1])

        # RSI(14)
        delta = hist["Close"].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi_series = 100 - 100 / (1 + rs)
        rsi_val = float(rsi_series.iloc[-1])
        if not np.isnan(rsi_val):
            out["rsi"] = round(rsi_val, 2)
    except Exception as e:
        logger.warning(f"Alert snapshot failed for {symbol}: {e}")
    return out


# ─── Routes ───────────────────────────────────────────


@router.post("/", response_model=AlertOut, status_code=201)
async def create_alert(payload: AlertCreate, db: AsyncSession = Depends(get_db)):
    alert = Alert(
        symbol=payload.symbol,
        kind=payload.kind,
        value=payload.value,
        note=payload.note,
        active=True,
        triggered=False,
    )
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    return alert


@router.get("/", response_model=list[AlertOut])
async def list_alerts(
    evaluate: bool = True,
    include_triggered: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """
    List alerts. If `evaluate` is true (default), also evaluates active
    alerts against live market data and persists any triggers.
    """
    stmt = select(Alert).order_by(Alert.created_at.desc())
    res = await db.execute(stmt)
    alerts = list(res.scalars().all())

    if evaluate:
        # Group active alerts by symbol so we fetch each only once.
        active = [a for a in alerts if a.active and not a.triggered]
        symbols = {a.symbol for a in active}
        snapshots: dict[str, dict] = {}
        for sym in symbols:
            snapshots[sym] = _snapshot(sym)

        changed = False
        now = datetime.utcnow()
        for a in active:
            snap = snapshots.get(a.symbol) or {}
            if should_fire(a.kind, a.value, price=snap.get("price"), rsi=snap.get("rsi")):
                a.triggered = True
                a.triggered_at = now
                a.triggered_price = snap.get("price")
                a.triggered_value = snap.get("rsi") if a.kind.startswith("rsi") else snap.get("price")
                changed = True

        if changed:
            await db.commit()

    if not include_triggered:
        alerts = [a for a in alerts if not a.triggered]
    return alerts


@router.delete("/{alert_id}", status_code=204)
async def delete_alert(alert_id: int, db: AsyncSession = Depends(get_db)):
    a = await db.get(Alert, alert_id)
    if not a:
        raise HTTPException(404, "Alert not found")
    await db.delete(a)
    await db.commit()
    return None


@router.post("/{alert_id}/reset", response_model=AlertOut)
async def reset_alert(alert_id: int, db: AsyncSession = Depends(get_db)):
    """Re-arm a previously triggered alert."""
    a = await db.get(Alert, alert_id)
    if not a:
        raise HTTPException(404, "Alert not found")
    a.triggered = False
    a.triggered_at = None
    a.triggered_price = None
    a.triggered_value = None
    a.active = True
    await db.commit()
    await db.refresh(a)
    return a
