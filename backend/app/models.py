"""SQLAlchemy models for trade logging and portfolio tracking."""

from sqlalchemy import (
    Column, Integer, Float, String, DateTime, Date, Boolean, Enum, Text
)
from sqlalchemy.sql import func
import enum

from app.database import Base


class TradeStatus(str, enum.Enum):
    OPEN = "OPEN"
    CLOSED_TP = "CLOSED_TP"       # closed at target
    CLOSED_SL = "CLOSED_SL"       # closed at stop loss
    CLOSED_MANUAL = "CLOSED_MANUAL"


class TradeDirection(str, enum.Enum):
    LONG = "LONG"


class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    direction = Column(String(10), default=TradeDirection.LONG.value)

    # Entry
    entry_date = Column(Date, nullable=False)
    entry_price = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False)

    # Risk management
    stop_loss = Column(Float, nullable=False)
    target = Column(Float, nullable=False)
    risk_per_share = Column(Float, nullable=False)
    risk_amount = Column(Float, nullable=False)
    r_multiple = Column(Float, default=0.0)

    # Exit
    exit_date = Column(Date, nullable=True)
    exit_price = Column(Float, nullable=True)

    # P&L
    pnl = Column(Float, default=0.0)
    pnl_pct = Column(Float, default=0.0)

    # Status
    status = Column(String(20), default=TradeStatus.OPEN.value)

    # Capital at time of trade
    capital_at_entry = Column(Float, nullable=False)
    position_size = Column(Float, nullable=False)

    # Metadata
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class ScanResult(Base):
    __tablename__ = "scan_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    scan_date = Column(Date, nullable=False, index=True)
    symbol = Column(String(20), nullable=False)

    # Scores & signals
    price = Column(Float)
    dma_200 = Column(Float)
    dma_50 = Column(Float)
    dma_20 = Column(Float)
    rsi = Column(Float)
    volume_ratio = Column(Float)  # current vol / avg vol
    prev_high = Column(Float)
    swing_low = Column(Float)

    # Flags
    above_200dma = Column(Boolean, default=False)
    dma50_trending_up = Column(Boolean, default=False)
    pullback_to_20dma = Column(Boolean, default=False)
    rsi_in_zone = Column(Boolean, default=False)
    volume_contracting = Column(Boolean, default=False)
    entry_triggered = Column(Boolean, default=False)

    # Overall
    is_candidate = Column(Boolean, default=False)
    criteria_met = Column(Integer, default=0)       # 0-6 count of flags met
    recommendation = Column(String(15), default="HOLD")  # BUY / HOLD / AVOID / RECOMMENDED
    reasoning = Column(Text, nullable=True)  # Human-readable explanation

    # Enhanced Intelligence Fields
    conviction = Column(String(10), default="LOW")       # LOW / MEDIUM / HIGH
    conviction_score = Column(Float, default=0.0)        # 0-100
    primary_reason = Column(Text, nullable=True)
    category_tag = Column(String(50), nullable=True)     # e.g. "MOMENTUM PICK"
    risk_warning = Column(String(200), nullable=True)

    # Trade Setup
    entry_price = Column(Float, nullable=True)
    stop_loss_price = Column(Float, nullable=True)
    target_1 = Column(Float, nullable=True)
    target_2 = Column(Float, nullable=True)
    target_3 = Column(Float, nullable=True)
    risk_pct = Column(Float, nullable=True)             # SL distance %
    reward_pct = Column(Float, nullable=True)            # T2 reward %
    risk_reward = Column(String(10), nullable=True)      # e.g. "1:2.0"

    # Earnings Momentum
    earnings_momentum = Column(String(10), default="NEUTRAL")
    earnings_score = Column(Float, default=50.0)
    quarterly_trend = Column(Text, nullable=True)

    # Geo Risk snapshot
    geo_risk_level = Column(String(10), default="LOW")
    geo_risk_score = Column(Float, default=0.0)

    created_at = Column(DateTime, server_default=func.now())


