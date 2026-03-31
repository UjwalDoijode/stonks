"""API routes for risk scoring, allocation, macro status, and allocation backtest."""

import asyncio
import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.database import get_db
from app.schemas import (
    RiskComponentsOut,
    AllocationOut,
    MacroStatusOut,
    BrokerageCheckOut,
    AllocBacktestResultOut,
    AllocBacktestPointOut,
    AllocBacktestRequest,
)
from app.models import RiskScore, RegimeHistory, AllocationRecommendation
from app.services import get_current_capital

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Risk & Allocation"])


# ─── Risk Score ───────────────────────────────────────────
@router.get("/risk-score", response_model=RiskComponentsOut)
async def get_risk_score(db: AsyncSession = Depends(get_db)):
    """Compute current risk score from live macro data."""
    try:
        from app.strategy.macro_data import get_macro_snapshot
        from app.strategy.risk_engine import compute_risk_score

        macro = await asyncio.to_thread(get_macro_snapshot)
        risk = await asyncio.to_thread(compute_risk_score, macro)

        # Persist
        row = RiskScore(
            score_date=date.today(),
            trend_risk=risk.trend_risk,
            volatility_risk=risk.volatility_risk,
            breadth_risk=risk.breadth_risk,
            global_risk=risk.global_risk,
            defensive_signal=risk.defensive_signal,
            total_risk_score=risk.total_risk_score,
            stability_score=risk.stability_score,
            nifty_close=macro.get("nifty_close"),
            nifty_200dma=macro.get("nifty_200dma"),
            nifty_50dma=macro.get("nifty_50dma"),
            vix=macro.get("vix"),
            breadth_pct_above_50dma=macro.get("breadth_pct_above_50dma"),
            sp500_above_200dma=macro.get("sp500_above_200dma"),
            dxy_breakout=macro.get("dxy_breakout"),
            oil_spike=macro.get("oil_spike"),
            gold_above_50dma=macro.get("gold_above_50dma"),
            gold_rs_vs_nifty=macro.get("gold_rs_vs_nifty"),
            regime=risk.regime,
        )
        db.add(row)
        await db.commit()

        return RiskComponentsOut(
            trend_risk=risk.trend_risk,
            volatility_risk=risk.volatility_risk,
            breadth_risk=risk.breadth_risk,
            global_risk=risk.global_risk,
            defensive_signal=risk.defensive_signal,
            total_risk_score=risk.total_risk_score,
            stability_score=risk.stability_score,
            regime=risk.regime,
        )
    except Exception as e:
        logger.error(f"Risk score error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── Allocation ───────────────────────────────────────────
@router.get("/allocation", response_model=AllocationOut)
async def get_allocation(db: AsyncSession = Depends(get_db)):
    """Get current allocation recommendation based on risk regime."""
    try:
        from app.strategy.macro_data import get_macro_snapshot
        from app.strategy.risk_engine import compute_risk_score
        from app.strategy.allocation_engine import compute_allocation

        macro = await asyncio.to_thread(get_macro_snapshot)
        risk = await asyncio.to_thread(compute_risk_score, macro)
        capital = await get_current_capital(db)

        # Get previous regime
        result = await db.execute(
            select(RegimeHistory).order_by(desc(RegimeHistory.change_date)).limit(1)
        )
        prev = result.scalar_one_or_none()
        prev_regime = prev.new_regime if prev else None

        alloc = compute_allocation(risk, capital, prev_regime)

        # Log regime change if needed
        if alloc.rebalance_needed:
            change = RegimeHistory(
                change_date=date.today(),
                previous_regime=prev_regime,
                new_regime=alloc.regime,
                risk_score=risk.total_risk_score,
                trigger_reason=alloc.reason,
            )
            db.add(change)

        # Persist allocation recommendation
        rec = AllocationRecommendation(
            recommendation_date=date.today(),
            regime=alloc.regime,
            risk_score=risk.total_risk_score,
            equity_pct=alloc.equity_pct,
            gold_pct=alloc.gold_pct,
            silver_pct=alloc.silver_pct,
            cash_pct=alloc.cash_pct,
            equity_amount=alloc.equity_amount,
            gold_amount=alloc.gold_amount,
            silver_amount=alloc.silver_amount,
            cash_amount=alloc.cash_amount,
            total_capital=capital,
            rebalance_needed=alloc.rebalance_needed,
            reason=alloc.reason,
        )
        db.add(rec)
        await db.commit()

        return AllocationOut(
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
    except Exception as e:
        logger.error(f"Allocation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── Macro Status ─────────────────────────────────────────
@router.get("/macro-status", response_model=MacroStatusOut)
async def get_macro_status():
    """Get current macro market snapshot."""
    try:
        from app.strategy.macro_data import get_macro_snapshot

        macro = await asyncio.to_thread(get_macro_snapshot)
        return MacroStatusOut(
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
    except Exception as e:
        logger.error(f"Macro status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── Brokerage Check ─────────────────────────────────────
@router.post("/brokerage-check", response_model=BrokerageCheckOut)
async def brokerage_check(
    entry_price: float,
    quantity: int,
    db: AsyncSession = Depends(get_db),
):
    """Check if a trade is viable after brokerage costs."""
    from app.strategy.allocation_engine import check_brokerage_viability
    capital = await get_current_capital(db)
    result = check_brokerage_viability(capital, entry_price, quantity)
    return BrokerageCheckOut(**result)


# ─── Allocation Backtest ──────────────────────────────────
@router.post("/allocation-backtest", response_model=AllocBacktestResultOut)
async def run_alloc_backtest(payload: AllocBacktestRequest):
    """Run historical allocation backtest."""
    try:
        from app.strategy.allocation_backtester import run_allocation_backtest

        result = await asyncio.to_thread(
            run_allocation_backtest,
            years=payload.years,
            initial_capital=payload.initial_capital,
            use_deployment_scores=payload.use_deployment_scores,
        )
        return AllocBacktestResultOut(
            start_date=result.start_date,
            end_date=result.end_date,
            initial_capital=result.initial_capital,
            final_capital=result.final_capital,
            total_return_pct=result.total_return_pct,
            cagr=result.cagr,
            max_drawdown_pct=result.max_drawdown_pct,
            annualised_volatility=result.annualised_volatility,
            sharpe_ratio=result.sharpe_ratio,
            sortino_ratio=result.sortino_ratio,
            regime_changes=result.regime_changes,
            time_in_regimes=result.time_in_regimes,
            benchmark_return_pct=result.benchmark_return_pct,
            curve=[
                AllocBacktestPointOut(
                    date=p.date,
                    regime=p.regime,
                    risk_score=p.risk_score,
                    equity_value=p.equity_value,
                    gold_value=p.gold_value,
                    cash_value=p.cash_value,
                    total_value=p.total_value,
                )
                for p in result.curve
            ],
        )
    except Exception as e:
        logger.error(f"Allocation backtest error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── Risk History ─────────────────────────────────────────
@router.get("/risk-history")
async def get_risk_history(
    limit: int = 30,
    db: AsyncSession = Depends(get_db),
):
    """Get last N risk score records."""
    result = await db.execute(
        select(RiskScore).order_by(desc(RiskScore.score_date)).limit(limit)
    )
    rows = result.scalars().all()
    return [
        {
            "date": str(r.score_date),
            "total_risk_score": r.total_risk_score,
            "stability_score": r.stability_score,
            "regime": r.regime,
            "trend_risk": r.trend_risk,
            "volatility_risk": r.volatility_risk,
            "breadth_risk": r.breadth_risk,
            "global_risk": r.global_risk,
            "defensive_signal": r.defensive_signal,
            "vix": r.vix,
        }
        for r in rows
    ]


# ─── Regime History ───────────────────────────────────────
@router.get("/regime-history")
async def get_regime_history(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """Get regime change history."""
    result = await db.execute(
        select(RegimeHistory).order_by(desc(RegimeHistory.change_date)).limit(limit)
    )
    rows = result.scalars().all()
    return [
        {
            "date": str(r.change_date),
            "previous_regime": r.previous_regime,
            "new_regime": r.new_regime,
            "risk_score": r.risk_score,
            "trigger_reason": r.trigger_reason,
        }
        for r in rows
    ]
