"""Scanner routes — universe scan, search, live prices, watchlist, sectors."""

import asyncio
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, delete

from app.database import get_db
from app.models import ScanResult, WatchlistItem
from app.schemas import (
    ScanResultOut, MarketSentimentOut, StockDetailOut,
    StockSearchResult, LivePriceOut, WatchlistItemOut,
    WatchlistAddRequest, SectorPerformanceOut, GeoRiskOut,
)
from app.services import run_weekly_scan

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/scanner", tags=["Scanner"])


@router.post("/run", response_model=list[ScanResultOut])
async def trigger_scan(db: AsyncSession = Depends(get_db)):
    """Run the weekly scanner across NIFTY 100 (batch download for speed)."""
    results = await run_weekly_scan(db)
    return results


@router.get("/latest", response_model=list[ScanResultOut])
async def get_latest_scan(db: AsyncSession = Depends(get_db)):
    """Get the most recent scan results."""
    result = await db.execute(
        select(ScanResult.scan_date).order_by(desc(ScanResult.scan_date)).limit(1)
    )
    latest_date = result.scalar_one_or_none()
    if not latest_date:
        return []

    result = await db.execute(
        select(ScanResult)
        .where(ScanResult.scan_date == latest_date)
        .order_by(desc(ScanResult.conviction_score), desc(ScanResult.is_candidate), desc(ScanResult.criteria_met), ScanResult.rsi)
    )
    return result.scalars().all()


@router.get("/candidates", response_model=list[ScanResultOut])
async def get_candidates(db: AsyncSession = Depends(get_db)):
    """Get only actionable candidates from latest scan."""
    result = await db.execute(
        select(ScanResult.scan_date).order_by(desc(ScanResult.scan_date)).limit(1)
    )
    latest_date = result.scalar_one_or_none()
    if not latest_date:
        return []

    result = await db.execute(
        select(ScanResult)
        .where(ScanResult.scan_date == latest_date, ScanResult.is_candidate == True)
        .order_by(ScanResult.rsi)
    )
    return result.scalars().all()


@router.get("/regime")
async def get_regime():
    """Check current market regime (NIFTY vs 200 DMA)."""
    from app.strategy.data_feed import get_nifty_regime_info
    info = await asyncio.to_thread(get_nifty_regime_info)
    return info


@router.get("/sentiment", response_model=MarketSentimentOut)
async def get_market_sentiment():
    """Get comprehensive market sentiment analysis."""
    from app.strategy.macro_data import compute_market_sentiment
    sentiment = await asyncio.to_thread(compute_market_sentiment)
    return sentiment

@router.get("/geo-risk", response_model=GeoRiskOut)
async def get_geo_risk():
    """Get geopolitical / macro risk assessment from market proxies + live news."""
    from app.strategy.macro_data import get_macro_snapshot
    from app.strategy.market_intelligence import assess_geopolitical_risk
    from app.strategy.news_intelligence import fetch_news_intelligence
    macro = await asyncio.to_thread(get_macro_snapshot)
    geo = assess_geopolitical_risk(macro)
    # Enrich with news intelligence
    try:
        news = fetch_news_intelligence()
    except Exception:
        from app.strategy.news_intelligence import NewsIntelligence
        news = NewsIntelligence()
    return {
        "risk_level": geo.risk_level,
        "risk_score": geo.risk_score,
        "events": geo.events,
        "safe_haven_flow": geo.safe_haven_flow,
        "currency_stress": geo.currency_stress,
        "oil_shock": geo.oil_shock,
        "vix_fear": geo.vix_fear,
        "defense_bias": geo.defense_bias,
        "active_conflicts": news.active_conflicts,
        "risk_headlines": news.risk_headlines,
        "conflict_count": news.conflict_count,
        "news_risk_score": news.news_risk_score,
        "last_updated": news.last_updated,
    }

# ─── Stock Search ──────────────────────────────────────
@router.get("/search", response_model=list[StockSearchResult])
async def search_stocks(q: str = Query(..., min_length=1, max_length=30)):
    """Search for a stock by name/symbol across NIFTY 500."""
    from app.strategy.universe import NIFTY_500_SYMBOLS, get_clean_symbol

    q_upper = q.upper().strip()
    matches = []
    for sym in NIFTY_500_SYMBOLS:
        clean = get_clean_symbol(sym)
        if q_upper in clean:
            matches.append(sym)
        if len(matches) >= 15:
            break

    if not matches:
        return []

    def _fetch_search_data(symbols):
        import yfinance as yf
        results = []
        tickers = yf.Tickers(" ".join(symbols))
        for sym in symbols:
            try:
                t = tickers.tickers.get(sym)
                if not t:
                    continue
                info = t.fast_info
                hist = t.history(period="5d")
                if hist.empty:
                    continue
                price = float(hist["Close"].iloc[-1])
                prev = float(hist["Close"].iloc[-2]) if len(hist) > 1 else price
                change_pct = ((price - prev) / prev * 100) if prev else 0
                vol = int(hist["Volume"].iloc[-1]) if "Volume" in hist.columns else 0
                mkt_cap = getattr(info, "market_cap", None)
                full_info = t.info if hasattr(t, "info") else {}
                results.append({
                    "symbol": sym,
                    "clean_symbol": get_clean_symbol(sym),
                    "name": full_info.get("longName", get_clean_symbol(sym)),
                    "price": round(price, 2),
                    "change_pct": round(change_pct, 2),
                    "volume": vol,
                    "market_cap": mkt_cap,
                    "sector": full_info.get("sector"),
                    "industry": full_info.get("industry"),
                })
            except Exception as e:
                logger.debug(f"Search skip {sym}: {e}")
                continue
        return results

    results = await asyncio.to_thread(_fetch_search_data, matches)
    return results


# ─── Stock Detail ──────────────────────────────────────
@router.get("/stock/{symbol}", response_model=StockDetailOut)
async def get_stock_detail(symbol: str):
    """Get comprehensive detail for a single stock with technical analysis."""
    from app.strategy.universe import get_clean_symbol
    from app.strategy.signals import scan_symbol

    # Normalise symbol
    sym = symbol.upper().strip()
    if not sym.endswith(".NS"):
        sym = f"{sym}.NS"

    def _fetch_stock_detail(sym):
        import yfinance as yf
        import pandas as pd
        from app.strategy.market_intelligence import (
            assess_geopolitical_risk, compile_stock_intelligence
        )
        from app.strategy.macro_data import get_macro_snapshot

        t = yf.Ticker(sym)
        hist = t.history(period="2y")
        if hist is None or hist.empty:
            return None

        info = t.info if hasattr(t, "info") else {}
        fast = t.fast_info

        # Current price data
        price = float(hist["Close"].iloc[-1])
        prev = float(hist["Close"].iloc[-2]) if len(hist) > 1 else price
        change_pct = ((price - prev) / prev * 100) if prev else 0

        # 52-week
        year_data = hist.tail(252) if len(hist) >= 252 else hist
        w52_high = float(year_data["High"].max())
        w52_low = float(year_data["Low"].min())

        # Technical analysis via signals
        df = hist.copy()
        df.index = pd.to_datetime(df.index)
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        df.columns = [c.lower().replace(" ", "_") for c in df.columns]
        expected = {"open", "high", "low", "close", "volume"}
        if not expected.issubset(set(df.columns)):
            df_clean = None
        else:
            df_clean = df[["open", "high", "low", "close", "volume"]].copy()
            df_clean.dropna(inplace=True)

        sig = None
        intel = None
        if df_clean is not None and len(df_clean) >= 220:
            sig = scan_symbol(sym, df_clean)
            if sig:
                try:
                    macro = get_macro_snapshot()
                    geo_risk = assess_geopolitical_risk(macro)
                except Exception:
                    from app.strategy.market_intelligence import GeoRiskAssessment
                    geo_risk = GeoRiskAssessment()
                intel = compile_stock_intelligence(sig, df_clean, geo_risk)

        # Price history for sparkline (last 6 months)
        hist_6m = hist.tail(126)
        price_history = [
            {"date": str(d.date()), "price": round(float(r["Close"]), 2)}
            for d, r in hist_6m.iterrows()
        ]

        result = {
            "symbol": sym,
            "clean_symbol": get_clean_symbol(sym),
            "name": info.get("longName", get_clean_symbol(sym)),
            "price": round(price, 2),
            "change_pct": round(change_pct, 2),
            "day_high": round(float(hist["High"].iloc[-1]), 2),
            "day_low": round(float(hist["Low"].iloc[-1]), 2),
            "week_52_high": round(w52_high, 2),
            "week_52_low": round(w52_low, 2),
            "volume": int(hist["Volume"].iloc[-1]),
            "avg_volume": int(hist["Volume"].tail(20).mean()),
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE"),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "price_history": price_history,
        }

        if sig:
            result.update({
                "dma_200": sig.dma_200,
                "dma_50": sig.dma_50,
                "dma_20": sig.dma_20,
                "rsi": sig.rsi,
                "volume_ratio": sig.volume_ratio,
                "above_200dma": sig.above_200dma,
                "dma50_trending_up": sig.dma50_trending_up,
                "pullback_to_20dma": sig.pullback_to_20dma,
                "rsi_in_zone": sig.rsi_in_zone,
                "volume_contracting": sig.volume_contracting,
                "entry_triggered": sig.entry_triggered,
                "criteria_met": sig.criteria_met,
                "entry_price": sig.entry_price,
                "stop_loss": sig.stop_loss,
                "target": sig.target,
                "risk_per_share": sig.risk_per_share,
            })

        if intel:
            result.update({
                "recommendation": intel.recommendation,
                "reasoning": intel.reasoning,
                "conviction": intel.conviction,
                "conviction_score": intel.conviction_score,
                "primary_reason": intel.primary_reason,
                "category_tag": intel.category_tag,
                "risk_warning": intel.risk_warning,
                "target_1": intel.target_1,
                "target_2": intel.target_2,
                "target_3": intel.target_3,
                "risk_pct": intel.risk_pct,
                "reward_pct": intel.reward_pct,
                "risk_reward": intel.risk_reward,
                "earnings_momentum": intel.earnings_momentum,
                "earnings_score": intel.earnings_score,
                "quarterly_trend": intel.quarterly_trend,
                "geo_risk_level": intel.geo_risk_level if hasattr(intel, "geo_risk_level") else "LOW",
                "geo_risk_score": intel.geo_risk_score if hasattr(intel, "geo_risk_score") else 0,
                "support_levels": intel.support_levels,
                "resistance_levels": intel.resistance_levels,
                "reasons": intel.reasons,
            })
        elif sig:
            result.update({
                "recommendation": getattr(sig, 'recommendation', 'HOLD'),
                "reasoning": getattr(sig, 'reasoning', ''),
            })

        return result

    detail = await asyncio.to_thread(_fetch_stock_detail, sym)
    if not detail:
        raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")
    return detail


# ─── Live Prices ───────────────────────────────────────
@router.get("/live-prices", response_model=list[LivePriceOut])
async def get_live_prices(
    symbols: str = Query(None, description="Comma-separated symbols (e.g. RELIANCE,TCS,INFY)")
):
    """Get near-real-time prices. If no symbols given, use latest scanned BUY stocks."""
    from app.strategy.universe import get_clean_symbol

    def _fetch_live(symbol_list):
        import yfinance as yf
        results = []

        # Add .NS suffix if missing
        ns_symbols = [s if s.endswith(".NS") else f"{s}.NS" for s in symbol_list]

        try:
            batch = yf.download(
                ns_symbols, period="5d", group_by="ticker", threads=True, progress=False,
            )
            if batch is None or batch.empty:
                return []

            now_str = datetime.now().strftime("%H:%M:%S")

            if len(ns_symbols) == 1:
                # Single symbol — no multi-level columns
                sym = ns_symbols[0]
                if len(batch) >= 2:
                    price = float(batch["Close"].iloc[-1])
                    prev = float(batch["Close"].iloc[-2])
                    vol = int(batch["Volume"].iloc[-1])
                else:
                    price = float(batch["Close"].iloc[-1])
                    prev = price
                    vol = int(batch["Volume"].iloc[-1])
                change = price - prev
                change_pct = (change / prev * 100) if prev else 0
                results.append({
                    "symbol": get_clean_symbol(sym),
                    "price": round(price, 2),
                    "change": round(change, 2),
                    "change_pct": round(change_pct, 2),
                    "volume": vol,
                    "last_updated": now_str,
                })
            else:
                # Multi-symbol — tickers at level 0 (group_by="ticker")
                available = set(batch.columns.get_level_values(0).unique())
                for sym in ns_symbols:
                    try:
                        if sym not in available:
                            continue
                        df = batch[sym].dropna(how="all")
                        if df.empty:
                            continue
                        # Flatten column names
                        df.columns = [c if isinstance(c, str) else c[0] for c in df.columns]
                        price = float(df["Close"].iloc[-1])
                        prev = float(df["Close"].iloc[-2]) if len(df) > 1 else price
                        vol = int(df["Volume"].iloc[-1]) if "Volume" in df.columns else 0
                        change = price - prev
                        change_pct = (change / prev * 100) if prev else 0
                        results.append({
                            "symbol": get_clean_symbol(sym),
                            "price": round(price, 2),
                            "change": round(change, 2),
                            "change_pct": round(change_pct, 2),
                            "volume": vol,
                            "last_updated": now_str,
                        })
                    except Exception as ex:
                        logger.debug(f"Live price skip {sym}: {ex}")
                        continue
        except Exception as e:
            logger.error(f"Live price fetch failed: {e}")
        return results

    if symbols:
        sym_list = list(dict.fromkeys(s.strip() for s in symbols.split(",") if s.strip()))
    else:
        # Default: use NIFTY 50 index + top 10 NIFTY stocks
        from app.strategy.universe import NIFTY_50_SYMBOLS
        sym_list = NIFTY_50_SYMBOLS[:20]

    prices = await asyncio.to_thread(_fetch_live, sym_list)
    return prices


