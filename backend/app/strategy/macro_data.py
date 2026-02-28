"""Macro & global data fetching — VIX, Gold, Oil, DXY, S&P 500, breadth."""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date
from typing import Optional
import logging

from app.config import settings

logger = logging.getLogger(__name__)

# ── In-memory TTL cache ──────────────────────────────────
_cache: dict[str, tuple[datetime, pd.DataFrame]] = {}


def _get_cached(key: str) -> Optional[pd.DataFrame]:
    if key in _cache:
        ts, df = _cache[key]
        if (datetime.now() - ts).total_seconds() < settings.CACHE_TTL_SECONDS:
            return df
    return None


def _set_cached(key: str, df: pd.DataFrame):
    _cache[key] = (datetime.now(), df)


def fetch_with_cache(symbol: str, period_years: int = 2) -> Optional[pd.DataFrame]:
    """Fetch OHLCV with in-memory cache."""
    cache_key = f"{symbol}_{period_years}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    try:
        end = datetime.now()
        start = end - timedelta(days=period_years * 365)
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"))

        if df.empty:
            logger.warning(f"No data for {symbol}")
            return None

        df.index = pd.to_datetime(df.index)
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)

        df.columns = [c.lower().replace(" ", "_") for c in df.columns]
        cols = [c for c in ["open", "high", "low", "close", "volume"] if c in df.columns]
        df = df[cols].copy()
        df.dropna(inplace=True)
        _set_cached(cache_key, df)
        return df

    except Exception as e:
        logger.error(f"Error fetching {symbol}: {e}")
        return None


# ── Specific fetchers ────────────────────────────────────
def fetch_nifty(years: int = 2) -> Optional[pd.DataFrame]:
    return fetch_with_cache(settings.NIFTY_SYMBOL, years)


def fetch_vix(years: int = 2) -> Optional[pd.DataFrame]:
    return fetch_with_cache(settings.VIX_SYMBOL, years)


def fetch_sp500(years: int = 2) -> Optional[pd.DataFrame]:
    return fetch_with_cache(settings.SP500_SYMBOL, years)


def fetch_dxy(years: int = 2) -> Optional[pd.DataFrame]:
    return fetch_with_cache(settings.DXY_SYMBOL, years)


def fetch_gold(years: int = 2) -> Optional[pd.DataFrame]:
    return fetch_with_cache(settings.GOLD_SYMBOL, years)


def fetch_oil(years: int = 2) -> Optional[pd.DataFrame]:
    return fetch_with_cache(settings.OIL_SYMBOL, years)


def fetch_gold_etf(years: int = 2) -> Optional[pd.DataFrame]:
    return fetch_with_cache(settings.GOLD_ETF_SYMBOL, years)


def fetch_silver_etf(years: int = 2) -> Optional[pd.DataFrame]:
    return fetch_with_cache(settings.SILVER_ETF_SYMBOL, years)


# ── Derived metrics ──────────────────────────────────────
def _safe_last(series: pd.Series, default=0.0):
    """Return last non-NaN value or default."""
    s = series.dropna()
    return float(s.iloc[-1]) if len(s) > 0 else default


