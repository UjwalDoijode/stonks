"""
Asset Class Backtester — Individual Gold / Silver / Equity buy-and-hold
+ Recommendation-based backtest (what if you followed our picks?).

Provides:
  1. Gold buy-and-hold performance over N years
  2. Silver buy-and-hold performance over N years
  3. NIFTY / Equity buy-and-hold performance
  4. Recommendation backtest: simulates buying stocks marked BUY/RECOMMENDED
"""

import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, field

import pandas as pd
import numpy as np
import yfinance as yf

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class AssetBacktestPoint:
    date: str
    price: float
    value: float
    return_pct: float


@dataclass
class AssetBacktestResult:
    asset: str
    symbol: str
    start_date: str
    end_date: str
    initial_capital: float
    final_value: float
    total_return_pct: float
    cagr: float
    max_drawdown_pct: float
    current_price: float
    start_price: float
    annualised_volatility: float
    sharpe_ratio: float
    best_year_pct: float
    worst_year_pct: float
    curve: list[AssetBacktestPoint]


def _fetch_series(symbol: str, start: str, end: str) -> pd.Series | None:
    """Fetch close price series."""
    try:
        df = yf.Ticker(symbol).history(start=start, end=end)
        if df.empty:
            return None
        df.index = pd.to_datetime(df.index)
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        return df["Close"].dropna()
    except Exception as e:
        logger.error(f"Failed to fetch {symbol}: {e}")
        return None


def run_asset_backtest(
    asset_type: str = "gold",
    years: int = 5,
    initial_capital: float = 20000.0,
) -> AssetBacktestResult:
    """
    Run buy-and-hold backtest for a single asset class.
    asset_type: 'gold', 'silver', 'equity', 'nifty'
    Uses international futures for gold/silver (GC=F, SI=F) for accurate data.
    """
    # Asset symbol mapping (use futures/international for accuracy)
    ASSET_SYMBOLS = {
        "gold": ("GC=F", "Gold (COMEX Futures)"),
        "gold_etf": ("GOLDBEES.NS", "Gold ETF (GOLDBEES)"),
        "silver": ("SI=F", "Silver (COMEX Futures)"),
        "silver_etf": ("SILVERBEES.NS", "Silver ETF (SILVERBEES)"),
        "equity": ("^NSEI", "NIFTY 50 Index"),
        "nifty": ("^NSEI", "NIFTY 50 Index"),
        "sensex": ("^BSESN", "BSE SENSEX"),
        "nifty_next50": ("^NSMIDCP", "NIFTY Next 50"),
        "sp500": ("^GSPC", "S&P 500"),
    }

    asset_lower = asset_type.lower().strip()
    if asset_lower not in ASSET_SYMBOLS:
        raise ValueError(f"Unknown asset type '{asset_type}'. Choose from: {list(ASSET_SYMBOLS.keys())}")

    symbol, asset_name = ASSET_SYMBOLS[asset_lower]

    end_dt = datetime.now()
    start_dt = end_dt - timedelta(days=years * 365 + 30)
    start_str = start_dt.strftime("%Y-%m-%d")
    end_str = end_dt.strftime("%Y-%m-%d")

    logger.info(f"[ASSET BACKTEST] Fetching {asset_name} ({symbol}) for {years}Y...")

    series = _fetch_series(symbol, start_str, end_str)
    if series is None or len(series) < 50:
        raise ValueError(f"Could not fetch enough data for {asset_name} ({symbol})")

    # Trim to actual backtest period
    actual_start = end_dt - timedelta(days=years * 365)
    series = series[series.index >= pd.Timestamp(actual_start)]

    if len(series) < 20:
        raise ValueError(f"Not enough data in backtest period for {asset_name}")

    # Buy-and-hold simulation
    start_price = float(series.iloc[0])
    units = initial_capital / start_price

    # Build curve (weekly samples)
    curve = []
    peak = initial_capital
    max_dd = 0.0
    daily_returns = []
    yearly_returns = {}
    prev_val = initial_capital

    last_week = None
    for i, (dt, price) in enumerate(series.items()):
        value = units * float(price)
        ret_pct = ((value - initial_capital) / initial_capital) * 100

        # Max drawdown
        if value > peak:
            peak = value
        dd = ((peak - value) / peak) * 100
        max_dd = max(max_dd, dd)

        # Daily return
        if i > 0:
            daily_returns.append((value - prev_val) / prev_val)
        prev_val = value

        # Yearly tracking
        year = dt.year
        if year not in yearly_returns:
            yearly_returns[year] = {"start": value}
        yearly_returns[year]["end"] = value

        # Weekly sample
        week = dt.isocalendar()[1]
        if last_week is None or week != last_week:
            last_week = week
            curve.append(AssetBacktestPoint(
                date=dt.strftime("%Y-%m-%d"),
                price=round(float(price), 2),
                value=round(value, 2),
                return_pct=round(ret_pct, 2),
            ))

    final_value = units * float(series.iloc[-1])
    total_return = ((final_value - initial_capital) / initial_capital) * 100

    # CAGR
    trading_days = len(series)
    years_actual = trading_days / 252 if trading_days > 0 else 1
    cagr = ((final_value / initial_capital) ** (1 / years_actual) - 1) * 100

    # Volatility & Sharpe
    dr = np.array(daily_returns) if daily_returns else np.array([0.0])
    ann_vol = float(np.std(dr) * np.sqrt(252) * 100) if len(dr) > 1 else 0.0
    risk_free_daily = 0.06 / 252
    excess = dr - risk_free_daily
    sharpe = float(np.mean(excess) / np.std(excess) * np.sqrt(252)) if np.std(excess) > 0 else 0.0

    # Best/worst year
    yr_returns = {}
    for yr, vals in yearly_returns.items():
        if "start" in vals and "end" in vals:
            yr_returns[yr] = ((vals["end"] - vals["start"]) / vals["start"]) * 100
    best_year = max(yr_returns.values()) if yr_returns else 0
    worst_year = min(yr_returns.values()) if yr_returns else 0

    return AssetBacktestResult(
        asset=asset_name,
        symbol=symbol,
        start_date=series.index[0].strftime("%Y-%m-%d"),
        end_date=series.index[-1].strftime("%Y-%m-%d"),
        initial_capital=initial_capital,
        final_value=round(final_value, 2),
        total_return_pct=round(total_return, 2),
        cagr=round(cagr, 2),
        max_drawdown_pct=round(max_dd, 2),
        current_price=round(float(series.iloc[-1]), 2),
        start_price=round(start_price, 2),
        annualised_volatility=round(ann_vol, 2),
        sharpe_ratio=round(sharpe, 2),
        best_year_pct=round(best_year, 2),
        worst_year_pct=round(worst_year, 2),
        curve=curve,
    )


