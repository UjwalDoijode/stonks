"""
Allocation Backtester v3 — Momentum-Enhanced Regime-Based Strategy

Strategy:
  1. Regime detection (daily) → determines equity/gold/cash split
  2. Equity portion: Top-N momentum stocks from NIFTY 50 (monthly rotation)
  3. Gold portion: GOLDBEES ETF
  4. Cash: earns risk-free rate
  5. Trailing stop-loss per stock position (-8% from peak)
  6. Monthly rebalance of stock selection

Historical CAGR target: 15-25% (vs NIFTY ~8-12%)
"""

import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, field

import pandas as pd
import numpy as np
import yfinance as yf

from app.config import settings
from app.strategy.risk_engine import classify_regime

logger = logging.getLogger(__name__)

# ── Regime-based allocation (aggressive) ──
REGIME_ALLOCATION = {
    "STRONG_RISK_ON": {"equity": 90, "gold": 5, "cash": 5},
    "MILD_RISK_ON":   {"equity": 75, "gold": 15, "cash": 10},
    "NEUTRAL":        {"equity": 50, "gold": 30, "cash": 20},
    "RISK_OFF":       {"equity": 15, "gold": 50, "cash": 35},
    "EXTREME_RISK":   {"equity": 0,  "gold": 55, "cash": 45},
}

# Top liquid NIFTY stocks for momentum picking
MOMENTUM_UNIVERSE = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "HINDUNILVR.NS", "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "KOTAKBANK.NS",
    "LT.NS", "AXISBANK.NS", "BAJFINANCE.NS", "ASIANPAINT.NS", "MARUTI.NS",
    "HCLTECH.NS", "SUNPHARMA.NS", "TITAN.NS", "WIPRO.NS", "ULTRACEMCO.NS",
    "BAJAJFINSV.NS", "TECHM.NS", "POWERGRID.NS", "NTPC.NS",
    "TATAMOTORS.NS", "M&M.NS", "ONGC.NS", "JSWSTEEL.NS", "TATASTEEL.NS",
    "ADANIENT.NS", "COALINDIA.NS", "HDFCLIFE.NS",
    "BAJAJ-AUTO.NS", "DRREDDY.NS", "DIVISLAB.NS", "CIPLA.NS",
    "BRITANNIA.NS", "EICHERMOT.NS", "APOLLOHOSP.NS",
    "BPCL.NS", "TATACONSUM.NS",
]

NUM_MOMENTUM_PICKS = 5
TRAILING_STOP_PCT = 0.08        # 8% trailing stop
MOMENTUM_LOOKBACK = 126         # ~6 months
MOMENTUM_SKIP = 21              # skip last month (mean-reversion avoidance)
REBALANCE_FREQ_DAYS = 21        # ~monthly rebalance


@dataclass
class AllocBacktestPoint:
    date: str
    regime: str
    risk_score: float
    equity_value: float
    gold_value: float
    cash_value: float
    total_value: float


@dataclass
class AllocBacktestResult:
    start_date: str
    end_date: str
    initial_capital: float
    final_capital: float
    total_return_pct: float
    cagr: float
    max_drawdown_pct: float
    annualised_volatility: float
    sharpe_ratio: float
    sortino_ratio: float
    regime_changes: int
    time_in_regimes: dict
    benchmark_return_pct: float
    curve: list[AllocBacktestPoint]


def _fetch_series(symbol: str, start: str, end: str):
    """Fetch close price series."""
    try:
        df = yf.Ticker(symbol).history(start=start, end=end)
        if df.empty:
            return None
        df.index = pd.to_datetime(df.index)
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        return df["Close"]
    except Exception as e:
        logger.debug(f"Failed to fetch {symbol}: {e}")
        return None


def _download_batch(symbols: list, start: str, end: str) -> dict[str, pd.Series]:
    """Batch download close prices for multiple symbols."""
    result = {}
    try:
        data = yf.download(
            symbols, start=start, end=end,
            group_by="ticker", threads=True, progress=False
        )
        if data is None or data.empty:
            return result

        has_multi = isinstance(data.columns, pd.MultiIndex)
        if not has_multi and len(symbols) == 1:
            s = data["Close"].dropna()
            if not s.empty:
                if s.index.tz is not None:
                    s.index = s.index.tz_localize(None)
                result[symbols[0]] = s
        elif has_multi:
            available = set(data.columns.get_level_values(0).unique())
            for sym in symbols:
                if sym in available:
                    try:
                        s = data[sym]["Close"].dropna()
                        if not s.empty:
                            if s.index.tz is not None:
                                s.index = s.index.tz_localize(None)
                            result[sym] = s
                    except Exception:
                        continue
    except Exception as e:
        logger.error(f"Batch download failed: {e}")
    return result


