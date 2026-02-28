"""
Portfolio Risk Governor — drawdown protection & capital survival engine.

Rules:
  1. Portfolio drawdown > 8%  → reduce equity allocation by 50%
  2. 3 consecutive losing trades → pause equity entries for 1 week
  3. Monthly loss > 5%        → force defensive allocation (Gold + Cash)
  4. Portfolio-level stop-loss  → hard floor at 15% total drawdown

This module OVERRIDES normal allocation logic when any rule triggers.
"""

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# ── Thresholds ────────────────────────────────────────────
DRAWDOWN_THRESHOLD_PCT = 8.0         # Rule 1: equity cut trigger
EQUITY_REDUCTION_FACTOR = 0.50       # Rule 1: reduce equity by this factor
CONSECUTIVE_LOSS_LIMIT = 3           # Rule 2: pause after N consecutive losses
PAUSE_DURATION_DAYS = 7              # Rule 2: pause duration
MONTHLY_LOSS_THRESHOLD_PCT = 5.0     # Rule 3: force defensive
HARD_STOP_DRAWDOWN_PCT = 15.0        # Rule 4: portfolio stop-loss


@dataclass
class GovernorStatus:
    """Current state of the Risk Governor."""
    is_active: bool = False                 # True if any rule is triggered

    # Rule 1: Drawdown
    drawdown_pct: float = 0.0
    drawdown_triggered: bool = False
    equity_reduction_factor: float = 1.0    # 1.0 = no reduction

    # Rule 2: Consecutive losses
    consecutive_losses: int = 0
    equity_paused: bool = False
    pause_until: Optional[str] = None

    # Rule 3: Monthly loss
    monthly_loss_pct: float = 0.0
    monthly_loss_triggered: bool = False
    force_defensive: bool = False

    # Rule 4: Hard stop
    hard_stop_triggered: bool = False

    # Summary
    active_rules: list[str] = field(default_factory=list)
    override_allocation: Optional[dict] = None   # If set, replaces normal allocation
    reason: str = ""
    severity: str = "NORMAL"                     # NORMAL / WARNING / CRITICAL / EMERGENCY


def compute_drawdown(equity_curve: list[dict], initial_capital: float) -> float:
    """Compute current drawdown % from peak equity."""
    if not equity_curve:
        return 0.0

    peak = initial_capital
    current = initial_capital

    for point in equity_curve:
        eq = point.get("equity", point.get("value", initial_capital))
        if eq > peak:
            peak = eq
        current = eq

    if peak <= 0:
        return 0.0

    drawdown = ((peak - current) / peak) * 100
    return round(drawdown, 2)


def count_consecutive_losses(trades: list[dict]) -> int:
    """Count consecutive losing trades from the most recent trade backwards."""
    if not trades:
        return 0

    # Sort by exit_date descending (most recent first)
    closed = [t for t in trades if t.get("status", "") != "OPEN" and t.get("pnl") is not None]
    closed.sort(key=lambda t: t.get("exit_date", ""), reverse=True)

    count = 0
    for t in closed:
        if t.get("pnl", 0) < 0:
            count += 1
        else:
            break

    return count


def compute_monthly_loss(trades: list[dict], initial_capital: float) -> float:
    """Compute loss % over the current calendar month from closed trades."""
    if not trades:
        return 0.0

    today = date.today()
    month_start = today.replace(day=1)

    monthly_pnl = 0.0
    for t in trades:
        exit_date = t.get("exit_date")
        if exit_date is None:
            continue
        if isinstance(exit_date, str):
            try:
                exit_date = datetime.strptime(exit_date, "%Y-%m-%d").date()
            except ValueError:
                continue
        if exit_date >= month_start:
            monthly_pnl += t.get("pnl", 0)

    if initial_capital <= 0:
        return 0.0

    return round(abs(min(monthly_pnl, 0)) / initial_capital * 100, 2)