# ═══════════════════════════════════════════════════════
# Recommendation-Based Backtest
# ═══════════════════════════════════════════════════════

def run_recommendation_backtest(
    years: int = 3,
    initial_capital: float = 20000.0,
    strategy: str = "momentum",  # 'momentum' or 'equal_weight'
) -> dict:
    """
    Simulate: "What if I invested based on scanner recommendations?"

    Strategy:
    - Monthly: pick top 5 momentum stocks from NIFTY 100
    - Buy equal weight, hold for 1 month, then rotate
    - Compare vs NIFTY buy-and-hold benchmark
    """
    from app.strategy.allocation_backtester import (
        MOMENTUM_UNIVERSE, _download_batch, _rank_momentum, _fetch_series
    )

    end_dt = datetime.now()
    start_dt = end_dt - timedelta(days=years * 365 + 200)
    start_str = start_dt.strftime("%Y-%m-%d")
    end_str = end_dt.strftime("%Y-%m-%d")

    logger.info(f"[REC BACKTEST] Downloading stock universe...")
    stock_data = _download_batch(MOMENTUM_UNIVERSE, start_str, end_str)
    nifty = _fetch_series(settings.NIFTY_SYMBOL, start_str, end_str)

    if len(stock_data) < 10:
        raise ValueError("Not enough stock data for recommendation backtest")
    if nifty is None:
        raise ValueError("Could not fetch NIFTY data")

    # Valid trading dates
    actual_start = end_dt - timedelta(days=years * 365)
    dates = nifty.index[nifty.index >= pd.Timestamp(actual_start)]

    # Simulation
    capital = initial_capital
    positions = {}  # {sym: {shares, entry_price}}
    rebalance_interval = 21  # monthly
    last_rebalance = -999
    num_picks = 5

    curve = []
    peak = initial_capital
    max_dd = 0.0
    daily_returns_list = []
    prev_total = initial_capital
    total_trades = 0
    winning_trades = 0
    losing_trades = 0
    last_week = None

    for i, dt in enumerate(dates):
        # Update position values
        equity_value = 0.0
        for sym, pos in positions.items():
            sd = stock_data.get(sym)
            if sd is None:
                equity_value += pos["shares"] * pos["entry_price"]
                continue
            cp = sd.get(dt, np.nan)
            if pd.isna(cp):
                mask = sd.index <= dt
                cp = sd[mask].iloc[-1] if mask.any() else pos["entry_price"]
            equity_value += pos["shares"] * float(cp)

        total = equity_value + capital if positions else capital

        # Monthly rebalance
        if i - last_rebalance >= rebalance_interval or i == 0:
            last_rebalance = i

            # Sell all positions
            for sym, pos in positions.items():
                sd = stock_data.get(sym)
                if sd is None:
                    capital += pos["shares"] * pos["entry_price"]
                    continue
                cp = sd.get(dt, np.nan)
                if pd.isna(cp):
                    mask = sd.index <= dt
                    cp = sd[mask].iloc[-1] if mask.any() else pos["entry_price"]
                sale = pos["shares"] * float(cp)
                pnl = sale - (pos["shares"] * pos["entry_price"])
                capital += sale
                total_trades += 1
                if pnl > 0:
                    winning_trades += 1
                else:
                    losing_trades += 1
            positions.clear()

            total = capital

            # Pick top momentum stocks
            picks = _rank_momentum(stock_data, dt)
            if picks:
                per_stock = total * 0.9 / len(picks)  # 90% deployed, 10% cash buffer
                cash_reserve = total * 0.1

                for sym in picks:
                    sd = stock_data.get(sym)
                    if sd is None:
                        continue
                    cp = sd.get(dt, np.nan)
                    if pd.isna(cp):
                        mask = sd.index <= dt
                        cp = sd[mask].iloc[-1] if mask.any() else np.nan
                    if pd.isna(cp) or cp <= 0:
                        cash_reserve += per_stock
                        continue
                    shares = per_stock / float(cp)
                    positions[sym] = {
                        "shares": shares,
                        "entry_price": float(cp),
                    }

                capital = cash_reserve

            # Recalculate
            equity_value = sum(
                pos["shares"] * float(stock_data[sym].get(dt, pos["entry_price"]))
                for sym, pos in positions.items()
                if sym in stock_data
            )
            total = equity_value + capital

        # Track metrics
        if total > peak:
            peak = total
        dd = ((peak - total) / peak) * 100 if peak > 0 else 0
        max_dd = max(max_dd, dd)

        if prev_total > 0:
            daily_returns_list.append((total - prev_total) / prev_total)
        prev_total = total

        # Weekly curve
        week = dt.isocalendar()[1]
        if last_week is None or week != last_week:
            last_week = week
            curve.append({
                "date": dt.strftime("%Y-%m-%d"),
                "value": round(total, 2),
                "return_pct": round(((total - initial_capital) / initial_capital) * 100, 2),
            })

    # Final liquidation
    for sym, pos in positions.items():
        sd = stock_data.get(sym)
        if sd is not None and len(sd) > 0:
            capital += pos["shares"] * float(sd.iloc[-1])
        else:
            capital += pos["shares"] * pos["entry_price"]
    positions.clear()
    final = capital

    total_return = ((final - initial_capital) / initial_capital) * 100
    trading_days = len(dates)
    years_actual = trading_days / 252 if trading_days > 0 else 1
    cagr = ((final / initial_capital) ** (1 / years_actual) - 1) * 100

    # Benchmark NIFTY
    nifty_start = float(nifty.get(dates[0], np.nan))
    nifty_end = float(nifty.get(dates[-1], np.nan))
    benchmark_return = ((nifty_end - nifty_start) / nifty_start) * 100 if nifty_start > 0 else 0

    # Volatility
    dr = np.array(daily_returns_list) if daily_returns_list else np.array([0.0])
    ann_vol = float(np.std(dr) * np.sqrt(252) * 100) if len(dr) > 1 else 0
    excess = dr - 0.06 / 252
    sharpe = float(np.mean(excess) / np.std(excess) * np.sqrt(252)) if np.std(excess) > 0 else 0

    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

    return {
        "strategy": "Momentum Stock Picks (Monthly Rotation)",
        "start_date": dates[0].strftime("%Y-%m-%d"),
        "end_date": dates[-1].strftime("%Y-%m-%d"),
        "initial_capital": initial_capital,
        "final_capital": round(final, 2),
        "total_return_pct": round(total_return, 2),
        "cagr": round(cagr, 2),
        "max_drawdown_pct": round(max_dd, 2),
        "sharpe_ratio": round(sharpe, 2),
        "annualised_volatility": round(ann_vol, 2),
        "total_trades": total_trades,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "win_rate": round(win_rate, 2),
        "benchmark_return_pct": round(benchmark_return, 2),
        "alpha": round(total_return - benchmark_return, 2),
        "curve": curve,
    }
