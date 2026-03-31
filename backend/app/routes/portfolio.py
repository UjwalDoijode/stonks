"""Portfolio, position sizing, compounding, and dashboard routes."""

import asyncio
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.database import get_db
from app.models import Trade, ScanResult, TradeStatus
from app.schemas import (
    PositionSizeRequest, PositionSizeResponse,
    PortfolioStats, EquityCurvePoint,
    CompoundingRequest, CompoundingResponse,
    DashboardData, TradeOut, ScanResultOut,
    RiskComponentsOut, AllocationOut, MacroStatusOut,
    CapitalDeploymentOut, AssetDeploymentOut, StockDeploymentOut,
    AIRiskProbabilityOut, StockRankingOut,
    GovernorStatusOut, VolatilityMetricsOut, SmartCashPlanOut,
    CashRecommendationOut,
)
from app.services import (
    get_portfolio_stats, get_equity_curve,
    simulate_compounding, get_current_capital,
)
from app.strategy.position_sizing import calculate_position_size
from app.strategy.data_feed import get_nifty_regime_info

router = APIRouter(tags=["Portfolio"])


# ─── Position Sizing ─────────────────────────────────────
@router.post("/position-size", response_model=PositionSizeResponse)
async def calc_position_size(
    payload: PositionSizeRequest,
    db: AsyncSession = Depends(get_db),
):
    """Calculate risk-based position size."""
    capital = payload.capital or await get_current_capital(db)
    ps = calculate_position_size(
        capital=capital,
        entry_price=payload.entry_price,
        stop_loss=payload.stop_loss,
        risk_pct=payload.risk_pct,
    )
    return PositionSizeResponse(
        capital=ps.capital,
        risk_amount=ps.risk_amount,
        risk_per_share=ps.risk_per_share,
        quantity=ps.quantity,
        position_size=ps.position_size,
        target_price=ps.target_price,
        reward_amount=ps.reward_amount,
        risk_reward_ratio=ps.risk_reward_ratio,
        capital_used_pct=ps.capital_used_pct,
    )


# ─── Portfolio Stats ─────────────────────────────────────
@router.get("/portfolio/stats", response_model=PortfolioStats)
async def portfolio_stats(db: AsyncSession = Depends(get_db)):
    return await get_portfolio_stats(db)


@router.get("/portfolio/equity-curve", response_model=list[EquityCurvePoint])
async def equity_curve(db: AsyncSession = Depends(get_db)):
    return await get_equity_curve(db)


# ─── Compounding Simulator ───────────────────────────────
@router.post("/compounding", response_model=CompoundingResponse)
async def compounding_sim(payload: CompoundingRequest):
    return simulate_compounding(
        initial_capital=payload.initial_capital,
        monthly_return_pct=payload.monthly_return_pct,
        monthly_addition=payload.monthly_addition,
        years=payload.years,
    )


