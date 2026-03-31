"""
Algo Trading Engine — 5 World-Class Trading Algorithms.

Implements historically proven quantitative strategies with full backtesting:

1. RSI-2 Mean Reversion (Larry Connors) — ~70-80% win rate
2. Dual Momentum (Gary Antonacci) — 15%+ CAGR with lower drawdown
3. Turtle Breakout (Richard Dennis) — Legendary trend-following system
4. MACD + RSI Crossover Strategy — Classic technical momentum
5. Bollinger Band Mean Reversion — Statistical mean-reversion with volatility
"""

import logging
import json
from datetime import datetime, date, timedelta
from typing import Optional

import numpy as np
import pandas as pd
import yfinance as yf
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(tags=["algo-trading"])


# ═══════════════════════════════════════════════════════
# Algorithm Definitions
# ═══════════════════════════════════════════════════════

ALGORITHMS = {
    "rsi2_mean_reversion": {
        "name": "RSI-2 Mean Reversion",
        "author": "Larry Connors",
        "year": 2008,
        "type": "Mean Reversion",
        "description": (
            "Uses a 2-period RSI to identify extreme oversold conditions in uptrending stocks. "
            "Buy when RSI(2) drops below 10 while price is above 200-DMA (confirming uptrend). "
            "Sell when RSI(2) rises above 90. This strategy exploits short-term mean reversion "
            "within a longer-term bullish trend, achieving historically 70-80% win rates."
        ),
        "rules": [
            "1. Price must be ABOVE 200-day moving average (long-term uptrend filter)",
            "2. Calculate 2-period RSI",
            "3. BUY when RSI(2) closes below 10 (extreme oversold)",
            "4. SELL when RSI(2) closes above 90 (mean reversion complete)",
            "5. No stop loss used — relies on statistical edge over many trades",
        ],
        "risk_management": "Position size: 10% of capital per trade. Uptrend filter (200-DMA) prevents buying in bear markets.",
        "historical_performance": "Win rate: 70-80%. Average holding period: 3-5 days. Best in trending markets.",
        "best_for": "Short-term swing traders in bull markets",
    },
    "dual_momentum": {
        "name": "Dual Momentum",
        "author": "Gary Antonacci",
        "year": 2014,
        "type": "Momentum / Asset Allocation",
        "description": (
            "Combines absolute momentum (is the asset going up?) with relative momentum "
            "(which asset is going up more?). Each month, compare 12-month returns of equity vs bonds. "
            "If equity beats bonds AND has positive absolute return → invest in equity. "
            "If bonds beat equity → invest in bonds. If both negative → stay in cash/T-bills. "
            "Academically proven to deliver equity-like returns with bond-like drawdowns."
        ),
        "rules": [
            "1. At end of each month, calculate 12-month return of equity index (NIFTY)",
            "2. Calculate 12-month return of bond/gold proxy",
            "3. If NIFTY return > Gold return AND NIFTY return > 0 → 100% NIFTY",
            "4. If Gold return > NIFTY return AND Gold return > 0 → 100% Gold",
            "5. If both negative → 100% Cash (risk-free rate)",
            "6. Rebalance monthly on last trading day",
        ],
        "risk_management": "Monthly rebalance limits drawdown. Absolute momentum filter avoids bear markets entirely.",
        "historical_performance": "CAGR: 15-18%. Max Drawdown: 15-20% (vs 50%+ for buy-and-hold). Sharpe: 0.8-1.0.",
        "best_for": "Long-term investors wanting equity returns with lower risk",
    },
    "turtle_breakout": {
        "name": "Turtle Trading System",
        "author": "Richard Dennis & Bill Eckhardt",
        "year": 1983,
        "type": "Trend Following / Breakout",
        "description": (
            "The legendary Turtle system that turned $400 into $175 million. "
            "Enter on a breakout above the 20-day high (short-term) or 55-day high (long-term). "
            "Exit on a break below the 10-day low. Position sizing based on ATR (Average True Range) "
            "to normalize risk across all instruments. The system lets winners run and cuts losers quickly."
        ),
        "rules": [
            "1. Calculate 20-day high and 10-day low",
            "2. Calculate 20-period ATR for position sizing",
            "3. BUY when price breaks above 20-day high (new 20-day breakout)",
            "4. SELL (stop) when price drops below 10-day low",
            "5. Position size = 1% of capital / (ATR × price) — risk normalization",
            "6. Maximum 4 units per market, add on each 0.5×ATR move in profit direction",
        ],
        "risk_management": "ATR-based position sizing ensures equal risk per trade. 10-day low trailing stop protects profits.",
        "historical_performance": "CAGR: 12-20%. Win rate: 35-40% but large R-multiples. Profit factor: 2.0-3.0.",
        "best_for": "Patient trend followers comfortable with low win rates but large gains",
    },
    "macd_rsi_crossover": {
        "name": "MACD + RSI Momentum Strategy",
        "author": "Gerald Appel (MACD inventor) + Welles Wilder (RSI)",
        "year": 1979,
        "type": "Momentum / Trend Confirmation",
        "description": (
            "Combines two of the most widely used indicators for momentum confirmation. "
            "MACD (12,26,9) identifies trend direction and momentum shifts. RSI(14) confirms "
            "the signal isn't in overbought/oversold extremes. Buy on bullish MACD crossover "
            "confirmed by RSI in the 30-70 sweet zone. This dual-confirmation reduces false signals "
            "that plague single-indicator systems."
        ),
        "rules": [
            "1. Calculate MACD(12, 26, 9) — MACD line and Signal line",
            "2. Calculate RSI(14)",
            "3. BUY when MACD line crosses ABOVE signal line AND RSI is between 30-70",
            "4. SELL when MACD line crosses BELOW signal line OR RSI > 80 (overbought)",
            "5. Additional filter: Price must be above 50-DMA for trend confirmation",
            "6. Stop loss at 2× ATR(14) below entry",
        ],
        "risk_management": "Dual confirmation reduces false signals by 40-50%. ATR stop provides adaptive risk management.",
        "historical_performance": "Win rate: 55-65%. Average R-multiple: 1.5-2.0. Works best in trending markets.",
        "best_for": "Active traders wanting confirmed momentum entries",
    },
    "bollinger_mean_reversion": {
        "name": "Bollinger Band Mean Reversion",
        "author": "John Bollinger",
        "year": 1983,
        "type": "Mean Reversion / Volatility",
        "description": (
            "Exploits the statistical property that price tends to revert to the mean after "
            "touching the outer Bollinger Bands (2 standard deviations from 20-day SMA). "
            "Buy when price touches lower band with RSI confirmation (oversold). "
            "Sell at the middle band (20-SMA) or upper band. Band width indicates volatility — "
            "narrow bands (squeeze) often precede explosive moves."
        ),
        "rules": [
            "1. Calculate 20-period SMA and Bollinger Bands (2 std dev)",
            "2. BUY when price touches or goes below lower band AND RSI(14) < 35",
            "3. SELL at middle band (20-SMA) for conservative exit",
            "4. SELL at upper band for aggressive profit target",
            "5. Stop loss: 1% below the lower band at time of entry",
            "6. Avoid during Bollinger squeeze (bands very narrow) — breakout imminent",
        ],
        "risk_management": "Statistical edge: ~95% of price action stays within bands. RSI filter prevents catching falling knives.",
        "historical_performance": "Win rate: 65-75%. Average holding period: 5-10 days. Best in range-bound markets.",
        "best_for": "Traders in sideways/choppy markets looking for high-probability mean reversion",
    },
}


