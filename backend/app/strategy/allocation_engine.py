"""
Dynamic Capital Allocation Engine.

Maps regime → allocation percentages across asset classes.
Rebalancing only occurs when the regime CATEGORY changes.
"""

import logging
from dataclasses import dataclass
from datetime import date
from typing import Optional

from app.config import settings, ALLOCATION_MAP
from app.strategy.risk_engine import RiskComponents, REGIME_LABELS, REGIME_EQUITY_ALLOWED

logger = logging.getLogger(__name__)


@dataclass
class AllocationResult:
    regime: str
    regime_label: str
    risk_score: float
    stability_score: float

    equity_pct: float
    gold_pct: float
    silver_pct: float
    cash_pct: float

    equity_amount: float
    gold_amount: float
    silver_amount: float
    cash_amount: float

    total_capital: float
    equity_allowed: bool
    rebalance_needed: bool
    reason: str


def compute_allocation(
    risk: RiskComponents,
    capital: float,
    previous_regime: Optional[str] = None,
) -> AllocationResult:
    """
    Compute capital allocation based on current regime.
    Flags rebalance_needed only if regime category changed.
    """
    regime = risk.regime
    alloc = ALLOCATION_MAP.get(regime, ALLOCATION_MAP["NEUTRAL"])

    equity_pct = alloc["equity"]
    gold_pct = alloc["gold"]
    silver_pct = alloc["silver"]
    cash_pct = alloc["cash"]

    # Small capital constraint: if equity allocation results in < min position,
    # shift to cash
    equity_amount = round(capital * equity_pct / 100, 2)
    if equity_amount < settings.MIN_POSITION_VALUE and equity_pct > 0:
        cash_pct += equity_pct
        equity_pct = 0
        equity_amount = 0

    gold_amount = round(capital * gold_pct / 100, 2)
    silver_amount = round(capital * silver_pct / 100, 2)
    cash_amount = round(capital * cash_pct / 100, 2)
    equity_amount = round(capital * equity_pct / 100, 2)

    # Rebalance check
    rebalance_needed = previous_regime is not None and previous_regime != regime
    equity_allowed = REGIME_EQUITY_ALLOWED.get(regime, False)

    # Build reason
    if not equity_allowed:
        reason = (
            f"Equity DISABLED — regime is {REGIME_LABELS[regime]} "
            f"(Risk Score: {risk.total_risk_score}). "
            f"Defensive allocation: {gold_pct}% Gold, {cash_pct}% Cash."
        )
    elif rebalance_needed:
        reason = (
            f"Regime shifted from {REGIME_LABELS.get(previous_regime, previous_regime)} "
            f"to {REGIME_LABELS[regime]}. Rebalancing recommended."
        )
    else:
        reason = (
            f"Regime: {REGIME_LABELS[regime]} — "
            f"Equity {equity_pct}% | Gold {gold_pct}% | Cash {cash_pct}%"
        )

    return AllocationResult(
        regime=regime,
        regime_label=REGIME_LABELS[regime],
        risk_score=risk.total_risk_score,
        stability_score=risk.stability_score,
        equity_pct=equity_pct,
        gold_pct=gold_pct,
        silver_pct=silver_pct,
        cash_pct=cash_pct,
        equity_amount=equity_amount,
        gold_amount=gold_amount,
        silver_amount=silver_amount,
        cash_amount=cash_amount,
        total_capital=capital,
        equity_allowed=equity_allowed,
        rebalance_needed=rebalance_needed,
        reason=reason,
    )


def check_brokerage_viability(
    capital: float,
    entry_price: float,
    quantity: int,
) -> dict:
    """Check if a trade is viable after brokerage costs for small capital."""
    position_value = entry_price * quantity
    brokerage = settings.BROKERAGE_PER_ORDER * 2  # buy + sell
    stt = position_value * settings.STT_PCT / 100 * 2
    total_cost = brokerage + stt
    cost_pct = (total_cost / position_value) * 100 if position_value > 0 else 100

    return {
        "position_value": round(position_value, 2),
        "brokerage": round(brokerage, 2),
        "stt": round(stt, 2),
        "total_cost": round(total_cost, 2),
        "cost_pct": round(cost_pct, 2),
        "viable": position_value >= settings.MIN_POSITION_VALUE and cost_pct < 2.0,
        "reason": (
            "OK" if position_value >= settings.MIN_POSITION_VALUE and cost_pct < 2.0
            else f"Position too small (₹{position_value:.0f}) or cost too high ({cost_pct:.1f}%)"
        ),
    }
