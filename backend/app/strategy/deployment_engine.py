"""
Capital Deployment Prediction Engine.

Computes exact capital deployment recommendations:
  Expected Score = (Expected Return / Volatility) × Regime Confidence

For each asset class and individual stock picks:
  1. Score each candidate (from stock ranker)
  2. Normalise scores → allocation weights
  3. Map to exact ₹ amounts and share quantities
  4. Apply small-capital constraints (₹20K, max 2-3 positions)
  5. Factor in brokerage costs

Output: Precise "Buy X shares of RELIANCE at ₹Y, allocate ₹Z to Gold ETF"
"""

import logging
import math
from dataclasses import dataclass, field
from typing import Optional

from app.config import settings, ALLOCATION_MAP
from app.strategy.risk_engine import RiskComponents, REGIME_LABELS, REGIME_EQUITY_ALLOWED
from app.strategy.ai_risk_model import AIRiskPrediction
from app.strategy.stock_ranker import StockScore

logger = logging.getLogger(__name__)

# Regime confidence mapping (how confident we are in the regime signal)
REGIME_CONFIDENCE = {
    "STRONG_RISK_ON": 0.90,
    "MILD_RISK_ON": 0.70,
    "NEUTRAL": 0.50,
    "RISK_OFF": 0.70,
    "EXTREME_RISK": 0.95,
}

# Expected return estimates per regime (annualised %)
REGIME_EXPECTED_RETURNS = {
    "STRONG_RISK_ON": {"equity": 18.0, "gold": 5.0, "silver": 6.0, "cash": 4.0},
    "MILD_RISK_ON":   {"equity": 12.0, "gold": 8.0, "silver": 7.0, "cash": 4.0},
    "NEUTRAL":        {"equity": 8.0,  "gold": 10.0, "silver": 8.0, "cash": 4.0},
    "RISK_OFF":       {"equity": 2.0,  "gold": 14.0, "silver": 10.0, "cash": 5.0},
    "EXTREME_RISK":   {"equity": -5.0, "gold": 18.0, "silver": 12.0, "cash": 6.0},
}

# Typical volatility per asset class (annualised %)
ASSET_VOLATILITY = {
    "equity": 22.0,
    "gold": 12.0,
    "silver": 25.0,
    "cash": 0.5,
}


@dataclass
class StockDeployment:
    """Individual stock deployment recommendation."""
    symbol: str
    clean_symbol: str
    price: float
    quantity: int
    amount: float
    weight_pct: float
    rank_score: float
    expected_score: float
    reason: str


@dataclass
class AssetDeployment:
    """Per-asset-class deployment."""
    asset: str
    expected_score: float
    allocation_pct: float
    amount: float
    instrument: str        # e.g., "GOLDBEES.NS" or "Cash"
    stocks: list[StockDeployment] = field(default_factory=list)


@dataclass
class DeploymentPlan:
    """Complete capital deployment plan."""
    regime: str
    regime_label: str
    regime_confidence: float
    total_capital: float
    blended_risk_score: float
    ai_confidence: float

    assets: list[AssetDeployment]
    stock_picks: list[StockDeployment]

    total_deployed: float
    cash_reserve: float
    why_no_trades: str
    rebalance_needed: bool
    rebalance_reason: str
    brokerage_total: float


def _compute_expected_scores(regime: str, ai_pred: Optional[AIRiskPrediction] = None) -> dict:
    """
    Compute Expected Score for each asset class:
    Expected Score = (Expected Return / Volatility) × Regime Confidence
    """
    confidence = REGIME_CONFIDENCE.get(regime, 0.5)
    returns = REGIME_EXPECTED_RETURNS.get(regime, REGIME_EXPECTED_RETURNS["NEUTRAL"])

    scores = {}
    for asset in ["equity", "gold", "silver", "cash"]:
        exp_ret = returns[asset]
        vol = ASSET_VOLATILITY[asset]

        # AI adjustment: shift expected returns based on AI prediction
        if ai_pred and ai_pred.model_available:
            if asset == "equity":
                exp_ret += ai_pred.expected_equity_return * 2
            elif asset in ("gold", "silver"):
                exp_ret += ai_pred.expected_gold_return * 2

        score = (exp_ret / vol) * confidence if vol > 0 else 0
        scores[asset] = round(score, 4)

    return scores