def get_macro_snapshot() -> dict:
    """
    Collect all macro data points needed by the risk engine.
    Returns a flat dict of raw values.
    """
    result = {}

    # ── NIFTY ────────────────────────────────────
    nifty = fetch_nifty()
    if nifty is not None and len(nifty) > 200:
        c = nifty["close"]
        result["nifty_close"] = round(float(c.iloc[-1]), 2)
        result["nifty_200dma"] = round(float(c.rolling(200).mean().iloc[-1]), 2)
        result["nifty_50dma"] = round(float(c.rolling(50).mean().iloc[-1]), 2)
        result["nifty_above_200dma"] = result["nifty_close"] > result["nifty_200dma"]

        # 50 DMA slope (positive = uptrend)
        dma50 = c.rolling(50).mean()
        result["nifty_50dma_slope"] = round(float(dma50.diff(5).iloc[-1]), 2)

        # Lower-highs detection: compare last 2 swing highs
        highs_20 = c.rolling(20).max()
        recent_high = float(highs_20.iloc[-1])
        prev_high = float(highs_20.iloc[-21]) if len(highs_20) > 21 else recent_high
        result["nifty_lower_highs"] = recent_high < prev_high * 0.99

        # ATR expansion
        if "high" in nifty.columns and "low" in nifty.columns:
            atr14 = (nifty["high"] - nifty["low"]).rolling(14).mean()
            atr50 = (nifty["high"] - nifty["low"]).rolling(50).mean()
            result["atr_expansion"] = float(atr14.iloc[-1]) > float(atr50.iloc[-1]) * 1.2
        else:
            result["atr_expansion"] = False

        # Gap frequency (gaps > 0.5% in last 20 days)
        gaps = abs(nifty["open"].pct_change()) if "open" in nifty.columns else abs(c.pct_change())
        result["gap_frequency"] = int((gaps.tail(20) > 0.005).sum())
    else:
        result.update({
            "nifty_close": 0, "nifty_200dma": 0, "nifty_50dma": 0,
            "nifty_above_200dma": False, "nifty_50dma_slope": 0,
            "nifty_lower_highs": False, "atr_expansion": False, "gap_frequency": 0,
        })

    # ── VIX ──────────────────────────────────────
    vix = fetch_vix()
    if vix is not None and len(vix) > 20:
        c = vix["close"]
        result["vix"] = round(float(c.iloc[-1]), 2)
        result["vix_sma10"] = round(float(c.rolling(10).mean().iloc[-1]), 2)
        result["vix_rising"] = float(c.iloc[-1]) > float(c.rolling(10).mean().iloc[-1])
    else:
        result.update({"vix": 15.0, "vix_sma10": 15.0, "vix_rising": False})

    # ── Breadth (% of NIFTY stocks above 50 DMA) ─
    # Approximation: we check a subset of universe
    result["breadth_pct_above_50dma"] = _estimate_breadth()

    # ── S&P 500 ──────────────────────────────────
    sp = fetch_sp500()
    if sp is not None and len(sp) > 200:
        c = sp["close"]
        dma = c.rolling(200).mean()
        result["sp500_above_200dma"] = float(c.iloc[-1]) > float(dma.iloc[-1])
    else:
        result["sp500_above_200dma"] = True  # default safe

    # ── DXY (Dollar Index) ───────────────────────
    dxy = fetch_dxy()
    if dxy is not None and len(dxy) > 50:
        c = dxy["close"]
        dma50 = c.rolling(50).mean()
        result["dxy_breakout"] = float(c.iloc[-1]) > float(dma50.iloc[-1]) * 1.02
    else:
        result["dxy_breakout"] = False

    # ── Oil ──────────────────────────────────────
    oil = fetch_oil()
    if oil is not None and len(oil) > 50:
        c = oil["close"]
        dma50 = c.rolling(50).mean()
        spike_pct = (float(c.iloc[-1]) - float(dma50.iloc[-1])) / float(dma50.iloc[-1]) * 100
        result["oil_spike"] = spike_pct > settings.OIL_SPIKE_PCT
        result["oil_spike_pct"] = round(spike_pct, 2)
    else:
        result["oil_spike"] = False
        result["oil_spike_pct"] = 0

    # ── Gold ─────────────────────────────────────
    gold = fetch_gold()
    if gold is not None and len(gold) > 50:
        gc = gold["close"]
        result["gold_above_50dma"] = float(gc.iloc[-1]) > float(gc.rolling(50).mean().iloc[-1])

        # Gold relative strength vs NIFTY (20-day returns)
        if nifty is not None and len(nifty) > 20:
            common_idx = gc.index.intersection(nifty["close"].index)
            if len(common_idx) > 20:
                g_ret = gc.reindex(common_idx).pct_change(20).iloc[-1]
                n_ret = nifty["close"].reindex(common_idx).pct_change(20).iloc[-1]
                result["gold_rs_vs_nifty"] = round(float(g_ret - n_ret) * 100, 2)
            else:
                result["gold_rs_vs_nifty"] = 0.0
        else:
            result["gold_rs_vs_nifty"] = 0.0
    else:
        result["gold_above_50dma"] = False
        result["gold_rs_vs_nifty"] = 0.0

    # ── Extra features for AI model ──────────────
    if nifty is not None and len(nifty) > 20:
        c = nifty["close"]
        # 5-day and 20-day returns
        result["nifty_return_5d"] = round(float((c.iloc[-1] / c.iloc[-6] - 1) * 100), 2) if len(c) > 6 else 0.0
        result["nifty_return_20d"] = round(float((c.iloc[-1] / c.iloc[-21] - 1) * 100), 2) if len(c) > 21 else 0.0
        # 20-day volatility (annualised)
        daily_ret = c.pct_change().dropna().tail(20)
        result["nifty_volatility_20d"] = round(float(daily_ret.std() * (252 ** 0.5)), 4) if len(daily_ret) > 5 else 0.15
    else:
        result["nifty_return_5d"] = 0.0
        result["nifty_return_20d"] = 0.0
        result["nifty_volatility_20d"] = 0.15

    if vix is not None and len(vix) > 20:
        v = vix["close"]
        v_window = v.tail(20)
        result["vix_percentile_20d"] = round(float((v_window < v.iloc[-1]).sum() / len(v_window) * 100), 1)
    else:
        result["vix_percentile_20d"] = 50.0

    return result


