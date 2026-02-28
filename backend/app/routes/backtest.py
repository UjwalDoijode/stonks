"""Backtesting routes."""

import json
import asyncio
from datetime import date as date_type, datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.database import get_db
from app.models import BacktestResult
from app.schemas import BacktestRequest, BacktestSummary
from app.strategy.backtester import run_backtest

router = APIRouter(prefix="/backtest", tags=["Backtest"])


@router.post("/run", response_model=BacktestSummary)
async def trigger_backtest(
    payload: BacktestRequest,
    db: AsyncSession = Depends(get_db),
):
    """Run a backtest and persist results."""
    try:
        metrics = await asyncio.to_thread(
            run_backtest,
            start_date=payload.start_date,
            end_date=payload.end_date,
            initial_capital=payload.initial_capital,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backtest failed: {str(e)}")

    # Parse string dates to date objects for SQLite
    def _parse_date(d):
        if isinstance(d, date_type):
            return d
        if isinstance(d, str):
            return datetime.strptime(d, "%Y-%m-%d").date()
        return d

    result = BacktestResult(
        start_date=_parse_date(metrics.start_date),
        end_date=_parse_date(metrics.end_date),
        initial_capital=metrics.initial_capital,
        final_capital=metrics.final_capital,
        total_trades=metrics.total_trades,
        winning_trades=metrics.winning_trades,
        losing_trades=metrics.losing_trades,
        win_rate=metrics.win_rate,
        avg_win=metrics.avg_win,
        avg_loss=metrics.avg_loss,
        max_drawdown_pct=metrics.max_drawdown_pct,
        cagr=metrics.cagr,
        profit_factor=metrics.profit_factor,
        sharpe_ratio=metrics.sharpe_ratio,
        total_return_pct=metrics.total_return_pct,
        equity_curve_json=json.dumps(metrics.equity_curve),
        trades_json=json.dumps(metrics.trades),
    )
    db.add(result)
    await db.commit()
    await db.refresh(result)
    return result


@router.get("/results", response_model=list[BacktestSummary])
async def list_backtests(db: AsyncSession = Depends(get_db)):
    """List all backtest results."""
    result = await db.execute(
        select(BacktestResult).order_by(desc(BacktestResult.run_date))
    )
    return result.scalars().all()


@router.get("/results/{result_id}")
async def get_backtest_detail(result_id: int, db: AsyncSession = Depends(get_db)):
    """Get detailed backtest result including equity curve and trades."""
    result = await db.execute(
        select(BacktestResult).where(BacktestResult.id == result_id)
    )
    bt = result.scalar_one_or_none()
    if not bt:
        raise HTTPException(status_code=404, detail="Backtest result not found")

    return {
        "summary": {
            "id": bt.id,
            "start_date": bt.start_date,
            "end_date": bt.end_date,
            "initial_capital": bt.initial_capital,
            "final_capital": bt.final_capital,
            "total_trades": bt.total_trades,
            "winning_trades": bt.winning_trades,
            "losing_trades": bt.losing_trades,
            "win_rate": bt.win_rate,
            "avg_win": bt.avg_win,
            "avg_loss": bt.avg_loss,
            "max_drawdown_pct": bt.max_drawdown_pct,
            "cagr": bt.cagr,
            "profit_factor": bt.profit_factor,
            "sharpe_ratio": bt.sharpe_ratio,
            "total_return_pct": bt.total_return_pct,
        },
        "equity_curve": json.loads(bt.equity_curve_json) if bt.equity_curve_json else [],
        "trades": json.loads(bt.trades_json) if bt.trades_json else [],
    }


# ─── Asset Class Backtest (Gold / Silver / Equity) ────────
@router.post("/asset")
async def run_asset_class_backtest(
    asset_type: str = "gold",
    years: int = 5,
    initial_capital: float = 20000.0,
):
    """Run buy-and-hold backtest for individual asset class (gold/silver/equity)."""
    from app.strategy.asset_backtester import run_asset_backtest
    try:
        result = await asyncio.to_thread(
            run_asset_backtest,
            asset_type=asset_type,
            years=years,
            initial_capital=initial_capital,
        )
        return {
            "asset": result.asset,
            "symbol": result.symbol,
            "start_date": result.start_date,
            "end_date": result.end_date,
            "initial_capital": result.initial_capital,
            "final_value": result.final_value,
            "total_return_pct": result.total_return_pct,
            "cagr": result.cagr,
            "max_drawdown_pct": result.max_drawdown_pct,
            "current_price": result.current_price,
            "start_price": result.start_price,
            "annualised_volatility": result.annualised_volatility,
            "sharpe_ratio": result.sharpe_ratio,
            "best_year_pct": result.best_year_pct,
            "worst_year_pct": result.worst_year_pct,
            "curve": [
                {"date": p.date, "price": p.price, "value": p.value, "return_pct": p.return_pct}
                for p in result.curve
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Recommendation Backtest ─────────────────────────────
@router.post("/recommendation")
async def run_recommendation_bt(
    years: int = 3,
    initial_capital: float = 20000.0,
):
    """Backtest: what if you followed our momentum stock recommendations?"""
    from app.strategy.asset_backtester import run_recommendation_backtest
    try:
        result = await asyncio.to_thread(
            run_recommendation_backtest,
            years=years,
            initial_capital=initial_capital,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