def _scores_to_allocation(scores: dict) -> dict:
    """
    Convert expected scores to allocation percentages.
    Negative scores → 0 allocation, positive → proportional.
    Floor cash at 10%.
    """
    # Clamp negative scores to 0
    positive = {k: max(v, 0) for k, v in scores.items()}
    total = sum(positive.values())

    if total <= 0:
        return {"equity": 0, "gold": 0, "silver": 0, "cash": 100}

    alloc = {k: round(v / total * 100, 1) for k, v in positive.items()}

    # Floor cash at 10%
    if alloc["cash"] < 10:
        deficit = 10 - alloc["cash"]
        alloc["cash"] = 10
        # Redistribute deficit proportionally from others
        others_total = sum(alloc[k] for k in ["equity", "gold", "silver"])
        if others_total > 0:
            for k in ["equity", "gold", "silver"]:
                alloc[k] -= (alloc[k] / others_total) * deficit
                alloc[k] = max(0, round(alloc[k], 1))

    # Normalise to 100
    total = sum(alloc.values())
    if total != 100:
        diff = 100 - total
        alloc["cash"] = round(alloc["cash"] + diff, 1)

    return alloc


def compute_deployment(
    risk: RiskComponents,
    capital: float,
    ranked_stocks: list[StockScore],
    ai_pred: Optional[AIRiskPrediction] = None,
    previous_allocation: Optional[dict] = None,
    blended_risk_score: Optional[float] = None,
    trades_for_governor: Optional[list] = None,
    peak_capital: Optional[float] = None,
) -> DeploymentPlan:
    """
    Compute the full capital deployment plan with integrated risk controls.

    Pipeline:
      1. Base allocation from expected scores
      2. Governor override (drawdown / loss streak protection)
      3. Volatility targeting (scale equity to target 12% annual vol)
      4. Opportunity filter (ensure positive return/drawdown ratio)
      5. Correlation control (sector / correlation dedup on stock picks)
      6. Liquidity filter (remove illiquid stocks)
      7. Smart cash utilization (optimize idle cash)

    Args:
        risk: Current risk components
        capital: Available capital
        ranked_stocks: Top-ranked stocks from stock ranker
        ai_pred: AI risk prediction (optional)
        previous_allocation: Previous allocation dict for drift check
        blended_risk_score: Combined rule+AI risk score
        trades_for_governor: List of recent trades for governor evaluation
        peak_capital: Peak capital for drawdown calculation
    """
    regime = risk.regime
    regime_label = REGIME_LABELS.get(regime, regime)
    confidence = REGIME_CONFIDENCE.get(regime, 0.5)
    equity_allowed = REGIME_EQUITY_ALLOWED.get(regime, False)

    effective_risk = blended_risk_score if blended_risk_score is not None else risk.total_risk_score
    ai_confidence = ai_pred.confidence if ai_pred and ai_pred.model_available else 0.0

    # ── 1. Compute expected scores & dynamic allocation ──
    exp_scores = _compute_expected_scores(regime, ai_pred)

    if equity_allowed:
        alloc = _scores_to_allocation(exp_scores)
    else:
        alloc = {"equity": 0, "gold": 45, "silver": 15, "cash": 40}

    # ── 2. Governor override ─────────────────────────────
    governor_status = None
    try:
        from app.strategy.risk_governor import evaluate_governor, apply_governor_to_allocation
        governor_status = evaluate_governor(
            equity_curve=[],
            trades=trades_for_governor or [],
            initial_capital=settings.INITIAL_CAPITAL,
            current_capital=capital,
        )
        if governor_status.is_active:
            alloc = apply_governor_to_allocation(alloc, governor_status)
            logger.info(f"Governor active: rules={governor_status.active_rules}, allocation adjusted")
    except Exception as e:
        logger.warning(f"Governor evaluation skipped: {e}")

    # ── 3. Volatility targeting ──────────────────────────
    vol_metrics = None
    try:
        from app.strategy.volatility_targeting import compute_volatility_scaling, apply_volatility_scaling
        vol_metrics = compute_volatility_scaling(current_equity_pct=alloc["equity"])
        alloc = apply_volatility_scaling(alloc, vol_metrics)
        logger.debug(f"Vol scaling: factor={vol_metrics.scaling_factor:.2f}")
    except Exception as e:
        logger.warning(f"Volatility targeting skipped: {e}")

    # ── 4. Opportunity filter ────────────────────────────
    try:
        from app.strategy.opportunity_filter import compute_opportunity_scores, apply_opportunity_filter
        opp = compute_opportunity_scores(regime)
        alloc = apply_opportunity_filter(alloc, opp)
    except Exception as e:
        logger.warning(f"Opportunity filter skipped: {e}")

    # ── Small capital constraints ────────────────────────
    equity_amount = round(capital * alloc["equity"] / 100, 2)
    gold_amount = round(capital * alloc["gold"] / 100, 2)
    silver_amount = round(capital * alloc["silver"] / 100, 2)
    cash_amount = round(capital * alloc["cash"] / 100, 2)

    # If equity allocation too small for any trade, shift to cash
    if equity_amount < settings.MIN_POSITION_VALUE and alloc["equity"] > 0:
        cash_amount += equity_amount
        equity_amount = 0
        alloc["equity"] = 0
        alloc["cash"] = round(alloc["cash"] + alloc["equity"], 1)

    # ── 5. Correlation control on stock picks ────────────
    filtered_stocks = ranked_stocks
    try:
        from app.strategy.correlation_control import filter_correlated_stocks
        corr_result = filter_correlated_stocks(ranked_stocks)
        filtered_stocks = [s for s in ranked_stocks if s.clean_symbol not in corr_result.removed_symbols]
        if corr_result.removed_symbols:
            logger.info(f"Correlation filter removed: {corr_result.removed_symbols}")
    except Exception as e:
        logger.warning(f"Correlation control skipped: {e}")

    # ── 6. Liquidity filter on remaining stocks ──────────
    try:
        from app.strategy.liquidity_filter import filter_by_liquidity
        liq_result = filter_by_liquidity(filtered_stocks)
        if liq_result.rejected:
            rejected_syms = {r.symbol for r in liq_result.rejected}
            filtered_stocks = [s for s in filtered_stocks if s.symbol not in rejected_syms]
            logger.info(f"Liquidity filter rejected: {[r.symbol for r in liq_result.rejected]}")
    except Exception as e:
        logger.warning(f"Liquidity filter skipped: {e}")

    # ── Stock picks from filtered ranked stocks ──────────
    stock_picks: list[StockDeployment] = []
    if equity_amount < 5000:
        max_positions = 1
    elif equity_amount < 15000:
        max_positions = 2
    else:
        max_positions = min(settings.MAX_SIMULTANEOUS_TRADES, 3)
    brokerage_total = 0.0

    if equity_allowed and equity_amount >= settings.MIN_POSITION_VALUE and filtered_stocks:
        top = filtered_stocks[:max_positions]
        total_score = sum(s.composite for s in top)

        if total_score > 0:
            for stock in top:
                weight = stock.composite / total_score
                stock_amount = equity_amount * weight

                if stock.price > 0:
                    raw_qty = stock_amount / stock.price
                    qty = math.floor(raw_qty)
                else:
                    qty = 0

                if qty <= 0:
                    continue

                actual_amount = qty * stock.price

                brokerage = settings.BROKERAGE_PER_ORDER * 2
                stt = actual_amount * settings.STT_PCT / 100 * 2
                trade_cost = brokerage + stt
                cost_pct = (trade_cost / actual_amount * 100) if actual_amount > 0 else 100
                brokerage_total += trade_cost

                if cost_pct > 5.0:
                    continue

                stock_picks.append(StockDeployment(
                    symbol=stock.symbol,
                    clean_symbol=stock.clean_symbol,
                    price=stock.price,
                    quantity=qty,
                    amount=round(actual_amount, 2),
                    weight_pct=round(weight * alloc["equity"], 1),
                    rank_score=stock.composite,
                    expected_score=round(exp_scores["equity"] * stock.composite / 100, 4),
                    reason=(
                        f"Rank #{stock.rank} — RS:{stock.rs_3m:.0f} Mom:{stock.momentum_6m:.0f} "
                        f"VA:{stock.vol_adj_return:.0f} VS:{stock.volume_strength:.0f} Tr:{stock.trend_slope:.0f}"
                    ),
                ))

    # ── Rebalancing check ────────────────────────────────
    rebalance_needed = False
    rebalance_reason = ""

    if previous_allocation:
        # Check for >10% drift in any asset class
        for asset in ["equity", "gold", "silver", "cash"]:
            prev_pct = previous_allocation.get(f"{asset}_pct", alloc.get(asset, 0))
            new_pct = alloc.get(asset, 0)
            drift = abs(new_pct - prev_pct)
            if drift > 10:
                rebalance_needed = True
                rebalance_reason = (
                    f"Allocation drift: {asset} shifted {drift:.1f}pp "
                    f"(was {prev_pct:.0f}%, now {new_pct:.0f}%)"
                )
                break

        # Also rebalance on regime change
        prev_regime = previous_allocation.get("regime")
        if prev_regime and prev_regime != regime:
            rebalance_needed = True
            rebalance_reason = (
                f"Regime change: {REGIME_LABELS.get(prev_regime, prev_regime)} → {regime_label}"
            )

    # ── "Why No Trades?" explanation ─────────────────────
    why_no_trades = ""
    if not equity_allowed:
        why_no_trades = (
            f"Equity trading is DISABLED in {regime_label} regime "
            f"(risk score: {effective_risk:.0f}/100). "
            f"Capital is defensively allocated to Gold ({alloc['gold']:.0f}%) "
            f"and Cash ({alloc['cash']:.0f}%) until risk subsides."
        )
    elif not stock_picks:
        reasons = []
        if not ranked_stocks:
            reasons.append("No stocks passed the ranking criteria")
        if equity_amount < settings.MIN_POSITION_VALUE:
            reasons.append(f"Equity allocation (₹{equity_amount:.0f}) is below minimum position size (₹{settings.MIN_POSITION_VALUE:.0f})")
        if not reasons:
            reasons.append("No viable stock picks after brokerage cost analysis")
        why_no_trades = ". ".join(reasons) + "."

    # ── Build asset deployments ──────────────────────────
    assets = []

    # Equity
    assets.append(AssetDeployment(
        asset="Equity",
        expected_score=exp_scores["equity"],
        allocation_pct=alloc["equity"],
        amount=equity_amount,
        instrument="Stock Picks" if stock_picks else "N/A",
        stocks=stock_picks,
    ))

    # Gold
    assets.append(AssetDeployment(
        asset="Gold",
        expected_score=exp_scores["gold"],
        allocation_pct=alloc["gold"],
        amount=gold_amount,
        instrument=settings.GOLD_ETF_SYMBOL,
    ))

    # Silver
    if alloc["silver"] > 0:
        assets.append(AssetDeployment(
            asset="Silver",
            expected_score=exp_scores["silver"],
            allocation_pct=alloc["silver"],
            amount=silver_amount,
            instrument=settings.SILVER_ETF_SYMBOL,
        ))

    # Cash
    assets.append(AssetDeployment(
        asset="Cash",
        expected_score=exp_scores["cash"],
        allocation_pct=alloc["cash"],
        amount=cash_amount,
        instrument="Savings / Liquid Fund",
    ))

    # ── 7. Smart cash utilization ────────────────────────
    smart_cash_plan = None
    try:
        from app.strategy.smart_cash import compute_smart_cash_plan
        smart_cash_plan = compute_smart_cash_plan(cash_amount, regime)
        # Update cash instrument description
        if smart_cash_plan and smart_cash_plan.recommendations:
            primary = smart_cash_plan.recommendations[0]
            for a in assets:
                if a.asset == "Cash":
                    a.instrument = primary.name
    except Exception as e:
        logger.warning(f"Smart cash skipped: {e}")

    total_deployed = sum(a.amount for a in assets if a.asset != "Cash")

    return DeploymentPlan(
        regime=regime,
        regime_label=regime_label,
        regime_confidence=confidence,
        total_capital=capital,
        blended_risk_score=effective_risk,
        ai_confidence=ai_confidence,
        assets=assets,
        stock_picks=stock_picks,
        total_deployed=round(total_deployed, 2),
        cash_reserve=cash_amount,
        why_no_trades=why_no_trades,
        rebalance_needed=rebalance_needed,
        rebalance_reason=rebalance_reason,
        brokerage_total=round(brokerage_total, 2),
    )
