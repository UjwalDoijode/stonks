"""
Smart Cash Utilization — optimize idle cash.

When allocation recommends cash:
  - Suggest Liquid ETF or short-term instrument
  - Differentiate by risk regime
  - Add small yield assumption for backtesting

Available instruments (Indian market):
  - LIQUIDBEES.NS  — Nippon Liquid ETF (~6.5% annualised)
  - ICICILIQD.NS   — ICICI Liquid Fund (~6.3%)
  - Bank Savings    — (~4% annualised)
  - Short-term FD   — (~7% annualised for 1 year)
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# ── Cash Instruments ──────────────────────────────────────
CASH_INSTRUMENTS = {
    "LIQUID_ETF": {
        "name": "Nippon Liquid ETF",
        "symbol": "LIQUIDBEES.NS",
        "annual_yield_pct": 6.5,
        "risk_level": "VERY_LOW",
        "min_investment": 1000,
        "exit_load_days": 0,
        "description": "Exchange-traded liquid fund. Near-zero risk, instant liquidity.",
    },
    "LIQUID_MF": {
        "name": "Liquid Mutual Fund",
        "symbol": "ICICILIQD.NS",
        "annual_yield_pct": 6.3,
        "risk_level": "VERY_LOW",
        "min_investment": 500,
        "exit_load_days": 7,
        "description": "Overnight to 91-day paper. T+1 redemption.",
    },
    "SHORT_TERM_DEBT": {
        "name": "Short Term Debt Fund",
        "symbol": "N/A",
        "annual_yield_pct": 7.2,
        "risk_level": "LOW",
        "min_investment": 5000,
        "exit_load_days": 30,
        "description": "1-3 year maturity corporate bonds. Slightly higher return.",
    },
    "SAVINGS": {
        "name": "Bank Savings Account",
        "symbol": "N/A",
        "annual_yield_pct": 4.0,
        "risk_level": "NONE",
        "min_investment": 0,
        "exit_load_days": 0,
        "description": "Instant access. Lowest return but zero risk.",
    },
    "ARBITRAGE_FUND": {
        "name": "Arbitrage Fund",
        "symbol": "N/A",
        "annual_yield_pct": 6.8,
        "risk_level": "LOW",
        "min_investment": 5000,
        "exit_load_days": 30,
        "description": "Equity taxation benefits with debt-like returns.",
    },
}

# Regime-based recommendations
REGIME_CASH_PREFERENCE = {
    "STRONG_RISK_ON": ["LIQUID_ETF", "LIQUID_MF"],
    "MILD_RISK_ON": ["LIQUID_ETF", "LIQUID_MF"],
    "NEUTRAL": ["LIQUID_ETF", "SHORT_TERM_DEBT", "LIQUID_MF"],
    "RISK_OFF": ["LIQUID_ETF", "LIQUID_MF", "SAVINGS"],
    "EXTREME_RISK": ["SAVINGS", "LIQUID_MF"],
}


@dataclass
class CashRecommendation:
    """Recommendation for cash utilization."""
    instrument_key: str
    name: str
    symbol: str
    annual_yield_pct: float
    amount: float
    monthly_yield: float
    description: str
    risk_level: str
    priority: int  # 1 = primary recommendation


@dataclass
class SmartCashPlan:
    """Complete cash utilization plan."""
    total_cash: float
    regime: str
    recommendations: list[CashRecommendation] = field(default_factory=list)
    weighted_annual_yield: float = 0.0
    monthly_expected_income: float = 0.0
    reason: str = ""


def compute_smart_cash_plan(
    cash_amount: float,
    regime: str = "NEUTRAL",
) -> SmartCashPlan:
    """
    Generate smart cash utilization recommendations based on regime.

    Args:
        cash_amount: Amount allocated to cash
        regime: Current market regime

    Returns:
        SmartCashPlan with instrument recommendations
    """
    if cash_amount <= 0:
        return SmartCashPlan(
            total_cash=0,
            regime=regime,
            reason="No cash allocation to optimize.",
        )

    preferred = REGIME_CASH_PREFERENCE.get(regime, ["LIQUID_ETF", "SAVINGS"])
    recommendations = []
    total_weighted_yield = 0.0
    remaining = cash_amount

    for priority, key in enumerate(preferred, 1):
        instrument = CASH_INSTRUMENTS.get(key)
        if not instrument:
            continue

        # Allocate proportionally
        if priority == 1:
            alloc = remaining * 0.6  # 60% to primary
        elif priority == 2:
            alloc = remaining * 0.3  # 30% to secondary
        else:
            alloc = remaining * 0.1  # 10% to tertiary

        alloc = round(alloc, 2)
        if alloc < instrument["min_investment"]:
            continue

        monthly_yield = round(alloc * (instrument["annual_yield_pct"] / 100 / 12), 2)
        total_weighted_yield += alloc * instrument["annual_yield_pct"] / 100

        recommendations.append(CashRecommendation(
            instrument_key=key,
            name=instrument["name"],
            symbol=instrument["symbol"],
            annual_yield_pct=instrument["annual_yield_pct"],
            amount=alloc,
            monthly_yield=monthly_yield,
            description=instrument["description"],
            risk_level=instrument["risk_level"],
            priority=priority,
        ))

        remaining -= alloc
        if remaining <= 0:
            break

    # Handle remaining
    if remaining > 100:
        savings = CASH_INSTRUMENTS["SAVINGS"]
        monthly_yield = round(remaining * (savings["annual_yield_pct"] / 100 / 12), 2)
        recommendations.append(CashRecommendation(
            instrument_key="SAVINGS",
            name=savings["name"],
            symbol=savings["symbol"],
            annual_yield_pct=savings["annual_yield_pct"],
            amount=round(remaining, 2),
            monthly_yield=monthly_yield,
            description=savings["description"],
            risk_level=savings["NONE"] if "NONE" in savings else "NONE",
            priority=len(recommendations) + 1,
        ))
        total_weighted_yield += remaining * savings["annual_yield_pct"] / 100

    weighted_yield = (total_weighted_yield / cash_amount * 100) if cash_amount > 0 else 0
    monthly_income = round(total_weighted_yield / 12, 2)

    reason = (
        f"In {regime.replace('_', ' ').title()} regime: "
        f"recommended split across {len(recommendations)} instrument(s) "
        f"yielding ~{weighted_yield:.1f}% p.a. (₹{monthly_income:,.0f}/month)."
    )

    return SmartCashPlan(
        total_cash=cash_amount,
        regime=regime,
        recommendations=recommendations,
        weighted_annual_yield=round(weighted_yield, 2),
        monthly_expected_income=monthly_income,
        reason=reason,
    )


def get_cash_yield_for_backtest(regime: str = "NEUTRAL") -> float:
    """
    Return annualised cash yield assumption for backtesting.
    Based on regime-appropriate instrument.
    """
    preferred = REGIME_CASH_PREFERENCE.get(regime, ["LIQUID_ETF"])
    if preferred:
        instrument = CASH_INSTRUMENTS.get(preferred[0], {})
        return instrument.get("annual_yield_pct", 4.0) / 100
    return 0.04  # Default 4%
