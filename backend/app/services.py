"""Service layer — business logic between routes and strategy/DB."""

import json
import logging
from datetime import date, datetime
from typing import Optional

import yfinance as yf
import pandas as pd
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import Trade, ScanResult, PortfolioSnapshot, BacktestResult, TradeStatus
from app.schemas import (
    PositionSizeResponse, PortfolioStats, EquityCurvePoint,
    CompoundingPoint, CompoundingResponse,
)
from app.strategy.position_sizing import calculate_position_size
from app.strategy.data_feed import fetch_ohlcv, is_market_bullish, get_nifty_regime_info
from app.strategy.signals import scan_symbol, Signal
from app.strategy.universe import NIFTY_100_SYMBOLS, get_clean_symbol

logger = logging.getLogger(__name__)


def _batch_fetch_ohlcv(symbols: list[str], period_years: int = 2) -> dict[str, pd.DataFrame]:
    """Batch-fetch OHLCV for all symbols at once using yf.download()."""
    from datetime import timedelta
    end = datetime.now()
    start = end - timedelta(days=period_years * 365)

    try:
        batch_df = yf.download(
            symbols,
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
            group_by="ticker",
            threads=True,
            progress=False,
        )
    except Exception as e:
        logger.error(f"Batch download failed: {e}")
        return {}

    if batch_df is None or batch_df.empty:
        return {}

    result: dict[str, pd.DataFrame] = {}
    available = set(batch_df.columns.get_level_values(0).unique())

    for sym in symbols:
        try:
            if sym not in available:
                continue
            df = batch_df[sym].dropna(how="all")
            if df.empty or len(df) < settings.DMA_LONG + 20:
                continue

            df.index = pd.to_datetime(df.index)
            if df.index.tz is not None:
                df.index = df.index.tz_localize(None)

            # Standardise column names
            df.columns = [c.lower().replace(" ", "_") for c in df.columns]
            expected = {"open", "high", "low", "close", "volume"}
            if not expected.issubset(set(df.columns)):
                continue
            df = df[["open", "high", "low", "close", "volume"]].copy()
            df.dropna(inplace=True)
            if len(df) >= settings.DMA_LONG + 20:
                result[sym] = df
        except Exception as e:
            logger.debug(f"Batch parse skip {sym}: {e}")
            continue

    return result


def _run_scan_sync(symbols: list[str]) -> list[dict]:
    """Synchronous scan logic — runs in thread to avoid blocking event loop."""
    from app.strategy.market_intelligence import (
        assess_geopolitical_risk, compile_stock_intelligence
    )
    from app.strategy.macro_data import get_macro_snapshot

    scan_date = date.today()
    results = []

    # Get current macro snapshot for geo risk assessment
    try:
        macro = get_macro_snapshot()
        geo_risk = assess_geopolitical_risk(macro)
    except Exception as e:
        logger.warning(f"Macro/geo risk fetch failed: {e}")
        from app.strategy.market_intelligence import GeoRiskAssessment
        geo_risk = GeoRiskAssessment()
        macro = {}

    # Batch-fetch all data at once (FAST)
    logger.info(f"Batch-downloading {len(symbols)} symbols...")
    data_map = _batch_fetch_ohlcv(symbols, period_years=2)
    logger.info(f"Got data for {len(data_map)} symbols")

    for sym, df in data_map.items():
        try:
            sig = scan_symbol(sym, df)
            if sig is None:
                continue

            # Generate enhanced intelligence
            intel = compile_stock_intelligence(sig, df, geo_risk)

            results.append({
                "scan_date": scan_date,
                "symbol": get_clean_symbol(sym),
                "price": sig.close,
                "dma_200": sig.dma_200,
                "dma_50": sig.dma_50,
                "dma_20": sig.dma_20,
                "rsi": sig.rsi,
                "volume_ratio": sig.volume_ratio,
                "prev_high": sig.entry_price,
                "swing_low": sig.stop_loss,
                "above_200dma": sig.above_200dma,
                "dma50_trending_up": sig.dma50_trending_up,
                "pullback_to_20dma": sig.pullback_to_20dma,
                "rsi_in_zone": sig.rsi_in_zone,
                "volume_contracting": sig.volume_contracting,
                "entry_triggered": sig.entry_triggered,
                "is_candidate": intel.recommendation in ("BUY", "RECOMMENDED"),
                "criteria_met": sig.criteria_met,
                "recommendation": intel.recommendation,
                "reasoning": intel.reasoning,
                # Enhanced fields
                "conviction": intel.conviction,
                "conviction_score": intel.conviction_score,
                "primary_reason": intel.primary_reason,
                "category_tag": intel.category_tag,
                "risk_warning": intel.risk_warning,
                "entry_price": intel.entry_price,
                "stop_loss_price": intel.stop_loss,
                "target_1": intel.target_1,
                "target_2": intel.target_2,
                "target_3": intel.target_3,
                "risk_pct": intel.risk_pct,
                "reward_pct": intel.reward_pct,
                "risk_reward": intel.risk_reward,
                "earnings_momentum": intel.earnings_momentum,
                "earnings_score": intel.earnings_score,
                "quarterly_trend": intel.quarterly_trend,
                "geo_risk_level": geo_risk.risk_level,
                "geo_risk_score": geo_risk.risk_score,
            })
        except Exception as e:
            logger.error(f"Scan error for {sym}: {e}")
            continue

    return results