# ─── Commodities Prices ───────────────────────────────
_commodity_cache: list[dict] = []
_commodity_cache_time: float = 0

@router.get("/commodities")
async def get_commodities_prices():
    """Get live Gold, Silver, Crude Oil, VIX, Natural Gas, Brent Crude and inflation proxy prices."""
    import time as _time
    global _commodity_cache, _commodity_cache_time

    # Return cache if fresh (< 60 seconds)
    if _commodity_cache and (_time.time() - _commodity_cache_time) < 60:
        return _commodity_cache

    def _fetch_commodities():
        import yfinance as yf
        import pandas as pd

        # Global futures + market indicators
        ITEMS = {
            "GC=F":          {"name": "Gold",         "unit": "oz",    "currency": "$",  "type": "global"},
            "SI=F":          {"name": "Silver",       "unit": "oz",    "currency": "$",  "type": "global"},
            "CL=F":          {"name": "Crude Oil",    "unit": "bbl",   "currency": "$",  "type": "global"},
            "BZ=F":          {"name": "Brent Crude",  "unit": "bbl",   "currency": "$",  "type": "global"},
            "NG=F":          {"name": "Natural Gas",  "unit": "MMBtu", "currency": "$",  "type": "global"},
            "^INDIAVIX":     {"name": "India VIX",    "unit": "",      "currency": "",   "type": "vix"},
            "GOLDBEES.NS":   {"name": "Gold ETF",     "unit": "unit",  "currency": "₹",  "type": "etf"},
            "SILVERBEES.NS": {"name": "Silver ETF",   "unit": "unit",  "currency": "₹",  "type": "etf"},
        }

        results = []
        now_str = datetime.now().strftime("%H:%M:%S")
        syms = list(ITEMS.keys())

        # ── Try batch download first ─────────────────────
        fetched_syms = set()
        try:
            batch = yf.download(syms, period="5d", group_by="ticker", threads=True, progress=False)
            if batch is not None and not batch.empty:
                has_multi = isinstance(batch.columns, pd.MultiIndex)
                for sym in syms:
                    try:
                        if has_multi:
                            avail = set(batch.columns.get_level_values(0).unique())
                            if sym not in avail:
                                continue
                            df = batch[sym].dropna(how="all")
                        else:
                            df = batch
                        if df.empty or len(df) < 2:
                            continue
                        close_col = [c for c in df.columns if "close" in str(c).lower()]
                        if close_col:
                            price = float(df[close_col[0]].iloc[-1])
                            prev = float(df[close_col[0]].iloc[-2])
                        else:
                            price = float(df["Close"].iloc[-1])
                            prev = float(df["Close"].iloc[-2])
                        change = price - prev
                        change_pct = (change / prev * 100) if prev else 0
                        vol_col = [c for c in df.columns if "volume" in str(c).lower()]
                        vol = int(df[vol_col[0]].iloc[-1]) if vol_col else 0
                        info = ITEMS[sym]
                        clean_sym = sym.replace(".NS", "").replace("^", "").replace("=F", "")
                        results.append({
                            "symbol": clean_sym,
                            "name": info["name"],
                            "price": round(price, 2),
                            "change": round(change, 2),
                            "change_pct": round(change_pct, 2),
                            "currency": info["currency"],
                            "unit": info["unit"],
                            "volume": vol,
                            "last_updated": now_str,
                            "type": info["type"],
                        })
                        fetched_syms.add(sym)
                    except Exception as ex:
                        logger.debug(f"Commodity batch-parse skip {sym}: {ex}")
                        continue
        except Exception as e:
            logger.warning(f"Commodity batch download failed: {e}")

        # ── Individual fallback for missing symbols ──────
        missing = [s for s in syms if s not in fetched_syms]
        if missing:
            logger.info(f"Commodity individual fallback for: {missing}")
            for sym in missing:
                try:
                    tk = yf.Ticker(sym)
                    hist = tk.history(period="5d")
                    if hist is None or hist.empty or len(hist) < 2:
                        continue
                    price = float(hist["Close"].iloc[-1])
                    prev = float(hist["Close"].iloc[-2])
                    change = price - prev
                    change_pct = (change / prev * 100) if prev else 0
                    vol = int(hist["Volume"].iloc[-1]) if "Volume" in hist.columns else 0
                    info = ITEMS[sym]
                    clean_sym = sym.replace(".NS", "").replace("^", "").replace("=F", "")
                    results.append({
                        "symbol": clean_sym,
                        "name": info["name"],
                        "price": round(price, 2),
                        "change": round(change, 2),
                        "change_pct": round(change_pct, 2),
                        "currency": info["currency"],
                        "unit": info["unit"],
                        "volume": vol,
                        "last_updated": now_str,
                        "type": info["type"],
                    })
                    fetched_syms.add(sym)
                except Exception as ex:
                    logger.debug(f"Commodity individual skip {sym}: {ex}")

        # ── USD/INR exchange rate ────────────────────────
        try:
            tk = yf.Ticker("INR=X")
            hist = tk.history(period="5d")
            if hist is not None and not hist.empty and len(hist) >= 2:
                price = float(hist["Close"].iloc[-1])
                prev = float(hist["Close"].iloc[-2])
                change = price - prev
                change_pct = (change / prev * 100) if prev else 0
                results.append({
                    "symbol": "USDINR",
                    "name": "USD/INR",
                    "price": round(price, 2),
                    "change": round(change, 2),
                    "change_pct": round(change_pct, 2),
                    "currency": "₹",
                    "unit": "",
                    "volume": 0,
                    "last_updated": now_str,
                    "type": "forex",
                })
        except Exception:
            pass

        # India CPI Inflation — RBI publishes monthly, add as static entry
        results.append({
            "symbol": "INCPI",
            "name": "Inflation",
            "price": 4.31,
            "change": -0.27,
            "change_pct": -5.9,
            "currency": "",
            "unit": "%",
            "volume": 0,
            "last_updated": "Jan 2026",
            "type": "macro",
        })

        # Sort: global first, then vix, forex, etf, macro last
        type_order = {"global": 0, "vix": 1, "forex": 2, "etf": 3, "macro": 4}
        results.sort(key=lambda x: type_order.get(x["type"], 99))

        return results

    prices = await asyncio.to_thread(_fetch_commodities)

    # Update cache
    if len(prices) > 1:  # Only cache if we got more than just Inflation
        _commodity_cache = prices
        _commodity_cache_time = _time.time()

    return prices


