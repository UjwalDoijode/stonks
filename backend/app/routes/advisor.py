"""Smart Money Advisor — personalized investment recommendations with specific stock names."""

import asyncio
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/advisor", tags=["Smart Advisor"])


@router.get("/recommend")
async def get_smart_recommendation(
    capital: float = Query(..., gt=0, description="Amount to invest (₹)"),
):
    """
    Smart Money Advisor: Given a capital amount, returns specific stock/ETF
    recommendations with exact quantities and amounts, considering real-time
    risk, geopolitics, market regime, AI prediction, and stock rankings.

    Returns SPECIFIC recommendations like:
    - "Buy 2 shares of SBIN at ₹1,201 (₹2,402)"
    - "Buy 10 units GOLDBEES at ₹131 (₹1,310)"
    - "Keep ₹16,880 in savings"
    """
    try:
        from app.strategy.macro_data import get_macro_snapshot
        from app.strategy.risk_engine import compute_risk_score
        from app.strategy.ai_risk_model import predict_risk, blend_risk_scores
        from app.strategy.stock_ranker import get_top_ranked
        from app.strategy.deployment_engine import compute_deployment
        from app.strategy.news_intelligence import fetch_news_intelligence
        from app.config import settings
        import yfinance as yf
        import math

        # 1. Real-time risk assessment
        macro = await asyncio.to_thread(get_macro_snapshot)
        risk = await asyncio.to_thread(compute_risk_score, macro)
        ai_pred = await asyncio.to_thread(predict_risk, macro)
        blended = blend_risk_scores(risk.total_risk_score, ai_pred)

        # 2. Geopolitical risk
        geo_data = None
        try:
            geo_data = await asyncio.to_thread(fetch_news_intelligence)
        except Exception:
            pass

        geo_risk_level = "LOW"
        geo_risk_score = 0
        active_conflicts = []
        if geo_data:
            geo_risk_score = getattr(geo_data, "news_risk_score", 0)
            active_conflicts = getattr(geo_data, "active_conflicts", [])
            if geo_risk_score >= 70:
                geo_risk_level = "EXTREME"
            elif geo_risk_score >= 50:
                geo_risk_level = "HIGH"
            elif geo_risk_score >= 30:
                geo_risk_level = "MODERATE"

        # 3. Stock ranking — get more stocks for better selection
        max_stocks = 10 if capital >= 50000 else 7 if capital >= 20000 else 5
        ranked = await asyncio.to_thread(
            get_top_ranked,
            n=max_stocks,
            universe_tier=settings.UNIVERSE_TIER,
            regime=risk.regime,
        )

        # 4. Compute deployment using user's custom capital
        plan = compute_deployment(
            risk=risk,
            capital=capital,
            ranked_stocks=ranked,
            ai_pred=ai_pred,
            previous_allocation=None,
            blended_risk_score=blended,
        )

        # 5. Fetch live commodity ETF prices for Gold/Silver recommendations
        commodity_prices = {}
        try:
            def _get_etf_prices():
                etfs = [settings.GOLD_ETF_SYMBOL, settings.SILVER_ETF_SYMBOL]
                data = yf.download(etfs, period="5d", group_by="ticker", threads=True, progress=False)
                prices = {}
                if data is not None and not data.empty:
                    import pandas as pd
                    has_multi = isinstance(data.columns, pd.MultiIndex)
                    for sym in etfs:
                        try:
                            if has_multi:
                                avail = set(data.columns.get_level_values(0).unique())
                                if sym not in avail:
                                    continue
                                df = data[sym].dropna(how="all")
                            else:
                                df = data
                            if df.empty:
                                continue
                            prices[sym] = round(float(df["Close"].iloc[-1]), 2)
                        except Exception:
                            continue
                return prices
            commodity_prices = await asyncio.to_thread(_get_etf_prices)
        except Exception:
            pass

        # 6. Build specific actionable recommendations
        recommendations = []
        total_invested = 0

        # --- Equity picks (specific stock names) ---
        for stock in plan.stock_picks:
            rec = {
                "type": "EQUITY",
                "action": "BUY",
                "symbol": stock.clean_symbol,
                "name": stock.clean_symbol,
                "instrument": f"{stock.clean_symbol}.NS",
                "price": stock.price,
                "quantity": stock.quantity,
                "amount": stock.amount,
                "weight_pct": stock.weight_pct,
                "reason": stock.reason,
                "rank_score": stock.rank_score,
                "confidence": "HIGH" if stock.rank_score >= 70 else "MEDIUM" if stock.rank_score >= 50 else "LOW",
            }
            recommendations.append(rec)
            total_invested += stock.amount

        # --- Gold allocation (specific ETF) ---
        gold_asset = next((a for a in plan.assets if a.asset == "Gold"), None)
        if gold_asset and gold_asset.amount >= 100:
            gold_price = commodity_prices.get(settings.GOLD_ETF_SYMBOL, 131.0)
            gold_qty = math.floor(gold_asset.amount / gold_price) if gold_price > 0 else 0
            gold_amount = gold_qty * gold_price if gold_qty > 0 else 0
            if gold_qty > 0:
                recommendations.append({
                    "type": "GOLD",
                    "action": "BUY",
                    "symbol": "GOLDBEES",
                    "name": "Nippon Gold ETF",
                    "instrument": settings.GOLD_ETF_SYMBOL,
                    "price": gold_price,
                    "quantity": gold_qty,
                    "amount": round(gold_amount, 2),
                    "weight_pct": gold_asset.allocation_pct,
                    "reason": f"Gold hedge — {plan.regime_label} regime, allocation {gold_asset.allocation_pct:.0f}%",
                    "rank_score": gold_asset.expected_score * 100,
                    "confidence": "HIGH" if plan.regime in ("RISK_OFF", "EXTREME_RISK") else "MEDIUM",
                })
                total_invested += gold_amount

        # --- Silver allocation (specific ETF) ---
        silver_asset = next((a for a in plan.assets if a.asset == "Silver"), None)
        if silver_asset and silver_asset.amount >= 100:
            silver_price = commodity_prices.get(settings.SILVER_ETF_SYMBOL, 72.0)
            silver_qty = math.floor(silver_asset.amount / silver_price) if silver_price > 0 else 0
            silver_amount = silver_qty * silver_price if silver_qty > 0 else 0
            if silver_qty > 0:
                recommendations.append({
                    "type": "SILVER",
                    "action": "BUY",
                    "symbol": "SILVERBEES",
                    "name": "Nippon Silver ETF",
                    "instrument": settings.SILVER_ETF_SYMBOL,
                    "price": silver_price,
                    "quantity": silver_qty,
                    "amount": round(silver_amount, 2),
                    "weight_pct": silver_asset.allocation_pct,
                    "reason": f"Silver diversification — {plan.regime_label} regime",
                    "rank_score": silver_asset.expected_score * 100,
                    "confidence": "MEDIUM",
                })
                total_invested += silver_amount

        # --- Cash reserve ---
        cash_amount = capital - total_invested
        if cash_amount > 0:
            recommendations.append({
                "type": "CASH",
                "action": "HOLD",
                "symbol": "SAVINGS",
                "name": "Savings / Liquid Fund",
                "instrument": "Bank Savings or Liquid MF",
                "price": 0,
                "quantity": 0,
                "amount": round(cash_amount, 2),
                "weight_pct": round(cash_amount / capital * 100, 1),
                "reason": f"Cash reserve for safety — {plan.regime_label} regime",
                "rank_score": 0,
                "confidence": "HIGH",
            })

        # 7. Build risk context
        risk_context = {
            "regime": plan.regime,
            "regime_label": plan.regime_label,
            "regime_confidence": plan.regime_confidence,
            "blended_risk_score": round(blended, 1),
            "ai_confidence": round(ai_pred.confidence * 100, 1) if ai_pred.model_available else 0,
            "geo_risk_level": geo_risk_level,
            "geo_risk_score": geo_risk_score,
            "active_conflicts": len(active_conflicts),
            "vix": macro.get("vix", 0),
            "nifty_trend": "Bullish" if macro.get("nifty_above_200dma", False) else "Bearish",
        }

        # 8. Summary text
        equity_count = len([r for r in recommendations if r["type"] == "EQUITY"])
        gold_rec = next((r for r in recommendations if r["type"] == "GOLD"), None)
        silver_rec = next((r for r in recommendations if r["type"] == "SILVER"), None)

        parts = []
        if equity_count > 0:
            stock_names = ", ".join(r["symbol"] for r in recommendations if r["type"] == "EQUITY")
            parts.append(f"Buy {equity_count} stock{'s' if equity_count > 1 else ''}: {stock_names}")
        if gold_rec:
            parts.append(f"Buy {gold_rec['quantity']} units GOLDBEES (₹{gold_rec['amount']:,.0f})")
        if silver_rec:
            parts.append(f"Buy {silver_rec['quantity']} units SILVERBEES (₹{silver_rec['amount']:,.0f})")
        cash_rec = next((r for r in recommendations if r["type"] == "CASH"), None)
        if cash_rec:
            parts.append(f"Keep ₹{cash_rec['amount']:,.0f} in savings")

        summary = " | ".join(parts)

        # 9. Gemini AI analysis (non-blocking, best-effort)
        ai_insight = None
        try:
            from app.config import settings as cfg
            if cfg.GEMINI_API_KEY:
                import httpx
                stock_list = ", ".join(
                    f"{r['symbol']} (₹{r['price']}, rank {r['rank_score']:.0f})"
                    for r in recommendations if r["type"] == "EQUITY"
                )
                prompt = (
                    f"I have ₹{capital:,.0f} to invest in Indian stock market today.\n"
                    f"Market regime: {plan.regime_label} (risk score {blended:.0f}/100)\n"
                    f"VIX: {macro.get('vix', 'N/A')}\n"
                    f"NIFTY: {'Above' if macro.get('nifty_above_200dma') else 'Below'} 200-DMA\n"
                    f"Geo risk: {geo_risk_level}\n"
                    f"My system picked these stocks: {stock_list or 'None (regime too risky)'}\n"
                    f"Allocation: Equity {plan.assets[0].allocation_pct if plan.assets else 0}%, "
                    f"Gold {next((a.allocation_pct for a in plan.assets if a.asset == 'Gold'), 0)}%, "
                    f"Cash {next((a.allocation_pct for a in plan.assets if a.asset == 'Cash'), 0)}%\n\n"
                    "Give me a 100-word sharp assessment: Is this a good time to deploy? "
                    "Any red flags? What should I watch out for this week? "
                    "If the stock picks are poor, suggest 2-3 better alternatives from NIFTY 50. "
                    "Be direct and actionable. Use ₹ for amounts."
                )
                gemini_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
                body = {
                    "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                    "systemInstruction": {"parts": [{"text": "You are an expert Indian stock market advisor. Be concise, specific, actionable. No disclaimers."}]},
                    "generationConfig": {"temperature": 0.7, "maxOutputTokens": 300},
                }
                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.post(f"{gemini_url}?key={cfg.GEMINI_API_KEY}", json=body)
                if resp.status_code == 200:
                    data = resp.json()
                    ai_insight = data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            logger.warning(f"Gemini advisor insight failed: {e}")

        return {
            "capital": capital,
            "recommendations": recommendations,
            "risk_context": risk_context,
            "summary": summary,
            "ai_insight": ai_insight,
            "total_invested": round(total_invested, 2),
            "total_cash": round(cash_amount, 2),
            "allocation_breakdown": {
                "equity_pct": next((a.allocation_pct for a in plan.assets if a.asset == "Equity"), 0),
                "gold_pct": next((a.allocation_pct for a in plan.assets if a.asset == "Gold"), 0),
                "silver_pct": next((a.allocation_pct for a in plan.assets if a.asset == "Silver"), 0),
                "cash_pct": next((a.allocation_pct for a in plan.assets if a.asset == "Cash"), 0),
            },
            "brokerage_estimate": round(plan.brokerage_total, 2),
            "why_no_trades": plan.why_no_trades if plan.why_no_trades else None,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Smart advisor error: {e}")
        raise


# ─── AI-Powered Recommendation Endpoint ──────────────


@router.get("/ai-recommend")
async def ai_stock_recommendation(
    capital: float = Query(..., gt=0, description="Amount to invest (₹)"),
):
    """
    Ask Gemini AI directly for stock recommendations,
    enriched with live NIFTY market data & top-ranked stocks.
    """
    import httpx
    import numpy as np
    import yfinance as yf
    from app.config import settings

    if not settings.GEMINI_API_KEY:
        return {"recommendation": "AI is unavailable — no API key configured.", "market_data": {}}

    # 1. Gather live market context
    market_context = ""
    try:
        def _snapshot():
            lines = []
            indices = {"NIFTY 50": "^NSEI", "Bank NIFTY": "^NSEBANK", "SENSEX": "^BSESN"}
            for name, sym in indices.items():
                try:
                    h = yf.Ticker(sym).history(period="5d")
                    if h is not None and not h.empty:
                        c = float(h["Close"].iloc[-1])
                        p = float(h["Close"].iloc[-2]) if len(h) > 1 else c
                        chg = (c - p) / p * 100
                        lines.append(f"- {name}: ₹{c:,.2f} ({chg:+.2f}%)")
                except Exception:
                    pass
            try:
                vix = yf.Ticker("^INDIAVIX").history(period="5d")
                if vix is not None and not vix.empty:
                    lines.append(f"- India VIX: {float(vix['Close'].iloc[-1]):.2f}")
            except Exception:
                pass
            return "\n".join(lines)
        market_context = await asyncio.to_thread(_snapshot)
    except Exception:
        market_context = "Market data unavailable."

    # 2. Fetch top-ranked stocks from our engine for AI to evaluate
    ranked_context = ""
    try:
        from app.strategy.stock_ranker import get_top_ranked
        ranked = await asyncio.to_thread(get_top_ranked, n=15, universe_tier="100")
        if ranked:
            parts = []
            for s in ranked:
                sym = getattr(s, "symbol", getattr(s, "clean_symbol", "?"))
                score = getattr(s, "composite_score", getattr(s, "rank_score", 0))
                price = getattr(s, "price", 0)
                parts.append(f"{sym} (Score:{score:.0f}, ₹{price:,.0f})")
            ranked_context = "System-ranked top stocks (by momentum+quality): " + ", ".join(parts)
    except Exception as e:
        logger.warning(f"Stock ranker failed: {e}")

    # 3. Ask Gemini
    prompt = f"""I have ₹{capital:,.0f} to invest in Indian stock market today ({datetime.now().strftime('%B %d, %Y')}).

📈 Live Market Data:
{market_context or 'Unavailable'}

🏆 System-Ranked Stocks:
{ranked_context or 'Unavailable'}

Based on current market conditions, give me a SPECIFIC investment plan:

### Market Assessment
Brief 2-3 line current market view (bullish/bearish/sideways, key drivers)

### Top Stock Picks (3-5 stocks)
For each stock:
- **SYMBOL** — Why buy, entry price zone, target, stop-loss
- Include exact quantity I can buy with my capital (allocate across picks)

### Asset Allocation
- What % in equities, what % in gold (GOLDBEES), what % cash
- Be specific with amounts in ₹

### Key Risks & Watchlist
- 2-3 risks to monitor this week
- 1-2 stocks to watchlist for future entry

Rules:
- Only recommend NSE-listed stocks
- Use ₹ for all amounts
- Be specific with price levels (entry, target, stop-loss)
- Consider my capital size for position sizing
- If market is risky, recommend higher cash allocation
- You can disagree with the system-ranked stocks if you have better picks
- No disclaimers — be direct and actionable
"""

    gemini_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "systemInstruction": {"parts": [{"text": (
            "You are STONKS AI — an elite Indian stock market advisor. "
            "You give specific, actionable stock recommendations with exact price levels. "
            "You analyze technicals (RSI, moving averages, chart patterns) and fundamentals "
            "(PE, earnings growth, sector trends). You're direct, confident, and never vague. "
            f"Today is {datetime.now().strftime('%B %d, %Y')}."
        )}]},
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 2048, "topP": 0.9},
    }

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(f"{gemini_url}?key={settings.GEMINI_API_KEY}", json=body)
        if resp.status_code != 200:
            logger.error(f"Gemini advisor error {resp.status_code}: {resp.text[:300]}")
            return {"recommendation": "AI service temporarily unavailable. Please try again.", "market_data": market_context}
        data = resp.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return {
            "recommendation": text,
            "market_data": market_context,
            "ranked_stocks": ranked_context,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Gemini AI recommend failed: {e}")
        return {"recommendation": "AI service error. Please try again.", "market_data": market_context}