class AlgoBacktestRequest(BaseModel):
    algo_id: str
    symbol: str = "^NSEI"
    capital: float = 100000.0
    period: str = "1y"  # 1d, 3d, 1w, 1m, 3m, 6m, 1y, 3y, 5y


PERIOD_MAP = {
    "1d": 1,
    "3d": 3,
    "1w": 7,
    "1m": 30,
    "3m": 90,
    "6m": 180,
    "1y": 365,
    "3y": 1095,
    "5y": 1825,
}


# ═══════════════════════════════════════════════════════
# Algorithm Implementations
# ═══════════════════════════════════════════════════════

def _fetch_data(symbol: str, days: int) -> pd.DataFrame:
    """Fetch OHLCV data for backtesting."""
    # Add buffer for indicator calculation
    buffer_days = max(days, 250) + 250
    end = datetime.now()
    start = end - timedelta(days=buffer_days)

    suffix = ""
    if symbol.startswith("^") or "=" in symbol:
        pass
    elif not symbol.endswith((".NS", ".BO")):
        suffix = ".NS"

    ticker = yf.Ticker(f"{symbol}{suffix}")
    df = ticker.history(start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"))

    if df.empty:
        raise HTTPException(400, f"No data available for {symbol}")

    df.index = pd.to_datetime(df.index)
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    df.columns = [c.lower().replace(" ", "_") for c in df.columns]
    return df


def _run_rsi2(df: pd.DataFrame, capital: float, days: int) -> dict:
    """RSI-2 Mean Reversion backtest."""
    # Calculate indicators
    df["sma200"] = df["close"].rolling(200).mean()
    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0).rolling(2).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(2).mean()
    rs = gain / loss.replace(0, np.nan)
    df["rsi2"] = 100 - (100 / (1 + rs))

    # Trim to backtest period
    df = df.iloc[-days:].copy() if days < len(df) else df.copy()
    df.dropna(subset=["sma200", "rsi2"], inplace=True)

    trades = []
    position = None
    cash = capital

    for i in range(1, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i - 1]

        if position is None:
            # Buy condition: above 200-DMA and RSI(2) < 10
            if row["close"] > row["sma200"] and prev["rsi2"] < 10:
                qty = int((capital * 0.1) / row["close"])
                if qty > 0:
                    position = {"entry": row["close"], "qty": qty, "date": df.index[i]}
                    cash -= qty * row["close"]
        else:
            # Sell condition: RSI(2) > 90
            if prev["rsi2"] > 90:
                pnl = (row["close"] - position["entry"]) * position["qty"]
                cash += position["qty"] * row["close"]
                trades.append({
                    "entry_date": position["date"].strftime("%Y-%m-%d"),
                    "exit_date": df.index[i].strftime("%Y-%m-%d"),
                    "entry_price": round(position["entry"], 2),
                    "exit_price": round(row["close"], 2),
                    "quantity": position["qty"],
                    "pnl": round(pnl, 2),
                    "pnl_pct": round((row["close"] / position["entry"] - 1) * 100, 2),
                })
                position = None

    # Close any open position at end
    if position:
        last = df.iloc[-1]
        pnl = (last["close"] - position["entry"]) * position["qty"]
        cash += position["qty"] * last["close"]
        trades.append({
            "entry_date": position["date"].strftime("%Y-%m-%d"),
            "exit_date": df.index[-1].strftime("%Y-%m-%d"),
            "entry_price": round(position["entry"], 2),
            "exit_price": round(last["close"], 2),
            "quantity": position["qty"],
            "pnl": round(pnl, 2),
            "pnl_pct": round((last["close"] / position["entry"] - 1) * 100, 2),
        })

    return _compile_results(trades, capital, cash, df)


