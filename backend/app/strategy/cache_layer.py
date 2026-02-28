"""
DB-backed OHLCV caching layer.

Uses the CachedOHLCV table for persistent storage, falling back to yfinance.
Minimises API calls by only fetching missing date ranges.
"""

import logging
from datetime import date, datetime, timedelta
from typing import Optional

import pandas as pd
import yfinance as yf
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import CachedOHLCV

logger = logging.getLogger(__name__)


async def get_cached_ohlcv(
    db: AsyncSession,
    symbol: str,
    lookback_days: int = 500,
) -> Optional[pd.DataFrame]:
    """
    Return OHLCV dataframe for symbol, using DB cache where available.
    Missing ranges are fetched from yfinance and persisted.
    """
    end = date.today()
    start = end - timedelta(days=lookback_days)

    # 1. Query cached rows
    result = await db.execute(
        select(CachedOHLCV)
        .where(
            and_(
                CachedOHLCV.symbol == symbol,
                CachedOHLCV.trade_date >= start,
                CachedOHLCV.trade_date <= end,
            )
        )
        .order_by(CachedOHLCV.trade_date)
    )
    rows = result.scalars().all()

    # 2. Build DataFrame from cache
    if rows:
        cached_df = pd.DataFrame([
            {
                "date": r.trade_date,
                "open": r.open,
                "high": r.high,
                "low": r.low,
                "close": r.close,
                "volume": r.volume,
            }
            for r in rows
        ])
        cached_df["date"] = pd.to_datetime(cached_df["date"])
        cached_df.set_index("date", inplace=True)

        last_cached = cached_df.index.max().date()
        # If cache is fresh (within CACHE_OHLCV_DAYS), return it
        if (end - last_cached).days <= settings.CACHE_OHLCV_DAYS:
            if len(cached_df) >= 200:
                return cached_df
    else:
        last_cached = None
        cached_df = None

    # 3. Fetch from yfinance for missing range
    fetch_start = last_cached + timedelta(days=1) if last_cached else start
    try:
        ticker = yf.Ticker(symbol)
        fresh = ticker.history(
            start=fetch_start.strftime("%Y-%m-%d"),
            end=(end + timedelta(days=1)).strftime("%Y-%m-%d"),
        )
        if fresh.empty:
            return cached_df  # return whatever we had

        fresh.index = pd.to_datetime(fresh.index)
        if fresh.index.tz is not None:
            fresh.index = fresh.index.tz_localize(None)
        fresh.columns = [c.lower().replace(" ", "_") for c in fresh.columns]
        fresh = fresh[["open", "high", "low", "close", "volume"]].copy()
        fresh.dropna(inplace=True)

        # 4. Persist new rows
        for idx, row in fresh.iterrows():
            obj = CachedOHLCV(
                symbol=symbol,
                trade_date=idx.date(),
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=float(row["volume"]),
            )
            db.add(obj)

        try:
            await db.commit()
        except Exception:
            await db.rollback()
            logger.warning(f"Cache write conflict for {symbol}, ignoring duplicates")

        # 5. Merge cached + fresh
        if cached_df is not None:
            merged = pd.concat([cached_df, fresh])
            merged = merged[~merged.index.duplicated(keep="last")]
            merged.sort_index(inplace=True)
            return merged
        return fresh

    except Exception as e:
        logger.error(f"Cache fetch failed for {symbol}: {e}")
        return cached_df