def _compute_risk(nifty_close, nifty_200, nifty_50, vix, sp_above_200, gold_above_50):
    """Simplified risk score from available historical data."""
    risk = 0.0
    if nifty_close < nifty_200:
        risk += 12.0
    elif nifty_200 > 0 and (nifty_close - nifty_200) / nifty_200 * 100 < 2:
        risk += 4.0
    if nifty_close < nifty_50:
        risk += 8.0
    if vix > settings.VIX_HIGH:
        risk += 10.0
    elif vix > settings.VIX_ELEVATED:
        risk += 5.0
    if not sp_above_200:
        risk += 6.0
    if gold_above_50:
        risk += 8.0
    return min(risk, 100.0)


def _rank_momentum(stock_data: dict[str, pd.Series], as_of_date: pd.Timestamp) -> list[str]:
    """
    Rank stocks by risk-adjusted momentum (6-month return, skip last month).
    Returns top N symbols sorted by momentum score.
    """
    scores = {}
    for sym, series in stock_data.items():
        mask = series.index <= as_of_date
        s = series[mask]
        if len(s) < MOMENTUM_LOOKBACK:
            continue
        # 6-month return, skip last 1 month
        end_idx = len(s) - MOMENTUM_SKIP
        start_idx = end_idx - (MOMENTUM_LOOKBACK - MOMENTUM_SKIP)
        if start_idx < 0 or end_idx < 1:
            continue
        p_end = s.iloc[end_idx]
        p_start = s.iloc[start_idx]
        if p_start <= 0:
            continue
        raw_return = (p_end - p_start) / p_start

        # Volatility adjustment: divide by recent volatility
        recent = s.iloc[max(0, end_idx - 63):end_idx]
        if len(recent) < 20:
            continue
        vol = recent.pct_change().std()
        if vol <= 0:
            continue
        momentum_score = raw_return / vol
        scores[sym] = momentum_score

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [sym for sym, _ in ranked[:NUM_MOMENTUM_PICKS]]


