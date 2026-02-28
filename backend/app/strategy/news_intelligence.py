"""
News Intelligence — Real-time geopolitical & market news analysis.

Uses free RSS feeds and web sources (no API key needed) to detect:
- Active wars & military conflicts (Russia-Ukraine, Iran, Middle East, etc.)
- Trade wars, sanctions, embargoes
- Central bank policy changes
- Major economic events
- India-specific geopolitical risks

Combines real news signals with market proxy data for accurate risk assessment.
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional
from urllib.request import urlopen, Request
from xml.etree import ElementTree
import json

logger = logging.getLogger(__name__)

# ── In-memory news cache ──
_news_cache: dict = {}
_NEWS_CACHE_TTL = 1800  # 30 minutes


# ═══════════════════════════════════════════════════════
# Known Geopolitical Events Database (manually maintained)
# Updated as of Feb 2026 — these are KNOWN ongoing events
# ═══════════════════════════════════════════════════════

KNOWN_GEOPOLITICAL_EVENTS = [
    {
        "event": "Russia-Ukraine War",
        "status": "ACTIVE",
        "severity": "HIGH",
        "regions": ["Europe", "Global"],
        "impact": "Energy supply disruption, grain exports affected, sanctions on Russia, NATO tensions",
        "market_impact": "Oil/gas volatility, European equities risk, defense stocks up, safe haven demand",
        "keywords": ["russia", "ukraine", "nato", "crimea", "donbas", "zelensky", "putin", "sanctions russia"],
    },
    {
        "event": "Iran-Israel / Middle East Conflict",
        "status": "ACTIVE",
        "severity": "HIGH",
        "regions": ["Middle East", "Global"],
        "impact": "Oil supply risk from Strait of Hormuz, regional destabilization, proxy wars",
        "market_impact": "Oil price spikes, gold as safe haven, shipping disruptions, defense sector boost",
        "keywords": ["iran", "israel", "hezbollah", "hamas", "gaza", "hormuz", "middle east", "yemen", "houthi"],
    },
    {
        "event": "US-China Trade & Tech Tensions",
        "status": "ONGOING",
        "severity": "MODERATE",
        "regions": ["Asia", "Global"],
        "impact": "Semiconductor restrictions, tariffs, Taiwan strait concerns, supply chain shifts",
        "market_impact": "Tech sector volatility, semiconductor supply risk, EM currency pressure",
        "keywords": ["china", "taiwan", "tariff", "semiconductor", "trade war", "chip ban", "xi jinping"],
    },
    {
        "event": "India-Pakistan / India-China Border Tensions",
        "status": "ELEVATED",
        "severity": "MODERATE",
        "regions": ["South Asia"],
        "impact": "LAC tensions, defense spending increase, diplomatic friction",
        "market_impact": "Indian defense stocks, INR volatility, FII outflows during escalation",
        "keywords": ["india china border", "india pakistan", "lac", "ladakh", "kashmir", "line of control"],
    },
    {
        "event": "Red Sea / Suez Shipping Disruptions",
        "status": "ACTIVE",
        "severity": "MODERATE",
        "regions": ["Middle East", "Global Trade"],
        "impact": "Houthi attacks on shipping, supply chain delays, rerouting via Cape of Good Hope",
        "market_impact": "Shipping costs up, oil transport risk, inflation pressure",
        "keywords": ["red sea", "suez", "houthi", "shipping attack", "bab el-mandeb"],
    },
]

# Keywords that indicate geopolitical risk in news
RISK_KEYWORDS = {
    "war": 10, "conflict": 8, "military": 7, "missile": 9, "attack": 8,
    "nuclear": 10, "sanctions": 7, "invasion": 9, "troops": 6, "bombing": 9,
    "escalation": 8, "crisis": 7, "tension": 5, "ceasefire": 4,
    "airstrikes": 9, "casualties": 8, "refugees": 6, "blockade": 7,
    "embargo": 7, "tariff": 5, "trade war": 6, "retaliation": 6,
    "coup": 8, "protest": 4, "unrest": 5, "martial law": 8,
    "pandemic": 7, "recession": 6, "default": 7, "debt crisis": 7,
    "oil shock": 8, "energy crisis": 7, "hyperinflation": 8,
    "iran": 6, "russia": 6, "ukraine": 6, "gaza": 7, "israel": 5,
    "north korea": 7, "taiwan": 6, "houthi": 6, "hezbollah": 6,
}

# RSS feeds for geopolitical and financial news
RSS_FEEDS = [
    ("Reuters World", "https://feeds.reuters.com/Reuters/worldNews"),
    ("Reuters Business", "https://feeds.reuters.com/reuters/businessNews"),
    ("CNBC World", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100727362"),
    ("BBC World", "http://feeds.bbci.co.uk/news/world/rss.xml"),
    ("Economic Times", "https://economictimes.indiatimes.com/rssfeedsdefault.cms"),
    ("Livemint", "https://www.livemint.com/rss/markets"),
]


@dataclass
class NewsItem:
    title: str
    source: str
    published: str
    risk_score: float = 0.0
    matched_keywords: list = field(default_factory=list)


@dataclass
class NewsIntelligence:
    """Aggregated news-based geopolitical intelligence."""
    active_conflicts: list = field(default_factory=list)
    conflict_count: int = 0
    news_risk_score: float = 0.0  # 0-100
    risk_headlines: list = field(default_factory=list)
    recent_events: list = field(default_factory=list)
    india_impact_events: list = field(default_factory=list)
    last_updated: str = ""


def _fetch_rss_feed(name: str, url: str, timeout: int = 10) -> list[NewsItem]:
    """Fetch and parse a single RSS feed."""
    items = []
    try:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0 (Stonks App)"})
        with urlopen(req, timeout=timeout) as response:
            tree = ElementTree.parse(response)
            root = tree.getroot()

            # Handle both RSS and Atom formats
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            entries = root.findall(".//item") or root.findall(".//atom:entry", ns)

            for entry in entries[:20]:  # last 20 items
                title_el = entry.find("title") or entry.find("atom:title", ns)
                pub_el = entry.find("pubDate") or entry.find("atom:published", ns)

                if title_el is None or title_el.text is None:
                    continue

                title = title_el.text.strip()
                published = pub_el.text.strip() if pub_el is not None and pub_el.text else ""

                # Score the headline
                title_lower = title.lower()
                matched = []
                score = 0
                for kw, weight in RISK_KEYWORDS.items():
                    if kw in title_lower:
                        matched.append(kw)
                        score += weight

                if score > 0:
                    items.append(NewsItem(
                        title=title,
                        source=name,
                        published=published,
                        risk_score=min(score, 30),
                        matched_keywords=matched,
                    ))

    except Exception as e:
        logger.debug(f"RSS fetch failed for {name}: {e}")
    return items


def fetch_news_intelligence() -> NewsIntelligence:
    """
    Gather real-time geopolitical intelligence from:
    1. Known ongoing conflicts database
    2. Live RSS news feeds
    """
    cache_key = "news_intel"
    if cache_key in _news_cache:
        ts, cached = _news_cache[cache_key]
        if (datetime.now() - ts).total_seconds() < _NEWS_CACHE_TTL:
            return cached

    intel = NewsIntelligence()
    intel.last_updated = datetime.now().strftime("%Y-%m-%d %H:%M")

    # ── 1. Known ongoing conflicts (always active) ──
    active_events = []
    for event in KNOWN_GEOPOLITICAL_EVENTS:
        if event["status"] in ("ACTIVE", "ONGOING", "ELEVATED"):
            active_events.append({
                "event": event["event"],
                "severity": event["severity"],
                "status": event["status"],
                "impact": event["impact"],
                "market_impact": event["market_impact"],
            })
    intel.active_conflicts = active_events
    intel.conflict_count = len(active_events)

    # Base score from known conflicts
    base_score = 0
    for event in active_events:
        if event["severity"] == "HIGH":
            base_score += 20
        elif event["severity"] == "MODERATE":
            base_score += 10
        elif event["severity"] == "LOW":
            base_score += 5

    # ── 2. Live news feed scanning ──
    all_news: list[NewsItem] = []
    for name, url in RSS_FEEDS:
        try:
            items = _fetch_rss_feed(name, url)
            all_news.extend(items)
        except Exception as e:
            logger.debug(f"Feed {name} failed: {e}")

    # Sort by risk score
    all_news.sort(key=lambda x: x.risk_score, reverse=True)

    # Top risk headlines
    intel.risk_headlines = [
        {"title": n.title, "source": n.source, "score": n.risk_score}
        for n in all_news[:10]
    ]

    # News-based score boost
    news_score = 0
    if all_news:
        # Average of top 5 headlines
        top_scores = [n.risk_score for n in all_news[:5]]
        news_score = sum(top_scores) / len(top_scores) if top_scores else 0
        # Scale to 0-30 range
        news_score = min(news_score * 1.5, 30)

    # India-specific events
    india_keywords = ["india", "nifty", "sensex", "rbi", "modi", "rupee", "fii", "sebi"]
    for n in all_news:
        title_lower = n.title.lower()
        if any(kw in title_lower for kw in india_keywords):
            intel.india_impact_events.append(n.title)

    # ── 3. Compile recent events summary ──
    recent = []
    for event in active_events:
        severity_emoji = "🔴" if event["severity"] == "HIGH" else "🟠" if event["severity"] == "MODERATE" else "🟡"
        recent.append(f"{severity_emoji} {event['event']} [{event['status']}] — {event['impact']}")

    if all_news:
        recent.append(f"📰 {len(all_news)} risk-related headlines detected in last scan")
        for n in all_news[:3]:
            recent.append(f"  📌 {n.title} ({n.source})")

    intel.recent_events = recent

    # ── Final score ──
    total_score = min(base_score + news_score, 100)
    intel.news_risk_score = round(total_score, 1)

    # Cache
    _news_cache[cache_key] = (datetime.now(), intel)

    return intel


def get_enhanced_geo_events(macro: dict) -> tuple[list[str], float]:
    """
    Combine known conflicts + news feeds + market proxies for
    comprehensive event list. Returns (events_list, bonus_score).
    """
    try:
        news_intel = fetch_news_intelligence()
    except Exception as e:
        logger.warning(f"News intelligence failed: {e}")
        return [], 0.0

    events = []
    bonus_score = 0.0

    # Known active conflicts
    for conflict in news_intel.active_conflicts:
        severity = conflict["severity"]
        emoji = "🔴" if severity == "HIGH" else "🟠" if severity == "MODERATE" else "🟡"
        events.append(f"{emoji} {conflict['event']} [{conflict['status']}] — {conflict['market_impact']}")
        if severity == "HIGH":
            bonus_score += 12
        elif severity == "MODERATE":
            bonus_score += 6

    # Live news risk headlines
    if news_intel.risk_headlines:
        top_headlines = news_intel.risk_headlines[:3]
        for hl in top_headlines:
            events.append(f"📰 {hl['title']} ({hl['source']})")
            bonus_score += min(hl["score"] * 0.5, 5)

    # India-specific
    if news_intel.india_impact_events:
        for evt in news_intel.india_impact_events[:2]:
            events.append(f"🇮🇳 {evt}")
            bonus_score += 3

    events.append(f"🕐 News last scanned: {news_intel.last_updated}")

    return events, min(bonus_score, 40)