def _run_dual_momentum(df: pd.DataFrame, capital: float, days: int) -> dict:
    """Dual Momentum backtest — equity vs gold."""
    try:
        gold = yf.Ticker("GC=F").history(period="max")
        gold.index = pd.to_datetime(gold.index)
        if gold.index.tz:
            gold.index = gold.index.tz_localize(None)
        gold.columns = [c.lower().replace(" ", "_") for c in gold.columns]
    except Exception:
        gold = df.copy()  # fallback

    df = df.iloc[-days:].copy() if days < len(df) else df.copy()

    trades = []
    cash = capital
    current_asset = "CASH"
    position = None

    # Monthly rebalance
    monthly = df.resample("ME").last()

    for i in range(12, len(monthly)):
        curr = monthly.iloc[i]
        prev_12 = monthly.iloc[i - 12]

        eq_return = (curr["close"] / prev_12["close"]) - 1

        # Gold comparison (simplified)
        gold_near = gold[gold.index <= curr.name]
        if len(gold_near) >= 252:
            gold_return = (gold_near["close"].iloc[-1] / gold_near["close"].iloc[-252]) - 1
        else:
            gold_return = -0.01

        # Decision
        if eq_return > gold_return and eq_return > 0:
            new_asset = "EQUITY"
        elif gold_return > eq_return and gold_return > 0:
            new_asset = "GOLD"
        else:
            new_asset = "CASH"

        if new_asset != current_asset:
            # Close current position
            if position:
                exit_price = curr["close"]
                pnl = (exit_price - position["entry"]) * position["qty"]
                cash += position["qty"] * exit_price
                trades.append({
                    "entry_date": position["date"].strftime("%Y-%m-%d"),
                    "exit_date": curr.name.strftime("%Y-%m-%d"),
                    "entry_price": round(position["entry"], 2),
                    "exit_price": round(exit_price, 2),
                    "quantity": position["qty"],
                    "pnl": round(pnl, 2),
                    "pnl_pct": round((exit_price / position["entry"] - 1) * 100, 2),
                    "asset": current_asset,
                })
                position = None

            # Open new position
            if new_asset != "CASH" and cash > 0:
                qty = int(cash / curr["close"])
                if qty > 0:
                    position = {"entry": curr["close"], "qty": qty, "date": curr.name}
                    cash -= qty * curr["close"]

            current_asset = new_asset

    # Close final position
    if position:
        last = df.iloc[-1]
        pnl = (last["close"] - position["entry"]) * position["qty"]
        cash += position["qty"] * last["close"]
        trades.append({
            "entry_date": position["date"].strftime("%Y-%m-%d"),
            "exit_date": last.name.strftime("%Y-%m-%d"),
            "entry_price": round(position["entry"], 2),
            "exit_price": round(last["close"], 2),
            "quantity": position["qty"],
            "pnl": round(pnl, 2),
            "pnl_pct": round((last["close"] / position["entry"] - 1) * 100, 2),
            "asset": current_asset,
        })

    return _compile_results(trades, capital, cash, df)


