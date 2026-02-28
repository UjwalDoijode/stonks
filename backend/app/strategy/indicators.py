"""Technical indicator calculations."""

import pandas as pd
import numpy as np
from app.config import settings


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add all required technical indicators to a DataFrame."""
    df = df.copy()

    # ── Moving Averages ──────────────────────────────────
    df["dma_200"] = df["close"].rolling(window=settings.DMA_LONG).mean()
    df["dma_50"] = df["close"].rolling(window=settings.DMA_MID).mean()
    df["dma_20"] = df["close"].rolling(window=settings.DMA_SHORT).mean()

    # ── 50 DMA Slope (trending up if slope > 0 over last 5 days) ─
    df["dma_50_slope"] = df["dma_50"].diff(5)

    # ── RSI ──────────────────────────────────────────────
    df["rsi"] = compute_rsi(df["close"], settings.RSI_PERIOD)

    # ── Volume metrics ───────────────────────────────────
    df["vol_sma"] = df["volume"].rolling(window=settings.VOLUME_LOOKBACK).mean()
    df["volume_ratio"] = df["volume"] / df["vol_sma"]

    # ── Previous candle high (for entry trigger) ─────────
    df["prev_high"] = df["high"].shift(1)

    # ── Swing low (lowest low of last N candles) ─────────
    df["swing_low"] = df["low"].rolling(window=settings.SWING_LOW_LOOKBACK).min()

    # ── Pullback proximity to 20 DMA ─────────────────────
    df["dist_to_20dma_pct"] = ((df["close"] - df["dma_20"]) / df["dma_20"]) * 100

    df.dropna(inplace=True)
    return df


def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Compute RSI using exponential moving average method."""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1 / period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi
