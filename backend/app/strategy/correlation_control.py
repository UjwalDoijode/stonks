"""
Correlation & Cluster Control — portfolio diversification guard.

When selecting top NIFTY 500 stocks:
  1. Compute rolling correlation matrix for candidate stocks
  2. Avoid selecting > 2 stocks from the same sector
  3. Penalize highly correlated stocks (> 0.75 correlation)
  4. Prefer diversified exposure

Improves portfolio robustness by reducing concentration risk.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────
MAX_STOCKS_PER_SECTOR = 2
CORRELATION_PENALTY_THRESHOLD = 0.75
CORRELATION_PENALTY_FACTOR = 0.3     # Reduce composite score by this factor
CORRELATION_LOOKBACK_DAYS = 90


# Sector mapping for major NIFTY stocks
SECTOR_MAP = {
    # IT
    "TCS.NS": "IT", "INFY.NS": "IT", "WIPRO.NS": "IT", "HCLTECH.NS": "IT",
    "TECHM.NS": "IT", "LTIM.NS": "IT", "PERSISTENT.NS": "IT", "COFORGE.NS": "IT",
    "MPHASIS.NS": "IT", "TATAELXSI.NS": "IT", "KPITTECH.NS": "IT",
    "BIRLASOFT.NS": "IT", "CYIENT.NS": "IT", "MASTEK.NS": "IT",
    # Banks
    "HDFCBANK.NS": "Banks", "ICICIBANK.NS": "Banks", "SBIN.NS": "Banks",
    "KOTAKBANK.NS": "Banks", "AXISBANK.NS": "Banks", "INDUSINDBK.NS": "Banks",
    "BANKBARODA.NS": "Banks", "PNB.NS": "Banks", "IDFCFIRSTB.NS": "Banks",
    "CANBK.NS": "Banks", "FEDERALBNK.NS": "Banks", "AUBANK.NS": "Banks",
    # NBFC / Financials
    "BAJFINANCE.NS": "Financials", "BAJAJFINSV.NS": "Financials",
    "HDFCLIFE.NS": "Financials", "SBILIFE.NS": "Financials",
    "ICICIGI.NS": "Financials", "ICICIPRULI.NS": "Financials",
    "MUTHOOTFIN.NS": "Financials", "SHRIRAMFIN.NS": "Financials",
    "CHOLAFIN.NS": "Financials", "MANAPPURAM.NS": "Financials",
    "PEL.NS": "Financials", "LICHSGFIN.NS": "Financials",
    # Auto
    "MARUTI.NS": "Auto", "TATAMOTORS.NS": "Auto", "M&M.NS": "Auto",
    "BAJAJ-AUTO.NS": "Auto", "EICHERMOT.NS": "Auto", "HEROMOTOCO.NS": "Auto",
    "TVSMOTOR.NS": "Auto", "ASHOKLEY.NS": "Auto",
    # Pharma
    "SUNPHARMA.NS": "Pharma", "DRREDDY.NS": "Pharma", "CIPLA.NS": "Pharma",
    "DIVISLAB.NS": "Pharma", "LUPIN.NS": "Pharma", "TORNTPHARM.NS": "Pharma",
    "AUROPHARMA.NS": "Pharma", "BIOCON.NS": "Pharma", "ALKEM.NS": "Pharma",
    "IPCALAB.NS": "Pharma", "ABBOTINDIA.NS": "Pharma",
    # FMCG
    "HINDUNILVR.NS": "FMCG", "ITC.NS": "FMCG", "NESTLEIND.NS": "FMCG",
    "BRITANNIA.NS": "FMCG", "DABUR.NS": "FMCG", "GODREJCP.NS": "FMCG",
    "MARICO.NS": "FMCG", "COLPAL.NS": "FMCG", "TATACONSUM.NS": "FMCG",
    "EMAMILTD.NS": "FMCG",
    # Metals & Mining
    "TATASTEEL.NS": "Metals", "JSWSTEEL.NS": "Metals", "HINDALCO.NS": "Metals",
    "COALINDIA.NS": "Metals", "VEDL.NS": "Metals", "SAIL.NS": "Metals",
    "NMDC.NS": "Metals", "NATIONALUM.NS": "Metals", "HINDCOPPER.NS": "Metals",
    # Energy
    "RELIANCE.NS": "Energy", "ONGC.NS": "Energy", "BPCL.NS": "Energy",
    "IOC.NS": "Energy", "GAIL.NS": "Energy", "HINDPETRO.NS": "Energy",
    "PETRONET.NS": "Energy",
    # Infrastructure / Capital Goods
    "LT.NS": "Infra", "ADANIENT.NS": "Infra", "ADANIPORTS.NS": "Infra",
    "POWERGRID.NS": "Infra", "NTPC.NS": "Infra", "SIEMENS.NS": "Infra",
    "ABB.NS": "Infra", "BHEL.NS": "Infra", "HAL.NS": "Infra",
    "BEL.NS": "Infra", "POLYCAB.NS": "Infra",
    # Real Estate
    "DLF.NS": "Realty", "GODREJPROP.NS": "Realty", "OBEROIRLTY.NS": "Realty",
    "PRESTIGE.NS": "Realty", "LODHA.NS": "Realty", "SOBHA.NS": "Realty",
    "BRIGADE.NS": "Realty",
    # Telecom
    "BHARTIARTL.NS": "Telecom", "INDUSTOWER.NS": "Telecom",
    # Consumer Durables
    "TITAN.NS": "Consumer", "ASIANPAINT.NS": "Consumer", "PIDILITIND.NS": "Consumer",
    "HAVELLS.NS": "Consumer", "VOLTAS.NS": "Consumer", "CROMPTON.NS": "Consumer",
    "TRENT.NS": "Consumer", "PAGEIND.NS": "Consumer", "BATAINDIA.NS": "Consumer",
    # Cement
    "ULTRACEMCO.NS": "Cement", "SHREECEM.NS": "Cement", "AMBUJACEM.NS": "Cement",
    "ACC.NS": "Cement", "RAMCOCEM.NS": "Cement", "JKCEMENT.NS": "Cement",
    # Chemicals
    "SRF.NS": "Chemicals", "PIIND.NS": "Chemicals", "DEEPAKNTR.NS": "Chemicals",
    "NAVINFLUOR.NS": "Chemicals", "ATUL.NS": "Chemicals",
    # Healthcare
    "APOLLOHOSP.NS": "Healthcare", "MAXHEALTH.NS": "Healthcare",
    "FORTIS.NS": "Healthcare",
    # Power / Utilities
    "TATAPOWER.NS": "Utilities", "RECLTD.NS": "Utilities", "PFC.NS": "Utilities",
    "NHPC.NS": "Utilities", "SJVN.NS": "Utilities", "IRFC.NS": "Utilities",
    # Others
    "GRASIM.NS": "Diversified", "IRCTC.NS": "Services", "DMART.NS": "Retail",
    "ZOMATO.NS": "Tech", "NYKAA.NS": "Tech", "PAYTM.NS": "Tech",
    "NAUKRI.NS": "Tech", "JIOFIN.NS": "Financials", "LICI.NS": "Insurance",
}


def get_stock_sector(symbol: str) -> str:
    """Get sector for a stock symbol. Returns 'Unknown' if not mapped."""
    return SECTOR_MAP.get(symbol, "Unknown")


@dataclass
class CorrelationResult:
    """Result of correlation analysis for a set of stocks."""
    selected_symbols: list[str] = field(default_factory=list)
    removed_symbols: list[str] = field(default_factory=list)
    sector_counts: dict = field(default_factory=dict)
    high_correlations: list[dict] = field(default_factory=list)  # pairs with corr > threshold
    diversification_score: float = 0.0   # 0-100, higher = more diversified


def compute_correlation_matrix(
    symbols: list[str],
    lookback_days: int = CORRELATION_LOOKBACK_DAYS,
) -> Optional[pd.DataFrame]:
    """
    Compute rolling correlation matrix for a list of stock symbols.
    Uses batch yfinance download for speed.
    """
    import yfinance as yf
    from datetime import datetime, timedelta

    if len(symbols) < 2:
        return None

    end = datetime.now()
    start = end - timedelta(days=lookback_days + 30)  # extra buffer

    try:
        batch = yf.download(
            symbols,
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
            group_by="ticker",
            threads=True,
            progress=False,
        )
    except Exception as e:
        logger.error(f"Correlation data download failed: {e}")
        return None

    if batch is None or batch.empty:
        return None

    # Extract close prices
    closes = pd.DataFrame()
    available = set(batch.columns.get_level_values(0).unique())

    for sym in symbols:
        try:
            if sym in available:
                close = batch[sym]["Close"].dropna()
                if len(close) > lookback_days * 0.6:
                    closes[sym] = close
        except Exception:
            continue

    if len(closes.columns) < 2:
        return None

    # Compute returns and correlation
    returns = closes.pct_change().dropna()
    if len(returns) < 20:
        return None

    corr_matrix = returns.corr()
    return corr_matrix


def filter_correlated_stocks(
    scored_stocks: list,
    max_per_sector: int = MAX_STOCKS_PER_SECTOR,
    corr_threshold: float = CORRELATION_PENALTY_THRESHOLD,
    corr_penalty: float = CORRELATION_PENALTY_FACTOR,
) -> CorrelationResult:
    """
    Filter and penalise correlated / sector-concentrated stocks.

    Args:
        scored_stocks: List of StockScore objects (from stock_ranker)
        max_per_sector: Max stocks from same sector
        corr_threshold: Correlation above which to penalize
        corr_penalty: Score reduction factor for high correlation

    Returns:
        CorrelationResult with filtered stock list
    """
    if not scored_stocks:
        return CorrelationResult()

    symbols = [s.symbol for s in scored_stocks]

    # Step 1: Sector filtering
    sector_counts = {}
    sector_filtered = []
    sector_removed = []

    for stock in scored_stocks:
        sector = get_stock_sector(stock.symbol)
        count = sector_counts.get(sector, 0)
        if count < max_per_sector:
            sector_counts[sector] = count + 1
            sector_filtered.append(stock)
        else:
            sector_removed.append(stock)

    # Step 2: Correlation analysis
    filtered_symbols = [s.symbol for s in sector_filtered]
    corr_matrix = compute_correlation_matrix(filtered_symbols)

    high_correlations = []
    corr_removed = []

    if corr_matrix is not None and len(sector_filtered) > 1:
        # Check all pairs
        checked = set()
        for i, stock_a in enumerate(sector_filtered):
            for j, stock_b in enumerate(sector_filtered):
                if i >= j:
                    continue
                pair_key = tuple(sorted([stock_a.symbol, stock_b.symbol]))
                if pair_key in checked:
                    continue
                checked.add(pair_key)

                try:
                    corr = corr_matrix.loc[stock_a.symbol, stock_b.symbol]
                    if pd.isna(corr):
                        continue

                    if abs(corr) > corr_threshold:
                        high_correlations.append({
                            "stock_a": stock_a.clean_symbol,
                            "stock_b": stock_b.clean_symbol,
                            "correlation": round(float(corr), 3),
                        })

                        # Penalize the lower-ranked stock
                        if stock_a.composite >= stock_b.composite:
                            stock_b.composite *= (1 - corr_penalty)
                        else:
                            stock_a.composite *= (1 - corr_penalty)
                except Exception:
                    continue

        # Re-sort after penalization
        sector_filtered.sort(key=lambda s: s.composite, reverse=True)

    # Re-assign ranks
    for i, s in enumerate(sector_filtered):
        s.rank = i + 1

    # Calculate diversification score
    unique_sectors = len(set(get_stock_sector(s.symbol) for s in sector_filtered))
    total_sectors = max(1, len(sector_filtered))
    sector_diversity = min(unique_sectors / total_sectors, 1.0) * 50

    corr_score = 50.0
    if high_correlations:
        avg_corr = np.mean([abs(c["correlation"]) for c in high_correlations])
        corr_score = max(0, 50 * (1 - avg_corr))

    diversification_score = round(sector_diversity + corr_score, 1)

    return CorrelationResult(
        selected_symbols=[s.symbol for s in sector_filtered],
        removed_symbols=[s.symbol for s in sector_removed + corr_removed],
        sector_counts=sector_counts,
        high_correlations=high_correlations,
        diversification_score=diversification_score,
    )