async def run_weekly_scan(db: AsyncSession) -> list[ScanResult]:
    """Run full universe scan using batch download and persist results."""
    import asyncio
    from sqlalchemy import delete as sa_delete

    scan_dicts = await asyncio.to_thread(_run_scan_sync, NIFTY_100_SYMBOLS)

    # Delete any existing results for today to prevent duplicates
    today = date.today()
    await db.execute(sa_delete(ScanResult).where(ScanResult.scan_date == today))

    models = []
    for d in scan_dicts:
        scan = ScanResult(**d)
        db.add(scan)
        models.append(scan)

    await db.commit()
    return models


# ─── Trade Service ────────────────────────────────────────
async def get_current_capital(db: AsyncSession) -> float:
    """Calculate current available capital."""
    # Get latest snapshot or use initial
    result = await db.execute(
        select(PortfolioSnapshot).order_by(desc(PortfolioSnapshot.snapshot_date)).limit(1)
    )
    snapshot = result.scalar_one_or_none()
    base_capital = snapshot.capital if snapshot else settings.INITIAL_CAPITAL

    # Subtract capital locked in open trades
    result = await db.execute(
        select(func.coalesce(func.sum(Trade.position_size), 0)).where(
            Trade.status == TradeStatus.OPEN.value
        )
    )
    locked = result.scalar()
    return base_capital - locked


async def get_open_trade_count(db: AsyncSession) -> int:
    result = await db.execute(
        select(func.count(Trade.id)).where(Trade.status == TradeStatus.OPEN.value)
    )
    return result.scalar()


async def create_trade(
    db: AsyncSession,
    symbol: str,
    entry_date: date,
    entry_price: float,
    stop_loss: float,
    notes: Optional[str] = None,
) -> Trade:
    """Create a new trade with proper position sizing."""
    open_count = await get_open_trade_count(db)
    if open_count >= settings.MAX_SIMULTANEOUS_TRADES:
        raise ValueError(f"Max {settings.MAX_SIMULTANEOUS_TRADES} simultaneous trades allowed")

    capital = await get_current_capital(db)
    ps = calculate_position_size(capital, entry_price, stop_loss)

    if ps.position_size > capital:
        raise ValueError(f"Insufficient capital: need ₹{ps.position_size:.2f}, have ₹{capital:.2f}")

    trade = Trade(
        symbol=symbol,
        entry_date=entry_date,
        entry_price=entry_price,
        quantity=ps.quantity,
        stop_loss=stop_loss,
        target=ps.target_price,
        risk_per_share=ps.risk_per_share,
        risk_amount=ps.risk_amount,
        capital_at_entry=capital,
        position_size=ps.position_size,
        notes=notes,
    )
    db.add(trade)
    await db.commit()
    await db.refresh(trade)
    return trade


async def close_trade(
    db: AsyncSession,
    trade_id: int,
    exit_date: date,
    exit_price: float,
    status: str = TradeStatus.CLOSED_MANUAL.value,
) -> Trade:
    """Close an open trade and calculate P&L."""
    result = await db.execute(select(Trade).where(Trade.id == trade_id))
    trade = result.scalar_one_or_none()
    if not trade:
        raise ValueError(f"Trade {trade_id} not found")
    if trade.status != TradeStatus.OPEN.value:
        raise ValueError(f"Trade {trade_id} is not open")

    trade.exit_date = exit_date
    trade.exit_price = exit_price
    trade.pnl = (exit_price - trade.entry_price) * trade.quantity
    trade.pnl_pct = (trade.pnl / trade.position_size) * 100 if trade.position_size else 0
    trade.r_multiple = trade.pnl / trade.risk_amount if trade.risk_amount else 0
    trade.status = status

    # Record adaptive feedback (Part 6)
    try:
        from app.strategy.adaptive_feedback import record_trade_feedback
        record_trade_feedback(
            trade_id=trade.id,
            symbol=trade.symbol,
            pnl=trade.pnl,
            pnl_pct=trade.pnl_pct,
            r_multiple=trade.r_multiple,
        )
    except Exception as fb_err:
        logger.warning(f"Feedback recording failed (non-fatal): {fb_err}")

    # Update capital
    new_capital = await get_current_capital(db)
    new_capital += trade.position_size + trade.pnl

    await db.commit()
    await db.refresh(trade)
    return trade


