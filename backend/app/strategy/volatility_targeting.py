"""
Volatility Targeting Engine — stabilize portfolio equity curve.

Estimates rolling 30-day realised volatility for equity basket and gold,
then scales allocation to target a specified annualised portfolio volatility.

If portfolio vol > target → reduce equity, increase cash/gold.
If portfolio vol < target → moderately increase equity.

This improves risk-adjusted returns by keeping volatility in a band.
"""

import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

from app.config import settings

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────
TARGET_ANNUAL_VOL = 12.0       # Target annualised portfolio vol (%)
VOL_LOOKBACK_DAYS = 30         # Rolling window
VOL_FLOOR_SCALE = 0.5          # Min scaling factor (don't go below 50%)
VOL_CEILING_SCALE = 1.3        # Max scaling factor (max 130%)
SCALE_SMOOTHING = 0.7          # Smoothing factor to avoid whiplash (EMA)


@dataclass
class VolatilityMetrics:
    """Volatility metrics for the portfolio."""
    equity_vol_30d: float = 0.0          # Equity basket 30-day annualised vol
    gold_vol_30d: float = 0.0            # Gold 30-day annualised vol
    portfolio_vol_30d: float = 0.0       # Portfolio-level blended vol
    target_vol: float = TARGET_ANNUAL_VOL
    vol_ratio: float = 1.0              # portfolio_vol / target_vol
    scaling_factor: float = 1.0          # Factor to apply to equity allocation
    recommendation: str = "HOLD"         # SCALE_DOWN / HOLD / SCALE_UP
    detail: str = ""


def estimate_rolling_volatility(
    prices: pd.Series,
    window: int = VOL_LOOKBACK_DAYS,
) -> float:
    """
    Compute annualised rolling volatility from a price series.
    Returns vol as a percentage (e.g., 15.0 for 15%).
    """
    if prices is None or len(prices) < window + 1:
        return 20.0  # Default conservative estimate

    returns = prices.pct_change().dropna().tail(window)
    if len(returns) < 10:
        return 20.0

    daily_vol = float(returns.std())
    annual_vol = daily_vol * np.sqrt(252) * 100
    return round(annual_vol, 2)


def compute_portfolio_volatility(
    equity_prices: Optional[pd.Series],
    gold_prices: Optional[pd.Series],
    equity_weight: float = 0.7,
    gold_weight: float = 0.2,
    cash_weight: float = 0.1,
) -> float:
    """
    Estimate portfolio-level volatility using weighted asset vols.
    Simplified: assumes moderate correlation between equity and gold (-0.2).
    """
    eq_vol = estimate_rolling_volatility(equity_prices) / 100 if equity_prices is not None else 0.20
    gold_vol = estimate_rolling_volatility(gold_prices) / 100 if gold_prices is not None else 0.12
    cash_vol = 0.005  # Near zero

    # Correlation assumptions
    corr_eq_gold = -0.2  # Typically negative
    corr_eq_cash = 0.0
    corr_gold_cash = 0.0

    # Portfolio variance = sum of w_i^2 * sigma_i^2 + 2 * sum(w_i * w_j * sigma_i * sigma_j * rho_ij)
    port_var = (
        (equity_weight ** 2) * (eq_vol ** 2)
        + (gold_weight ** 2) * (gold_vol ** 2)
        + (cash_weight ** 2) * (cash_vol ** 2)
        + 2 * equity_weight * gold_weight * eq_vol * gold_vol * corr_eq_gold
        + 2 * equity_weight * cash_weight * eq_vol * cash_vol * corr_eq_cash
        + 2 * gold_weight * cash_weight * gold_vol * cash_vol * corr_gold_cash
    )

    port_vol = np.sqrt(max(port_var, 0)) * 100
    return round(port_vol, 2)