def run_allocation_backtest(
    years: int = 5,
    initial_capital: float = None,
    rebalance_freq: str = "monthly",
    use_deployment_scores: bool = True,
) -> AllocBacktestResult:
    """
    Run a historical backtest with momentum stock picking + regime allocation.
    """
    if initial_capital is None:
        initial_capital = settings.INITIAL_CAPITAL

    end_dt = datetime.now()
    start_dt = end_dt - timedelta(days=years * 365 + 250)  # extra for warmup
    start_str = start_dt.strftime("%Y-%m-%d")
    end_str = end_dt.strftime("%Y-%m-%d")

    logger.info(f"[BACKTEST] Fetching market data {start_str} to {end_str}...")

    # ── Fetch market indicators ──
    nifty = _fetch_series(settings.NIFTY_SYMBOL, start_str, end_str)
    vix = _fetch_series(settings.VIX_SYMBOL, start_str, end_str)
    sp500 = _fetch_series(settings.SP500_SYMBOL, start_str, end_str)
    gold = _fetch_series(settings.GOLD_ETF_SYMBOL, start_str, end_str)

    if nifty is None:
        raise ValueError("Could not fetch NIFTY data for backtest")

    # ── Fetch momentum universe stocks ──
    logger.info(f"[BACKTEST] Downloading {len(MOMENTUM_UNIVERSE)} stocks...")
    stock_data = _download_batch(MOMENTUM_UNIVERSE, start_str, end_str)
    logger.info(f"[BACKTEST] Got data for {len(stock_data)} stocks")

    if len(stock_data) < 10:
        raise ValueError(f"Only got data for {len(stock_data)} stocks, need at least 10")

    # ── Compute moving averages ──
    nifty_200 = nifty.rolling(200).mean()
    nifty_50 = nifty.rolling(50).mean()
    sp500_200 = sp500.rolling(200).mean() if sp500 is not None else None
    gold_50 = gold.rolling(50).mean() if gold is not None else None

    # ── Valid trading dates (after warmup) ──
    actual_start = end_dt - timedelta(days=years * 365)
    valid_start = max(
        nifty_200.dropna().index[0] if len(nifty_200.dropna()) else nifty.index[200],
        pd.Timestamp(actual_start)
    )
    dates = nifty.index[nifty.index >= valid_start]

    if len(dates) < 50:
        raise ValueError("Not enough trading days for backtest")

    # ── State tracking ──
    prev_regime = None
    regime_changes = 0
    regime_time: dict[str, int] = {}

    # Portfolio state
    cash = initial_capital
    gold_units = 0.0  # number of gold ETF units
    positions: dict[str, dict] = {}  # {sym: {shares, entry_price, peak_price}}
    current_picks: list[str] = []
    last_rebalance_idx = -999
    target_alloc = REGIME_ALLOCATION["NEUTRAL"]

    # Tracking
    curve: list[AllocBacktestPoint] = []
    daily_returns: list[float] = []
    prev_total = initial_capital
    peak = initial_capital
    max_dd = 0.0
    last_week = None

    logger.info(f"[BACKTEST] Running simulation over {len(dates)} trading days...")

    for i, dt in enumerate(dates):
        n_close = nifty.get(dt, np.nan)
        n_200 = nifty_200.get(dt, np.nan)
        n_50 = nifty_50.get(dt, np.nan)
        v = vix.get(dt, 15.0) if vix is not None else 15.0
        sp_val = sp500.get(dt, np.nan) if sp500 is not None else np.nan
        sp_200_val = sp500_200.get(dt, np.nan) if sp500_200 is not None else np.nan
        g_val = gold.get(dt, np.nan) if gold is not None else np.nan
        g_50 = gold_50.get(dt, np.nan) if gold_50 is not None else np.nan

        if pd.isna(n_close) or pd.isna(n_200):
            continue

        sp_above = bool(sp_val > sp_200_val) if not pd.isna(sp_val) and not pd.isna(sp_200_val) else True
        g_above = bool(g_val > g_50) if not pd.isna(g_val) and not pd.isna(g_50) else False

        # ── Regime detection ──
        risk = _compute_risk(n_close, n_200, n_50, v, sp_above, g_above)
        regime = classify_regime(risk)
        regime_time[regime] = regime_time.get(regime, 0) + 1

        if regime != prev_regime:
            if prev_regime is not None:
                regime_changes += 1
            target_alloc = REGIME_ALLOCATION.get(regime, REGIME_ALLOCATION["NEUTRAL"])
            prev_regime = regime

        # ── Daily PnL update for existing positions ──
        equity_value = 0.0
        stopped_out = []
        for sym, pos in positions.items():
            sd = stock_data.get(sym)
            if sd is None:
                equity_value += pos["shares"] * pos["entry_price"]
                continue
            current_price = sd.get(dt, np.nan)
            if pd.isna(current_price):
                # Use last known price
                mask = sd.index <= dt
                if mask.any():
                    current_price = sd[mask].iloc[-1]
                else:
                    current_price = pos["entry_price"]

            # Update peak price for trailing stop
            if current_price > pos["peak_price"]:
                pos["peak_price"] = current_price

            # Check trailing stop
            stop_price = pos["peak_price"] * (1 - TRAILING_STOP_PCT)
            if current_price <= stop_price:
                # Stopped out — sell
                sale_value = pos["shares"] * current_price
                cash += sale_value
                stopped_out.append(sym)
            else:
                equity_value += pos["shares"] * current_price

        for sym in stopped_out:
            del positions[sym]

        # ── Gold value ──
        gold_value = 0.0
        if gold_units > 0 and gold is not None:
            gp = gold.get(dt, np.nan)
            if pd.isna(gp):
                mask = gold.index <= dt
                if mask.any():
                    gp = gold[mask].iloc[-1]
                else:
                    gp = 0
            gold_value = gold_units * gp

        # Cash earns risk-free rate daily (6% annual)
        cash *= (1 + 0.06 / 252)

        total = equity_value + gold_value + cash

        # ── Rebalance check (monthly or regime change) ──
        should_rebalance = (
            (i - last_rebalance_idx >= REBALANCE_FREQ_DAYS) or
            (i == 0)
        )

        if should_rebalance:
            last_rebalance_idx = i

            # 1. Liquidate all stock positions
            for sym, pos in positions.items():
                sd = stock_data.get(sym)
                if sd is None:
                    cash += pos["shares"] * pos["entry_price"]
                    continue
                cp = sd.get(dt, np.nan)
                if pd.isna(cp):
                    mask = sd.index <= dt
                    cp = sd[mask].iloc[-1] if mask.any() else pos["entry_price"]
                cash += pos["shares"] * cp
            positions.clear()

            # 2. Sell gold
            if gold_units > 0 and gold is not None:
                gp = gold.get(dt, np.nan)
                if pd.isna(gp):
                    mask = gold.index <= dt
                    if mask.any():
                        gp = gold[mask].iloc[-1]
                cash += gold_units * gp if not pd.isna(gp) else 0
                gold_units = 0

            total = cash  # everything in cash now

            # 3. Allocate to equity / gold / cash
            eq_pct = target_alloc["equity"] / 100
            gold_pct = target_alloc["gold"] / 100
            cash_pct = target_alloc["cash"] / 100

            eq_budget = total * eq_pct
            gold_budget = total * gold_pct
            cash = total * cash_pct

            # 4. Buy gold ETF
            if gold_budget > 0 and gold is not None:
                gp = gold.get(dt, np.nan)
                if not pd.isna(gp) and gp > 0:
                    gold_units = gold_budget / gp

            # 5. Select top momentum stocks and buy
            if eq_budget > 100:  # only if meaningful amount
                current_picks = _rank_momentum(stock_data, dt)
                if current_picks:
                    per_stock = eq_budget / len(current_picks)
                    for sym in current_picks:
                        sd = stock_data.get(sym)
                        if sd is None:
                            cash += per_stock
                            continue
                        cp = sd.get(dt, np.nan)
                        if pd.isna(cp):
                            mask = sd.index <= dt
                            cp = sd[mask].iloc[-1] if mask.any() else np.nan
                        if pd.isna(cp) or cp <= 0:
                            cash += per_stock
                            continue
                        shares = per_stock / cp  # fractional shares OK for backtest
                        positions[sym] = {
                            "shares": shares,
                            "entry_price": cp,
                            "peak_price": cp,
                        }
                else:
                    cash += eq_budget  # no picks available

            # Recalculate total
            equity_value = sum(
                pos["shares"] * stock_data[sym].get(dt, pos["entry_price"])
                for sym, pos in positions.items()
                if sym in stock_data
            )
            gold_value = gold_units * (gold.get(dt, 0) if gold is not None else 0)
            total = equity_value + gold_value + cash

        # ── Track metrics ──
        if total > peak:
            peak = total
        dd = ((peak - total) / peak) * 100 if peak > 0 else 0
        max_dd = max(max_dd, dd)

        if prev_total > 0:
            daily_returns.append((total - prev_total) / prev_total)
        prev_total = total

        # ── Weekly curve sample ──
        week = dt.isocalendar()[1]
        if last_week is None or week != last_week:
            last_week = week
            curve.append(AllocBacktestPoint(
                date=dt.strftime("%Y-%m-%d"),
                regime=regime,
                risk_score=round(risk, 1),
                equity_value=round(equity_value, 2),
                gold_value=round(gold_value, 2),
                cash_value=round(cash, 2),
                total_value=round(total, 2),
            ))

    # ── Final liquidation ──
    final_equity = 0
    for sym, pos in positions.items():
        sd = stock_data.get(sym)
        if sd is not None and len(sd) > 0:
            final_equity += pos["shares"] * sd.iloc[-1]
        else:
            final_equity += pos["shares"] * pos["entry_price"]

    final_gold = 0
    if gold_units > 0 and gold is not None and len(gold) > 0:
        final_gold = gold_units * gold.iloc[-1]

    final = final_equity + final_gold + cash

    # ── Metrics ──
    total_return = ((final - initial_capital) / initial_capital) * 100
    trading_days = len(dates)
    years_actual = trading_days / 252 if trading_days else 1
    cagr = ((final / initial_capital) ** (1 / years_actual) - 1) * 100 if initial_capital > 0 and years_actual > 0 else 0

    dr = np.array(daily_returns) if daily_returns else np.array([0.0])
    ann_vol = float(np.std(dr) * np.sqrt(252) * 100) if len(dr) > 1 else 0.0
    risk_free_daily = 0.06 / 252
    excess = dr - risk_free_daily
    sharpe = float(np.mean(excess) / np.std(excess) * np.sqrt(252)) if np.std(excess) > 0 else 0.0
    downside = dr[dr < 0]
    sortino = float(np.mean(excess) / np.std(downside) * np.sqrt(252)) if len(downside) > 0 and np.std(downside) > 0 else 0.0

    # Benchmark: buy-and-hold NIFTY
    if nifty is not None and len(dates) > 0:
        first = nifty.get(dates[0], np.nan)
        last = nifty.get(dates[-1], np.nan)
        bm_return = ((last - first) / first) * 100 if not pd.isna(first) and first > 0 and not pd.isna(last) else 0.0
    else:
        bm_return = 0.0

    total_days = sum(regime_time.values()) or 1
    regime_pct = {k: round(v / total_days * 100, 1) for k, v in regime_time.items()}

    logger.info(
        f"[BACKTEST] Done — Final: ₹{final:.2f}, Return: {total_return:.1f}%, "
        f"CAGR: {cagr:.1f}%, Max DD: {max_dd:.1f}%, Sharpe: {sharpe:.2f}"
    )

    return AllocBacktestResult(
        start_date=dates[0].strftime("%Y-%m-%d") if len(dates) else start_str,
        end_date=dates[-1].strftime("%Y-%m-%d") if len(dates) else end_str,
        initial_capital=initial_capital,
        final_capital=round(final, 2),
        total_return_pct=round(total_return, 2),
        cagr=round(cagr, 2),
        max_drawdown_pct=round(max_dd, 2),
        annualised_volatility=round(ann_vol, 2),
        sharpe_ratio=round(sharpe, 2),
        sortino_ratio=round(sortino, 2),
        regime_changes=regime_changes,
        time_in_regimes=regime_pct,
        benchmark_return_pct=round(bm_return, 2),
        curve=curve,
    )
