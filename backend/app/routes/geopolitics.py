"""
Geopolitics & Global Risk routes.

Provides dedicated geopolitical intelligence with:
- Active conflicts with market impact + actionable suggestions
- Live risk headlines with source attribution
- Geopolitical risk score with trend
- India-specific risk assessment
- Commodity correlation with geo events
"""

import logging
from datetime import datetime

from fastapi import APIRouter

from app.strategy.news_intelligence import (
    fetch_news_intelligence,
    KNOWN_GEOPOLITICAL_EVENTS,
    RSS_FEEDS,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["geopolitics"])

# Actionable suggestions for each conflict type
CONFLICT_SUGGESTIONS = {
    "Russia-Ukraine War": {
        "portfolio_action": "HEDGE",
        "suggestions": [
            "Increase gold allocation by 5-10% as safe haven",
            "Consider energy sector ETFs (ONGC, Reliance) for oil price upside",
            "Reduce European-exposed stocks if escalation",
            "Add defense stocks: HAL, BEL, Bharat Dynamics to watchlist",
            "Monitor wheat/grain futures — consider agri ETFs",
        ],
        "assets_to_watch": ["Gold", "Crude Oil", "Natural Gas", "Defense Stocks", "Wheat"],
        "risk_direction": "Bullish for Gold & Oil, Bearish for European equities",
    },
    "Iran-Israel / Middle East Conflict": {
        "portfolio_action": "DEFENSIVE",
        "suggestions": [
            "Oil prices likely to spike — hold energy positions",
            "Increase gold allocation immediately on escalation",
            "Avoid shipping/logistics stocks during Red Sea disruptions",
            "Monitor VIX — buy protection if VIX < 15 before escalation",
            "Consider inverse ETFs if war escalates to direct confrontation",
        ],
        "assets_to_watch": ["Crude Oil", "Gold", "VIX", "Shipping Rates", "USD/INR"],
        "risk_direction": "Bullish for Oil & Gold, Bearish for EM equities",
    },
    "US-China Trade & Tech Tensions": {
        "portfolio_action": "SELECTIVE",
        "suggestions": [
            "Reduce China-dependent supply chain stocks",
            "Semiconductor stocks volatile — wait for clarity before entry",
            "India may benefit from China+1 strategy — watch manufacturing sector",
            "Monitor Taiwan Strait developments closely",
            "Consider domestic consumption plays over export-dependent stocks",
        ],
        "assets_to_watch": ["Semiconductors", "USD/CNY", "Taiwan Index", "Nifty IT", "DXY"],
        "risk_direction": "Mixed — India could benefit from supply chain shifts",
    },
    "India-Pakistan / India-China Border Tensions": {
        "portfolio_action": "MONITOR",
        "suggestions": [
            "Defense stocks (HAL, BEL, BDL) typically rally on border tensions",
            "Watch for FII outflows — could create buying opportunities",
            "INR may weaken — consider USD-hedged positions",
            "NIFTY may dip 3-5% on escalation — keep cash ready for buying",
            "Avoid leveraged positions during high tension periods",
        ],
        "assets_to_watch": ["INR/USD", "FII Flows", "Defense Sector", "NIFTY", "Gold"],
        "risk_direction": "Short-term bearish for Indian equities, bullish for defense",
    },
    "Red Sea / Suez Shipping Disruptions": {
        "portfolio_action": "HEDGE",
        "suggestions": [
            "Shipping costs increase — affects import-heavy companies negatively",
            "Oil transport risk — energy prices may stay elevated",
            "Container shipping stocks may benefit (short term)",
            "Monitor inflation data — supply chain disruptions are inflationary",
            "Companies with domestic supply chains are relatively safe",
        ],
        "assets_to_watch": ["Shipping Index", "Crude Oil", "CPI Data", "Container Rates"],
        "risk_direction": "Inflationary — bearish for rate-sensitive sectors",
    },
}

# General news-based suggestions
NEWS_KEYWORD_SUGGESTIONS = {
    "sanctions": "New sanctions may disrupt trade flows. Monitor affected sectors and consider hedging exposure.",
    "tariff": "Tariff changes affect import costs. Review portfolio for tariff-exposed companies.",
    "nuclear": "Nuclear escalation risk is extreme. Move to maximum defensive allocation immediately.",
    "missile": "Military escalation detected. Increase gold allocation and reduce equity exposure.",
    "ceasefire": "Ceasefire signals reduce risk. Consider gradually increasing equity exposure.",
    "recession": "Recession signals detected. Shift to defensive sectors: FMCG, Pharma, Utilities.",
    "oil shock": "Oil price shock incoming. Energy longs profitable but broader market at risk.",
    "trade war": "Trade war escalation. Domestic-focused companies safer than exporters.",
    "pandemic": "Health crisis detected. Pharma/healthcare may benefit. Avoid travel/hospitality.",
    "default": "Sovereign default risk. Avoid affected currency/bond exposure. Increase safe havens.",
}