def _estimate_breadth(sample_size: int = 30) -> float:
    """
    Estimate % of NIFTY stocks above 50 DMA.
    Uses a sample for speed; cached.
    """
    from app.strategy.universe import NIFTY_100_SYMBOLS, NIFTY_200_SYMBOLS
    import random

    cache_key = "breadth_estimate"
    cached = _get_cached(cache_key)
    if cached is not None:
        # cached is a DataFrame, but we stored a float sentinel
        return float(cached["value"].iloc[0])

    # Use NIFTY 200 for better breadth estimate, sample for speed
    universe = NIFTY_200_SYMBOLS
    sample = random.sample(universe, min(sample_size, len(universe)))
    above = 0
    total = 0

    for sym in sample:
        try:
            df = fetch_with_cache(sym, period_years=1)
            if df is not None and len(df) > 50:
                c = df["close"]
                if float(c.iloc[-1]) > float(c.rolling(50).mean().iloc[-1]):
                    above += 1
                total += 1
        except Exception:
            continue

    pct = (above / total * 100) if total > 0 else 50.0
    # Store as fake DataFrame for cache compatibility
    _set_cached(cache_key, pd.DataFrame({"value": [pct]}))
    return round(pct, 1)


def compute_market_sentiment() -> dict:
    """
    Compute overall market sentiment by combining macro indicators.
    Returns a dict with sentiment label, score (0-100), and components.
    0 = extreme fear, 100 = extreme greed.
    """
    macro = get_macro_snapshot()
    components = []
    total_score = 0.0
    total_weight = 0.0

    # ── 1. NIFTY Trend (weight 30) ───────────────────────
    nifty_score = 50.0
    nifty_trend = "Neutral"
    nifty_close = macro.get("nifty_close", 0)
    nifty_200 = macro.get("nifty_200dma", 0)
    nifty_50 = macro.get("nifty_50dma", 0)
    if nifty_close and nifty_200:
        dist_200 = ((nifty_close - nifty_200) / nifty_200) * 100
        dist_50 = ((nifty_close - nifty_50) / nifty_50) * 100 if nifty_50 else 0
        if dist_200 > 5:
            nifty_score = min(90, 70 + dist_200)
            nifty_trend = "Strong Uptrend"
        elif dist_200 > 0:
            nifty_score = 55 + dist_200 * 3
            nifty_trend = "Uptrend"
        elif dist_200 > -3:
            nifty_score = 40 + dist_200 * 3
            nifty_trend = "Weak"
        else:
            nifty_score = max(10, 30 + dist_200 * 2)
            nifty_trend = "Downtrend"
        # Boost/penalise based on 50 DMA
        if dist_50 > 0:
            nifty_score = min(100, nifty_score + 5)
        else:
            nifty_score = max(0, nifty_score - 5)
    total_score += nifty_score * 0.30
    total_weight += 0.30

    # ── 2. VIX Fear (weight 25) ──────────────────────────
    vix_score = 50.0
    vix_status = "Normal"
    vix = macro.get("vix", 15)
    if vix < 12:
        vix_score = 90
        vix_status = "Very Low (Complacent)"
    elif vix < 15:
        vix_score = 75
        vix_status = "Low (Calm)"
    elif vix < 18:
        vix_score = 55
        vix_status = "Normal"
    elif vix < 22:
        vix_score = 35
        vix_status = "Elevated"
    elif vix < 28:
        vix_score = 20
        vix_status = "High (Fear)"
    else:
        vix_score = 5
        vix_status = "Extreme Fear"
    # Penalise rising VIX
    if macro.get("vix_rising", False):
        vix_score = max(0, vix_score - 10)
        vix_status += " ↑"
    total_score += vix_score * 0.25
    total_weight += 0.25

    # ── 3. Breadth (weight 20) ───────────────────────────
    breadth = macro.get("breadth_pct_above_50dma", 50)
    breadth_score = min(100, max(0, breadth))  # directly maps 0-100
    if breadth > 70:
        breadth_status = "Strong (Broad Rally)"
    elif breadth > 50:
        breadth_status = "Healthy"
    elif breadth > 35:
        breadth_status = "Weakening"
    else:
        breadth_status = "Poor (Narrow Market)"
    total_score += breadth_score * 0.20
    total_weight += 0.20

    # ── 4. Global Factors (weight 15) ────────────────────
    global_score = 50.0
    global_flags = 0
    if macro.get("sp500_above_200dma", True):
        global_score += 15
        global_flags += 1
    else:
        global_score -= 15
    if macro.get("dxy_breakout", False):
        global_score -= 10  # strong dollar hurts EM
    else:
        global_score += 5
        global_flags += 1
    if macro.get("oil_spike", False):
        global_score -= 15  # oil spike hurts India
    else:
        global_score += 5
        global_flags += 1
    global_score = min(100, max(0, global_score))
    if global_flags >= 3:
        global_status = "Supportive"
    elif global_flags >= 2:
        global_status = "Mixed"
    else:
        global_status = "Adverse"
    total_score += global_score * 0.15
    total_weight += 0.15

    # ── 5. FII/DII proxy via Gold RS (weight 10) ─────────
    gold_rs = macro.get("gold_rs_vs_nifty", 0)
    fii_score = 50.0
    if gold_rs < -2:
        fii_score = 75  # equity outperforming gold = bullish
        fii_status = "Risk-On (Equity > Gold)"
    elif gold_rs > 3:
        fii_score = 25  # gold outperforming = flight to safety
        fii_status = "Risk-Off (Gold > Equity)"
    else:
        fii_score = 50
        fii_status = "Balanced"
    total_score += fii_score * 0.10
    total_weight += 0.10

    # ── Overall ──────────────────────────────────────────
    final_score = round(total_score / total_weight, 1) if total_weight > 0 else 50.0

    if final_score >= 75:
        sentiment = "BULLISH"
        summary = "Market conditions are strongly favourable. Most indicators align for equity exposure."
    elif final_score >= 55:
        sentiment = "CAUTIOUS"
        summary = "Market is mildly positive but some headwinds exist. Selective stock picking advised."
    elif final_score >= 40:
        sentiment = "NEUTRAL"
        summary = "Mixed signals. Stay cautious with smaller positions and tight stops."
    else:
        sentiment = "BEARISH"
        summary = "Multiple risk indicators are elevated. Reduce exposure, favour cash and gold."

    return {
        "overall_sentiment": sentiment,
        "sentiment_score": final_score,
        "nifty_trend": nifty_trend,
        "nifty_trend_score": round(nifty_score, 1),
        "vix_status": vix_status,
        "vix_score": round(vix_score, 1),
        "breadth_status": breadth_status,
        "breadth_score": round(breadth_score, 1),
        "global_status": global_status,
        "global_score": round(global_score, 1),
        "fii_proxy_status": fii_status,
        "fii_proxy_score": round(fii_score, 1),
        "summary": summary,
    }


def clear_cache():
    """Clear in-memory data cache."""
    _cache.clear()
