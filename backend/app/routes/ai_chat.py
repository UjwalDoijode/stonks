"""
Gemini AI-powered market intelligence assistant.

Features:
- General market chat with real-time data enrichment
- Deep stock analysis with live technicals + fundamentals
- AI morning market brief
"""

import asyncio
import json
import logging
import math
from datetime import datetime

import httpx
import numpy as np
import yfinance as yf
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(tags=["ai"])

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
)

SYSTEM_PROMPT = """You are STONKS AI — an expert Indian stock market analyst and trading advisor built into a professional trading terminal.

Your expertise covers:
- Indian markets (NSE/BSE), NIFTY 50/500, Bank NIFTY, sectoral indices
- Technical analysis: moving averages, RSI, MACD, Bollinger Bands, Fibonacci, candlestick patterns, support/resistance
- Fundamental analysis: PE/PB ratios, earnings growth, ROCE, debt/equity, cash flows, promoter holding
- Macro factors: RBI policy, crude oil impact on INR, FII/DII flows, US Fed, global risk sentiment
- Risk management: position sizing, stop losses, portfolio allocation, hedging
- Indian market specifics: F&O expiry effects, budget impact, quarterly results season

Guidelines:
- Be SPECIFIC and ACTIONABLE — give exact price levels, targets, and stop losses when analyzing stocks
- Use ₹ for all Indian rupee amounts
- Format with markdown: **bold** for key points, bullet lists for clarity, ### headers for sections
- Keep responses concise (150-300 words) unless user asks for detailed analysis
- When real market data is provided, reference it prominently in your analysis
- Always mention key risk factors and include a brief disclaimer for trade recommendations
- If data seems stale or markets are closed, mention it
- Sound confident but honest — if you're uncertain, say so

Current date: {date}
"""

ANALYSIS_PROMPT = """Perform a comprehensive analysis of **{name}** ({symbol}) using this real market data:

📊 **Price Data:**
- Current Price: ₹{price} ({change_pct:+.2f}% today)
- 52-Week High: ₹{high_52w} | Low: ₹{low_52w}
- Distance from 52W High: {dist_from_high:.1f}%

📈 **Technical Indicators:**
- 50-DMA: ₹{dma50} | 200-DMA: {dma200}
- RSI(14): {rsi}
- Volume: {volume}

💰 **Fundamentals:**
- Market Cap: {market_cap}
- PE Ratio: {pe}
- Sector: {sector}

Provide your analysis in this structure:
### Technical Outlook
(Trend direction, key support/resistance levels, patterns)

### Fundamental View
(Valuation assessment, growth outlook, quality)

### Recommendation
(Clear BUY / HOLD / AVOID with entry zone, target, stop-loss)

### Risk Factors
(2-3 key risks specific to this stock)

Be specific with price levels. Keep it actionable."""

COMMON_STOCKS = {
    "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN", "WIPRO",
    "BHARTIARTL", "ITC", "KOTAKBANK", "LT", "AXISBANK", "MARUTI", "TITAN",
    "BAJFINANCE", "ADANIENT", "TATAMOTORS", "TATASTEEL", "SUNPHARMA",
    "HINDUNILVR", "ONGC", "POWERGRID", "NTPC", "COALINDIA", "JSWSTEEL",
    "NESTLEIND", "HCLTECH", "TECHM", "BAJAJ", "ULTRACEMCO", "DRREDDY",
    "CIPLA", "APOLLOHOSP", "ASIANPAINT", "DMART", "ZOMATO", "PAYTM",
    "NIFTY", "BANKNIFTY", "SENSEX", "HDFC",
}


class ChatRequest(BaseModel):
    message: str
    context: list[dict] | None = None


class AnalyzeRequest(BaseModel):
    symbol: str


# ─── Data Fetching ────────────────────────────────────


def _format_large_number(value):
    if not value or value == 0:
        return "N/A"
    crores = value / 1e7
    if crores >= 100_000:
        return f"{crores / 100_000:.1f}L Cr"
    if crores >= 1000:
        return f"{crores / 1000:.1f}K Cr"
    return f"{crores:,.0f} Cr"


