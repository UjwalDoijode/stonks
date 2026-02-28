"""Pydantic schemas for API request/response validation."""

from pydantic import BaseModel, Field, field_validator
from datetime import date, datetime
from typing import Optional
from enum import Enum


# ─── Enums ─────────────────────────────────────────────
class TradeStatusEnum(str, Enum):
    OPEN = "OPEN"
    CLOSED_TP = "CLOSED_TP"
    CLOSED_SL = "CLOSED_SL"
    CLOSED_MANUAL = "CLOSED_MANUAL"


# ─── Trade ─────────────────────────────────────────────
class TradeCreate(BaseModel):
    symbol: str
    entry_date: date
    entry_price: float
    stop_loss: float
    notes: Optional[str] = None


class TradeClose(BaseModel):
    exit_date: date
    exit_price: float
    status: TradeStatusEnum = TradeStatusEnum.CLOSED_MANUAL


class TradeOut(BaseModel):
    id: int
    symbol: str
    direction: str
    entry_date: date
    entry_price: float
    quantity: int
    stop_loss: float
    target: float
    risk_per_share: float
    risk_amount: float
    r_multiple: float
    exit_date: Optional[date]
    exit_price: Optional[float]
    pnl: float
    pnl_pct: float
    status: str
    capital_at_entry: float
    position_size: float
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Scanner ───────────────────────────────────────────
class ScanResultOut(BaseModel):
    id: int
    scan_date: date
    symbol: str
    price: Optional[float]
    dma_200: Optional[float]
    dma_50: Optional[float]
    dma_20: Optional[float]
    rsi: Optional[float]
    volume_ratio: Optional[float]
    prev_high: Optional[float]
    swing_low: Optional[float]
    above_200dma: bool
    dma50_trending_up: bool
    pullback_to_20dma: bool
    rsi_in_zone: bool
    volume_contracting: bool
    entry_triggered: bool
    is_candidate: bool
    criteria_met: int = 0
    recommendation: str = "HOLD"  # BUY / HOLD / AVOID / RECOMMENDED
    reasoning: Optional[str] = None  # Human-readable explanation

    # Enhanced Intelligence
    conviction: str = "LOW"
    conviction_score: float = 0.0
    primary_reason: Optional[str] = None
    category_tag: Optional[str] = None
    risk_warning: Optional[str] = None

    # Trade Setup
    entry_price: Optional[float] = None
    stop_loss_price: Optional[float] = None
    target_1: Optional[float] = None
    target_2: Optional[float] = None
    target_3: Optional[float] = None
    risk_pct: Optional[float] = None
    reward_pct: Optional[float] = None
    risk_reward: Optional[str] = None

    # Earnings
    earnings_momentum: str = "NEUTRAL"
    earnings_score: float = 50.0
    quarterly_trend: Optional[str] = None

    # Geo Risk
    geo_risk_level: str = "LOW"
    geo_risk_score: float = 0.0

    @field_validator("criteria_met", mode="before")
    @classmethod
    def _coerce_criteria_met(cls, v):
        if isinstance(v, bytes):
            return int.from_bytes(v, byteorder="little")
        return int(v) if v is not None else 0

    class Config:
        from_attributes = True


class MarketSentimentOut(BaseModel):
    overall_sentiment: str  # BULLISH / CAUTIOUS / NEUTRAL / BEARISH
    sentiment_score: float  # 0-100 (0=extreme fear, 100=extreme greed)
    nifty_trend: str
    nifty_trend_score: float
    vix_status: str
    vix_score: float
    breadth_status: str
    breadth_score: float
    global_status: str
    global_score: float
    fii_proxy_status: str
    fii_proxy_score: float
    summary: str


# ─── Position Sizing ──────────────────────────────────
class PositionSizeRequest(BaseModel):
    capital: float = Field(default=20000.0, description="Available capital")
    entry_price: float = Field(..., description="Planned entry price")
    stop_loss: float = Field(..., description="Stop loss price")
    risk_pct: float = Field(default=1.5, description="Risk per trade %")


class PositionSizeResponse(BaseModel):
    capital: float
    risk_amount: float
    risk_per_share: float
    quantity: int
    position_size: float
    target_price: float
    reward_amount: float
    risk_reward_ratio: float
    capital_used_pct: float


# ─── Portfolio ─────────────────────────────────────────
class PortfolioStats(BaseModel):
    current_capital: float
    initial_capital: float
    total_return_pct: float
    total_trades: int
    open_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_win: float
    avg_loss: float
    max_drawdown_pct: float
    cagr: float
    profit_factor: float


