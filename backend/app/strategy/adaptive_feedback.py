"""
Adaptive Model Feedback Loop — learn from trade outcomes.

After each closed trade:
  1. Record: AI confidence, regime, risk score, outcome (R-multiple)
  2. Track performance by:
     - High-confidence vs low-confidence trades
     - Each regime type
  3. Adjust AI blending weight slowly (e.g., 70/30 → 60/40 if AI underperforms)

This module improves the model adaptively without overfitting.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

FEEDBACK_FILE = Path(__file__).parent.parent.parent / "data" / "ai_feedback.json"
MIN_TRADES_FOR_ADAPT = 10          # Minimum trades before adjusting weights
ADAPTATION_RATE = 0.02              # How fast to adjust per evaluation
MIN_RULE_WEIGHT = 0.50              # Never go below 50% rule-based
MAX_RULE_WEIGHT = 0.90              # Never go above 90% rule-based


@dataclass
class TradeFeedback:
    """Record of a single trade's AI context and outcome."""
    trade_id: int
    symbol: str
    entry_date: str
    exit_date: str
    ai_confidence: float           # AI model confidence at time of trade
    regime: str                    # Market regime at entry
    risk_score: float              # Blended risk score at entry
    r_multiple: float              # Outcome: (exit - entry) / risk_per_share
    pnl: float                    # P&L in currency
    pnl_pct: float                 # P&L %
    was_winner: bool
    timestamp: str = ""


@dataclass
class FeedbackStats:
    """Aggregated performance statistics from feedback data."""
    total_trades: int = 0

    # By confidence
    high_conf_trades: int = 0
    high_conf_win_rate: float = 0.0
    high_conf_avg_r: float = 0.0
    low_conf_trades: int = 0
    low_conf_win_rate: float = 0.0
    low_conf_avg_r: float = 0.0

    # By regime
    regime_stats: dict = field(default_factory=dict)  # regime → {trades, win_rate, avg_r}

    # AI performance
    ai_profitable: bool = True         # Is AI adding value?
    ai_edge: float = 0.0              # high_conf excess return vs low_conf
    recommended_rule_weight: float = 0.70
    recommended_ai_weight: float = 0.30
    adaptation_reason: str = ""