class PortfolioSnapshot(Base):
    __tablename__ = "portfolio_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    snapshot_date = Column(Date, nullable=False, index=True)
    capital = Column(Float, nullable=False)
    invested = Column(Float, default=0.0)
    open_trades = Column(Integer, default=0)
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    total_pnl = Column(Float, default=0.0)
    max_drawdown_pct = Column(Float, default=0.0)
    equity = Column(Float, nullable=False)

    created_at = Column(DateTime, server_default=func.now())


# ─── Risk & Regime ─────────────────────────────────────
class RiskScore(Base):
    __tablename__ = "risk_scores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    score_date = Column(Date, nullable=False, index=True)
    frequency = Column(String(10), default="DAILY")  # DAILY or WEEKLY

    # Components (0-100 each, weighted)
    trend_risk = Column(Float, default=0.0)         # max 25
    volatility_risk = Column(Float, default=0.0)    # max 25
    breadth_risk = Column(Float, default=0.0)       # max 20
    global_risk = Column(Float, default=0.0)        # max 15
    defensive_signal = Column(Float, default=0.0)   # max 15

    total_risk_score = Column(Float, default=0.0)   # 0-100
    stability_score = Column(Float, default=100.0)  # 100 - risk

    # Raw inputs for transparency
    nifty_close = Column(Float)
    nifty_200dma = Column(Float)
    nifty_50dma = Column(Float)
    vix = Column(Float)
    breadth_pct_above_50dma = Column(Float)
    sp500_above_200dma = Column(Boolean)
    dxy_breakout = Column(Boolean)
    oil_spike = Column(Boolean)
    gold_above_50dma = Column(Boolean)
    gold_rs_vs_nifty = Column(Float)

    regime = Column(String(20), nullable=False)  # derived regime label

    created_at = Column(DateTime, server_default=func.now())


class RegimeHistory(Base):
    __tablename__ = "regime_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    change_date = Column(Date, nullable=False, index=True)
    previous_regime = Column(String(20))
    new_regime = Column(String(20), nullable=False)
    risk_score = Column(Float)
    trigger_reason = Column(Text)  # human-readable why

    created_at = Column(DateTime, server_default=func.now())


class AllocationRecommendation(Base):
    __tablename__ = "allocation_recommendations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    recommendation_date = Column(Date, nullable=False, index=True)
    regime = Column(String(20), nullable=False)
    risk_score = Column(Float)

    equity_pct = Column(Float, default=0.0)
    gold_pct = Column(Float, default=0.0)
    silver_pct = Column(Float, default=0.0)
    cash_pct = Column(Float, default=0.0)

    equity_amount = Column(Float, default=0.0)
    gold_amount = Column(Float, default=0.0)
    silver_amount = Column(Float, default=0.0)
    cash_amount = Column(Float, default=0.0)

    total_capital = Column(Float)
    rebalance_needed = Column(Boolean, default=False)
    reason = Column(Text)

    created_at = Column(DateTime, server_default=func.now())


class CachedOHLCV(Base):
    """Cached daily OHLCV to avoid repeated yfinance calls."""
    __tablename__ = "cached_ohlcv"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(30), nullable=False, index=True)
    trade_date = Column(Date, nullable=False, index=True)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float)

    # composite unique
    __table_args__ = (
        # SQLAlchemy UniqueConstraint
        {"sqlite_autoincrement": True},
    )


class BacktestResult(Base):
    __tablename__ = "backtest_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_date = Column(DateTime, server_default=func.now())
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    initial_capital = Column(Float, nullable=False)
    final_capital = Column(Float, nullable=False)
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)
    avg_win = Column(Float, default=0.0)
    avg_loss = Column(Float, default=0.0)
    max_drawdown_pct = Column(Float, default=0.0)
    cagr = Column(Float, default=0.0)
    profit_factor = Column(Float, default=0.0)
    sharpe_ratio = Column(Float, default=0.0)
    total_return_pct = Column(Float, default=0.0)

    # Serialized equity curve as JSON
    equity_curve_json = Column(Text, nullable=True)
    trades_json = Column(Text, nullable=True)

    created_at = Column(DateTime, server_default=func.now())


