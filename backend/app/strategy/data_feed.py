"""Market data fetching via yfinance."""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
import logging

from app.config import settings

logger = logging.getLogger(__name__)


def fetch_ohlcv(symbol: str, period_years: int = 5) -> Optional[pd.DataFrame]:
    """Fetch daily OHLCV data for a symbol."""
    try:
        end = datetime.now()
        start = end - timedelta(days=period_years * 365)
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"))

        if df.empty or len(df) < settings.DMA_LONG + 20:
            logger.warning(f"Insufficient data for {symbol}: {len(df)} rows")
            return None

        df.index = pd.to_datetime(df.index)
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)

        # Standardize column names
        df.columns = [c.lower().replace(" ", "_") for c in df.columns]
        expected = {"open", "high", "low", "close", "volume"}
        if not expected.issubset(set(df.columns)):
            logger.warning(f"Missing columns for {symbol}: {df.columns.tolist()}")
            return None

        df = df[["open", "high", "low", "close", "volume"]].copy()
        df.dropna(inplace=True)
        return df

    except Exception as e:
        logger.error(f"Error fetching {symbol}: {e}")
        return None


def fetch_nifty_data(period_years: int = 5) -> Optional[pd.DataFrame]:
    """Fetch NIFTY 50 index data for regime filter."""
    return fetch_ohlcv(settings.NIFTY_SYMBOL, period_years)


def is_market_bullish(nifty_df: Optional[pd.DataFrame] = None) -> bool:
    """Check if NIFTY is above its 200 DMA (regime filter)."""
    if nifty_df is None:
        nifty_df = fetch_nifty_data(period_years=2)
    if nifty_df is None or len(nifty_df) < settings.DMA_LONG:
        return False

    dma_200 = nifty_df["close"].rolling(settings.DMA_LONG).mean()
    latest_close = nifty_df["close"].iloc[-1]
    latest_dma = dma_200.iloc[-1]
    return latest_close > latest_dma


def get_nifty_regime_info(nifty_df: Optional[pd.DataFrame] = None) -> dict:
    """Get regime information for the dashboard."""
    if nifty_df is None:
        nifty_df = fetch_nifty_data(period_years=2)
    if nifty_df is None or len(nifty_df) < settings.DMA_LONG:
        return {"nifty_close": 0, "nifty_200dma": 0, "above_200dma": False}

    dma_200 = nifty_df["close"].rolling(settings.DMA_LONG).mean()
    return {
        "nifty_close": round(nifty_df["close"].iloc[-1], 2),
        "nifty_200dma": round(dma_200.iloc[-1], 2),
        "above_200dma": bool(nifty_df["close"].iloc[-1] > dma_200.iloc[-1]),
    }