# ─── Watchlist ─────────────────────────────────────────
@router.get("/watchlist", response_model=list[WatchlistItemOut])
async def get_watchlist(db: AsyncSession = Depends(get_db)):
    """Get all watchlist items with live price data."""
    result = await db.execute(select(WatchlistItem).order_by(WatchlistItem.added_at.desc()))
    items = result.scalars().all()

    if not items:
        return []

    # Fetch live prices for watchlist
    symbols = [item.symbol for item in items]

    def _fetch_watchlist_prices(syms):
        import yfinance as yf
        import pandas as pd
        ns_syms = [s if s.endswith(".NS") else f"{s}.NS" for s in syms]
        price_map = {}
        try:
            batch = yf.download(ns_syms, period="5d", group_by="ticker", threads=True, progress=False)
            if batch is not None and not batch.empty:
                has_multi = isinstance(batch.columns, pd.MultiIndex)
                if not has_multi:
                    sym = ns_syms[0]
                    clean = sym.replace(".NS", "")
                    price = float(batch["Close"].iloc[-1])
                    prev = float(batch["Close"].iloc[-2]) if len(batch) > 1 else price
                    price_map[clean] = {"price": round(price, 2), "change_pct": round((price - prev) / prev * 100, 2) if prev else 0}
                else:
                    available = set(batch.columns.get_level_values(0).unique())
                    for sym in ns_syms:
                        try:
                            if sym not in available:
                                continue
                            df = batch[sym].dropna(how="all")
                            if df.empty:
                                continue
                            price = float(df["Close"].iloc[-1])
                            prev = float(df["Close"].iloc[-2]) if len(df) > 1 else price
                            clean = sym.replace(".NS", "")
                            price_map[clean] = {"price": round(price, 2), "change_pct": round((price - prev) / prev * 100, 2) if prev else 0}
                        except Exception:
                            continue
        except Exception as e:
            logger.debug(f"Watchlist price fetch failed: {e}")
        return price_map

    price_map = await asyncio.to_thread(_fetch_watchlist_prices, symbols)

    results = []
    for item in items:
        pm = price_map.get(item.symbol, {})
        results.append({
            "id": item.id,
            "symbol": item.symbol,
            "added_at": item.added_at,
            "notes": item.notes,
            "price": pm.get("price"),
            "change_pct": pm.get("change_pct"),
            "recommendation": None,
        })
    return results