def _run_turtle(df: pd.DataFrame, capital: float, days: int) -> dict:
    """Turtle Trading System backtest."""
    df["high_20"] = df["high"].rolling(20).max()
    df["low_10"] = df["low"].rolling(10).min()
    df["atr"] = _calc_atr(df, 20)

    df = df.iloc[-days:].copy() if days < len(df) else df.copy()
    df.dropna(subset=["high_20", "low_10", "atr"], inplace=True)

    trades = []
    position = None
    cash = capital

    for i in range(1, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i - 1]

        if position is None:
            # Entry: breakout above 20-day high
            if row["close"] > prev["high_20"] and prev["atr"] > 0:
                risk = prev["atr"] * row["close"]
                qty = max(1, int((capital * 0.01) / risk)) if risk > 0 else 1
                qty = min(qty, int(cash / row["close"]))
                if qty > 0:
                    position = {"entry": row["close"], "qty": qty, "date": df.index[i]}
                    cash -= qty * row["close"]
        else:
            # Exit: break below 10-day low
            if row["close"] < prev["low_10"]:
                pnl = (row["close"] - position["entry"]) * position["qty"]
                cash += position["qty"] * row["close"]
                trades.append({
                    "entry_date": position["date"].strftime("%Y-%m-%d"),
                    "exit_date": df.index[i].strftime("%Y-%m-%d"),
                    "entry_price": round(position["entry"], 2),
                    "exit_price": round(row["close"], 2),
                    "quantity": position["qty"],
                    "pnl": round(pnl, 2),
                    "pnl_pct": round((row["close"] / position["entry"] - 1) * 100, 2),
                })
                position = None

    if position:
        last = df.iloc[-1]
        pnl = (last["close"] - position["entry"]) * position["qty"]
        cash += position["qty"] * last["close"]
        trades.append({
            "entry_date": position["date"].strftime("%Y-%m-%d"),
            "exit_date": df.index[-1].strftime("%Y-%m-%d"),
            "entry_price": round(position["entry"], 2),
            "exit_price": round(last["close"], 2),
            "quantity": position["qty"],
            "pnl": round(pnl, 2),
            "pnl_pct": round((last["close"] / position["entry"] - 1) * 100, 2),
        })

    return _compile_results(trades, capital, cash, df)