# ─── Stock Rankings ────────────────────────────────────
class StockRanking(Base):
    __tablename__ = "stock_rankings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ranking_date = Column(Date, nullable=False, index=True)
    symbol = Column(String(30), nullable=False)
    rank = Column(Integer, nullable=False)
    composite_score = Column(Float, default=0.0)
    rs_3m = Column(Float, default=0.0)
    momentum_6m = Column(Float, default=0.0)
    vol_adj_return = Column(Float, default=0.0)
    volume_strength = Column(Float, default=0.0)
    trend_slope = Column(Float, default=0.0)
    price = Column(Float)

    created_at = Column(DateTime, server_default=func.now())


# ─── Capital Deployment ───────────────────────────────
class CapitalDeployment(Base):
    __tablename__ = "capital_deployments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    deployment_date = Column(Date, nullable=False, index=True)
    regime = Column(String(20), nullable=False)
    blended_risk_score = Column(Float, default=0.0)
    ai_confidence = Column(Float, default=0.0)
    total_capital = Column(Float, default=0.0)

    equity_pct = Column(Float, default=0.0)
    gold_pct = Column(Float, default=0.0)
    silver_pct = Column(Float, default=0.0)
    cash_pct = Column(Float, default=0.0)

    equity_amount = Column(Float, default=0.0)
    gold_amount = Column(Float, default=0.0)
    silver_amount = Column(Float, default=0.0)
    cash_amount = Column(Float, default=0.0)

    stock_picks_json = Column(Text)  # JSON array of stock picks
    rebalance_needed = Column(Boolean, default=False)
    why_no_trades = Column(Text)

    created_at = Column(DateTime, server_default=func.now())


# ─── AI Risk Predictions ─────────────────────────────
class AIRiskRecord(Base):
    __tablename__ = "ai_risk_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    prediction_date = Column(Date, nullable=False, index=True)
    ai_risk_score = Column(Float, default=50.0)
    p_risk_on = Column(Float, default=0.5)
    p_risk_off = Column(Float, default=0.5)
    expected_equity_return = Column(Float, default=0.0)
    expected_gold_return = Column(Float, default=0.0)
    confidence = Column(Float, default=0.0)
    model_available = Column(Boolean, default=False)
    rule_based_score = Column(Float, default=50.0)
    blended_score = Column(Float, default=50.0)

    created_at = Column(DateTime, server_default=func.now())


class WatchlistItem(Base):
    """User watchlist — saved stocks to track."""
    __tablename__ = "watchlist"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(30), nullable=False, unique=True, index=True)
    added_at = Column(DateTime, server_default=func.now())
    notes = Column(Text, nullable=True)


# ─── Risk Governor Events ─────────────────────────────
class GovernorEvent(Base):
    """Records governor activation/deactivation events."""
    __tablename__ = "governor_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_date = Column(DateTime, server_default=func.now(), index=True)
    severity = Column(String(20), nullable=False)           # NORMAL / WARNING / CRITICAL / EMERGENCY
    drawdown_pct = Column(Float, default=0.0)
    consecutive_losses = Column(Integer, default=0)
    monthly_loss_pct = Column(Float, default=0.0)
    is_active = Column(Boolean, default=False)
    override_equity_pct = Column(Float, nullable=True)
    reason = Column(Text, nullable=True)

    created_at = Column(DateTime, server_default=func.now())


# ─── Trade Feedback Records ──────────────────────────
class TradeFeedbackRecord(Base):
    """Records individual trade outcomes for adaptive AI feedback."""
    __tablename__ = "trade_feedback"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_id = Column(Integer, nullable=False, index=True)
    symbol = Column(String(30), nullable=False)
    closed_at = Column(DateTime, server_default=func.now())
    pnl = Column(Float, default=0.0)
    pnl_pct = Column(Float, default=0.0)
    r_multiple = Column(Float, default=0.0)
    regime_at_entry = Column(String(20), nullable=True)
    ai_confidence_at_entry = Column(Float, nullable=True)
    was_profitable = Column(Boolean, default=False)

    created_at = Column(DateTime, server_default=func.now())
