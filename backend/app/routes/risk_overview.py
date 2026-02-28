"""API routes for the unified Risk Overview — aggregates Parts 1-8."""

import asyncio
import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.database import get_db
from app.models import Trade, TradeStatus
from app.schemas import (
    RiskOverviewOut,
    GovernorStatusOut,
    VolatilityMetricsOut,
    OpportunityAssessmentOut,
    OpportunityScoreOut,
    CorrelationResultOut,
    LiquidityFilterResultOut,
    LiquidityMetricsOut,
    FeedbackStatsOut,
    SmartCashPlanOut,
    CashRecommendationOut,
    MonteCarloResultOut,
)
from app.services import get_current_capital, get_equity_curve
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Risk Overview"])


@router.get("/risk-overview", response_model=RiskOverviewOut)
async def risk_overview(db: AsyncSession = Depends(get_db)):
    """
    Unified risk overview — evaluates all 8 risk control modules.
    Single call for the frontend Risk Dashboard.
    """
    # ── Gather data ──────────────────────────────────────
    capital = await get_current_capital(db)

    # Recent trades for governor
    result = await db.execute(
        select(Trade).order_by(desc(Trade.entry_date)).limit(50)
    )
    all_trades = result.scalars().all()

    # Equity curve for governor
    eq_curve = await get_equity_curve(db)
    equity_curve_dicts = [{"date": str(p.date), "equity": p.equity} for p in eq_curve]

    # Determine regime
    regime = "NEUTRAL"
    risk = None
    try:
        from app.strategy.macro_data import get_macro_snapshot
        from app.strategy.risk_engine import compute_risk_score
        macro = await asyncio.to_thread(get_macro_snapshot)
        risk = await asyncio.to_thread(compute_risk_score, macro)
        regime = risk.regime
        risk_obj = risk  # save for smart cash
    except Exception as e:
        logger.warning(f"Regime detection failed: {e}")

    # Closed trades for governor
    closed_trades = [t for t in all_trades if t.status != TradeStatus.OPEN.value]
    trade_dicts = [
        {
            "pnl": t.pnl,
            "pnl_pct": t.pnl_pct,
            "exit_date": str(t.exit_date) if t.exit_date else None,
            "status": t.status,
        }
        for t in closed_trades
    ]

    # ── 1. Governor (Part 1) ─────────────────────────────
    governor_out = GovernorStatusOut()
    try:
        from app.strategy.risk_governor import evaluate_governor
        gov = evaluate_governor(
            equity_curve=equity_curve_dicts,
            trades=trade_dicts,
            initial_capital=settings.INITIAL_CAPITAL,
            current_capital=capital,
        )
        severity = "NORMAL"
        if gov.hard_stop_triggered:
            severity = "EMERGENCY"
        elif gov.force_defensive or gov.monthly_loss_triggered:
            severity = "CRITICAL"
        elif gov.equity_paused or gov.drawdown_triggered:
            severity = "WARNING"
        governor_out = GovernorStatusOut(
            is_active=gov.is_active,
            severity=severity,
            drawdown_pct=gov.drawdown_pct,
            drawdown_triggered=gov.drawdown_triggered,
            consecutive_losses=gov.consecutive_losses,
            equity_paused=gov.equity_paused,
            monthly_loss_pct=gov.monthly_loss_pct,
            monthly_loss_triggered=gov.monthly_loss_triggered,
            hard_stop_triggered=gov.hard_stop_triggered,
            override_allocation=gov.override_allocation,
            reason=gov.reason or f"Severity: {severity}. Drawdown: {gov.drawdown_pct:.1f}%",
        )
    except Exception as e:
        logger.warning(f"Governor evaluation failed: {e}")

    # ── 2. Volatility Metrics (Part 2) ───────────────────
    vol_out = VolatilityMetricsOut()
    try:
        from app.strategy.volatility_targeting import compute_volatility_scaling
        vol = compute_volatility_scaling(current_equity_pct=50.0)
        vol_out = VolatilityMetricsOut(
            equity_vol=vol.equity_vol_30d,
            gold_vol=vol.gold_vol_30d,
            portfolio_vol=vol.portfolio_vol_30d,
            target_vol=vol.target_vol,
            scaling_factor=vol.scaling_factor,
            original_equity_pct=50.0,
            adjusted_equity_pct=round(50.0 * vol.scaling_factor, 1),
            reason=vol.detail or vol.recommendation,
        )
    except Exception as e:
        logger.warning(f"Volatility metrics failed: {e}")

    # ── 3. Opportunity Assessment (Part 3) ───────────────
    opp_out = OpportunityAssessmentOut()
    try:
        from app.strategy.opportunity_filter import compute_opportunity_scores
        opp = compute_opportunity_scores(regime)
        opp_out = OpportunityAssessmentOut(
            scores=[
                OpportunityScoreOut(
                    asset=s.asset,
                    expected_return=s.expected_return,
                    max_drawdown=s.expected_drawdown,
                    opportunity_score=s.score,
                    passes_threshold=s.passes_threshold,
                )
                for s in opp.scores
            ],
            any_passes=opp.any_opportunity,
            cash_boost_applied=opp.cash_boost_pct > 0,
            reason=opp.recommendation,
        )
    except Exception as e:
        logger.warning(f"Opportunity assessment failed: {e}")

    # ── 4. Correlation Control (Part 4) ──────────────────
    corr_out = None
    ranked = []
    try:
        from app.strategy.stock_ranker import get_top_ranked
        from app.strategy.correlation_control import filter_correlated_stocks
        ranked = await asyncio.to_thread(
            get_top_ranked, n=10, universe_tier=settings.UNIVERSE_TIER, regime=regime
        )
        corr = filter_correlated_stocks(ranked)
        corr_out = CorrelationResultOut(
            original_count=len(corr.selected_symbols) + len(corr.removed_symbols),
            filtered_count=len(corr.selected_symbols),
            removed_symbols=corr.removed_symbols,
            sector_limits_applied=len(corr.sector_counts) > 0,
            correlation_penalty_applied=len(corr.high_correlations) > 0,
            reason=f"Diversification: {corr.diversification_score:.0f}/100. "
                   f"Sectors: {len(corr.sector_counts)}. "
                   f"High correlations: {len(corr.high_correlations)}.",
        )
    except Exception as e:
        logger.warning(f"Correlation control failed: {e}")

    # ── 5. Liquidity Filter (Part 5) ─────────────────────
    liq_out = None
    try:
        if ranked:
            from app.strategy.liquidity_filter import filter_by_liquidity
            liq = await asyncio.to_thread(filter_by_liquidity, ranked[:5])
            liq_out = LiquidityFilterResultOut(
                original_count=liq.total_candidates,
                passed_count=liq.passed_count,
                rejected=[
                    LiquidityMetricsOut(
                        symbol=r.symbol,
                        avg_daily_volume=r.avg_daily_volume,
                        avg_daily_turnover=r.avg_daily_turnover,
                        estimated_spread_pct=r.estimated_spread_pct,
                        passes=r.is_liquid,
                        rejection_reason=r.reason,
                    )
                    for r in liq.rejected
                ],
                reason=f"Passed: {liq.passed_count}/{liq.total_candidates}. Avg liquidity: {liq.avg_liquidity_score:.0f}/100.",
            )
    except Exception as e:
        logger.warning(f"Liquidity filter failed: {e}")

    # ── 6. Adaptive Feedback (Part 6) ────────────────────
    feedback_out = FeedbackStatsOut()
    try:
        from app.strategy.adaptive_feedback import compute_feedback_stats, get_adaptive_blend_weights
        stats = compute_feedback_stats()
        rule_w, ai_w = get_adaptive_blend_weights()
        feedback_out = FeedbackStatsOut(
            total_trades=stats.total_trades,
            winning_trades=stats.high_conf_trades + stats.low_conf_trades,
            losing_trades=0,
            win_rate=stats.high_conf_win_rate if stats.high_conf_trades > 0 else 0.0,
            high_conf_win_rate=stats.high_conf_win_rate,
            low_conf_win_rate=stats.low_conf_win_rate,
            avg_r_multiple=stats.high_conf_avg_r,
            current_rule_weight=rule_w,
            current_ai_weight=ai_w,
            adaptation_active=abs(rule_w - 0.70) > 0.01,
            reason=stats.adaptation_reason,
        )
    except Exception as e:
        logger.warning(f"Adaptive feedback failed: {e}")

    # ── 7. Smart Cash (Part 8) ───────────────────────────
    smart_cash_out = None
    try:
        from app.strategy.smart_cash import compute_smart_cash_plan
        from app.strategy.allocation_engine import compute_allocation
        if risk is not None:
            alloc_result = compute_allocation(risk, capital, None)
            cash_amt = alloc_result.cash_amount
        else:
            cash_amt = capital * 0.2
        plan = compute_smart_cash_plan(cash_amt, regime)
        smart_cash_out = SmartCashPlanOut(
            total_cash=plan.total_cash,
            regime=plan.regime,
            recommendations=[
                CashRecommendationOut(
                    instrument_key=r.instrument_key,
                    name=r.name,
                    symbol=r.symbol,
                    annual_yield_pct=r.annual_yield_pct,
                    amount=r.amount,
                    monthly_yield=r.monthly_yield,
                    description=r.description,
                    risk_level=r.risk_level,
                    priority=r.priority,
                )
                for r in plan.recommendations
            ],
            weighted_annual_yield=plan.weighted_annual_yield,
            monthly_expected_income=plan.monthly_expected_income,
            reason=plan.reason,
        )
    except Exception as e:
        logger.warning(f"Smart cash failed: {e}")

    # ── 8. Monte Carlo (Part 7) ──────────────────────────
    mc_out = None
    try:
        from app.strategy.monte_carlo import simulate_from_trades
        trade_returns = [t.pnl_pct / 100 for t in closed_trades if t.pnl_pct is not None]
        mc = await asyncio.to_thread(simulate_from_trades, trade_returns, capital)
        mc_out = MonteCarloResultOut(
            num_simulations=mc.n_simulations,
            months_forward=mc.months_forward,
            expected_return=mc.expected_return_pct,
            best_case_return=mc.best_case_pct,
            worst_case_return=mc.worst_case_pct,
            prob_negative_month=mc.prob_negative_month,
            var_95=mc.value_at_risk_95,
            skewness=mc.skewness,
            kurtosis=mc.kurtosis,
            histogram_bins=mc.histogram_bins,
            histogram_counts=mc.histogram_counts,
            percentile_curves={
                "p5": mc.percentile_5,
                "p25": mc.percentile_25,
                "p50": mc.percentile_50,
                "p75": mc.percentile_75,
                "p95": mc.percentile_95,
            },
        )
    except Exception as e:
        logger.warning(f"Monte Carlo failed: {e}")

    return RiskOverviewOut(
        governor=governor_out,
        volatility=vol_out,
        opportunity=opp_out,
        correlation=corr_out,
        liquidity=liq_out,
        feedback=feedback_out,
        smart_cash=smart_cash_out,
        monte_carlo=mc_out,
    )