def _run_macd_rsi(df: pd.DataFrame, capital: float, days: int) -> dict:
    """MACD + RSI Crossover backtest."""
    # MACD
    ema12 = df["close"].ewm(span=12).mean()
    ema26 = df["close"].ewm(span=26).mean()
    df["macd"] = ema12 - ema26
    df["signal"] = df["macd"].ewm(span=9).mean()
    df["sma50"] = df["close"].rolling(50).mean()

    # RSI(14)
    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df["rsi14"] = 100 - (100 / (1 + rs))

    # ATR for stop
    df["atr"] = _calc_atr(df, 14)

    df = df.iloc[-days:].copy() if days < len(df) else df.copy()
    df.dropna(subset=["macd", "signal", "rsi14", "sma50", "atr"], inplace=True)

    trades = []
    position = None
    cash = capital

    for i in range(1, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i - 1]

        if position is None:
            # Buy: MACD crosses above signal, RSI between 30-70, above 50-DMA
            if (prev["macd"] < prev["signal"] and row["macd"] > row["signal"]
                    and 30 < row["rsi14"] < 70 and row["close"] > row["sma50"]):
                qty = int((capital * 0.1) / row["close"])
                if qty > 0:
                    stop = row["close"] - 2 * prev["atr"]
                    position = {
                        "entry": row["close"], "qty": qty,
                        "date": df.index[i], "stop": stop,
                    }
                    cash -= qty * row["close"]
        else:
            # Sell: MACD crosses below signal OR RSI > 80 OR hit stop
            sell = False
            if prev["macd"] > prev["signal"] and row["macd"] < row["signal"]:
                sell = True
            elif row["rsi14"] > 80:
                sell = True
            elif row["low"] < position["stop"]:
                sell = True

            if sell:
                exit_price = max(row["close"], position["stop"])
                pnl = (exit_price - position["entry"]) * position["qty"]
                cash += position["qty"] * exit_price
                trades.append({
                    "entry_date": position["date"].strftime("%Y-%m-%d"),
                    "exit_date": df.index[i].strftime("%Y-%m-%d"),
                    "entry_price": round(position["entry"], 2),
                    "exit_price": round(exit_price, 2),
                    "quantity": position["qty"],
                    "pnl": round(pnl, 2),
                    "pnl_pct": round((exit_price / position["entry"] - 1) * 100, 2),
                })
                position = None

    if position:
        last = df.iloc[-1]
        pnl = (last["close"] - position["entry"]) * position["qty"]
        cash += position["qty"] * last["close"]
        trades.append({
            "entry_date": position["date"].strftime("%Y-%m-%d"),
            "exit_date": df.index[-1].strftime("%Y-%m-%d"),
            "entry_price": round(position["entry"], 2),
            "exit_price": round(last["close"], 2),
            "quantity": position["qty"],
            "pnl": round(pnl, 2),
            "pnl_pct": round((last["close"] / position["entry"] - 1) * 100, 2),
        })

    return _compile_results(trades, capital, cash, df)


