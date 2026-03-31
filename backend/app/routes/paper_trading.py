"""
Paper Trading routes.

Virtual paper trading system with:
- Virtual portfolio with configurable starting capital
- Buy/sell simulation with real market prices
- P&L tracking, win rate, performance metrics
- No real money involved — pure simulation
"""

import logging
import json
from datetime import datetime, date
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(tags=["paper-trading"])

# In-memory paper trading state (persists during server lifetime)
_paper_state = {
    "capital": 100000.0,
    "initial_capital": 100000.0,
    "positions": [],  # open positions
    "closed_trades": [],  # history
    "cash": 100000.0,
}


class PaperTradeRequest(BaseModel):
    symbol: str
    action: str  # BUY or SELL
    quantity: int
    price: Optional[float] = None  # if None, fetch live


class PaperResetRequest(BaseModel):
    capital: float = 100000.0


def _get_live_price(symbol: str) -> float:
    """Get latest price for a symbol."""
    try:
        import yfinance as yf
        suffix = ".NS" if not symbol.endswith((".NS", ".BO")) else ""
        ticker = yf.Ticker(f"{symbol}{suffix}")
        hist = ticker.history(period="1d")
        if not hist.empty:
            return float(hist["Close"].iloc[-1])
    except Exception as e:
        logger.warning(f"Price fetch failed for {symbol}: {e}")
    raise HTTPException(400, f"Could not fetch price for {symbol}")


@router.post("/api/paper/trade")
async def paper_trade(req: PaperTradeRequest):
    """Execute a paper trade."""
    symbol = req.symbol.upper().replace(".NS", "").replace(".BO", "")
    price = req.price or _get_live_price(symbol)

    if req.action.upper() == "BUY":
        cost = price * req.quantity
        if cost > _paper_state["cash"]:
            raise HTTPException(400, f"Insufficient cash. Need ₹{cost:,.0f}, have ₹{_paper_state['cash']:,.0f}")

        _paper_state["cash"] -= cost
        # Check if already have position in this symbol
        existing = next((p for p in _paper_state["positions"] if p["symbol"] == symbol), None)
        if existing:
            # Average up/down
            total_qty = existing["quantity"] + req.quantity
            total_cost = existing["avg_price"] * existing["quantity"] + price * req.quantity
            existing["avg_price"] = total_cost / total_qty
            existing["quantity"] = total_qty
            existing["invested"] = total_cost
        else:
            _paper_state["positions"].append({
                "symbol": symbol,
                "quantity": req.quantity,
                "avg_price": price,
                "invested": cost,
                "entry_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            })

        return {
            "status": "BOUGHT",
            "symbol": symbol,
            "quantity": req.quantity,
            "price": price,
            "cost": cost,
            "cash_remaining": _paper_state["cash"],
        }

    elif req.action.upper() == "SELL":
        position = next((p for p in _paper_state["positions"] if p["symbol"] == symbol), None)
        if not position:
            raise HTTPException(400, f"No open position in {symbol}")
        if req.quantity > position["quantity"]:
            raise HTTPException(400, f"Insufficient quantity. Have {position['quantity']}, trying to sell {req.quantity}")

        proceeds = price * req.quantity
        pnl = (price - position["avg_price"]) * req.quantity
        pnl_pct = ((price / position["avg_price"]) - 1) * 100

        _paper_state["cash"] += proceeds

        # Record closed trade
        _paper_state["closed_trades"].append({
            "symbol": symbol,
            "quantity": req.quantity,
            "entry_price": position["avg_price"],
            "exit_price": price,
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl_pct, 2),
            "entry_date": position["entry_date"],
            "exit_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        })

        # Update or remove position
        if req.quantity >= position["quantity"]:
            _paper_state["positions"] = [p for p in _paper_state["positions"] if p["symbol"] != symbol]
        else:
            position["quantity"] -= req.quantity
            position["invested"] = position["avg_price"] * position["quantity"]

        return {
            "status": "SOLD",
            "symbol": symbol,
            "quantity": req.quantity,
            "price": price,
            "proceeds": proceeds,
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl_pct, 2),
            "cash_remaining": _paper_state["cash"],
        }

    else:
        raise HTTPException(400, "Action must be BUY or SELL")


@router.get("/api/paper/portfolio")
async def paper_portfolio():
    """Get paper trading portfolio with live P&L."""
    positions_with_pnl = []
    total_invested = 0
    total_current = 0

    for pos in _paper_state["positions"]:
        try:
            current_price = _get_live_price(pos["symbol"])
        except Exception:
            current_price = pos["avg_price"]

        current_value = current_price * pos["quantity"]
        pnl = (current_price - pos["avg_price"]) * pos["quantity"]
        pnl_pct = ((current_price / pos["avg_price"]) - 1) * 100

        total_invested += pos["invested"]
        total_current += current_value

        positions_with_pnl.append({
            **pos,
            "current_price": round(current_price, 2),
            "current_value": round(current_value, 2),
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl_pct, 2),
        })

    # Calculate stats from closed trades
    closed = _paper_state["closed_trades"]
    winners = [t for t in closed if t["pnl"] > 0]
    losers = [t for t in closed if t["pnl"] <= 0]
    total_pnl = sum(t["pnl"] for t in closed)
    unrealized_pnl = total_current - total_invested

    total_equity = _paper_state["cash"] + total_current

    return {
        "cash": round(_paper_state["cash"], 2),
        "initial_capital": _paper_state["initial_capital"],
        "total_equity": round(total_equity, 2),
        "total_invested": round(total_invested, 2),
        "unrealized_pnl": round(unrealized_pnl, 2),
        "realized_pnl": round(total_pnl, 2),
        "total_return_pct": round(((total_equity / _paper_state["initial_capital"]) - 1) * 100, 2),
        "positions": positions_with_pnl,
        "positions_count": len(positions_with_pnl),
        "stats": {
            "total_trades": len(closed),
            "winners": len(winners),
            "losers": len(losers),
            "win_rate": round(len(winners) / len(closed) * 100, 1) if closed else 0,
            "avg_win": round(sum(t["pnl"] for t in winners) / len(winners), 2) if winners else 0,
            "avg_loss": round(sum(t["pnl"] for t in losers) / len(losers), 2) if losers else 0,
            "best_trade": max((t["pnl"] for t in closed), default=0),
            "worst_trade": min((t["pnl"] for t in closed), default=0),
        },
        "closed_trades": list(reversed(closed[-20:])),  # last 20
    }


@router.post("/api/paper/reset")
async def paper_reset(req: PaperResetRequest):
    """Reset paper trading account."""
    _paper_state["capital"] = req.capital
    _paper_state["initial_capital"] = req.capital
    _paper_state["cash"] = req.capital
    _paper_state["positions"] = []
    _paper_state["closed_trades"] = []
    return {"status": "RESET", "capital": req.capital}
