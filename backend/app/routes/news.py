"""
Financial & Global News aggregator with importance scoring.

Sources (free RSS/public):
- Moneycontrol, Economic Times, LiveMint (Indian Markets & Finance)
- NDTV Profit (Indian stocks)
- Business Today (Indian finance)
- Reuters World (Global news & Geopolitics)
- Al Jazeera (International news)
- BBC News (Geopolitics & War)
- Times of India (Indian news)

Features:
- Date filtering (last 7 days only)
- Importance scoring based on keywords
- Categories: Indian Markets, Indian Finance, Geopolitics, War, Global
- AI-powered sentiment analysis via Gemini
"""

import asyncio
import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from typing import Optional

import httpx
from fastapi import APIRouter

from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(tags=["news"])

# RSS feeds — fresh, current content
NEWS_FEEDS = {
    "moneycontrol": {
        "name": "Moneycontrol",
        "category": "Indian Markets",
        "url": "https://www.moneycontrol.com/rss/marketreports.xml",
        "icon": "🇮🇳",
    },
    "et": {
        "name": "Economic Times Markets",
        "category": "Indian Finance",
        "url": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
        "icon": "📊",
    },
    "livemint": {
        "name": "LiveMint",
        "category": "Indian Finance",
        "url": "https://www.livemint.com/rss/markets",
        "icon": "💰",
    },
    "ndtv_profit": {
        "name": "NDTV Profit",
        "category": "Indian Markets",
        "url": "https://feeds.ndtv.com/ndtvprofit-latest",
        "icon": "📈",
    },
    "business_today": {
        "name": "Business Today",
        "category": "Indian Finance",
        "url": "https://www.businesstoday.in/latest/index.xml",
        "icon": "💼",
    },
    "reuters": {
        "name": "Reuters World",
        "category": "Global",
        "url": "https://feeds.reuters.com/reuters/businessNews",
        "icon": "🌍",
    },
    "bbc_business": {
        "name": "BBC Business",
        "category": "Global",
        "url": "http://feeds.bbc.co.uk/news/business/rss.xml",
        "icon": "📡",
    },
    "aljazeera": {
        "name": "Al Jazeera Business",
        "category": "Global",
        "url": "https://www.aljazeera.com/xml/rss/all.xml",
        "icon": "🌐",
    },
    "toi_news": {
        "name": "Times of India",
        "category": "Indian Markets",
        "url": "https://feeds.timesofindia.indiatimes.com/defaultappfeed.cms",
        "icon": "🗞️",
    },
}


