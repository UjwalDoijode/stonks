"""
Stock Ranking System — scores NIFTY 500 stocks on 5 factors.

Factors (each 0-20, composite 0-100):
  1. Relative Strength (3M)   — 3-month return vs NIFTY benchmark
  2. Momentum (6M)            — 6-month absolute momentum
  3. Vol-Adjusted Return      — 6-month return / volatility (mini Sharpe)
  4. Volume Strength          — recent volume vs 50-day avg
  5. Trend Slope              — slope of 50 DMA (normalised)

Process:
  1. Fetch data for full universe (with caching)
  2. Compute factor scores for each stock
  3. Rank by composite score descending
  4. Return top N (default 5) filtered by regime
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd

from app.config import settings
from app.strategy.macro_data import fetch_with_cache

logger = logging.getLogger(__name__)

# Cache for rankings (refresh at most once per hour)
_ranking_cache: Optional[tuple[datetime, list]] = None
_RANKING_TTL = 3600  # seconds


@dataclass
class StockScore:
    symbol: str
    clean_symbol: str
    price: float
    rs_3m: float = 0.0           # Relative Strength vs NIFTY (0-20)
    momentum_6m: float = 0.0     # 6M momentum score (0-20)
    vol_adj_return: float = 0.0  # Vol-adjusted return (0-20)
    volume_strength: float = 0.0 # Volume strength (0-20)
    trend_slope: float = 0.0     # Trend slope (0-20)
    composite: float = 0.0       # Total 0-100
    rank: int = 0

    # Raw values for transparency
    raw_return_3m: float = 0.0
    raw_return_6m: float = 0.0
    raw_volatility: float = 0.0
    raw_volume_ratio: float = 0.0
    raw_slope: float = 0.0


def _safe_pct_change(series: pd.Series, periods: int) -> float:
    """Safe percentage change over N periods."""
    if len(series) < periods + 1:
        return 0.0
    start = series.iloc[-(periods + 1)]
    end = series.iloc[-1]
    if start <= 0:
        return 0.0
    return ((end - start) / start) * 100


def _normalise_to_score(value: float, values: list[float], max_score: float = 20.0) -> float:
    """Normalise a value into 0-max_score using percentile rank within the group."""
    if not values or len(values) < 2:
        return max_score / 2
    sorted_v = sorted(values)
    # Percentile rank
    rank = sum(1 for v in sorted_v if v <= value)
    pct = rank / len(sorted_v)
    return round(pct * max_score, 2)


def compute_stock_scores(
    symbols: list[str],
    nifty_return_3m: float = 0.0,
    max_stocks: int = 50,
) -> list[StockScore]:
    """
    Compute composite scores for a list of symbols.
    Uses batch yf.download() for speed, then scores each stock on 5 factors,
    each 0-20, totalling 0-100.
    Returns sorted descending by composite score.
    """
    import yfinance as yf
    from datetime import datetime, timedelta

    # Batch-download all symbols at once (much faster than one-by-one)
    end = datetime.now()
    start = end - timedelta(days=365)
    try:
        batch_df = yf.download(
            symbols,
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
            group_by="ticker",
            threads=True,
            progress=False,
        )
    except Exception as e:
        logger.error(f"Batch download failed: {e}")
        return []

    if batch_df is None or batch_df.empty:
        return []

    raw_data: list[dict] = []

    # yfinance 1.2.0: group_by='ticker' always puts tickers at level 0
    available_tickers = set(batch_df.columns.get_level_values(0).unique())

    for sym in symbols:
        try:
            if sym not in available_tickers:
                continue
            df = batch_df[sym].dropna()

            if len(df) < 130:
                continue

            close = df["Close"]
            volume = df["Volume"] if "Volume" in df.columns else pd.Series([0] * len(df))

            price = float(close.iloc[-1])

            ret_3m = _safe_pct_change(close, 63)
            rs_3m_raw = ret_3m - nifty_return_3m
            ret_6m = _safe_pct_change(close, 126)

            daily_returns = close.pct_change().dropna().tail(126)
            volatility = float(daily_returns.std() * np.sqrt(252)) if len(daily_returns) > 20 else 1.0
            vol_adj = (ret_6m / volatility) if volatility > 0 else 0.0

            vol_sma50 = float(volume.rolling(50).mean().iloc[-1]) if len(volume) > 50 else 1.0
            vol_ratio = float(volume.iloc[-5:].mean() / vol_sma50) if vol_sma50 > 0 else 1.0

            dma50 = close.rolling(50).mean()
            slope_raw = float(dma50.diff(10).iloc[-1]) if len(dma50.dropna()) > 10 else 0.0
            slope_norm = (slope_raw / price * 100) if price > 0 else 0.0

            raw_data.append({
                "symbol": sym,
                "price": price,
                "rs_3m_raw": rs_3m_raw,
                "ret_6m": ret_6m,
                "vol_adj": vol_adj,
                "vol_ratio": vol_ratio,
                "slope_norm": slope_norm,
                "volatility": volatility,
                "ret_3m": ret_3m,
            })
        except Exception as e:
            logger.debug(f"Ranking skip {sym}: {e}")
            continue

    if not raw_data:
        return []

    # Extract raw value arrays for normalisation
    rs_vals = [d["rs_3m_raw"] for d in raw_data]
    mom_vals = [d["ret_6m"] for d in raw_data]
    va_vals = [d["vol_adj"] for d in raw_data]
    vr_vals = [d["vol_ratio"] for d in raw_data]
    sl_vals = [d["slope_norm"] for d in raw_data]

    scores: list[StockScore] = []
    for d in raw_data:
        rs_score = _normalise_to_score(d["rs_3m_raw"], rs_vals)
        mom_score = _normalise_to_score(d["ret_6m"], mom_vals)
        va_score = _normalise_to_score(d["vol_adj"], va_vals)
        vr_score = _normalise_to_score(d["vol_ratio"], vr_vals)
        sl_score = _normalise_to_score(d["slope_norm"], sl_vals)

        composite = round(rs_score + mom_score + va_score + vr_score + sl_score, 2)

        scores.append(StockScore(
            symbol=d["symbol"],
            clean_symbol=d["symbol"].replace(".NS", ""),
            price=round(d["price"], 2),
            rs_3m=rs_score,
            momentum_6m=mom_score,
            vol_adj_return=va_score,
            volume_strength=vr_score,
            trend_slope=sl_score,
            composite=composite,
            raw_return_3m=round(d["ret_3m"], 2),
            raw_return_6m=round(d["ret_6m"], 2),
            raw_volatility=round(d["volatility"], 4),
            raw_volume_ratio=round(d["vol_ratio"], 2),
            raw_slope=round(d["slope_norm"], 4),
        ))

    # Sort descending by composite
    scores.sort(key=lambda s: s.composite, reverse=True)

    # Assign ranks
    for i, s in enumerate(scores):
        s.rank = i + 1

    return scores[:max_stocks]


def get_top_ranked(
    n: int = 5,
    universe_tier: str = "100",
    regime: str = "NEUTRAL",
) -> list[StockScore]:
    """
    Get top N ranked stocks from the given universe tier.
    Uses cache to avoid re-computation within TTL.
    Filters based on regime (extreme risk → return empty).
    """
    global _ranking_cache

    if regime == "EXTREME_RISK":
        return []  # No equity in extreme risk

    # Check cache
    if _ranking_cache is not None:
        cached_time, cached_scores = _ranking_cache
        if (datetime.now() - cached_time).total_seconds() < _RANKING_TTL:
            return cached_scores[:n]

    from app.strategy.universe import get_universe

    # For interactive ranking, use NIFTY 50 for speed; full tier only for batch jobs
    scan_tier = "50" if universe_tier in ("100", "200", "500") else universe_tier
    symbols = get_universe(scan_tier)

    # Get NIFTY 3M return for relative strength
    nifty_df = fetch_with_cache(settings.NIFTY_SYMBOL, 1)
    nifty_ret_3m = 0.0
    if nifty_df is not None and len(nifty_df) > 63:
        nifty_ret_3m = _safe_pct_change(nifty_df["close"], 63)

    scores = compute_stock_scores(symbols, nifty_ret_3m, max_stocks=n * 3)
    _ranking_cache = (datetime.now(), scores)

    return scores[:n]


def clear_ranking_cache():
    """Clear the ranking cache."""
    global _ranking_cache
    _ranking_cache = None