# ─── Individual endpoints ────────────────────────────────

@router.get("/governor-status", response_model=GovernorStatusOut)
async def get_governor_status(db: AsyncSession = Depends(get_db)):
    """Quick governor status check."""
    capital = await get_current_capital(db)
    eq_curve = await get_equity_curve(db)
    equity_curve_dicts = [{"date": str(p.date), "equity": p.equity} for p in eq_curve]

    result = await db.execute(
        select(Trade).where(Trade.status != TradeStatus.OPEN.value).order_by(desc(Trade.entry_date)).limit(50)
    )
    closed = result.scalars().all()
    trade_dicts = [
        {"pnl": t.pnl, "pnl_pct": t.pnl_pct, "exit_date": str(t.exit_date) if t.exit_date else None, "status": t.status}
        for t in closed
    ]

    try:
        from app.strategy.risk_governor import evaluate_governor
        gov = evaluate_governor(
            equity_curve=equity_curve_dicts,
            trades=trade_dicts,
            initial_capital=settings.INITIAL_CAPITAL,
            current_capital=capital,
        )
        severity = "NORMAL"
        if gov.hard_stop_triggered:
            severity = "EMERGENCY"
        elif gov.force_defensive or gov.monthly_loss_triggered:
            severity = "CRITICAL"
        elif gov.equity_paused or gov.drawdown_triggered:
            severity = "WARNING"
        return GovernorStatusOut(
            is_active=gov.is_active,
            severity=severity,
            drawdown_pct=gov.drawdown_pct,
            drawdown_triggered=gov.drawdown_triggered,
            consecutive_losses=gov.consecutive_losses,
            equity_paused=gov.equity_paused,
            monthly_loss_pct=gov.monthly_loss_pct,
            monthly_loss_triggered=gov.monthly_loss_triggered,
            hard_stop_triggered=gov.hard_stop_triggered,
            override_allocation=gov.override_allocation,
            reason=gov.reason or f"Severity: {severity}",
        )
    except Exception as e:
        logger.error(f"Governor status error: {e}")
        return GovernorStatusOut()