def _resolve(symbol: str) -> str:
    s = symbol.strip().upper().replace(" ", "")
    aliases = {"NIFTY": "^NSEI", "NIFTY50": "^NSEI", "BANKNIFTY": "^NSEBANK", "SENSEX": "^BSESN"}
    if s in aliases:
        return aliases[s]
    if s.startswith("^") or "=" in s or s.endswith(".NS") or s.endswith(".BO"):
        return s
    return f"{s}.NS"


def _fetch_stock_data(symbol: str) -> dict | None:
    """Fetch real-time stock data for AI context enrichment."""
    try:
        resolved = _resolve(symbol)
        ticker = yf.Ticker(resolved)
        info = ticker.info or {}
        hist = ticker.history(period="1y")

        if hist is None or hist.empty:
            return None

        close = float(hist["Close"].iloc[-1])
        prev_close = float(hist["Close"].iloc[-2]) if len(hist) > 1 else close
        high_52w = float(hist["High"].tail(252).max())
        low_52w = float(hist["Low"].tail(252).min())

        # RSI(14)
        delta = hist["Close"].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi_series = 100 - 100 / (1 + rs)
        rsi_val = float(rsi_series.iloc[-1])
        rsi_display = round(rsi_val, 1) if not math.isnan(rsi_val) else "N/A"

        # DMAs
        dma50 = round(float(hist["Close"].rolling(50).mean().iloc[-1]), 2)
        dma200 = round(float(hist["Close"].rolling(200).mean().iloc[-1]), 2) if len(hist) >= 200 else "N/A"

        return {
            "symbol": resolved,
            "name": info.get("shortName", symbol.upper()),
            "price": round(close, 2),
            "change_pct": round((close - prev_close) / prev_close * 100, 2),
            "high_52w": round(high_52w, 2),
            "low_52w": round(low_52w, 2),
            "dist_from_high": round((close - high_52w) / high_52w * 100, 1),
            "volume": f"{int(hist['Volume'].iloc[-1]):,}",
            "market_cap": _format_large_number(info.get("marketCap", 0)),
            "pe": round(info.get("trailingPE", 0), 1) or "N/A",
            "dma50": dma50,
            "dma200": dma200,
            "rsi": rsi_display,
            "sector": info.get("sector", "N/A"),
        }
    except Exception as e:
        logger.warning(f"Stock data fetch failed for {symbol}: {e}")
        return None


def _fetch_market_snapshot() -> dict:
    """Fetch quick market data for context."""
    result = {}
    tickers = {"NIFTY 50": "^NSEI", "Bank NIFTY": "^NSEBANK", "SENSEX": "^BSESN"}
    for name, sym in tickers.items():
        try:
            h = yf.Ticker(sym).history(period="5d")
            if h is not None and not h.empty:
                c = float(h["Close"].iloc[-1])
                p = float(h["Close"].iloc[-2]) if len(h) > 1 else c
                result[name] = {"close": round(c, 2), "change_pct": round((c - p) / p * 100, 2)}
        except Exception:
            pass
    try:
        vix = yf.Ticker("^INDIAVIX").history(period="5d")
        if vix is not None and not vix.empty:
            result["India VIX"] = {"close": round(float(vix["Close"].iloc[-1]), 2), "change_pct": 0}
    except Exception:
        pass
    return result


# ─── Gemini API ───────────────────────────────────────


async def _call_gemini(messages: list[dict], system: str) -> str:
    """Call Gemini API and return the text response."""
    if not settings.GEMINI_API_KEY:
        raise HTTPException(503, "Gemini API key not configured. Set GEMINI_API_KEY in config.")

    contents = []
    for msg in messages:
        contents.append({
            "role": msg["role"],
            "parts": [{"text": msg["text"]}],
        })

    body = {
        "contents": contents,
        "systemInstruction": {"parts": [{"text": system}]},
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 2048,
            "topP": 0.9,
        },
    }

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(f"{GEMINI_URL}?key={settings.GEMINI_API_KEY}", json=body)

    if resp.status_code != 200:
        logger.error(f"Gemini API error {resp.status_code}: {resp.text[:500]}")
        raise HTTPException(502, "AI service temporarily unavailable. Please try again.")

    data = resp.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        logger.error(f"Unexpected Gemini response: {json.dumps(data)[:500]}")
        raise HTTPException(502, "Unexpected AI response. Please try again.")


