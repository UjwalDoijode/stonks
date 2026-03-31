"""Application configuration."""

from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    APP_NAME: str = "Stonks - Dynamic Capital Deployment Engine"
    VERSION: str = "2.0.0"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./stonks.db"
    SYNC_DATABASE_URL: str = "sqlite:///./stonks.db"

    # Trading Parameters
    INITIAL_CAPITAL: float = 20000.0
    MAX_SIMULTANEOUS_TRADES: int = 3  # up from 2 for NIFTY 500
    RISK_PER_TRADE_PCT: float = 1.5  # percent
    TARGET_R_MULTIPLE: float = 2.0

    # Strategy Parameters
    DMA_LONG: int = 200
    DMA_MID: int = 50
    DMA_SHORT: int = 20
    RSI_PERIOD: int = 14
    RSI_LOW: float = 40.0
    RSI_HIGH: float = 65.0
    VOLUME_LOOKBACK: int = 20
    SWING_LOW_LOOKBACK: int = 10

    # Market
    NIFTY_SYMBOL: str = "^NSEI"
    UNIVERSE: str = "NIFTY500"
    UNIVERSE_TIER: str = "100"  # default scan tier (50/100/200/500)
    TOP_RANKED_COUNT: int = 5   # top N stocks from ranker

    # Macro Symbols (yfinance tickers)
    VIX_SYMBOL: str = "^INDIAVIX"
    SP500_SYMBOL: str = "^GSPC"
    DXY_SYMBOL: str = "DX-Y.NYB"
    GOLD_SYMBOL: str = "GC=F"
    OIL_SYMBOL: str = "CL=F"
    GOLD_ETF_SYMBOL: str = "GOLDBEES.NS"
    SILVER_ETF_SYMBOL: str = "SILVERBEES.NS"

    # Risk Score Thresholds
    VIX_ELEVATED: float = 18.0
    VIX_HIGH: float = 25.0
    OIL_SPIKE_PCT: float = 15.0  # 15% above 50DMA

    # Regime Bands (risk score boundaries)
    REGIME_STRONG_RISK_ON: float = 25.0
    REGIME_MILD_RISK_ON: float = 45.0
    REGIME_NEUTRAL: float = 65.0
    REGIME_RISK_OFF: float = 80.0
    # above 80 = Extreme Risk

    # AI Risk Model
    AI_BLEND_RULE_WEIGHT: float = 0.70   # rule-based weight
    AI_BLEND_AI_WEIGHT: float = 0.30     # AI weight
    AI_RETRAIN_DAYS: int = 7             # retrain model every N days

    # Gemini AI (loaded from .env file)
    GEMINI_API_KEY: str = ""

    # Rebalancing
    REBALANCE_DRIFT_THRESHOLD: float = 10.0  # % drift to trigger rebalance

    # Brokerage (₹ per executed order, Zerodha-style)
    BROKERAGE_PER_ORDER: float = 20.0
    STT_PCT: float = 0.025  # Securities Transaction Tax %
    MIN_POSITION_VALUE: float = 500.0  # minimum ₹ position worth trading

    # Caching
    CACHE_TTL_SECONDS: int = 900  # 15 minutes
    CACHE_OHLCV_DAYS: int = 1  # re-fetch if older than 1 day (next market open)

    # Scheduler
    SCHEDULER_RISK_CRON: str = "0 9 * * 1-5"   # daily 9 AM IST on weekdays
    SCHEDULER_SCAN_CRON: str = "30 15 * * 5"    # Friday 3:30 PM IST
    SCHEDULER_VOL_CRON: str = "0 18 * * 1-5"   # daily 6 PM — update vol metrics
    SCHEDULER_AI_RETRAIN_CRON: str = "0 6 * * 0"  # Sunday 6 AM — weekly AI retrain

    # Governor (Part 1)
    GOVERNOR_DRAWDOWN_LIMIT: float = 8.0        # % drawdown → cut equity 50%
    GOVERNOR_CONSECUTIVE_LOSS_LIMIT: int = 3    # pause equity for 7 days
    GOVERNOR_MONTHLY_LOSS_LIMIT: float = 5.0    # % monthly loss → force defensive
    GOVERNOR_HARD_STOP: float = 15.0            # % → full cash

    # Volatility Targeting (Part 2)
    VOL_TARGET_ANNUAL: float = 12.0             # annualised portfolio vol target %

    # Opportunity Filter (Part 3)
    OPPORTUNITY_MIN_SCORE: float = 0.5          # min return/drawdown ratio

    # Liquidity Filter (Part 5)
    LIQUIDITY_MIN_TURNOVER: float = 5_000_000   # ₹50 lakh daily turnover
    LIQUIDITY_MIN_VOLUME: int = 50_000          # minimum avg daily volume

    # Data
    DATA_LOOKBACK_YEARS: int = 5
    DATA_DIR: str = str(Path(__file__).parent.parent / "data")

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

# ── Allocation Tables (static fallback) ─────────────────
ALLOCATION_MAP: dict[str, dict[str, float]] = {
    "STRONG_RISK_ON": {"equity": 90, "gold": 5, "silver": 0, "cash": 5},
    "MILD_RISK_ON":   {"equity": 75, "gold": 15, "silver": 0, "cash": 10},
    "NEUTRAL":        {"equity": 50, "gold": 30, "silver": 0, "cash": 20},
    "RISK_OFF":       {"equity": 15, "gold": 50, "silver": 5, "cash": 30},
    "EXTREME_RISK":   {"equity": 0,  "gold": 55, "silver": 0, "cash": 45},
}