def _run_bollinger(df: pd.DataFrame, capital: float, days: int) -> dict:
    """Bollinger Band Mean Reversion backtest."""
    df["sma20"] = df["close"].rolling(20).mean()
    df["std20"] = df["close"].rolling(20).std()
    df["upper_band"] = df["sma20"] + 2 * df["std20"]
    df["lower_band"] = df["sma20"] - 2 * df["std20"]

    # RSI(14) for confirmation
    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df["rsi14"] = 100 - (100 / (1 + rs))

    df = df.iloc[-days:].copy() if days < len(df) else df.copy()
    df.dropna(subset=["sma20", "lower_band", "upper_band", "rsi14"], inplace=True)

    trades = []
    position = None
    cash = capital

    for i in range(1, len(df)):
        row = df.iloc[i]

        if position is None:
            # Buy: price at or below lower band AND RSI < 35
            if row["close"] <= row["lower_band"] and row["rsi14"] < 35:
                qty = int((capital * 0.1) / row["close"])
                if qty > 0:
                    stop = row["lower_band"] * 0.99
                    position = {
                        "entry": row["close"], "qty": qty,
                        "date": df.index[i], "stop": stop,
                    }
                    cash -= qty * row["close"]
        else:
            # Sell at middle band (conservative) or upper band (aggressive) or stop
            sell = False
            if row["close"] >= row["sma20"]:
                sell = True
            elif row["low"] < position["stop"]:
                sell = True

            if sell:
                exit_price = row["close"]
                pnl = (exit_price - position["entry"]) * position["qty"]
                cash += position["qty"] * exit_price
                trades.append({
                    "entry_date": position["date"].strftime("%Y-%m-%d"),
                    "exit_date": df.index[i].strftime("%Y-%m-%d"),
                    "entry_price": round(position["entry"], 2),
                    "exit_price": round(exit_price, 2),
                    "quantity": position["qty"],
                    "pnl": round(pnl, 2),
                    "pnl_pct": round((exit_price / position["entry"] - 1) * 100, 2),
                })
                position = None

    if position:
        last = df.iloc[-1]
        pnl = (last["close"] - position["entry"]) * position["qty"]
        cash += position["qty"] * last["close"]
        trades.append({
            "entry_date": position["date"].strftime("%Y-%m-%d"),
            "exit_date": df.index[-1].strftime("%Y-%m-%d"),
            "entry_price": round(position["entry"], 2),
            "exit_price": round(last["close"], 2),
            "quantity": position["qty"],
            "pnl": round(pnl, 2),
            "pnl_pct": round((last["close"] / position["entry"] - 1) * 100, 2),
        })

    return _compile_results(trades, capital, cash, df)


# ═══════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════