@router.get("/monte-carlo", response_model=MonteCarloResultOut)
async def get_monte_carlo(db: AsyncSession = Depends(get_db)):
    """Run Monte Carlo simulation on trade history."""
    capital = await get_current_capital(db)
    result = await db.execute(
        select(Trade).where(Trade.status != TradeStatus.OPEN.value).order_by(desc(Trade.entry_date))
    )
    closed = result.scalars().all()
    trade_returns = [t.pnl_pct / 100 for t in closed if t.pnl_pct is not None]

    from app.strategy.monte_carlo import simulate_from_trades
    mc = await asyncio.to_thread(simulate_from_trades, trade_returns, capital)
    return MonteCarloResultOut(
        num_simulations=mc.n_simulations,
        months_forward=mc.months_forward,
        expected_return=mc.expected_return_pct,
        best_case_return=mc.best_case_pct,
        worst_case_return=mc.worst_case_pct,
        prob_negative_month=mc.prob_negative_month,
        var_95=mc.value_at_risk_95,
        skewness=mc.skewness,
        kurtosis=mc.kurtosis,
        histogram_bins=mc.histogram_bins,
        histogram_counts=mc.histogram_counts,
        percentile_curves={
            "p5": mc.percentile_5,
            "p25": mc.percentile_25,
            "p50": mc.percentile_50,
            "p75": mc.percentile_75,
            "p95": mc.percentile_95,
        },
    )