def _get_suggestion_for_headline(title: str) -> str:
    """Generate actionable suggestion based on headline keywords."""
    title_lower = title.lower()
    for keyword, suggestion in NEWS_KEYWORD_SUGGESTIONS.items():
        if keyword in title_lower:
            return suggestion
    return "Monitor this development. Assess potential market impact before taking action."


@router.get("/api/geopolitics/overview")
async def geopolitics_overview():
    """Full geopolitical intelligence overview."""
    try:
        intel = fetch_news_intelligence()

        # Enhance conflicts with suggestions
        enhanced_conflicts = []
        for conflict in intel.active_conflicts:
            event_name = conflict["event"]
            suggestions = CONFLICT_SUGGESTIONS.get(event_name, {
                "portfolio_action": "MONITOR",
                "suggestions": ["Monitor developments and adjust allocation if needed"],
                "assets_to_watch": ["Gold", "VIX"],
                "risk_direction": "Uncertain — await further clarity",
            })

            enhanced_conflicts.append({
                **conflict,
                "portfolio_action": suggestions["portfolio_action"],
                "suggestions": suggestions["suggestions"],
                "assets_to_watch": suggestions["assets_to_watch"],
                "risk_direction": suggestions["risk_direction"],
            })

        # Enhance headlines with sources and suggestions
        enhanced_headlines = []
        for hl in intel.risk_headlines:
            enhanced_headlines.append({
                **hl,
                "suggestion": _get_suggestion_for_headline(hl["title"]),
            })

        # Risk level classification
        score = intel.news_risk_score
        if score >= 70:
            risk_level = "CRITICAL"
            overall_action = "MAXIMUM DEFENSE — Move 50%+ to gold/cash immediately"
        elif score >= 50:
            risk_level = "HIGH"
            overall_action = "DEFENSIVE — Reduce equity to 30%, increase gold/cash"
        elif score >= 30:
            risk_level = "ELEVATED"
            overall_action = "CAUTIOUS — Maintain hedges, avoid new aggressive positions"
        elif score >= 15:
            risk_level = "MODERATE"
            overall_action = "NORMAL — Standard risk management, monitor key developments"
        else:
            risk_level = "LOW"
            overall_action = "RISK-ON — Geo risk is minimal, focus on technical setups"

        return {
            "risk_score": intel.news_risk_score,
            "risk_level": risk_level,
            "overall_action": overall_action,
            "conflict_count": intel.conflict_count,
            "active_conflicts": enhanced_conflicts,
            "risk_headlines": enhanced_headlines,
            "india_impact_events": intel.india_impact_events,
            "last_updated": intel.last_updated,
            "data_sources": [name for name, _ in RSS_FEEDS],
            "known_events_db_count": len(KNOWN_GEOPOLITICAL_EVENTS),
        }

    except Exception as e:
        logger.error(f"Geopolitics overview failed: {e}")
        return {
            "risk_score": 0,
            "risk_level": "UNKNOWN",
            "overall_action": "Data unavailable — use manual assessment",
            "conflict_count": 0,
            "active_conflicts": [],
            "risk_headlines": [],
            "india_impact_events": [],
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "data_sources": [],
            "known_events_db_count": 0,
        }


@router.get("/api/geopolitics/conflicts")
async def geopolitics_conflicts():
    """Detailed conflict data with known events database."""
    enhanced = []
    for event in KNOWN_GEOPOLITICAL_EVENTS:
        suggestions = CONFLICT_SUGGESTIONS.get(event["event"], {
            "portfolio_action": "MONITOR",
            "suggestions": ["Monitor and assess impact"],
            "assets_to_watch": [],
            "risk_direction": "Uncertain",
        })
        enhanced.append({
            **event,
            **suggestions,
        })
    return {"conflicts": enhanced}


@router.get("/api/geopolitics/headlines")
async def geopolitics_headlines():
    """Live risk headlines with source and suggestion."""
    intel = fetch_news_intelligence()
    return {
        "headlines": [
            {
                **hl,
                "suggestion": _get_suggestion_for_headline(hl["title"]),
            }
            for hl in intel.risk_headlines
        ],
        "total_scanned": len(intel.risk_headlines),
        "last_updated": intel.last_updated,
    }