# ─── Dashboard ────────────────────────────────────────────
@router.get("/dashboard", response_model=DashboardData)
async def dashboard(db: AsyncSession = Depends(get_db)):
    """Aggregated dashboard data — single API call for the frontend."""
    portfolio = await get_portfolio_stats(db)
    eq_curve = await get_equity_curve(db)

    # Open trades
    result = await db.execute(
        select(Trade)
        .where(Trade.status == TradeStatus.OPEN.value)
        .order_by(desc(Trade.entry_date))
    )
    open_trades = result.scalars().all()

    # Latest scan candidates
    result = await db.execute(
        select(ScanResult.scan_date).order_by(desc(ScanResult.scan_date)).limit(1)
    )
    latest_date = result.scalar_one_or_none()
    if latest_date:
        result = await db.execute(
            select(ScanResult)
            .where(ScanResult.scan_date == latest_date, ScanResult.is_candidate == True)
            .order_by(ScanResult.rsi)
        )
        scans = result.scalars().all()
    else:
        scans = []

    regime = await asyncio.to_thread(get_nifty_regime_info)

    # Fetch risk / allocation / macro / deployment / AI data (non-blocking — graceful fallback)
    risk_out = None
    alloc_out = None
    macro_out = None
    deployment_out = None
    ai_risk_out = None
    top_ranked_out = None
    blended_risk = None
    why_no_trades = None
    governor_out = None
    vol_metrics_out = None
    smart_cash_out = None

    try:
        from app.strategy.macro_data import get_macro_snapshot
        from app.strategy.risk_engine import compute_risk_score
        from app.strategy.allocation_engine import compute_allocation
        from app.strategy.ai_risk_model import predict_risk, blend_risk_scores
        from app.strategy.stock_ranker import get_top_ranked
        from app.strategy.deployment_engine import compute_deployment
        from app.models import RegimeHistory, AllocationRecommendation
        from app.config import settings

        macro = await asyncio.to_thread(get_macro_snapshot)
        risk = await asyncio.to_thread(compute_risk_score, macro)
        capital = await get_current_capital(db)

        # AI prediction
        ai_pred = predict_risk(macro)
        blended = blend_risk_scores(risk.total_risk_score, ai_pred)
        blended_risk = blended

        # Previous regime
        result = await db.execute(
            select(RegimeHistory).order_by(desc(RegimeHistory.change_date)).limit(1)
        )
        prev = result.scalar_one_or_none()
        prev_regime = prev.new_regime if prev else None
        alloc = compute_allocation(risk, capital, prev_regime)

        risk_out = RiskComponentsOut(
            trend_risk=risk.trend_risk,
            volatility_risk=risk.volatility_risk,
            breadth_risk=risk.breadth_risk,
            global_risk=risk.global_risk,
            defensive_signal=risk.defensive_signal,
            total_risk_score=risk.total_risk_score,
            stability_score=risk.stability_score,
            regime=risk.regime,
        )
        alloc_out = AllocationOut(
            regime=alloc.regime,
            regime_label=alloc.regime_label,
            risk_score=alloc.risk_score,
            stability_score=alloc.stability_score,
            equity_pct=alloc.equity_pct,
            gold_pct=alloc.gold_pct,
            silver_pct=alloc.silver_pct,
            cash_pct=alloc.cash_pct,
            equity_amount=alloc.equity_amount,
            gold_amount=alloc.gold_amount,
            silver_amount=alloc.silver_amount,
            cash_amount=alloc.cash_amount,
            total_capital=capital,
            equity_allowed=alloc.equity_allowed,
            rebalance_needed=alloc.rebalance_needed,
            reason=alloc.reason,
        )
        macro_out = MacroStatusOut(
            nifty_close=macro.get("nifty_close"),
            nifty_200dma=macro.get("nifty_200dma"),
            nifty_50dma=macro.get("nifty_50dma"),
            nifty_above_200dma=macro.get("nifty_above_200dma", False),
            vix=macro.get("vix"),
            vix_rising=macro.get("vix_rising", False),
            breadth_pct_above_50dma=macro.get("breadth_pct_above_50dma"),
            sp500_above_200dma=macro.get("sp500_above_200dma", True),
            dxy_breakout=macro.get("dxy_breakout", False),
            oil_spike=macro.get("oil_spike", False),
            gold_above_50dma=macro.get("gold_above_50dma", False),
            gold_rs_vs_nifty=macro.get("gold_rs_vs_nifty"),
            atr_expansion=macro.get("atr_expansion", False),
        )

        # AI risk output
        ai_risk_out = AIRiskProbabilityOut(
            ai_risk_score=ai_pred.ai_risk_score,
            p_risk_on=ai_pred.p_risk_on,
            p_risk_off=ai_pred.p_risk_off,
            expected_equity_return=ai_pred.expected_equity_return,
            expected_gold_return=ai_pred.expected_gold_return,
            confidence=ai_pred.confidence,
            model_available=ai_pred.model_available,
            rule_based_score=risk.total_risk_score,
            blended_score=blended,
        )

        # Stock rankings (top 5 — offloaded to thread to avoid blocking)
        try:
            ranked = await asyncio.to_thread(
                get_top_ranked,
                n=settings.TOP_RANKED_COUNT,
                universe_tier=settings.UNIVERSE_TIER,
                regime=risk.regime,
            )
            top_ranked_out = [
                StockRankingOut(
                    symbol=s.symbol,
                    clean_symbol=s.clean_symbol,
                    price=s.price,
                    rank=s.rank,
                    composite=s.composite,
                    rs_3m=s.rs_3m,
                    momentum_6m=s.momentum_6m,
                    vol_adj_return=s.vol_adj_return,
                    volume_strength=s.volume_strength,
                    trend_slope=s.trend_slope,
                ) for s in ranked
            ]
        except Exception:
            top_ranked_out = None

        # Deployment plan
        try:
            prev_alloc_dict = None
            result2 = await db.execute(
                select(AllocationRecommendation)
                .order_by(desc(AllocationRecommendation.recommendation_date))
                .limit(1)
            )
            prev_alloc_row = result2.scalar_one_or_none()
            if prev_alloc_row:
                prev_alloc_dict = {
                    "regime": prev_alloc_row.regime,
                    "equity_pct": prev_alloc_row.equity_pct,
                    "gold_pct": prev_alloc_row.gold_pct,
                    "silver_pct": prev_alloc_row.silver_pct,
                    "cash_pct": prev_alloc_row.cash_pct,
                }

            # Gather trades for governor
            from app.models import PortfolioSnapshot
            trade_result2 = await db.execute(
                select(Trade).order_by(desc(Trade.entry_date)).limit(50)
            )
            recent_trades = trade_result2.scalars().all()
            trade_dicts = [
                {"pnl": t.pnl, "pnl_pct": t.pnl_pct,
                 "exit_date": str(t.exit_date) if t.exit_date else None,
                 "status": t.status}
                for t in recent_trades
            ]
            peak_result = await db.execute(
                select(PortfolioSnapshot).order_by(desc(PortfolioSnapshot.equity)).limit(1)
            )
            peak_snap = peak_result.scalar_one_or_none()
            peak_capital = peak_snap.equity if peak_snap else settings.INITIAL_CAPITAL

            plan = compute_deployment(
                risk=risk,
                capital=capital,
                ranked_stocks=ranked if top_ranked_out else [],
                ai_pred=ai_pred,
                previous_allocation=prev_alloc_dict,
                blended_risk_score=blended,
                trades_for_governor=trade_dicts,
                peak_capital=peak_capital,
            )
            why_no_trades = plan.why_no_trades

            from app.routes.deployment import _plan_to_response
            deployment_out = _plan_to_response(plan)
        except Exception as de:
            import logging
            logging.getLogger(__name__).warning(f"Dashboard deployment failed (non-fatal): {de}")

        # Governor status for dashboard
        try:
            from app.strategy.risk_governor import evaluate_governor
            eq_curve = await get_equity_curve(db)
            equity_curve_dicts = [{"date": str(p.date), "equity": p.equity} for p in eq_curve]
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
                is_active=gov.is_active, severity=severity,
                drawdown_pct=gov.drawdown_pct, drawdown_triggered=gov.drawdown_triggered,
                consecutive_losses=gov.consecutive_losses, equity_paused=gov.equity_paused,
                monthly_loss_pct=gov.monthly_loss_pct, monthly_loss_triggered=gov.monthly_loss_triggered,
                hard_stop_triggered=gov.hard_stop_triggered,
                override_allocation=gov.override_allocation,
                reason=gov.reason or f"Severity: {severity}. Drawdown: {gov.drawdown_pct:.1f}%",
            )
        except Exception:
            pass

        # Volatility metrics for dashboard
        try:
            from app.strategy.volatility_targeting import compute_volatility_scaling
            vol = compute_volatility_scaling(current_equity_pct=alloc.equity_pct)
            vol_metrics_out = VolatilityMetricsOut(
                equity_vol=vol.equity_vol_30d, gold_vol=vol.gold_vol_30d,
                portfolio_vol=vol.portfolio_vol_30d, target_vol=vol.target_vol,
                scaling_factor=vol.scaling_factor,
                original_equity_pct=alloc.equity_pct,
                adjusted_equity_pct=round(alloc.equity_pct * vol.scaling_factor, 1),
                reason=vol.detail or vol.recommendation,
            )
        except Exception:
            pass

        # Smart cash for dashboard
        try:
            from app.strategy.smart_cash import compute_smart_cash_plan
            cash_plan = compute_smart_cash_plan(alloc.cash_amount, risk.regime)
            smart_cash_out = SmartCashPlanOut(
                total_cash=cash_plan.total_cash, regime=cash_plan.regime,
                recommendations=[
                    CashRecommendationOut(
                        instrument_key=r.instrument_key, name=r.name,
                        symbol=r.symbol, annual_yield_pct=r.annual_yield_pct,
                        amount=r.amount, monthly_yield=r.monthly_yield,
                        description=r.description, risk_level=r.risk_level,
                        priority=r.priority,
                    ) for r in cash_plan.recommendations
                ],
                weighted_annual_yield=cash_plan.weighted_annual_yield,
                monthly_expected_income=cash_plan.monthly_expected_income,
                reason=cash_plan.reason,
            )
        except Exception:
            pass

    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Dashboard risk/alloc failed (non-fatal): {e}")

    return DashboardData(
        portfolio=portfolio,
        open_trades=open_trades,
        recent_scans=scans,
        equity_curve=eq_curve,
        regime_ok=regime["above_200dma"],
        nifty_above_200dma=regime["above_200dma"],
        risk=risk_out,
        allocation=alloc_out,
        macro=macro_out,
        deployment=deployment_out,
        ai_risk=ai_risk_out,
        top_ranked=top_ranked_out,
        blended_risk_score=blended_risk,
        why_no_trades=why_no_trades,
        governor=governor_out,
        volatility_metrics=vol_metrics_out,
        smart_cash=smart_cash_out,
    )