def evaluate_governor(
    equity_curve: list[dict],
    trades: list[dict],
    initial_capital: float,
    current_capital: float,
) -> GovernorStatus:
    """
    Evaluate all Risk Governor rules and return combined status.
    This is the main entry point — called before allocation decisions.
    """
    status = GovernorStatus()
    active_rules = []
    reasons = []

    # ── Rule 1: Portfolio Drawdown > 8% ──────────────────
    dd = compute_drawdown(equity_curve, initial_capital)
    status.drawdown_pct = dd

    if dd >= HARD_STOP_DRAWDOWN_PCT:
        # Rule 4 supersedes Rule 1
        status.hard_stop_triggered = True
        status.drawdown_triggered = True
        status.equity_reduction_factor = 0.0
        active_rules.append("HARD_STOP")
        reasons.append(
            f"EMERGENCY: Portfolio drawdown {dd:.1f}% exceeds hard stop ({HARD_STOP_DRAWDOWN_PCT}%). "
            f"ALL equity positions should be closed."
        )
    elif dd >= DRAWDOWN_THRESHOLD_PCT:
        status.drawdown_triggered = True
        status.equity_reduction_factor = EQUITY_REDUCTION_FACTOR
        active_rules.append("DRAWDOWN_CUT")
        reasons.append(
            f"Drawdown {dd:.1f}% exceeds {DRAWDOWN_THRESHOLD_PCT}% threshold. "
            f"Equity allocation reduced by {int((1 - EQUITY_REDUCTION_FACTOR) * 100)}%."
        )

    # ── Rule 2: 3 Consecutive Losing Trades ──────────────
    consec = count_consecutive_losses(trades)
    status.consecutive_losses = consec

    if consec >= CONSECUTIVE_LOSS_LIMIT:
        status.equity_paused = True
        pause_end = date.today() + timedelta(days=PAUSE_DURATION_DAYS)
        status.pause_until = pause_end.isoformat()
        active_rules.append("LOSS_STREAK_PAUSE")
        reasons.append(
            f"{consec} consecutive losses detected. "
            f"New equity entries paused until {pause_end.isoformat()}."
        )

    # ── Rule 3: Monthly Loss > 5% ────────────────────────
    monthly = compute_monthly_loss(trades, initial_capital)
    status.monthly_loss_pct = monthly

    if monthly >= MONTHLY_LOSS_THRESHOLD_PCT:
        status.monthly_loss_triggered = True
        status.force_defensive = True
        active_rules.append("MONTHLY_LOSS_DEFENSIVE")
        reasons.append(
            f"Monthly loss {monthly:.1f}% exceeds {MONTHLY_LOSS_THRESHOLD_PCT}% limit. "
            f"Forced defensive allocation (Gold + Cash)."
        )

    # ── Determine override allocation ────────────────────
    if status.hard_stop_triggered:
        status.override_allocation = {
            "equity": 0, "gold": 40, "silver": 0, "cash": 60
        }
        status.severity = "EMERGENCY"
    elif status.force_defensive:
        status.override_allocation = {
            "equity": 0, "gold": 50, "silver": 5, "cash": 45
        }
        status.severity = "CRITICAL"
    elif status.equity_paused and status.drawdown_triggered:
        status.override_allocation = {
            "equity": 0, "gold": 45, "silver": 5, "cash": 50
        }
        status.severity = "CRITICAL"
    elif status.equity_paused:
        # Pause equity but don't fully override — just block equity
        status.override_allocation = None  # handled by equity_paused flag
        status.severity = "WARNING"
    elif status.drawdown_triggered:
        # Reduce equity by factor, don't fully override
        status.override_allocation = None  # handled by equity_reduction_factor
        status.severity = "WARNING"

    status.active_rules = active_rules
    status.is_active = len(active_rules) > 0
    status.reason = " | ".join(reasons) if reasons else "All clear — no risk governor rules triggered."

    return status


def apply_governor_to_allocation(
    allocation: dict,
    governor: GovernorStatus,
) -> dict:
    """
    Apply Risk Governor overrides to a proposed allocation.

    Args:
        allocation: dict with keys equity, gold, silver, cash (percentages)
        governor: GovernorStatus from evaluate_governor()

    Returns:
        Modified allocation dict
    """
    if not governor.is_active:
        return allocation

    # Full override takes precedence
    if governor.override_allocation is not None:
        return governor.override_allocation.copy()

    result = allocation.copy()

    # Rule 1: Reduce equity by factor
    if governor.drawdown_triggered and governor.equity_reduction_factor < 1.0:
        original_equity = result.get("equity", 0)
        reduced_equity = original_equity * governor.equity_reduction_factor
        freed = original_equity - reduced_equity
        result["equity"] = round(reduced_equity, 1)
        # Redistribute freed capital to gold & cash
        result["gold"] = round(result.get("gold", 0) + freed * 0.6, 1)
        result["cash"] = round(result.get("cash", 0) + freed * 0.4, 1)

    # Rule 2: Pause equity entries (set to 0)
    if governor.equity_paused:
        freed = result.get("equity", 0)
        result["equity"] = 0
        result["gold"] = round(result.get("gold", 0) + freed * 0.5, 1)
        result["cash"] = round(result.get("cash", 0) + freed * 0.5, 1)

    # Normalise to 100%
    total = sum(result.values())
    if total > 0 and abs(total - 100) > 0.5:
        factor = 100 / total
        for k in result:
            result[k] = round(result[k] * factor, 1)

    return result
