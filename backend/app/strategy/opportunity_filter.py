"""
Opportunity Threshold Filter — capital efficiency guard.

For each asset class, compute:
  Opportunity Score = Expected Return / Expected Drawdown

If no asset exceeds a minimum threshold, recommend higher cash allocation.
Prevents forced deployment into poor setups.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

from app.strategy.deployment_engine import (
    REGIME_EXPECTED_RETURNS,
    REGIME_CONFIDENCE,
)

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────
MIN_OPPORTUNITY_SCORE = 0.5          # Minimum score to justify deployment
CASH_BOOST_STEP = 15.0               # % to add to cash when no opportunity

# Expected max drawdown per asset class (historical estimates)
EXPECTED_DRAWDOWN = {
    "equity": 25.0,    # NIFTY can draw down 20-30% in bear markets
    "gold": 12.0,      # Gold typically 10-15% drawdowns
    "silver": 30.0,    # Silver is more volatile
    "cash": 0.5,       # Near zero
}


@dataclass
class OpportunityScore:
    """Score for a single asset class."""
    asset: str
    expected_return: float
    expected_drawdown: float
    score: float                # return / drawdown
    passes_threshold: bool


@dataclass
class OpportunityAssessment:
    """Combined opportunity assessment across all assets."""
    scores: list[OpportunityScore] = field(default_factory=list)
    any_opportunity: bool = False
    best_asset: str = "cash"
    best_score: float = 0.0
    cash_boost_pct: float = 0.0      # Additional % to allocate to cash
    recommendation: str = ""


def compute_opportunity_scores(
    regime: str,
    ai_equity_adjust: float = 0.0,
    ai_gold_adjust: float = 0.0,
) -> OpportunityAssessment:
    """
    Compute opportunity scores for each asset class.

    Opportunity Score = Expected Return / Expected Drawdown

    Args:
        regime: Current market regime
        ai_equity_adjust: AI-predicted return adjustment for equity
        ai_gold_adjust: AI-predicted return adjustment for gold

    Returns:
        OpportunityAssessment with scores and recommendation
    """
    returns = REGIME_EXPECTED_RETURNS.get(regime, REGIME_EXPECTED_RETURNS["NEUTRAL"])
    confidence = REGIME_CONFIDENCE.get(regime, 0.5)

    scores = []
    best_asset = "cash"
    best_score = 0.0

    for asset in ["equity", "gold", "silver", "cash"]:
        exp_ret = returns.get(asset, 0.0)

        # AI adjustments
        if asset == "equity":
            exp_ret += ai_equity_adjust
        elif asset in ("gold", "silver"):
            exp_ret += ai_gold_adjust

        # Scale by confidence
        adjusted_ret = exp_ret * confidence
        exp_dd = EXPECTED_DRAWDOWN.get(asset, 10.0)

        # Opportunity score
        score = adjusted_ret / exp_dd if exp_dd > 0 else 0.0

        passes = score >= MIN_OPPORTUNITY_SCORE
        scores.append(OpportunityScore(
            asset=asset,
            expected_return=round(adjusted_ret, 2),
            expected_drawdown=exp_dd,
            score=round(score, 4),
            passes_threshold=passes,
        ))

        if score > best_score:
            best_score = score
            best_asset = asset

    any_opportunity = any(s.passes_threshold and s.asset != "cash" for s in scores)

    # If no asset has a good opportunity, boost cash
    cash_boost = 0.0
    recommendation = ""

    if not any_opportunity:
        cash_boost = CASH_BOOST_STEP
        recommendation = (
            f"No asset class exceeds opportunity threshold ({MIN_OPPORTUNITY_SCORE}). "
            f"Boosting cash allocation by {cash_boost:.0f}%. "
            f"Avoid forced deployment — wait for better setups."
        )
    else:
        passing = [s for s in scores if s.passes_threshold and s.asset != "cash"]
        names = ", ".join(s.asset.title() for s in passing)
        recommendation = (
            f"Opportunity detected in: {names}. "
            f"Best risk/reward: {best_asset.title()} (score: {best_score:.2f})."
        )

    return OpportunityAssessment(
        scores=scores,
        any_opportunity=any_opportunity,
        best_asset=best_asset,
        best_score=round(best_score, 4),
        cash_boost_pct=cash_boost,
        recommendation=recommendation,
    )


def apply_opportunity_filter(
    allocation: dict,
    assessment: OpportunityAssessment,
) -> dict:
    """
    Apply opportunity filter to allocation.
    If no good opportunities, increase cash allocation.
    """
    if assessment.any_opportunity:
        return allocation

    result = allocation.copy()
    boost = assessment.cash_boost_pct

    # Reduce from assets that don't pass threshold
    for asset in ["equity", "silver", "gold"]:
        if result.get(asset, 0) > 0 and boost > 0:
            reduction = min(result[asset], boost * 0.6 if asset == "equity" else boost * 0.2)
            result[asset] = round(result[asset] - reduction, 1)
            result["cash"] = round(result.get("cash", 0) + reduction, 1)
            boost -= reduction

    # Normalise
    total = sum(result.values())
    if total > 0 and abs(total - 100) > 0.5:
        factor = 100 / total
        for k in result:
            result[k] = round(result[k] * factor, 1)

    return result