def _clean_html(text: str) -> str:
    """Strip HTML tags from text."""
    if not text:
        return ""
    clean = re.sub(r"<[^>]+>", "", text)
    clean = re.sub(r"&[a-zA-Z]+;", " ", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean[:300]


def _parse_date(date_str: str) -> Optional[datetime]:
    """Parse RSS date strings (RFC 2822 format mostly)."""
    if not date_str:
        return None
    try:
        # Try RFC 2822 format (RSS standard)
        return parsedate_to_datetime(date_str)
    except (TypeError, ValueError):
        try:
            # Try ISO format
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return None


def _calculate_importance(title: str, description: str, category: str) -> int:
    """Calculate importance score (0-100) based on keywords."""
    text = f"{title} {description}".lower()
    score = 0
    
    # Check for active war content first (highest priority)
    war_indicators = [
        "killed in", "wounded in", "casualties", "death toll", "attack", "bombing", "bombed",
        "missile strike", "airstrike", "shelling", "offensive", "invasion", "siege",
        "combat zone", "battlefield"
    ]
    if any(term in text for term in war_indicators):
        score += 60  # War/conflict gets highest importance
        return min(score, 100)
    
    # Geopolitical statements & actions (high priority)
    geopolitical_indicators = [
        "statement condemn", "condemned", "diplomatic statement", "government statement",
        "sanction", "embargo", "peace talks", "negotiation", "bilateral", "treaty",
        "broke relation", "restore relation"
    ]
    if any(term in text for term in geopolitical_indicators):
        score += 50
    
    # Finance & Markets (30 points)
    financial_terms = ["rbi", "inflationary", "interest rate", "rupee", "crash", "surge", "bull run",
                       "bear market", "ipo", "stock split", "dividend", "earnings", "profit", "revenue",
                       "merger", "acquisition", "nse", "bse", "sensex", "nifty", "circuit breaker"]
    if any(term in text for term in financial_terms):
        score += 30
    
    # Market Events (20 points)
    market_terms = ["market", "stock", "share", "price", "rally", "decline", "trading", "investor",
                    "volatility", "recovery", "correction", "record high", "record low"]
    if any(term in text for term in market_terms):
        score += 20
    
    # Fed/RBI/Policy (25 points)
    policy_terms = ["federal reserve", "interest rate hike", "rate cut", "monetary policy", "inflation",
                    "economic growth", "currency", "gold", "oil", "commodity", "gdp"]
    if any(term in text for term in policy_terms):
        score += 25
    
    # Company-specific (15 points)
    company_terms = ["tcs", "reliance", "infosys", "hdfc", "icici", "axis", "kotak", "hul", "pfc",
                     "sbi", "bajaj", "maruti", "ongc", "coal india", "ntpc", "indiabulls"]
    if any(term in text for term in company_terms):
        score += 15
    
    # Global indices (10 points)
    if any(term in text for term in ["s&p 500", "nasdaq", "ftse", "dax", "nikkei", "hang seng"]):
        score += 10
    
    return min(score, 100)  # Cap at 100


def _categorize_news(title: str, description: str) -> str:
    """
    Determine category: War, Geopolitics, or None (use original).
    
    War: Active military conflicts, attacks, combat, casualties
    Geopolitics: Diplomatic statements, international relations, sanctions, trade talks, agreements
    """
    text = f"{title} {description}".lower()
    
    # WAR CONTENT - Real military conflict, attacks, casualties (strict matching)
    war_indicators = [
        # Combat & attacks
        "attack", "attacking", "attacked", "bombing", "bombed", "strikes", "struck",
        "missile strike", "airstrike", "air strike", "shelling", "artillery",
        # Military operations
        "military operation", "offensive", "counter-offensive", "invasion",
        # Casualties & conflict
        "killed", "wounded", "casualties", "death toll", "fatalities",
        # Conflict zones
        "conflict zone", "battlefield", "combat zone", "armed clash",
        # Specific active conflicts  
        "ukraine russia", "russia ukraine", "israel gaza", "gaza israel", "hamas",
        "hezbollah", "iran war", "strike on", "struck by",
        # War-specific
        "siege", "ceasefire", "hostilities", "active conflict"
    ]
    
    if any(term in text for term in war_indicators):
        return "War"
    
    # GEOPOLITICS - Diplomatic, statements, international relations
    geopolitics_indicators = [
        # Statements & official responses
        "statement", "said", "told", "declared", "announced", "response",
        "spokesman", "ministry", "official", "government", "spokesperson",
        # Diplomatic actions
        "sanction", "embargo", "diplomat", "diplomatic", "ambassad",
        # International relations
        "relation", "relations", "alliance", "partnership", "cooperation", "agreement",
        "bilateral", "multilateral", "talks", "negotiation", "meeting", "summit",
        # Trade & economic diplomacy
        "trade deal", "trade agreement", "trade tension", "export", "tariff", "trade war",
        # International law & treaties
        "treaty", "protocol", "accord", "pact", "convention", "un vote",
        # Borders & territorial  
        "border", "territorial", "dispute", "claims over",
        # Major geopolitical contexts
        "china", "russia", "india", "usa", "europe", "middle east",
        "southeast asia", "taiwan", "korea", "africa"
    ]
    
    # Count matches for geopolitics (need at least 2 to confirm it's geopolitical)
    geo_matches = sum(1 for term in geopolitics_indicators if term in text)
    if geo_matches >= 2:  # Multiple geopolitical indicators
        return "Geopolitics"
    
    # Single strong geopolitical indicator
    strong_geo = ["sanction", "embargo", "diplomatic", "bilateral", "multilateral", "treaty", "accord"]
    if any(term in text for term in strong_geo):
        return "Geopolitics"
    
    # Default: let original category stand
    return None


async def _fetch_feed(client: httpx.AsyncClient, feed_id: str, feed: dict) -> list:
    """Fetch and parse a single RSS feed with recent articles only."""
    articles = []
    try:
        resp = await client.get(feed["url"], follow_redirects=True, timeout=20)
        if resp.status_code != 200:
            return []

        root = ET.fromstring(resp.text)

        # Handle both RSS 2.0 and Atom feeds
        items = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")

        now = datetime.now()
        week_ago = now - timedelta(days=7)

        for item in items[:15]:  # Check more items to get 7+ recent ones
            # RSS 2.0
            title = item.findtext("title", "")
            link = item.findtext("link", "")
            desc = item.findtext("description", "")
            pub_date = item.findtext("pubDate", "")

            # Atom fallback
            if not title:
                title = item.findtext("{http://www.w3.org/2005/Atom}title", "")
            if not link:
                link_el = item.find("{http://www.w3.org/2005/Atom}link")
                link = link_el.get("href", "") if link_el is not None else ""
            if not desc:
                desc = item.findtext("{http://www.w3.org/2005/Atom}summary", "")
            if not pub_date:
                pub_date = item.findtext("{http://www.w3.org/2005/Atom}updated", "")

            if not title:
                continue

            # Parse and validate date
            parsed_date = _parse_date(pub_date)
            if not parsed_date:
                # If we can't parse date, skip (likely old/invalid content)
                continue

            # Make comparable (remove timezone for simple comparison)
            if parsed_date.tzinfo:
                parsed_date = parsed_date.replace(tzinfo=None)

            # Only include articles from last 7 days
            if parsed_date < week_ago:
                continue

            # Calculate importance
            importance = _calculate_importance(title, desc, feed["category"])
            
            # Determine category (geopolitics/war override)
            category = _categorize_news(title, desc) or feed["category"]

            articles.append({
                "title": _clean_html(title),
                "link": link.strip() if link else "",
                "description": _clean_html(desc),
                "published": parsed_date.isoformat() if parsed_date else pub_date,
                "source": feed["name"],
                "source_id": feed_id,
                "category": category,
                "icon": feed["icon"],
                "importance": importance,
            })
    except Exception as e:
        logger.warning(f"Feed {feed_id} fetch failed: {e}")

    return articles


@router.get("/api/news")
async def get_news(sort_by: str = "importance"):
    """
    Fetch financial news from multiple RSS sources.
    
    Args:
        sort_by: "importance" (default), "recent", or specific category
    """
    async with httpx.AsyncClient(timeout=20, headers={"User-Agent": "Stonks/2.0"}) as client:
        tasks = [_fetch_feed(client, fid, feed) for fid, feed in NEWS_FEEDS.items()]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    all_articles = []
    for result in results:
        if isinstance(result, list):
            all_articles.extend(result)

    # Sort by importance (descending), then by date (newest first)
    if sort_by == "importance":
        all_articles.sort(key=lambda a: (-a.get("importance", 0), -datetime.fromisoformat(a["published"]).timestamp() if a["published"] else 0))
    elif sort_by == "recent":
        all_articles.sort(key=lambda a: -datetime.fromisoformat(a["published"]).timestamp() if a["published"] else 0)
    
    return {
        "articles": all_articles,
        "sources": len(NEWS_FEEDS),
        "total": len(all_articles),
        "timestamp": datetime.now().isoformat(),
        "filters": {
            "date_range": "Last 7 days",
            "sort_by": sort_by,
            "categories": list(set(a["category"] for a in all_articles))
        }
    }


@router.get("/api/news/ai-summary")
async def get_news_ai_summary():
    """Get AI-generated summary of current market news."""
    # First fetch news
    async with httpx.AsyncClient(timeout=15, headers={"User-Agent": "Stonks/2.0"}) as client:
        tasks = [_fetch_feed(client, fid, feed) for fid, feed in NEWS_FEEDS.items()]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    all_articles = []
    for result in results:
        if isinstance(result, list):
            all_articles.extend(result)

    if not all_articles:
        return {"summary": "Unable to fetch news. Please try again later.", "sentiment": "neutral"}

    # Build headlines for AI
    headlines = "\n".join(
        f"- [{a['source']}] {a['title']}"
        for a in all_articles[:20]
    )

    if not settings.GEMINI_API_KEY:
        return {"summary": "AI summary unavailable — no API key configured.", "sentiment": "neutral"}

    try:
        prompt = (
            f"Here are today's financial news headlines:\n\n{headlines}\n\n"
            "Provide a 150-word market intelligence brief:\n"
            "### Market Sentiment\n(Bullish/Bearish/Mixed with reasoning)\n\n"
            "### Key Headlines\n(Top 3-4 most impactful stories for Indian investors)\n\n"
            "### Action Items\n(What should traders watch/do based on this news)\n\n"
            "Be specific about which stocks/sectors are affected. Use ₹ for amounts."
        )

        gemini_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
        body = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "systemInstruction": {"parts": [{"text": "You are an expert Indian stock market analyst. Analyze news for trading impact. Be concise, specific, actionable."}]},
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 500},
        }

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{gemini_url}?key={settings.GEMINI_API_KEY}", json=body)

        if resp.status_code == 200:
            data = resp.json()
            summary = data["candidates"][0]["content"]["parts"][0]["text"]

            # Detect sentiment
            lower = summary.lower()
            if any(w in lower for w in ["bullish", "positive", "rally", "upbeat"]):
                sentiment = "bullish"
            elif any(w in lower for w in ["bearish", "negative", "sell-off", "decline", "crash"]):
                sentiment = "bearish"
            else:
                sentiment = "mixed"

            return {"summary": summary, "sentiment": sentiment}
        else:
            return {"summary": "AI summary temporarily unavailable.", "sentiment": "neutral"}

    except Exception as e:
        logger.warning(f"News AI summary failed: {e}")
        return {"summary": "AI summary temporarily unavailable.", "sentiment": "neutral"}
