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

    # ── CCI (Commodity Channel Index) ────────────────────
    df["cci"] = compute_cci(df, period=20)

    # ── Supertrend ───────────────────────────────────────
    st, st_dir = compute_supertrend(df, period=10, multiplier=3.0)
    df["supertrend"] = st
    df["supertrend_direction"] = st_dir  # 1 = bullish, -1 = bearish

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


def compute_cci(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """
    Compute Commodity Channel Index.
    CCI = (Typical Price - SMA of TP) / (0.015 * Mean Deviation)

    Interpretation:
      > +100 : strong bullish momentum / potential overbought
      < -100 : strong bearish momentum / potential oversold
      -100 to +100 : ranging / consolidation
      For swing pullback: ideal zone is -50 to +100 (not oversold, not overbought)
    """
    tp = (df["high"] + df["low"] + df["close"]) / 3
    sma_tp = tp.rolling(window=period).mean()
    mean_dev = tp.rolling(window=period).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
    cci = (tp - sma_tp) / (0.015 * mean_dev)
    return cci


def compute_supertrend(
    df: pd.DataFrame, period: int = 10, multiplier: float = 3.0
) -> tuple[pd.Series, pd.Series]:
    """
    Compute the Supertrend indicator.

    Returns:
      (supertrend_line, direction)
      direction: 1 = bullish (price above supertrend), -1 = bearish

    The Supertrend uses ATR bands around the midpoint (HL2):
      Upper Band = HL2 + multiplier * ATR
      Lower Band = HL2 - multiplier * ATR
    """
    hl2 = (df["high"] + df["low"]) / 2

    # ATR
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - df["close"].shift(1)).abs(),
        (df["low"] - df["close"].shift(1)).abs(),
    ], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()

    # Basic bands
    upper_basic = hl2 + multiplier * atr
    lower_basic = hl2 - multiplier * atr

    n = len(df)
    supertrend = pd.Series(np.nan, index=df.index)
    direction = pd.Series(1, index=df.index, dtype=int)

    upper_band = upper_basic.copy()
    lower_band = lower_basic.copy()

    for i in range(1, n):
        # Lower band logic: keep previous if current basic <= previous
        if lower_basic.iloc[i] > lower_band.iloc[i - 1] or df["close"].iloc[i - 1] <= lower_band.iloc[i - 1]:
            lower_band.iloc[i] = lower_basic.iloc[i]
        else:
            lower_band.iloc[i] = lower_band.iloc[i - 1]

        # Upper band logic: keep previous if current basic >= previous
        if upper_basic.iloc[i] < upper_band.iloc[i - 1] or df["close"].iloc[i - 1] >= upper_band.iloc[i - 1]:
            upper_band.iloc[i] = upper_basic.iloc[i]
        else:
            upper_band.iloc[i] = upper_band.iloc[i - 1]

        # Direction
        if direction.iloc[i - 1] == 1:  # was bullish
            if df["close"].iloc[i] < lower_band.iloc[i]:
                direction.iloc[i] = -1
            else:
                direction.iloc[i] = 1
        else:  # was bearish
            if df["close"].iloc[i] > upper_band.iloc[i]:
                direction.iloc[i] = 1
            else:
                direction.iloc[i] = -1

        # Supertrend value
        supertrend.iloc[i] = lower_band.iloc[i] if direction.iloc[i] == 1 else upper_band.iloc[i]

    return supertrend, direction