class EquityCurvePoint(BaseModel):
    date: date
    equity: float


# ─── Backtest ──────────────────────────────────────────
class BacktestRequest(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    initial_capital: float = 20000.0


class BacktestSummary(BaseModel):
    id: int
    run_date: datetime
    start_date: date
    end_date: date
    initial_capital: float
    final_capital: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_win: float
    avg_loss: float
    max_drawdown_pct: float
    cagr: float
    profit_factor: float
    sharpe_ratio: float
    total_return_pct: float

    class Config:
        from_attributes = True


# ─── Compounding ───────────────────────────────────────
class CompoundingRequest(BaseModel):
    initial_capital: float = 20000.0
    monthly_return_pct: float = 3.0
    monthly_addition: float = 0.0
    years: int = 5


class CompoundingPoint(BaseModel):
    month: int
    capital: float


class CompoundingResponse(BaseModel):
    initial_capital: float
    final_capital: float
    total_return_pct: float
    cagr: float
    curve: list[CompoundingPoint]


# ─── Risk & Allocation ─────────────────────────────────
class RiskComponentsOut(BaseModel):
    trend_risk: float
    volatility_risk: float
    breadth_risk: float
    global_risk: float
    defensive_signal: float
    total_risk_score: float
    stability_score: float
    regime: str


class AllocationOut(BaseModel):
    regime: str
    regime_label: str
    risk_score: float
    stability_score: float
    equity_pct: float
    gold_pct: float
    silver_pct: float
    cash_pct: float
    equity_amount: float
    gold_amount: float
    silver_amount: float
    cash_amount: float
    total_capital: float
    equity_allowed: bool
    rebalance_needed: bool
    reason: str


class MacroStatusOut(BaseModel):
    nifty_close: Optional[float] = None
    nifty_200dma: Optional[float] = None
    nifty_50dma: Optional[float] = None
    nifty_above_200dma: bool = False
    vix: Optional[float] = None
    vix_rising: bool = False
    breadth_pct_above_50dma: Optional[float] = None
    sp500_above_200dma: bool = True
    dxy_breakout: bool = False
    oil_spike: bool = False
    gold_above_50dma: bool = False
    gold_rs_vs_nifty: Optional[float] = None
    atr_expansion: bool = False


class BrokerageCheckOut(BaseModel):
    position_value: float
    brokerage: float
    stt: float
    total_cost: float
    cost_pct: float
    viable: bool
    reason: str


class AllocBacktestPointOut(BaseModel):
    date: str
    regime: str
    risk_score: float
    equity_value: float
    gold_value: float
    cash_value: float
    total_value: float


class AllocBacktestResultOut(BaseModel):
    start_date: str
    end_date: str
    initial_capital: float
    final_capital: float
    total_return_pct: float
    cagr: float
    max_drawdown_pct: float
    annualised_volatility: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    regime_changes: int
    time_in_regimes: dict
    benchmark_return_pct: float = 0.0
    curve: list[AllocBacktestPointOut]


class AllocBacktestRequest(BaseModel):
    years: int = 5
    initial_capital: float = 20000.0
    use_deployment_scores: bool = True


# ─── Stock Ranking ─────────────────────────────────────
class StockRankingOut(BaseModel):
    symbol: str
    clean_symbol: str
    price: float
    rank: int
    composite: float
    rs_3m: float
    momentum_6m: float
    vol_adj_return: float
    volume_strength: float
    trend_slope: float
    raw_return_3m: float = 0.0
    raw_return_6m: float = 0.0
    raw_volatility: float = 0.0


# ─── Stock Deployment ─────────────────────────────────
class StockDeploymentOut(BaseModel):
    symbol: str
    clean_symbol: str
    price: float
    quantity: int
    amount: float
    weight_pct: float
    rank_score: float
    expected_score: float
    reason: str


class AssetDeploymentOut(BaseModel):
    asset: str
    expected_score: float
    allocation_pct: float
    amount: float
    instrument: str
    stocks: list[StockDeploymentOut] = []


class CapitalDeploymentOut(BaseModel):
    regime: str
    regime_label: str
    regime_confidence: float
    total_capital: float
    blended_risk_score: float
    ai_confidence: float
    assets: list[AssetDeploymentOut]
    stock_picks: list[StockDeploymentOut]
    total_deployed: float
    cash_reserve: float
    why_no_trades: str
    rebalance_needed: bool
    rebalance_reason: str
    brokerage_total: float


# ─── AI Risk Probability ──────────────────────────────
class AIRiskProbabilityOut(BaseModel):
    ai_risk_score: float
    p_risk_on: float
    p_risk_off: float
    expected_equity_return: float
    expected_gold_return: float
    confidence: float
    model_available: bool
    rule_based_score: float = 0.0
    blended_score: float = 0.0
    blend_rule_weight: float = 0.70
    blend_ai_weight: float = 0.30


# ─── Stock Search / Detail ─────────────────────────────
class StockSearchResult(BaseModel):
    symbol: str
    clean_symbol: str
    name: str
    price: float
    change_pct: float
    volume: int
    market_cap: Optional[float] = None
    sector: Optional[str] = None
    industry: Optional[str] = None


class StockDetailOut(BaseModel):
    symbol: str
    clean_symbol: str
    name: str
    price: float
    change_pct: float
    day_high: float
    day_low: float
    week_52_high: float
    week_52_low: float
    volume: int
    avg_volume: int
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    # Technical analysis
    dma_200: Optional[float] = None
    dma_50: Optional[float] = None
    dma_20: Optional[float] = None
    rsi: Optional[float] = None
    volume_ratio: Optional[float] = None
    above_200dma: Optional[bool] = None
    dma50_trending_up: Optional[bool] = None
    pullback_to_20dma: Optional[bool] = None
    rsi_in_zone: Optional[bool] = None
    volume_contracting: Optional[bool] = None
    entry_triggered: Optional[bool] = None
    criteria_met: int = 0
    recommendation: str = "HOLD"
    reasoning: Optional[str] = None
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    target: Optional[float] = None
    risk_per_share: Optional[float] = None
    # Enhanced intelligence
    conviction: str = "LOW"
    conviction_score: float = 0.0
    primary_reason: Optional[str] = None
    category_tag: Optional[str] = None
    risk_warning: Optional[str] = None
    target_1: Optional[float] = None
    target_2: Optional[float] = None
    target_3: Optional[float] = None
    risk_pct: Optional[float] = None
    reward_pct: Optional[float] = None
    risk_reward: Optional[str] = None
    earnings_momentum: str = "NEUTRAL"
    earnings_score: float = 50.0
    quarterly_trend: Optional[str] = None
    geo_risk_level: str = "LOW"
    geo_risk_score: float = 0.0
    support_levels: list = []
    resistance_levels: list = []
    reasons: list = []
    # Price history (last 6 months)
    price_history: list[dict] = []


class LivePriceOut(BaseModel):
    symbol: str
    price: float
    change: float
    change_pct: float
    volume: int
    last_updated: str


# ─── Watchlist ──────────────────────────────────────────
class WatchlistItemOut(BaseModel):
    id: int
    symbol: str
    added_at: datetime
    notes: Optional[str] = None
    # Live data populated at read time
    price: Optional[float] = None
    change_pct: Optional[float] = None
    recommendation: Optional[str] = None

    class Config:
        from_attributes = True


class WatchlistAddRequest(BaseModel):
    symbol: str
    notes: Optional[str] = None


# ─── Sector Heatmap ────────────────────────────────────
class SectorPerformanceOut(BaseModel):
    sector: str
    change_1d: float
    change_1w: float
    change_1m: float
    top_stock: str
    top_stock_change: float
    stock_count: int


# ─── Geopolitical Risk ────────────────────────────────
class GeoRiskOut(BaseModel):
    risk_level: str = "LOW"
    risk_score: float = 0.0
    events: list[str] = []
    safe_haven_flow: bool = False
    currency_stress: bool = False
    oil_shock: bool = False
    vix_fear: bool = False
    defense_bias: str = "NEUTRAL"
    active_conflicts: list[dict] = []
    risk_headlines: list[dict] = []
    conflict_count: int = 0
    news_risk_score: float = 0.0
    last_updated: str = ""


# ─── Risk Governor (Part 1) ───────────────────────────
class GovernorStatusOut(BaseModel):
    is_active: bool = False
    severity: str = "NORMAL"
    drawdown_pct: float = 0.0
    drawdown_triggered: bool = False
    consecutive_losses: int = 0
    equity_paused: bool = False
    monthly_loss_pct: float = 0.0
    monthly_loss_triggered: bool = False
    hard_stop_triggered: bool = False
    override_allocation: Optional[dict] = None
    reason: str = ""


# ─── Volatility Targeting (Part 2) ────────────────────
class VolatilityMetricsOut(BaseModel):
    equity_vol: float = 0.0
    gold_vol: float = 0.0
    portfolio_vol: float = 0.0
    target_vol: float = 12.0
    scaling_factor: float = 1.0
    original_equity_pct: float = 0.0
    adjusted_equity_pct: float = 0.0
    reason: str = ""


# ─── Opportunity Filter (Part 3) ─────────────────────
class OpportunityScoreOut(BaseModel):
    asset: str
    expected_return: float = 0.0
    max_drawdown: float = 0.0
    opportunity_score: float = 0.0
    passes_threshold: bool = False


class OpportunityAssessmentOut(BaseModel):
    scores: list[OpportunityScoreOut] = []
    any_passes: bool = False
    cash_boost_applied: bool = False
    reason: str = ""


# ─── Correlation Control (Part 4) ─────────────────────
class CorrelationResultOut(BaseModel):
    original_count: int = 0
    filtered_count: int = 0
    removed_symbols: list[str] = []
    sector_limits_applied: bool = False
    correlation_penalty_applied: bool = False
    reason: str = ""


# ─── Liquidity Filter (Part 5) ────────────────────────
class LiquidityMetricsOut(BaseModel):
    symbol: str
    avg_daily_volume: float = 0.0
    avg_daily_turnover: float = 0.0
    estimated_spread_pct: float = 0.0
    passes: bool = True
    rejection_reason: str = ""


class LiquidityFilterResultOut(BaseModel):
    original_count: int = 0
    passed_count: int = 0
    rejected: list[LiquidityMetricsOut] = []
    reason: str = ""


# ─── Adaptive Feedback (Part 6) ──────────────────────
class FeedbackStatsOut(BaseModel):
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    high_conf_win_rate: float = 0.0
    low_conf_win_rate: float = 0.0
    avg_r_multiple: float = 0.0
    current_rule_weight: float = 0.70
    current_ai_weight: float = 0.30
    adaptation_active: bool = False
    reason: str = ""


# ─── Monte Carlo (Part 7) ─────────────────────────────
class MonteCarloResultOut(BaseModel):
    num_simulations: int = 5000
    months_forward: int = 12
    expected_return: float = 0.0
    best_case_return: float = 0.0
    worst_case_return: float = 0.0
    prob_negative_month: float = 0.0
    var_95: float = 0.0
    skewness: float = 0.0
    kurtosis: float = 0.0
    histogram_bins: list[float] = []
    histogram_counts: list[int] = []
    percentile_curves: dict = {}  # { "p5": [...], "p25": [...], "p50": [...], "p75": [...], "p95": [...] }


# ─── Smart Cash (Part 8) ──────────────────────────────
class CashRecommendationOut(BaseModel):
    instrument_key: str
    name: str
    symbol: str
    annual_yield_pct: float = 0.0
    amount: float = 0.0
    monthly_yield: float = 0.0
    description: str = ""
    risk_level: str = "NONE"
    priority: int = 1


class SmartCashPlanOut(BaseModel):
    total_cash: float = 0.0
    regime: str = "NEUTRAL"
    recommendations: list[CashRecommendationOut] = []
    weighted_annual_yield: float = 0.0
    monthly_expected_income: float = 0.0
    reason: str = ""


# ─── Risk Overview (combined all-in-one) ─────────────
class RiskOverviewOut(BaseModel):
    governor: GovernorStatusOut
    volatility: VolatilityMetricsOut
    opportunity: OpportunityAssessmentOut
    correlation: Optional[CorrelationResultOut] = None
    liquidity: Optional[LiquidityFilterResultOut] = None
    feedback: FeedbackStatsOut
    smart_cash: Optional[SmartCashPlanOut] = None
    monte_carlo: Optional[MonteCarloResultOut] = None


# ─── Enhanced Dashboard ──────────────────────────────
class DashboardData(BaseModel):
    portfolio: PortfolioStats
    open_trades: list[TradeOut]
    recent_scans: list[ScanResultOut]
    equity_curve: list[EquityCurvePoint]
    regime_ok: bool
    nifty_above_200dma: bool
    risk: Optional[RiskComponentsOut] = None
    allocation: Optional[AllocationOut] = None
    macro: Optional[MacroStatusOut] = None
    deployment: Optional[CapitalDeploymentOut] = None
    ai_risk: Optional[AIRiskProbabilityOut] = None
    top_ranked: Optional[list[StockRankingOut]] = None
    blended_risk_score: Optional[float] = None
    why_no_trades: Optional[str] = None
    # New risk control fields
    governor: Optional[GovernorStatusOut] = None
    volatility_metrics: Optional[VolatilityMetricsOut] = None
    smart_cash: Optional[SmartCashPlanOut] = None