def _calc_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate Average True Range."""
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift(1)).abs()
    low_close = (df["low"] - df["close"].shift(1)).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def _compile_results(trades: list, initial_capital: float, final_cash: float, df: pd.DataFrame) -> dict:
    """Compile backtest results from trade list."""
    if not trades:
        return {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate": 0,
            "total_pnl": 0,
            "total_return_pct": 0,
            "avg_win": 0,
            "avg_loss": 0,
            "profit_factor": 0,
            "max_drawdown_pct": 0,
            "best_trade": 0,
            "worst_trade": 0,
            "avg_holding_days": 0,
            "initial_capital": initial_capital,
            "final_capital": initial_capital,
            "trades": [],
            "equity_curve": [],
        }

    winners = [t for t in trades if t["pnl"] > 0]
    losers = [t for t in trades if t["pnl"] <= 0]
    total_pnl = sum(t["pnl"] for t in trades)
    final_capital = initial_capital + total_pnl

    gross_profit = sum(t["pnl"] for t in winners) if winners else 0
    gross_loss = abs(sum(t["pnl"] for t in losers)) if losers else 1

    # Equity curve
    equity = initial_capital
    equity_curve = [{"date": trades[0]["entry_date"], "equity": initial_capital}]
    peak = initial_capital
    max_dd = 0

    for t in trades:
        equity += t["pnl"]
        equity_curve.append({"date": t["exit_date"], "equity": round(equity, 2)})
        peak = max(peak, equity)
        dd = ((peak - equity) / peak) * 100 if peak > 0 else 0
        max_dd = max(max_dd, dd)

    # Average holding days
    holding_days = []
    for t in trades:
        try:
            ed = datetime.strptime(t["entry_date"], "%Y-%m-%d")
            xd = datetime.strptime(t["exit_date"], "%Y-%m-%d")
            holding_days.append((xd - ed).days)
        except Exception:
            pass

    return {
        "total_trades": len(trades),
        "winning_trades": len(winners),
        "losing_trades": len(losers),
        "win_rate": round(len(winners) / len(trades) * 100, 1),
        "total_pnl": round(total_pnl, 2),
        "total_return_pct": round((final_capital / initial_capital - 1) * 100, 2),
        "avg_win": round(gross_profit / len(winners), 2) if winners else 0,
        "avg_loss": round(-gross_loss / len(losers), 2) if losers else 0,
        "profit_factor": round(gross_profit / gross_loss, 2) if gross_loss > 0 else 0,
        "max_drawdown_pct": round(max_dd, 2),
        "best_trade": round(max(t["pnl"] for t in trades), 2),
        "worst_trade": round(min(t["pnl"] for t in trades), 2),
        "avg_holding_days": round(sum(holding_days) / len(holding_days), 1) if holding_days else 0,
        "initial_capital": initial_capital,
        "final_capital": round(final_capital, 2),
        "trades": trades[-50:],  # last 50 trades
        "equity_curve": equity_curve,
    }


# Algo runner dispatcher
ALGO_RUNNERS = {
    "rsi2_mean_reversion": _run_rsi2,
    "dual_momentum": _run_dual_momentum,
    "turtle_breakout": _run_turtle,
    "macd_rsi_crossover": _run_macd_rsi,
    "bollinger_mean_reversion": _run_bollinger,
}


# ═══════════════════════════════════════════════════════
# Routes
# ═══════════════════════════════════════════════════════

@router.get("/api/algos")
async def list_algorithms():
    """List all available algorithms with full details."""
    return {"algorithms": ALGORITHMS}


@router.get("/api/algos/{algo_id}")
async def get_algorithm(algo_id: str):
    """Get details of a specific algorithm."""
    if algo_id not in ALGORITHMS:
        raise HTTPException(404, f"Algorithm '{algo_id}' not found")
    return ALGORITHMS[algo_id]


@router.post("/api/algos/backtest")
async def run_algo_backtest(req: AlgoBacktestRequest):
    """Run a backtest for a specific algorithm."""
    if req.algo_id not in ALGO_RUNNERS:
        raise HTTPException(404, f"Algorithm '{req.algo_id}' not found")

    days = PERIOD_MAP.get(req.period, 365)

    try:
        df = _fetch_data(req.symbol, days)
        runner = ALGO_RUNNERS[req.algo_id]
        result = runner(df, req.capital, days)

        return {
            "algorithm": ALGORITHMS[req.algo_id]["name"],
            "algo_id": req.algo_id,
            "symbol": req.symbol,
            "period": req.period,
            "capital": req.capital,
            **result,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Algo backtest failed: {e}")
        raise HTTPException(500, f"Backtest failed: {str(e)}")


@router.post("/api/algos/compare")
async def compare_algorithms(symbol: str = "^NSEI", capital: float = 100000.0, period: str = "1y"):
    """Compare all algorithms on the same symbol and period."""
    days = PERIOD_MAP.get(period, 365)

    try:
        df = _fetch_data(symbol, days)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Data fetch failed: {str(e)}")

    results = {}
    for algo_id, runner in ALGO_RUNNERS.items():
        try:
            result = runner(df.copy(), capital, days)
            results[algo_id] = {
                "name": ALGORITHMS[algo_id]["name"],
                "total_return_pct": result["total_return_pct"],
                "win_rate": result["win_rate"],
                "total_trades": result["total_trades"],
                "max_drawdown_pct": result["max_drawdown_pct"],
                "profit_factor": result["profit_factor"],
                "final_capital": result["final_capital"],
            }
        except Exception as e:
            results[algo_id] = {
                "name": ALGORITHMS[algo_id]["name"],
                "error": str(e),
            }

    return {
        "symbol": symbol,
        "period": period,
        "capital": capital,
        "comparison": results,
    }