# ─── Routes ───────────────────────────────────────────


@router.post("/api/ai/chat")
async def ai_chat(req: ChatRequest):
    """Chat with AI market assistant. Auto-enriches with real stock data."""
    system = SYSTEM_PROMPT.format(date=datetime.now().strftime("%B %d, %Y"))

    # Detect stock symbols in message and enrich with real data
    words = set(req.message.upper().replace(",", " ").replace(".", " ").split())
    detected = [w for w in words if w in COMMON_STOCKS]
    enrichment = ""

    if detected:
        for sym in detected[:3]:
            data = await asyncio.to_thread(_fetch_stock_data, sym)
            if data:
                enrichment += (
                    f"\n📊 **{data['name']}** ({data['symbol']}): "
                    f"₹{data['price']} ({data['change_pct']:+.2f}%), "
                    f"RSI: {data['rsi']}, 50-DMA: ₹{data['dma50']}, "
                    f"52W: ₹{data['low_52w']}-₹{data['high_52w']}, "
                    f"PE: {data['pe']}, Cap: {data['market_cap']}"
                )

    # Also fetch general market data for context
    if any(kw in req.message.lower() for kw in ["market", "nifty", "today", "brief", "outlook", "buy", "sell"]):
        snapshot = await asyncio.to_thread(_fetch_market_snapshot)
        if snapshot:
            enrichment += "\n\n📈 Market Snapshot:"
            for name, vals in snapshot.items():
                enrichment += f"\n- {name}: ₹{vals['close']:,.2f} ({vals['change_pct']:+.2f}%)"

    # Build messages
    messages = []
    if req.context:
        for ctx in req.context[-8:]:
            role = ctx.get("role", "user")
            if role not in ("user", "model"):
                role = "user"
            messages.append({"role": role, "text": ctx.get("text", "")})

    user_text = req.message
    if enrichment:
        user_text += f"\n\n[Real-time market data for your analysis:]{enrichment}"

    messages.append({"role": "user", "text": user_text})
    response = await _call_gemini(messages, system)

    return {"response": response, "enriched_symbols": detected}


@router.post("/api/ai/analyze")
async def ai_analyze_stock(req: AnalyzeRequest):
    """Deep AI analysis of a specific stock with full technicals."""
    data = await asyncio.to_thread(_fetch_stock_data, req.symbol)
    if not data:
        raise HTTPException(404, f"Could not fetch data for '{req.symbol}'. Try: RELIANCE, TCS, INFY, HDFCBANK")

    system = SYSTEM_PROMPT.format(date=datetime.now().strftime("%B %d, %Y"))
    prompt = ANALYSIS_PROMPT.format(**data)
    messages = [{"role": "user", "text": prompt}]
    response = await _call_gemini(messages, system)

    return {"response": response, "stock_data": data}


@router.get("/api/ai/brief")
async def ai_market_brief():
    """Generate AI morning market brief with live data."""
    snapshot = await asyncio.to_thread(_fetch_market_snapshot)

    brief_prompt = f"Today is {datetime.now().strftime('%A, %B %d, %Y')}.\n\nLive Market Data:\n"
    for name, vals in snapshot.items():
        brief_prompt += f"- {name}: ₹{vals['close']:,.2f} ({vals['change_pct']:+.2f}%)\n"

    brief_prompt += """
Generate a morning market brief for an Indian retail trader:

### Market Mood
(Overall sentiment in 1-2 lines based on the data above)

### Key Levels
(NIFTY support/resistance levels, trend direction)

### Sectors to Watch
(2-3 sectors with reasoning)

### Today's Game Plan
(Specific actionable advice — what to buy/avoid/watch)

Keep it under 250 words. Be specific with numbers and levels."""

    system = SYSTEM_PROMPT.format(date=datetime.now().strftime("%B %d, %Y"))
    messages = [{"role": "user", "text": brief_prompt}]
    response = await _call_gemini(messages, system)

    return {"brief": response, "market_data": snapshot}
