"""
Financial & Global News aggregator.

Sources (free RSS/public):
- Moneycontrol (Indian markets)
- Economic Times (Indian economy)
- LiveMint (Indian finance)
- Reuters (global)
- Bloomberg (global markets)
- CNBC (US markets)

Plus Gemini AI for news sentiment summary.
"""

import asyncio
import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime

import httpx
from fastapi import APIRouter

from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(tags=["news"])

# RSS feeds — all free, no auth needed
NEWS_FEEDS = {
    "moneycontrol": {
        "name": "Moneycontrol",
        "category": "Indian Markets",
        "url": "https://www.moneycontrol.com/rss/marketreports.xml",
        "icon": "🇮🇳",
    },
    "et_markets": {
        "name": "Economic Times",
        "category": "Indian Economy",
        "url": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
        "icon": "📈",
    },
    "livemint": {
        "name": "LiveMint",
        "category": "Indian Finance",
        "url": "https://www.livemint.com/rss/markets",
        "icon": "💰",
    },
    "reuters_business": {
        "name": "Reuters",
        "category": "Global",
        "url": "https://news.google.com/rss/search?q=stock+market+finance&hl=en-IN&gl=IN&ceid=IN:en",
        "icon": "🌍",
    },
    "cnbc": {
        "name": "CNBC",
        "category": "US Markets",
        "url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10001147",
        "icon": "🇺🇸",
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


async def _fetch_feed(client: httpx.AsyncClient, feed_id: str, feed: dict) -> list:
    """Fetch and parse a single RSS feed."""
    articles = []
    try:
        resp = await client.get(feed["url"], follow_redirects=True)
        if resp.status_code != 200:
            return []

        root = ET.fromstring(resp.text)

        # Handle both RSS 2.0 and Atom feeds
        items = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")

        for item in items[:8]:  # Max 8 per source
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

            articles.append({
                "title": _clean_html(title),
                "link": link.strip() if link else "",
                "description": _clean_html(desc),
                "published": pub_date.strip() if pub_date else "",
                "source": feed["name"],
                "source_id": feed_id,
                "category": feed["category"],
                "icon": feed["icon"],
            })
    except Exception as e:
        logger.warning(f"Feed {feed_id} fetch failed: {e}")

    return articles


@router.get("/api/news")
async def get_news():
    """Fetch financial news from multiple RSS sources."""
    async with httpx.AsyncClient(timeout=15, headers={"User-Agent": "Stonks/2.0"}) as client:
        tasks = [_fetch_feed(client, fid, feed) for fid, feed in NEWS_FEEDS.items()]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    all_articles = []
    for result in results:
        if isinstance(result, list):
            all_articles.extend(result)

    # Sort by source order (Indian first, then global)
    source_order = list(NEWS_FEEDS.keys())
    all_articles.sort(key=lambda a: source_order.index(a["source_id"]) if a["source_id"] in source_order else 99)

    return {
        "articles": all_articles,
        "sources": len(NEWS_FEEDS),
        "total": len(all_articles),
        "timestamp": datetime.now().isoformat(),
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
