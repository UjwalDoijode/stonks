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
