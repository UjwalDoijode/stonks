"""Backtesting engine — event-driven bar-by-bar simulation."""

import pandas as pd
import numpy as np
import json
import logging
from datetime import date, datetime
from dataclasses import dataclass, field, asdict
from typing import Optional

from app.config import settings
from app.strategy.indicators import add_indicators
from app.strategy.position_sizing import calculate_position_size
from app.strategy.data_feed import fetch_ohlcv, fetch_nifty_data
from app.strategy.universe import NIFTY_100_SYMBOLS

logger = logging.getLogger(__name__)


@dataclass
class BTTrade:
    """A single backtested trade."""
    symbol: str
    entry_date: str
    entry_price: float
    stop_loss: float
    target: float
    quantity: int
    risk_per_share: float
    risk_amount: float
    position_size: float
    capital_at_entry: float
    exit_date: Optional[str] = None
    exit_price: Optional[float] = None
    pnl: float = 0.0
    pnl_pct: float = 0.0
    r_multiple: float = 0.0
    status: str = "OPEN"


@dataclass
class BacktestMetrics:
    """Summary metrics for a backtest run."""
    start_date: str
    end_date: str
    initial_capital: float
    final_capital: float
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    max_drawdown_pct: float = 0.0
    cagr: float = 0.0
    profit_factor: float = 0.0
    sharpe_ratio: float = 0.0
    total_return_pct: float = 0.0
    equity_curve: list = field(default_factory=list)
    trades: list = field(default_factory=list)