def _load_feedback() -> list[dict]:
    """Load feedback data from JSON file."""
    if not FEEDBACK_FILE.exists():
        return []
    try:
        with open(FEEDBACK_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load feedback: {e}")
        return []


def _save_feedback(data: list[dict]):
    """Save feedback data to JSON file."""
    try:
        FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(FEEDBACK_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save feedback: {e}")


def record_trade_feedback(
    trade_id: int,
    symbol: str,
    entry_date: str,
    exit_date: str,
    ai_confidence: float,
    regime: str,
    risk_score: float,
    r_multiple: float,
    pnl: float,
    pnl_pct: float,
) -> TradeFeedback:
    """
    Record a completed trade's feedback for model adaptation.
    Called when a trade is closed.
    """
    feedback = TradeFeedback(
        trade_id=trade_id,
        symbol=symbol,
        entry_date=str(entry_date),
        exit_date=str(exit_date),
        ai_confidence=ai_confidence,
        regime=regime,
        risk_score=risk_score,
        r_multiple=r_multiple,
        pnl=pnl,
        pnl_pct=pnl_pct,
        was_winner=pnl > 0,
        timestamp=datetime.now().isoformat(),
    )

    # Persist
    data = _load_feedback()
    data.append({
        "trade_id": feedback.trade_id,
        "symbol": feedback.symbol,
        "entry_date": feedback.entry_date,
        "exit_date": feedback.exit_date,
        "ai_confidence": feedback.ai_confidence,
        "regime": feedback.regime,
        "risk_score": feedback.risk_score,
        "r_multiple": feedback.r_multiple,
        "pnl": feedback.pnl,
        "pnl_pct": feedback.pnl_pct,
        "was_winner": feedback.was_winner,
        "timestamp": feedback.timestamp,
    })
    _save_feedback(data)

    logger.info(
        f"Recorded feedback: {symbol} R={r_multiple:.2f} "
        f"conf={ai_confidence:.2f} regime={regime}"
    )

    return feedback


def compute_feedback_stats() -> FeedbackStats:
    """
    Analyze all trade feedback to determine AI model effectiveness
    and recommend weight adjustments.
    """
    data = _load_feedback()

    if not data:
        return FeedbackStats()

    stats = FeedbackStats(total_trades=len(data))

    # Split by confidence
    high_conf = [d for d in data if d.get("ai_confidence", 0) >= 0.5]
    low_conf = [d for d in data if d.get("ai_confidence", 0) < 0.5]

    # High confidence stats
    stats.high_conf_trades = len(high_conf)
    if high_conf:
        wins = [d for d in high_conf if d.get("was_winner", False)]
        stats.high_conf_win_rate = round(len(wins) / len(high_conf) * 100, 1)
        stats.high_conf_avg_r = round(
            np.mean([d.get("r_multiple", 0) for d in high_conf]), 3
        )

    # Low confidence stats
    stats.low_conf_trades = len(low_conf)
    if low_conf:
        wins = [d for d in low_conf if d.get("was_winner", False)]
        stats.low_conf_win_rate = round(len(wins) / len(low_conf) * 100, 1)
        stats.low_conf_avg_r = round(
            np.mean([d.get("r_multiple", 0) for d in low_conf]), 3
        )

    # By regime
    regimes = set(d.get("regime", "UNKNOWN") for d in data)
    for regime in regimes:
        r_trades = [d for d in data if d.get("regime") == regime]
        if r_trades:
            r_wins = [d for d in r_trades if d.get("was_winner", False)]
            avg_r = np.mean([d.get("r_multiple", 0) for d in r_trades])
            stats.regime_stats[regime] = {
                "trades": len(r_trades),
                "win_rate": round(len(r_wins) / len(r_trades) * 100, 1),
                "avg_r_multiple": round(float(avg_r), 3),
            }

    # ── AI Performance Assessment ────────────────────────
    if stats.total_trades >= MIN_TRADES_FOR_ADAPT:
        stats.ai_edge = stats.high_conf_avg_r - stats.low_conf_avg_r

        if stats.ai_edge > 0.3:
            # AI is adding clear value → increase AI weight
            new_ai_weight = min(MAX_RULE_WEIGHT, 0.30 + ADAPTATION_RATE * 2)
            stats.ai_profitable = True
            stats.adaptation_reason = (
                f"AI adds value: High-conf R={stats.high_conf_avg_r:.2f} vs "
                f"Low-conf R={stats.low_conf_avg_r:.2f}. Increasing AI weight."
            )
        elif stats.ai_edge < -0.2:
            # AI is hurting → decrease AI weight
            new_ai_weight = max(1 - MAX_RULE_WEIGHT, 0.30 - ADAPTATION_RATE * 2)
            stats.ai_profitable = False
            stats.adaptation_reason = (
                f"AI underperforming: High-conf R={stats.high_conf_avg_r:.2f} vs "
                f"Low-conf R={stats.low_conf_avg_r:.2f}. Reducing AI weight."
            )
        else:
            new_ai_weight = 0.30
            stats.ai_profitable = True
            stats.adaptation_reason = "AI performance is neutral. Maintaining current weights."

        stats.recommended_ai_weight = round(new_ai_weight, 2)
        stats.recommended_rule_weight = round(1.0 - new_ai_weight, 2)
    else:
        stats.recommended_rule_weight = 0.70
        stats.recommended_ai_weight = 0.30
        stats.adaptation_reason = (
            f"Insufficient data ({stats.total_trades}/{MIN_TRADES_FOR_ADAPT} trades). "
            f"Using default 70/30 blend."
        )

    return stats


def get_adaptive_blend_weights() -> tuple[float, float]:
    """
    Get current recommended rule/AI blend weights.
    Returns (rule_weight, ai_weight) tuple.
    """
    stats = compute_feedback_stats()
    return stats.recommended_rule_weight, stats.recommended_ai_weight