@router.post("/watchlist", response_model=WatchlistItemOut)
async def add_to_watchlist(req: WatchlistAddRequest, db: AsyncSession = Depends(get_db)):
    """Add a stock to the watchlist."""
    symbol = req.symbol.upper().strip().replace(".NS", "")
    # Check if already exists
    result = await db.execute(select(WatchlistItem).where(WatchlistItem.symbol == symbol))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail=f"{symbol} is already in your watchlist")

    item = WatchlistItem(symbol=symbol, notes=req.notes)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return {"id": item.id, "symbol": item.symbol, "added_at": item.added_at, "notes": item.notes}


@router.delete("/watchlist/{symbol}")
async def remove_from_watchlist(symbol: str, db: AsyncSession = Depends(get_db)):
    """Remove a stock from the watchlist."""
    clean = symbol.upper().strip().replace(".NS", "")
    result = await db.execute(select(WatchlistItem).where(WatchlistItem.symbol == clean))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail=f"{clean} not found in watchlist")
    await db.delete(item)
    await db.commit()
    return {"status": "removed", "symbol": clean}


# ─── Sector Heatmap ────────────────────────────────────
@router.get("/sectors", response_model=list[SectorPerformanceOut])
async def get_sector_heatmap():
    """Get NIFTY sectoral index performance for heatmap."""
    def _fetch_sectors():
        import yfinance as yf
        from app.strategy.universe import get_clean_symbol

        # NSE Sectoral Indices
        sector_indices = {
            "IT": "^CNXIT",
            "Banks": "^NSEBANK",
            "Pharma": "^CNXPHARMA",
            "Auto": "^CNXAUTO",
            "FMCG": "^CNXFMCG",
            "Metal": "^CNXMETAL",
            "Realty": "^CNXREALTY",
            "Energy": "^CNXENERGY",
            "Infra": "^CNXINFRA",
            "PSE": "^CNXPSE",
            "Media": "^CNXMEDIA",
            "Financial": "^CNXFIN",
        }

        # Representative stocks per sector for "top stock"
        sector_stocks = {
            "IT": ["TCS.NS", "INFY.NS", "WIPRO.NS", "HCLTECH.NS", "TECHM.NS"],
            "Banks": ["HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "KOTAKBANK.NS", "AXISBANK.NS"],
            "Pharma": ["SUNPHARMA.NS", "DRREDDY.NS", "CIPLA.NS", "DIVISLAB.NS", "LUPIN.NS"],
            "Auto": ["MARUTI.NS", "TATAMOTORS.NS", "M&M.NS", "BAJAJ-AUTO.NS", "EICHERMOT.NS"],
            "FMCG": ["HINDUNILVR.NS", "ITC.NS", "NESTLEIND.NS", "BRITANNIA.NS", "DABUR.NS"],
            "Metal": ["TATASTEEL.NS", "JSWSTEEL.NS", "HINDALCO.NS", "COALINDIA.NS", "VEDL.NS"],
            "Realty": ["DLF.NS", "GODREJPROP.NS", "OBEROIRLTY.NS", "PRESTIGE.NS", "LODHA.NS"],
            "Energy": ["RELIANCE.NS", "ONGC.NS", "BPCL.NS", "IOC.NS", "GAIL.NS"],
            "Infra": ["LT.NS", "ADANIENT.NS", "ADANIPORTS.NS", "POWERGRID.NS", "NTPC.NS"],
            "Financial": ["BAJFINANCE.NS", "BAJAJFINSV.NS", "HDFCLIFE.NS", "SBILIFE.NS", "ICICIGI.NS"],
        }

        results = []

        # Fetch sector indices
        all_syms = list(sector_indices.values())
        try:
            batch = yf.download(all_syms, period="1mo", group_by="ticker", threads=True, progress=False)
        except Exception:
            batch = None

        for sector_name, idx_sym in sector_indices.items():
            try:
                if batch is not None and not batch.empty:
                    import pandas as pd
                    if isinstance(batch.columns, pd.MultiIndex):
                        avail = set(batch.columns.get_level_values(0).unique())
                        if idx_sym not in avail:
                            continue
                        df = batch[idx_sym].dropna(how="all")
                    else:
                        df = batch

                    if df.empty or len(df) < 2:
                        continue

                    close_now = float(df["Close"].iloc[-1])
                    close_1d = float(df["Close"].iloc[-2]) if len(df) > 1 else close_now
                    close_1w = float(df["Close"].iloc[-5]) if len(df) >= 5 else close_1d
                    close_1m = float(df["Close"].iloc[0])

                    chg_1d = (close_now - close_1d) / close_1d * 100 if close_1d else 0
                    chg_1w = (close_now - close_1w) / close_1w * 100 if close_1w else 0
                    chg_1m = (close_now - close_1m) / close_1m * 100 if close_1m else 0
                else:
                    chg_1d = chg_1w = chg_1m = 0

                # Find top stock in sector
                top_stock = sector_name
                top_change = 0
                stock_count = len(sector_stocks.get(sector_name, []))
                stocks = sector_stocks.get(sector_name, [])
                if stocks:
                    try:
                        stock_batch = yf.download(stocks, period="5d", group_by="ticker", threads=True, progress=False)
                        if stock_batch is not None and not stock_batch.empty:
                            best_chg = -999
                            if isinstance(stock_batch.columns, pd.MultiIndex):
                                s_avail = set(stock_batch.columns.get_level_values(0).unique())
                            else:
                                s_avail = set()
                            for s in stocks:
                                try:
                                    if isinstance(stock_batch.columns, pd.MultiIndex):
                                        if s not in s_avail:
                                            continue
                                        sdf = stock_batch[s].dropna(how="all")
                                    else:
                                        sdf = stock_batch
                                    if sdf.empty or len(sdf) < 2:
                                        continue
                                    sp = float(sdf["Close"].iloc[-1])
                                    sp_prev = float(sdf["Close"].iloc[-2])
                                    sc = (sp - sp_prev) / sp_prev * 100 if sp_prev else 0
                                    if sc > best_chg:
                                        best_chg = sc
                                        top_stock = get_clean_symbol(s)
                                        top_change = round(sc, 2)
                                except Exception:
                                    continue
                    except Exception:
                        pass

                results.append({
                    "sector": sector_name,
                    "change_1d": round(chg_1d, 2),
                    "change_1w": round(chg_1w, 2),
                    "change_1m": round(chg_1m, 2),
                    "top_stock": top_stock,
                    "top_stock_change": top_change,
                    "stock_count": stock_count,
                })
            except Exception as e:
                logger.debug(f"Sector {sector_name} error: {e}")
                continue

        # Sort by 1-day change
        results.sort(key=lambda x: x["change_1d"], reverse=True)
        return results

    sectors = await asyncio.to_thread(_fetch_sectors)
    return sectors