def run_backtest(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    initial_capital: float = None,
    symbols: Optional[list[str]] = None,
) -> BacktestMetrics:
    """
    Run a full backtest across the NIFTY 100 universe.

    Rules:
    - Regime filter: NIFTY must be above 200 DMA
    - Max 2 simultaneous trades
    - Risk per trade: 1.5% of current capital
    - Entry: pullback to 20 DMA with RSI 40-50, volume contraction
    - Exit: stop at swing low, target at 2R
    """
    if initial_capital is None:
        initial_capital = settings.INITIAL_CAPITAL
    if symbols is None:
        symbols = NIFTY_100_SYMBOLS

    capital = initial_capital
    open_trades: list[BTTrade] = []
    closed_trades: list[BTTrade] = []
    equity_curve: list[dict] = []

    # ── Fetch data ───────────────────────────────────────
    logger.info("Fetching NIFTY index data...")
    nifty_df = fetch_nifty_data(period_years=settings.DATA_LOOKBACK_YEARS)
    if nifty_df is None:
        raise ValueError("Cannot fetch NIFTY data for regime filter")

    nifty_df = add_indicators(nifty_df)

    logger.info(f"Fetching data for {len(symbols)} symbols...")
    all_data: dict[str, pd.DataFrame] = {}
    for sym in symbols:
        df = fetch_ohlcv(sym, period_years=settings.DATA_LOOKBACK_YEARS)
        if df is not None:
            df = add_indicators(df)
            if not df.empty:
                all_data[sym] = df

    logger.info(f"Loaded data for {len(all_data)} symbols")

    if not all_data:
        raise ValueError("No valid symbol data loaded")

    # ── Find common date range ───────────────────────────
    all_dates = set(nifty_df.index)
    for df in all_data.values():
        all_dates &= set(df.index)

    all_dates = sorted(all_dates)
    if start_date:
        all_dates = [d for d in all_dates if d.date() >= start_date]
    if end_date:
        all_dates = [d for d in all_dates if d.date() <= end_date]

    if len(all_dates) < 50:
        raise ValueError(f"Insufficient overlapping dates: {len(all_dates)}")

    logger.info(f"Backtesting from {all_dates[0].date()} to {all_dates[-1].date()}")

    peak_equity = initial_capital
    max_dd = 0.0

    # ── Bar-by-bar simulation ────────────────────────────
    for i, current_date in enumerate(all_dates):
        if i < 1:
            continue  # need at least 1 previous bar

        # ── Check regime ─────────────────────────────────
        try:
            nifty_row = nifty_df.loc[current_date]
        except KeyError:
            continue

        regime_ok = nifty_row["close"] > nifty_row["dma_200"]

        # ── Check open trades for exits ──────────────────
        trades_to_close = []
        for trade in open_trades:
            sym_df = all_data.get(trade.symbol)
            if sym_df is None:
                continue
            try:
                bar = sym_df.loc[current_date]
            except KeyError:
                continue

            # Check stop loss
            if bar["low"] <= trade.stop_loss:
                trade.exit_date = str(current_date.date())
                trade.exit_price = trade.stop_loss
                trade.pnl = (trade.exit_price - trade.entry_price) * trade.quantity
                trade.pnl_pct = (trade.pnl / trade.position_size) * 100
                trade.r_multiple = trade.pnl / trade.risk_amount if trade.risk_amount else 0
                trade.status = "CLOSED_SL"
                capital += trade.pnl + trade.position_size  # return capital
                trades_to_close.append(trade)
            # Check target
            elif bar["high"] >= trade.target:
                trade.exit_date = str(current_date.date())
                trade.exit_price = trade.target
                trade.pnl = (trade.exit_price - trade.entry_price) * trade.quantity
                trade.pnl_pct = (trade.pnl / trade.position_size) * 100
                trade.r_multiple = trade.pnl / trade.risk_amount if trade.risk_amount else 0
                trade.status = "CLOSED_TP"
                capital += trade.pnl + trade.position_size
                trades_to_close.append(trade)

        for t in trades_to_close:
            open_trades.remove(t)
            closed_trades.append(t)

        # ── Scan for new entries (if regime OK & slots available) ─
        if regime_ok and len(open_trades) < settings.MAX_SIMULTANEOUS_TRADES:
            for sym, sym_df in all_data.items():
                if len(open_trades) >= settings.MAX_SIMULTANEOUS_TRADES:
                    break
                # Skip if already in a trade for this symbol
                if any(t.symbol == sym for t in open_trades):
                    continue

                try:
                    row = sym_df.loc[current_date]
                    prev_date = all_dates[i - 1]
                    prev_row = sym_df.loc[prev_date]
                except KeyError:
                    continue

                # ── Strategy conditions ──────────────────
                above_200 = row["close"] > row["dma_200"]
                dma50_up = row["dma_50_slope"] > 0
                near_20dma = abs(row["dist_to_20dma_pct"]) <= 2.0
                rsi_ok = settings.RSI_LOW <= row["rsi"] <= settings.RSI_HIGH
                vol_contract = row["volume_ratio"] < 0.8
                entry_trigger = row["close"] > prev_row["high"]

                if all([above_200, dma50_up, near_20dma, rsi_ok, vol_contract, entry_trigger]):
                    entry_price = prev_row["high"]
                    stop_loss = row["swing_low"]
                    risk_per_share = entry_price - stop_loss

                    if risk_per_share <= 0:
                        continue

                    try:
                        ps = calculate_position_size(capital, entry_price, stop_loss)
                    except ValueError:
                        continue

                    if ps.position_size > capital:
                        continue

                    trade = BTTrade(
                        symbol=sym,
                        entry_date=str(current_date.date()),
                        entry_price=round(entry_price, 2),
                        stop_loss=round(stop_loss, 2),
                        target=round(ps.target_price, 2),
                        quantity=ps.quantity,
                        risk_per_share=round(risk_per_share, 2),
                        risk_amount=round(ps.risk_amount, 2),
                        position_size=round(ps.position_size, 2),
                        capital_at_entry=round(capital, 2),
                    )

                    capital -= ps.position_size  # deploy capital
                    open_trades.append(trade)

        # ── Record equity ────────────────────────────────
        # Equity = free capital + mark-to-market of open positions
        mtm = capital
        for trade in open_trades:
            sym_df = all_data.get(trade.symbol)
            if sym_df is not None:
                try:
                    current_price = sym_df.loc[current_date]["close"]
                    mtm += current_price * trade.quantity
                except KeyError:
                    mtm += trade.position_size

        equity_curve.append({
            "date": str(current_date.date()),
            "equity": round(mtm, 2),
        })

        # Track drawdown
        if mtm > peak_equity:
            peak_equity = mtm
        dd = ((peak_equity - mtm) / peak_equity) * 100
        if dd > max_dd:
            max_dd = dd

    # ── Force-close remaining open trades at last bar ────
    for trade in open_trades:
        sym_df = all_data.get(trade.symbol)
        if sym_df is not None:
            try:
                last_price = sym_df.loc[all_dates[-1]]["close"]
            except KeyError:
                last_price = trade.entry_price
        else:
            last_price = trade.entry_price

        trade.exit_date = str(all_dates[-1].date())
        trade.exit_price = round(last_price, 2)
        trade.pnl = (trade.exit_price - trade.entry_price) * trade.quantity
        trade.pnl_pct = (trade.pnl / trade.position_size) * 100 if trade.position_size else 0
        trade.r_multiple = trade.pnl / trade.risk_amount if trade.risk_amount else 0
        trade.status = "CLOSED_MANUAL"
        capital += trade.pnl + trade.position_size
        closed_trades.append(trade)

    # ── Calculate metrics ────────────────────────────────
    final_capital = capital
    total = len(closed_trades)
    wins = [t for t in closed_trades if t.pnl > 0]
    losses = [t for t in closed_trades if t.pnl <= 0]

    win_rate = (len(wins) / total * 100) if total > 0 else 0
    avg_win = np.mean([t.pnl for t in wins]) if wins else 0
    avg_loss = abs(np.mean([t.pnl for t in losses])) if losses else 0
    gross_profit = sum(t.pnl for t in wins)
    gross_loss = abs(sum(t.pnl for t in losses))
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float("inf")

    # CAGR
    days = (all_dates[-1] - all_dates[0]).days
    years = days / 365.25 if days > 0 else 1
    cagr = ((final_capital / initial_capital) ** (1 / years) - 1) * 100 if years > 0 else 0

    total_return = ((final_capital - initial_capital) / initial_capital) * 100

    # Sharpe (annualized from daily equity returns)
    if len(equity_curve) > 1:
        equities = pd.Series([e["equity"] for e in equity_curve])
        daily_returns = equities.pct_change().dropna()
        sharpe = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252) if daily_returns.std() > 0 else 0
    else:
        sharpe = 0

    return BacktestMetrics(
        start_date=str(all_dates[0].date()),
        end_date=str(all_dates[-1].date()),
        initial_capital=round(initial_capital, 2),
        final_capital=round(final_capital, 2),
        total_trades=total,
        winning_trades=len(wins),
        losing_trades=len(losses),
        win_rate=round(win_rate, 2),
        avg_win=round(avg_win, 2),
        avg_loss=round(avg_loss, 2),
        max_drawdown_pct=round(max_dd, 2),
        cagr=round(cagr, 2),
        profit_factor=round(profit_factor, 2),
        sharpe_ratio=round(sharpe, 2),
        total_return_pct=round(total_return, 2),
        equity_curve=equity_curve,
        trades=[asdict(t) for t in closed_trades],
    )