# ─── Portfolio Stats ──────────────────────────────────────
async def get_portfolio_stats(db: AsyncSession) -> PortfolioStats:
    """Calculate comprehensive portfolio statistics."""
    # All trades
    result = await db.execute(select(Trade))
    all_trades = result.scalars().all()

    closed = [t for t in all_trades if t.status != TradeStatus.OPEN.value]
    open_trades = [t for t in all_trades if t.status == TradeStatus.OPEN.value]
    wins = [t for t in closed if t.pnl > 0]
    losses = [t for t in closed if t.pnl <= 0]

    total_pnl = sum(t.pnl for t in closed)
    current_capital = settings.INITIAL_CAPITAL + total_pnl
    total_return = (total_pnl / settings.INITIAL_CAPITAL) * 100 if settings.INITIAL_CAPITAL else 0

    avg_win = sum(t.pnl for t in wins) / len(wins) if wins else 0
    avg_loss = abs(sum(t.pnl for t in losses) / len(losses)) if losses else 0
    win_rate = (len(wins) / len(closed) * 100) if closed else 0

    gross_profit = sum(t.pnl for t in wins)
    gross_loss = abs(sum(t.pnl for t in losses))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

    # Max drawdown from equity snapshots
    result = await db.execute(
        select(PortfolioSnapshot).order_by(PortfolioSnapshot.snapshot_date)
    )
    snapshots = result.scalars().all()
    max_dd = 0
    peak = settings.INITIAL_CAPITAL
    for s in snapshots:
        if s.equity > peak:
            peak = s.equity
        dd = ((peak - s.equity) / peak) * 100
        if dd > max_dd:
            max_dd = dd

    # CAGR
    if closed:
        first_date = min(t.entry_date for t in all_trades)
        last_date = max(t.exit_date or t.entry_date for t in all_trades)
        days = (last_date - first_date).days
        years = days / 365.25 if days > 0 else 1
        cagr = ((current_capital / settings.INITIAL_CAPITAL) ** (1 / years) - 1) * 100
    else:
        cagr = 0

    return PortfolioStats(
        current_capital=round(current_capital, 2),
        initial_capital=settings.INITIAL_CAPITAL,
        total_return_pct=round(total_return, 2),
        total_trades=len(closed),
        open_trades=len(open_trades),
        winning_trades=len(wins),
        losing_trades=len(losses),
        win_rate=round(win_rate, 2),
        avg_win=round(avg_win, 2),
        avg_loss=round(avg_loss, 2),
        max_drawdown_pct=round(max_dd, 2),
        cagr=round(cagr, 2),
        profit_factor=round(profit_factor, 2),
    )


async def get_equity_curve(db: AsyncSession) -> list[EquityCurvePoint]:
    """Get equity curve from portfolio snapshots."""
    result = await db.execute(
        select(PortfolioSnapshot).order_by(PortfolioSnapshot.snapshot_date)
    )
    snapshots = result.scalars().all()
    if not snapshots:
        return [EquityCurvePoint(date=date.today(), equity=settings.INITIAL_CAPITAL)]
    return [
        EquityCurvePoint(date=s.snapshot_date, equity=s.equity) for s in snapshots
    ]


# ─── Compounding Simulator ───────────────────────────────
def simulate_compounding(
    initial_capital: float,
    monthly_return_pct: float,
    monthly_addition: float,
    years: int,
) -> CompoundingResponse:
    """Simulate compound growth over time."""
    months = years * 12
    capital = initial_capital
    curve = [CompoundingPoint(month=0, capital=round(capital, 2))]

    for m in range(1, months + 1):
        capital += monthly_addition
        capital *= (1 + monthly_return_pct / 100)
        curve.append(CompoundingPoint(month=m, capital=round(capital, 2)))

    total_return = ((capital - initial_capital) / initial_capital) * 100
    cagr = ((capital / initial_capital) ** (1 / years) - 1) * 100 if years > 0 else 0

    return CompoundingResponse(
        initial_capital=initial_capital,
        final_capital=round(capital, 2),
        total_return_pct=round(total_return, 2),
        cagr=round(cagr, 2),
        curve=curve,
    )
