"""
Market Intelligence Engine — Expert-level stock analysis layer.

Provides:
  1. Target & Stop Loss with P&L % for every scanned stock
  2. Geopolitical / News-based risk assessment (using VIX, Gold, Oil, DXY proxies)
  3. Earnings momentum proxy (quarterly performance via price action around quarters)
  4. RECOMMENDED category — stocks that deserve special attention with reasons
  5. Enhanced reasoning with actionable trade setup details
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd

from app.config import settings

logger = logging.getLogger(__name__)

# ─── Cache ─────────────────────────────────────────────
_intelligence_cache: dict = {}
_CACHE_TTL = 1800  # 30 minutes


# ═══════════════════════════════════════════════════════
# 1. Geopolitical & Macro Event Risk Assessment
# ═══════════════════════════════════════════════════════

@dataclass
class GeoRiskAssessment:
    """Assesses geopolitical risk using market proxies (no external API needed)."""
    risk_level: str = "LOW"           # LOW / MODERATE / HIGH / EXTREME
    risk_score: float = 0.0           # 0 - 100
    events: list = field(default_factory=list)   # detected risk events
    safe_haven_flow: bool = False     # gold/bonds rallying
    currency_stress: bool = False     # DXY spiking
    oil_shock: bool = False           # crude oil volatile
    vix_fear: bool = False            # VIX elevated
    defense_bias: str = "NEUTRAL"     # RISK_ON / NEUTRAL / DEFENSIVE / CASH


def assess_geopolitical_risk(macro: dict) -> GeoRiskAssessment:
    """
    Detect geopolitical/macro stress using:
    1. Real news feeds (RSS) — actual conflicts, wars, sanctions
    2. Known ongoing events database — Russia-Ukraine, Iran, etc.
    3. Market proxies — VIX, Gold, Oil, DXY confirm stress
    """
    assessment = GeoRiskAssessment()
    events = []
    score = 0.0

    # ── 1. Real news intelligence (LIVE conflicts & headlines) ──
    try:
        from app.strategy.news_intelligence import get_enhanced_geo_events
        news_events, news_score = get_enhanced_geo_events(macro)
        events.extend(news_events)
        score += news_score
    except Exception as e:
        logger.warning(f"News intelligence unavailable: {e}")

    # ── 2. Market proxy confirmation ──
    vix = macro.get("vix") or 0
    gold_above_50dma = macro.get("gold_above_50dma", False)
    gold_rs = macro.get("gold_rs_vs_nifty") or 0
    oil_spike = macro.get("oil_spike", False)
    dxy_breakout = macro.get("dxy_breakout", False)
    nifty_above_200 = macro.get("nifty_above_200dma", False)
    sp500_above_200 = macro.get("sp500_above_200dma", True)

    # VIX Fear Assessment
    if vix > 30:
        score += 35
        assessment.vix_fear = True
        events.append(f"🔴 Extreme fear — VIX at {vix:.1f} (>30) signals panic/crisis")
    elif vix > 22:
        score += 20
        assessment.vix_fear = True
        events.append(f"🟠 Elevated fear — VIX at {vix:.1f} (>22) indicates heightened uncertainty")
    elif vix > 18:
        score += 10
        events.append(f"🟡 Mild caution — VIX at {vix:.1f} (>18) above comfort zone")
    else:
        events.append(f"🟢 Low fear — VIX at {vix:.1f} indicates calm markets")

    # Safe Haven Flow (Gold rallying = money moving to safety)
    if gold_above_50dma and gold_rs > 0.5:
        score += 20
        assessment.safe_haven_flow = True
        events.append(f"🥇 Safe haven demand — Gold outperforming NIFTY (RS: {gold_rs:.2f}), war/crisis hedging active")
    elif gold_above_50dma:
        score += 8
        events.append("🥇 Gold above 50DMA — mild defensive positioning detected")

    # Oil Shock (wars, supply disruptions)
    if oil_spike:
        score += 15
        assessment.oil_shock = True
        events.append("🛢️ Oil price shock — 15%+ above 50DMA, suggests supply disruption or geopolitical escalation")
    
    # Currency Stress (DXY breakout = EM pressure)
    if dxy_breakout:
        score += 12
        assessment.currency_stress = True
        events.append("💱 Dollar strength breakout — strong DXY pressures EM currencies & Indian markets")

    # Global risk-off (S&P500 below 200DMA)
    if not sp500_above_200:
        score += 10
        events.append("🌍 Global risk-off — S&P 500 below 200DMA, global bear pressure")

    # India-specific weakness
    if not nifty_above_200:
        score += 10
        events.append("📉 NIFTY below 200DMA — domestic market in bearish territory")

    # Combined stress signals
    combined_stress = sum([assessment.vix_fear, assessment.safe_haven_flow,
                           assessment.oil_shock, assessment.currency_stress])
    if combined_stress >= 3:
        score += 15
        events.append("⚠️ Multiple stress signals active — probable geopolitical crisis (war/sanctions/trade war)")

    score = min(score, 100)
    assessment.risk_score = round(score, 1)
    assessment.events = events

    # Risk level classification
    if score >= 70:
        assessment.risk_level = "EXTREME"
        assessment.defense_bias = "CASH"
    elif score >= 50:
        assessment.risk_level = "HIGH"
        assessment.defense_bias = "DEFENSIVE"
    elif score >= 30:
        assessment.risk_level = "MODERATE"
        assessment.defense_bias = "NEUTRAL"
    else:
        assessment.risk_level = "LOW"
        assessment.defense_bias = "RISK_ON"

    return assessment


# ═══════════════════════════════════════════════════════
# 2. Earnings Momentum Proxy
# ═══════════════════════════════════════════════════════

@dataclass
class EarningsInsight:
    """Quarterly earnings momentum derived from price action."""
    earnings_momentum: str = "NEUTRAL"  # STRONG / POSITIVE / NEUTRAL / WEAK / NEGATIVE
    earnings_score: float = 50.0        # 0 - 100
    quarterly_trend: str = ""           # description
    post_earnings_drift: float = 0.0    # recent quarter performance
    revenue_proxy: float = 0.0          # volume-weighted price strength


def analyze_earnings_momentum(df: pd.DataFrame, symbol: str) -> EarningsInsight:
    """
    Estimate earnings momentum from price action patterns.
    Good quarterly results → stock gaps up and holds. Bad → gaps down.
    We detect this from quarterly price performance + volume surges.
    """
    insight = EarningsInsight()

    if df is None or len(df) < 130:
        return insight

    close = df["close"]
    volume = df["volume"] if "volume" in df.columns else pd.Series([0] * len(df))

    # --- Quarterly performance (last 63 trading days ≈ 1 quarter) ---
    if len(close) >= 63:
        q1_return = ((close.iloc[-1] - close.iloc[-63]) / close.iloc[-63] * 100)
        insight.post_earnings_drift = round(q1_return, 2)
    else:
        q1_return = 0

    # --- Q-o-Q improvement ---
    if len(close) >= 126:
        q2_return = ((close.iloc[-63] - close.iloc[-126]) / close.iloc[-126] * 100)
    else:
        q2_return = 0

    qoq_improving = q1_return > q2_return

    # --- Volume-weighted strength (earnings beats cause volume surges) ---
    if len(volume) >= 63 and volume.iloc[-63:].mean() > 0:
        recent_vol = volume.iloc[-21:].mean()
        avg_vol = volume.iloc[-63:].mean()
        vol_ratio = recent_vol / avg_vol if avg_vol > 0 else 1.0
        vol_weighted_strength = q1_return * min(vol_ratio, 2.0)
        insight.revenue_proxy = round(vol_weighted_strength, 2)
    else:
        vol_weighted_strength = q1_return

    # --- Score calculation ---
    score = 50.0
    if q1_return > 15:
        score += 25
    elif q1_return > 8:
        score += 15
    elif q1_return > 3:
        score += 8
    elif q1_return < -15:
        score -= 25
    elif q1_return < -8:
        score -= 15
    elif q1_return < -3:
        score -= 8

    if qoq_improving:
        score += 10
    else:
        score -= 5

    if vol_weighted_strength > 15:
        score += 10
    elif vol_weighted_strength < -10:
        score -= 10

    # --- Gap detection (earnings day proxy) ---
    # Look for large gap-ups in recent 63 days (earnings day effect)
    if len(df) >= 63:
        daily_returns = close.pct_change().iloc[-63:] * 100
        big_gaps = daily_returns[daily_returns.abs() > 3.0]
        if len(big_gaps) > 0:
            avg_gap = big_gaps.mean()
            if avg_gap > 2:
                score += 8
            elif avg_gap < -2:
                score -= 8

    score = max(0, min(100, score))
    insight.earnings_score = round(score, 1)

    # --- Classification ---
    if score >= 80:
        insight.earnings_momentum = "STRONG"
        insight.quarterly_trend = f"Excellent quarterly momentum — {q1_return:+.1f}% this quarter"
        if qoq_improving:
            insight.quarterly_trend += ", accelerating QoQ"
    elif score >= 62:
        insight.earnings_momentum = "POSITIVE"
        insight.quarterly_trend = f"Solid quarterly performance — {q1_return:+.1f}% this quarter"
    elif score >= 40:
        insight.earnings_momentum = "NEUTRAL"
        insight.quarterly_trend = f"Flat quarterly performance — {q1_return:+.1f}%"
    elif score >= 25:
        insight.earnings_momentum = "WEAK"
        insight.quarterly_trend = f"Weak quarter — {q1_return:+.1f}%, possible earnings miss"
    else:
        insight.earnings_momentum = "NEGATIVE"
        insight.quarterly_trend = f"Poor quarterly results — {q1_return:+.1f}%, likely earnings disappointment"

    return insight


# ═══════════════════════════════════════════════════════
# 3. Enhanced Target / Stop Loss / P&L Calculator
# ═══════════════════════════════════════════════════════

@dataclass
class TradeSetup:
    """Complete trade setup with targets, stop loss, and P&L projections."""
    entry_price: float = 0.0
    stop_loss: float = 0.0
    target_1: float = 0.0           # Conservative target (1.5R)
    target_2: float = 0.0           # Normal target (2R)
    target_3: float = 0.0           # Aggressive target (3R)
    risk_per_share: float = 0.0
    risk_pct: float = 0.0           # risk from entry as %
    reward_pct_t1: float = 0.0      # reward to target 1 as %
    reward_pct_t2: float = 0.0      # reward to target 2 as %
    reward_pct_t3: float = 0.0      # reward to target 3 as %
    risk_reward_t1: float = 0.0     # R:R ratio for T1
    risk_reward_t2: float = 0.0     # R:R ratio for T2
    risk_reward_t3: float = 0.0     # R:R ratio for T3
    atr_stop: float = 0.0           # ATR-based stop loss
    support_levels: list = field(default_factory=list)   # nearby supports
    resistance_levels: list = field(default_factory=list) # nearby resistances


def compute_trade_setup(df: pd.DataFrame, entry_price: float, swing_low: float) -> TradeSetup:
    """
    Compute comprehensive trade setup with multiple targets,
    support/resistance levels, and ATR-based stops.
    """
    setup = TradeSetup()

    if df is None or len(df) < 50 or entry_price <= 0 or swing_low <= 0:
        return setup

    close = df["close"]
    high = df["high"]
    low = df["low"]

    setup.entry_price = round(entry_price, 2)

    # --- ATR-based stop (more dynamic than swing low) ---
    tr = pd.DataFrame({
        "hl": high - low,
        "hc": abs(high - close.shift(1)),
        "lc": abs(low - close.shift(1))
    }).max(axis=1)
    atr_14 = tr.rolling(14).mean().iloc[-1]
    atr_stop = entry_price - (2.0 * atr_14)

    # Use the HIGHER of swing_low and ATR stop (tighter stop for less risk)
    stop_loss = max(swing_low, atr_stop) if atr_stop > 0 else swing_low
    # But don't make stop above entry
    if stop_loss >= entry_price:
        stop_loss = swing_low
    if stop_loss >= entry_price:
        stop_loss = entry_price * 0.95  # fallback 5% stop

    setup.stop_loss = round(stop_loss, 2)
    setup.atr_stop = round(atr_stop, 2) if atr_stop > 0 else 0

    risk = entry_price - stop_loss
    if risk <= 0:
        risk = entry_price * 0.03  # fallback to 3%
    setup.risk_per_share = round(risk, 2)

    # --- Multiple Targets ---
    setup.target_1 = round(entry_price + (risk * 1.5), 2)
    setup.target_2 = round(entry_price + (risk * 2.0), 2)
    setup.target_3 = round(entry_price + (risk * 3.0), 2)

    # --- P&L percentages ---
    setup.risk_pct = round((risk / entry_price) * 100, 2)
    setup.reward_pct_t1 = round(((setup.target_1 - entry_price) / entry_price) * 100, 2)
    setup.reward_pct_t2 = round(((setup.target_2 - entry_price) / entry_price) * 100, 2)
    setup.reward_pct_t3 = round(((setup.target_3 - entry_price) / entry_price) * 100, 2)

    # --- R:R Ratios ---
    setup.risk_reward_t1 = 1.5
    setup.risk_reward_t2 = 2.0
    setup.risk_reward_t3 = 3.0

    # --- Support & Resistance from recent pivots ---
    lookback_data = df.tail(100)
    supports = _find_support_levels(lookback_data, close.iloc[-1])
    resistances = _find_resistance_levels(lookback_data, close.iloc[-1])
    setup.support_levels = supports[:3]   # top 3 supports
    setup.resistance_levels = resistances[:3]  # top 3 resistances

    return setup


def _find_support_levels(df: pd.DataFrame, current_price: float) -> list:
    """Find support levels from swing lows."""
    supports = []
    low = df["low"]
    for i in range(2, len(low) - 2):
        if low.iloc[i] < low.iloc[i-1] and low.iloc[i] < low.iloc[i-2] and \
           low.iloc[i] < low.iloc[i+1] and low.iloc[i] < low.iloc[i+2]:
            if low.iloc[i] < current_price:
                supports.append(round(float(low.iloc[i]), 2))
    supports = sorted(set(supports), reverse=True)  # closest first
    return supports[:5]


def _find_resistance_levels(df: pd.DataFrame, current_price: float) -> list:
    """Find resistance levels from swing highs."""
    resistances = []
    high = df["high"]
    for i in range(2, len(high) - 2):
        if high.iloc[i] > high.iloc[i-1] and high.iloc[i] > high.iloc[i-2] and \
           high.iloc[i] > high.iloc[i+1] and high.iloc[i] > high.iloc[i+2]:
            if high.iloc[i] > current_price:
                resistances.append(round(float(high.iloc[i]), 2))
    resistances = sorted(set(resistances))  # closest first
    return resistances[:5]


# ═══════════════════════════════════════════════════════
# 4. Expert Recommendation Engine
# ═══════════════════════════════════════════════════════

@dataclass
class ExpertRecommendation:
    """Complete expert analysis for a stock."""
    recommendation: str = "HOLD"       # BUY / HOLD / AVOID / RECOMMENDED
    conviction: str = "LOW"            # LOW / MEDIUM / HIGH
    conviction_score: float = 0.0      # 0-100
    primary_reason: str = ""           # Main reason for recommendation
    reasons: list = field(default_factory=list)   # All reasons
    trade_setup: Optional[TradeSetup] = None
    earnings: Optional[EarningsInsight] = None
    category_tag: str = ""             # e.g. "MOMENTUM PICK", "VALUE BUY", "EARNINGS PLAY"
    risk_warning: str = ""             # any risk flags


def generate_expert_recommendation(
    signal,                  # Signal dataclass from signals.py
    df: pd.DataFrame,        # OHLCV data
    geo_risk: GeoRiskAssessment,
) -> ExpertRecommendation:
    """
    Generate a comprehensive expert recommendation considering:
    - Technical setup (signal criteria)
    - Trade setup (target/SL/P&L)
    - Earnings momentum
    - Geopolitical risk environment
    """
    expert = ExpertRecommendation()

    if signal is None:
        return expert

    # --- Earnings Analysis ---
    earnings = analyze_earnings_momentum(df, signal.symbol)
    expert.earnings = earnings

    # --- Trade Setup ---
    trade_setup = compute_trade_setup(df, signal.entry_price, signal.stop_loss)
    expert.trade_setup = trade_setup

    # --- Score Calculation ---
    score = 0
    reasons = []

    # Technical criteria (max 40 points)
    tech_score = signal.criteria_met * 5.0  # 8 criteria * 5.0 = 40
    score += tech_score
    if signal.criteria_met >= 7:
        reasons.append(f"✅ Strong technical setup — {signal.criteria_met}/8 criteria met")
    elif signal.criteria_met >= 4:
        reasons.append(f"📊 Partial setup — {signal.criteria_met}/8 criteria met, watch for improvement")
    else:
        reasons.append(f"❌ Weak setup — only {signal.criteria_met}/8 criteria")

    # Trend alignment (max 15 points)
    if signal.above_200dma and signal.dma50_trending_up:
        score += 15
        reasons.append("📈 Strong uptrend — above 200DMA with rising 50DMA")
    elif signal.above_200dma:
        score += 10
        reasons.append("📈 In uptrend — above 200DMA")
    else:
        reasons.append("📉 Downtrend — below 200DMA, higher risk")

    # Earnings factor (max 20 points)
    if earnings.earnings_score >= 70:
        score += 20
        reasons.append(f"💰 {earnings.quarterly_trend}")
    elif earnings.earnings_score >= 55:
        score += 12
        reasons.append(f"💰 {earnings.quarterly_trend}")
    elif earnings.earnings_score < 35:
        score -= 10
        reasons.append(f"⚠️ {earnings.quarterly_trend}")

    # Geopolitical adjustment (max -25 points)
    if geo_risk.risk_level == "EXTREME":
        score -= 25
        reasons.append(f"🌐 EXTREME geo risk ({geo_risk.risk_score:.0f}/100) — avoid new positions")
    elif geo_risk.risk_level == "HIGH":
        score -= 15
        reasons.append(f"🌐 HIGH geo risk ({geo_risk.risk_score:.0f}/100) — reduce position sizes")
    elif geo_risk.risk_level == "MODERATE":
        score -= 5
        reasons.append(f"🌐 Moderate geo risk ({geo_risk.risk_score:.0f}/100) — normal caution")

    # Volume confirmation (max 10 points)
    if signal.volume_contracting and signal.pullback_to_20dma:
        score += 10
        reasons.append("📉 Volume contracting on pullback — healthy correction, bullish")
    elif signal.volume_ratio > 1.5:
        score -= 5
        reasons.append(f"⚠️ High volume ratio ({signal.volume_ratio:.1f}x) — could be distribution")

    # RSI sweet spot (max 10 points)
    if signal.rsi_in_zone:
        score += 10
        reasons.append(f"✅ RSI in sweet spot ({signal.rsi:.0f})")
    elif signal.rsi > 75:
        score -= 10
        reasons.append(f"⚠️ RSI overbought ({signal.rsi:.0f}) — high risk of pullback")
        expert.risk_warning = "Overbought — likely to correct"
    elif signal.rsi < 30:
        score -= 5
        reasons.append(f"⚠️ RSI oversold ({signal.rsi:.0f}) — could be value trap")

    # CCI confirmation (max 8 points)
    if hasattr(signal, 'cci_in_zone') and signal.cci_in_zone:
        score += 8
        reasons.append(f"✅ CCI in bullish zone ({signal.cci:.0f}) — momentum supports entry")
    elif hasattr(signal, 'cci') and signal.cci > 200:
        score -= 5
        reasons.append(f"⚠️ CCI extreme ({signal.cci:.0f}) — overbought risk")
    elif hasattr(signal, 'cci') and signal.cci < -200:
        score -= 5
        reasons.append(f"⚠️ CCI extreme ({signal.cci:.0f}) — heavy selling pressure")

    # Supertrend confirmation (max 8 points)
    if hasattr(signal, 'supertrend_bullish') and signal.supertrend_bullish:
        score += 8
        reasons.append(f"✅ Supertrend BULLISH — trend supports longs")
    elif hasattr(signal, 'supertrend_bullish'):
        score -= 5
        reasons.append(f"⚠️ Supertrend BEARISH — trend against longs")

    # R:R Quality (max 5 points)
    if trade_setup.risk_reward_t2 >= 2.0 and trade_setup.risk_pct < 5:
        score += 5
        reasons.append(f"✅ Good R:R setup — risk {trade_setup.risk_pct:.1f}%, reward {trade_setup.reward_pct_t2:.1f}%")

    score = max(0, min(100, score))
    expert.conviction_score = round(score, 1)
    expert.reasons = reasons

    # --- Final Recommendation ---
    if geo_risk.risk_level == "EXTREME":
        expert.recommendation = "AVOID"
        expert.conviction = "HIGH"
        expert.primary_reason = "Extreme geopolitical risk — preserve capital"
        expert.category_tag = "⚠️ RISK ALERT"
    elif score >= 75:
        expert.recommendation = "RECOMMENDED"
        expert.conviction = "HIGH"
        expert.primary_reason = reasons[0] if reasons else "Strong multi-factor setup"
        # Categorize
        if earnings.earnings_score >= 70:
            expert.category_tag = "🏆 EARNINGS + MOMENTUM"
        elif signal.criteria_met >= 5:
            expert.category_tag = "🎯 PULLBACK SETUP"
        else:
            expert.category_tag = "⭐ TOP PICK"
    elif score >= 55:
        expert.recommendation = "BUY"
        expert.conviction = "MEDIUM"
        expert.primary_reason = reasons[0] if reasons else "Technical setup forming"
        if signal.criteria_met >= 5:
            expert.category_tag = "🎯 SWING SETUP"
        else:
            expert.category_tag = "📊 MOMENTUM"
    elif score >= 30:
        expert.recommendation = "HOLD"
        expert.conviction = "LOW"
        expert.primary_reason = "Setup incomplete — monitor for development"
        expert.category_tag = "👁️ WATCHLIST"
    else:
        expert.recommendation = "AVOID"
        expert.conviction = "MEDIUM"
        expert.primary_reason = reasons[-1] if reasons else "Weak setup, unfavorable conditions"
        expert.category_tag = "🚫 AVOID"

    return expert


# ═══════════════════════════════════════════════════════
# 5. Full Intelligence Report
# ═══════════════════════════════════════════════════════

@dataclass
class StockIntelligence:
    """Complete intelligence for a single stock."""
    symbol: str = ""
    clean_symbol: str = ""
    price: float = 0.0

    # Original signal data
    criteria_met: int = 0
    rsi: float = 0.0
    volume_ratio: float = 0.0
    above_200dma: bool = False
    dma50_trending_up: bool = False

    # Enhanced recommendation
    recommendation: str = "HOLD"
    conviction: str = "LOW"
    conviction_score: float = 0.0
    primary_reason: str = ""
    reasons: list = field(default_factory=list)
    category_tag: str = ""
    risk_warning: str = ""

    # Trade setup
    entry_price: float = 0.0
    stop_loss: float = 0.0
    target_1: float = 0.0
    target_2: float = 0.0
    target_3: float = 0.0
    risk_pct: float = 0.0
    reward_pct: float = 0.0
    risk_reward: str = ""
    support_levels: list = field(default_factory=list)
    resistance_levels: list = field(default_factory=list)

    # Earnings
    earnings_momentum: str = "NEUTRAL"
    earnings_score: float = 50.0
    quarterly_trend: str = ""

    # Reasoning (full)
    reasoning: str = ""


def compile_stock_intelligence(
    signal, df: pd.DataFrame, geo_risk: GeoRiskAssessment
) -> StockIntelligence:
    """Build complete intelligence report for a stock."""
    intel = StockIntelligence()

    if signal is None:
        return intel

    # Basic info
    intel.symbol = signal.symbol
    intel.clean_symbol = signal.symbol.replace(".NS", "")
    intel.price = signal.close
    intel.criteria_met = signal.criteria_met
    intel.rsi = signal.rsi
    intel.volume_ratio = signal.volume_ratio
    intel.above_200dma = signal.above_200dma
    intel.dma50_trending_up = signal.dma50_trending_up

    # Generate expert recommendation
    expert = generate_expert_recommendation(signal, df, geo_risk)

    intel.recommendation = expert.recommendation
    intel.conviction = expert.conviction
    intel.conviction_score = expert.conviction_score
    intel.primary_reason = expert.primary_reason
    intel.reasons = expert.reasons
    intel.category_tag = expert.category_tag
    intel.risk_warning = expert.risk_warning

    # Trade setup
    if expert.trade_setup:
        ts = expert.trade_setup
        intel.entry_price = ts.entry_price
        intel.stop_loss = ts.stop_loss
        intel.target_1 = ts.target_1
        intel.target_2 = ts.target_2
        intel.target_3 = ts.target_3
        intel.risk_pct = ts.risk_pct
        intel.reward_pct = ts.reward_pct_t2
        intel.risk_reward = f"1:{ts.risk_reward_t2:.1f}"
        intel.support_levels = ts.support_levels
        intel.resistance_levels = ts.resistance_levels

    # Earnings
    if expert.earnings:
        intel.earnings_momentum = expert.earnings.earnings_momentum
        intel.earnings_score = expert.earnings.earnings_score
        intel.quarterly_trend = expert.earnings.quarterly_trend

    # Build full reasoning string
    reasoning_parts = [expert.primary_reason]
    for r in expert.reasons[1:]:  # skip first (duplicate of primary)
        reasoning_parts.append(r)

    if expert.trade_setup and expert.trade_setup.entry_price > 0:
        ts = expert.trade_setup
        reasoning_parts.append(
            f"📊 Entry ₹{ts.entry_price} | SL ₹{ts.stop_loss} (-{ts.risk_pct:.1f}%) "
            f"| T1 ₹{ts.target_1} (+{ts.reward_pct_t1:.1f}%) "
            f"| T2 ₹{ts.target_2} (+{ts.reward_pct_t2:.1f}%) "
            f"| T3 ₹{ts.target_3} (+{ts.reward_pct_t3:.1f}%)"
        )

    intel.reasoning = " | ".join(reasoning_parts)

    return intel