def compute_volatility_scaling(
    equity_prices: Optional[pd.Series] = None,
    gold_prices: Optional[pd.Series] = None,
    current_equity_pct: float = 70.0,
    current_gold_pct: float = 20.0,
    current_cash_pct: float = 10.0,
    target_vol: float = TARGET_ANNUAL_VOL,
) -> VolatilityMetrics:
    """
    Compute volatility-adjusted scaling factor.

    If current portfolio vol > target → scaling_factor < 1 → reduce equity
    If current portfolio vol < target → scaling_factor > 1 → increase equity (moderate)

    Returns:
        VolatilityMetrics with scaling_factor to apply to equity allocation.
    """
    # Fetch price data if not provided
    if equity_prices is None:
        try:
            from app.strategy.macro_data import fetch_nifty
            nifty = fetch_nifty(years=1)
            equity_prices = nifty["close"] if nifty is not None else None
        except Exception:
            equity_prices = None

    if gold_prices is None:
        try:
            from app.strategy.macro_data import fetch_gold
            gold = fetch_gold(years=1)
            gold_prices = gold["close"] if gold is not None else None
        except Exception:
            gold_prices = None

    eq_vol = estimate_rolling_volatility(equity_prices)
    gold_vol = estimate_rolling_volatility(gold_prices)

    # Normalise weights
    total_w = current_equity_pct + current_gold_pct + current_cash_pct
    if total_w <= 0:
        total_w = 100
    eq_w = current_equity_pct / total_w
    gold_w = current_gold_pct / total_w
    cash_w = current_cash_pct / total_w

    port_vol = compute_portfolio_volatility(
        equity_prices, gold_prices,
        equity_weight=eq_w, gold_weight=gold_w, cash_weight=cash_w,
    )

    # Calculate scaling factor
    if port_vol <= 0:
        scaling = 1.0
    else:
        raw_scale = target_vol / port_vol
        # Clamp
        scaling = max(VOL_FLOOR_SCALE, min(VOL_CEILING_SCALE, raw_scale))

    # Determine recommendation
    vol_ratio = port_vol / target_vol if target_vol > 0 else 1.0
    if vol_ratio > 1.2:
        recommendation = "SCALE_DOWN"
        detail = (
            f"Portfolio vol ({port_vol:.1f}%) exceeds target ({target_vol:.0f}%) by "
            f"{(vol_ratio - 1) * 100:.0f}%. Reduce equity allocation by "
            f"{(1 - scaling) * 100:.0f}%."
        )
    elif vol_ratio < 0.8:
        recommendation = "SCALE_UP"
        detail = (
            f"Portfolio vol ({port_vol:.1f}%) is below target ({target_vol:.0f}%) by "
            f"{(1 - vol_ratio) * 100:.0f}%. Moderate equity increase suggested."
        )
    else:
        recommendation = "HOLD"
        detail = (
            f"Portfolio vol ({port_vol:.1f}%) is within target band "
            f"({target_vol * 0.8:.0f}–{target_vol * 1.2:.0f}%). No adjustment needed."
        )

    return VolatilityMetrics(
        equity_vol_30d=eq_vol,
        gold_vol_30d=gold_vol,
        portfolio_vol_30d=port_vol,
        target_vol=target_vol,
        vol_ratio=round(vol_ratio, 3),
        scaling_factor=round(scaling, 3),
        recommendation=recommendation,
        detail=detail,
    )


def apply_volatility_scaling(
    allocation: dict,
    vol_metrics: VolatilityMetrics,
) -> dict:
    """
    Apply volatility-based scaling to allocation percentages.

    Adjusts equity percentage by scaling_factor and redistributes
    the difference to gold and cash.
    """
    result = allocation.copy()

    if vol_metrics.scaling_factor == 1.0:
        return result

    original_equity = result.get("equity", 0)
    scaled_equity = round(original_equity * vol_metrics.scaling_factor, 1)
    scaled_equity = max(0, min(scaled_equity, 100))

    freed = original_equity - scaled_equity
    result["equity"] = scaled_equity

    if freed > 0:
        # Risk reduction: shift to gold (60%) and cash (40%)
        result["gold"] = round(result.get("gold", 0) + freed * 0.6, 1)
        result["cash"] = round(result.get("cash", 0) + freed * 0.4, 1)
    elif freed < 0:
        # Moderate increase: take from cash first, then gold
        deficit = abs(freed)
        cash_avail = max(0, result.get("cash", 0) - 5)  # Keep min 5% cash
        from_cash = min(deficit, cash_avail)
        result["cash"] = round(result.get("cash", 0) - from_cash, 1)
        remaining = deficit - from_cash
        if remaining > 0:
            gold_avail = max(0, result.get("gold", 0) - 5)  # Keep min 5% gold
            from_gold = min(remaining, gold_avail)
            result["gold"] = round(result.get("gold", 0) - from_gold, 1)

    # Normalise to 100%
    total = sum(result.values())
    if total > 0 and abs(total - 100) > 0.5:
        factor = 100 / total
        for k in result:
            result[k] = round(result[k] * factor, 1)

    return result