@router.get("/feedback-stats", response_model=FeedbackStatsOut)
async def get_feedback_stats():
    """Get adaptive feedback statistics."""
    try:
        from app.strategy.adaptive_feedback import compute_feedback_stats, get_adaptive_blend_weights
        stats = compute_feedback_stats()
        rule_w, ai_w = get_adaptive_blend_weights()
        return FeedbackStatsOut(
            total_trades=stats.total_trades,
            winning_trades=stats.high_conf_trades + stats.low_conf_trades,
            losing_trades=0,
            win_rate=stats.high_conf_win_rate if stats.high_conf_trades > 0 else 0.0,
            high_conf_win_rate=stats.high_conf_win_rate,
            low_conf_win_rate=stats.low_conf_win_rate,
            avg_r_multiple=stats.high_conf_avg_r,
            current_rule_weight=rule_w,
            current_ai_weight=ai_w,
            adaptation_active=abs(rule_w - 0.70) > 0.01,
            reason=stats.adaptation_reason,
        )
    except Exception as e:
        return FeedbackStatsOut(reason=f"Error: {e}")


@router.get("/smart-cash", response_model=SmartCashPlanOut)
async def get_smart_cash(db: AsyncSession = Depends(get_db)):
    """Get smart cash utilization plan."""
    try:
        from app.strategy.macro_data import get_macro_snapshot
        from app.strategy.risk_engine import compute_risk_score
        from app.strategy.allocation_engine import compute_allocation
        from app.strategy.smart_cash import compute_smart_cash_plan

        capital = await get_current_capital(db)
        macro = await asyncio.to_thread(get_macro_snapshot)
        risk_result = await asyncio.to_thread(compute_risk_score, macro)
        alloc = compute_allocation(risk_result, capital, None)
        plan = compute_smart_cash_plan(alloc.cash_amount, risk_result.regime)

        return SmartCashPlanOut(
            total_cash=plan.total_cash,
            regime=plan.regime,
            recommendations=[
                CashRecommendationOut(
                    instrument_key=r.instrument_key,
                    name=r.name,
                    symbol=r.symbol,
                    annual_yield_pct=r.annual_yield_pct,
                    amount=r.amount,
                    monthly_yield=r.monthly_yield,
                    description=r.description,
                    risk_level=r.risk_level,
                    priority=r.priority,
                )
                for r in plan.recommendations
            ],
            weighted_annual_yield=plan.weighted_annual_yield,
            monthly_expected_income=plan.monthly_expected_income,
            reason=plan.reason,
        )
    except Exception as e:
        return SmartCashPlanOut(reason=f"Error: {e}")
