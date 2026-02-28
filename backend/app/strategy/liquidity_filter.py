"""
Liquidity & Slippage Filter — prevent allocation to illiquid stocks.

For NIFTY 500 stock selection:
  1. Filter stocks with minimum average daily turnover
  2. Estimate bid-ask spread from intraday range
  3. Adjust expected returns for estimated slippage
  4. Prevent allocation to illiquid smallcaps

Ensures only tradeable stocks enter the portfolio.
"""

import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────
MIN_AVG_DAILY_TURNOVER = 5_000_000   # ₹50 lakh minimum daily turnover
MIN_AVG_DAILY_VOLUME = 50_000        # 50K shares minimum
MAX_SPREAD_PCT = 1.0                  # Max acceptable estimated spread %
SLIPPAGE_ESTIMATE_PCT = 0.15          # Default slippage assumption
ILLIQUID_PENALTY = 0.5                # Score penalty for marginal liquidity


@dataclass
class LiquidityMetrics:
    """Liquidity assessment for a single stock."""
    symbol: str
    avg_daily_volume: float = 0.0
    avg_daily_turnover: float = 0.0       # Volume × Price
    estimated_spread_pct: float = 0.0     # Estimated from high-low range
    slippage_estimate_pct: float = 0.0    # Impact cost estimate
    liquidity_score: float = 0.0          # 0-100 (100 = most liquid)
    is_liquid: bool = True
    reason: str = ""


@dataclass
class LiquidityFilterResult:
    """Result of liquidity filtering across all candidates."""
    passed: list[LiquidityMetrics]
    rejected: list[LiquidityMetrics]
    total_candidates: int = 0
    passed_count: int = 0
    avg_liquidity_score: float = 0.0


def estimate_spread(df: pd.DataFrame) -> float:
    """
    Estimate bid-ask spread from daily high-low range.
    Spread ≈ 2 × (High - Low) / (High + Low) averaged over recent days.
    This is a rough proxy when order book data isn't available.
    """
    if df is None or len(df) < 5:
        return 1.0  # Conservative default

    try:
        recent = df.tail(20)
        if "high" in recent.columns and "low" in recent.columns:
            hl_spread = 2 * (recent["high"] - recent["low"]) / (recent["high"] + recent["low"])
            avg_spread = float(hl_spread.mean()) * 100
            return round(max(0.01, avg_spread), 4)
    except Exception:
        pass

    return 0.5  # Default


def estimate_slippage(avg_volume: float, position_value: float, spread_pct: float) -> float:
    """
    Estimate slippage based on position size relative to daily volume.
    Impact = spread/2 + (position_value / daily_turnover) × factor
    """
    base_slippage = spread_pct / 2
    if avg_volume <= 0:
        return base_slippage + 0.5

    # Impact cost increases with relative position size
    volume_impact = 0.0
    if position_value > 0 and avg_volume > 0:
        pct_of_volume = position_value / (avg_volume * 100)  # rough turnover proxy
        if pct_of_volume > 0.1:
            volume_impact = 0.3
        elif pct_of_volume > 0.05:
            volume_impact = 0.15
        elif pct_of_volume > 0.01:
            volume_impact = 0.05

    return round(base_slippage + volume_impact, 4)


def assess_liquidity(
    symbol: str,
    df: Optional[pd.DataFrame] = None,
    position_value: float = 10000.0,
) -> LiquidityMetrics:
    """
    Assess liquidity for a single stock.

    Args:
        symbol: Stock symbol
        df: OHLCV DataFrame (if available)
        position_value: Expected position size in ₹

    Returns:
        LiquidityMetrics with scores and pass/fail
    """
    if df is None or len(df) < 20:
        return LiquidityMetrics(
            symbol=symbol,
            is_liquid=False,
            reason="Insufficient price history for liquidity assessment",
        )

    try:
        recent = df.tail(20)
        close = recent["close"] if "close" in recent.columns else recent.iloc[:, 3]
        volume = recent["volume"] if "volume" in recent.columns else recent.iloc[:, 4]

        avg_vol = float(volume.mean())
        avg_price = float(close.mean())
        avg_turnover = avg_vol * avg_price

        spread = estimate_spread(df)
        slippage = estimate_slippage(avg_vol, position_value, spread)

        # Liquidity score (0-100)
        vol_score = min(40, (avg_vol / MIN_AVG_DAILY_VOLUME) * 20)
        turnover_score = min(30, (avg_turnover / MIN_AVG_DAILY_TURNOVER) * 15)
        spread_score = max(0, 30 - spread * 30)

        liquidity_score = round(vol_score + turnover_score + spread_score, 1)
        liquidity_score = min(100, max(0, liquidity_score))

        # Pass/fail
        reasons = []
        is_liquid = True

        if avg_turnover < MIN_AVG_DAILY_TURNOVER:
            is_liquid = False
            reasons.append(
                f"Avg daily turnover ₹{avg_turnover/1e6:.1f}L below "
                f"₹{MIN_AVG_DAILY_TURNOVER/1e6:.0f}L threshold"
            )

        if avg_vol < MIN_AVG_DAILY_VOLUME:
            is_liquid = False
            reasons.append(
                f"Avg daily volume {avg_vol/1000:.0f}K below "
                f"{MIN_AVG_DAILY_VOLUME/1000:.0f}K threshold"
            )

        if spread > MAX_SPREAD_PCT:
            is_liquid = False
            reasons.append(f"Estimated spread {spread:.2f}% exceeds {MAX_SPREAD_PCT}% limit")

        return LiquidityMetrics(
            symbol=symbol,
            avg_daily_volume=round(avg_vol, 0),
            avg_daily_turnover=round(avg_turnover, 0),
            estimated_spread_pct=spread,
            slippage_estimate_pct=slippage,
            liquidity_score=liquidity_score,
            is_liquid=is_liquid,
            reason="; ".join(reasons) if reasons else "Adequate liquidity",
        )

    except Exception as e:
        logger.error(f"Liquidity assessment failed for {symbol}: {e}")
        return LiquidityMetrics(
            symbol=symbol,
            is_liquid=False,
            reason=f"Assessment error: {str(e)}",
        )


def filter_by_liquidity(
    scored_stocks: list,
    data_map: Optional[dict] = None,
    position_value: float = 10000.0,
) -> LiquidityFilterResult:
    """
    Filter a list of StockScore objects by liquidity criteria.

    Args:
        scored_stocks: List of StockScore objects
        data_map: Dict of symbol → DataFrame (OHLCV) if available
        position_value: Expected position size per stock

    Returns:
        LiquidityFilterResult with passed/rejected lists
    """
    passed = []
    rejected = []

    for stock in scored_stocks:
        df = data_map.get(stock.symbol) if data_map else None

        if df is None:
            # Try fetching
            try:
                from app.strategy.macro_data import fetch_with_cache
                df = fetch_with_cache(stock.symbol, period_years=1)
            except Exception:
                df = None

        metrics = assess_liquidity(stock.symbol, df, position_value)

        if metrics.is_liquid:
            # Adjust score for slippage (reduce expected return)
            if metrics.slippage_estimate_pct > SLIPPAGE_ESTIMATE_PCT:
                stock.composite *= (1 - ILLIQUID_PENALTY * 0.1)
            passed.append(metrics)
        else:
            rejected.append(metrics)

    # Overall metrics
    avg_score = np.mean([m.liquidity_score for m in passed]) if passed else 0.0

    return LiquidityFilterResult(
        passed=passed,
        rejected=rejected,
        total_candidates=len(scored_stocks),
        passed_count=len(passed),
        avg_liquidity_score=round(avg_score, 1),
    )
