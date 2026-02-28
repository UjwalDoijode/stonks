"""
Probability Distribution View — Monte Carlo simulation of portfolio outcomes.

Instead of showing only expected return, display:
  - Best-case estimate
  - Worst-case estimate
  - 1 standard deviation range
  - Probability of a negative month

Uses resampling from past trade distribution for realistic projections.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────
N_SIMULATIONS = 5000             # Number of Monte Carlo paths
MONTHS_FORWARD = 12              # Simulation horizon
MIN_TRADES_FOR_SIMULATION = 5    # Need at least this many trades


@dataclass
class DistributionResult:
    """Monte Carlo simulation output."""
    # Summary statistics
    expected_return_pct: float = 0.0
    best_case_pct: float = 0.0           # 95th percentile
    worst_case_pct: float = 0.0          # 5th percentile
    std_dev_pct: float = 0.0             # 1 sigma
    upper_1sd_pct: float = 0.0           # mean + 1 sigma
    lower_1sd_pct: float = 0.0           # mean - 1 sigma

    # Risk metrics
    prob_negative_month: float = 0.0     # P(return < 0) in any given month
    prob_loss_5pct: float = 0.0          # P(loss > 5%)
    prob_gain_10pct: float = 0.0         # P(gain > 10%)
    max_drawdown_median: float = 0.0     # Median max drawdown across sims
    value_at_risk_95: float = 0.0        # 5% VaR

    # Distribution shape
    skewness: float = 0.0
    kurtosis: float = 0.0

    # Histogram data (for frontend charting)
    histogram_bins: list[float] = field(default_factory=list)
    histogram_counts: list[int] = field(default_factory=list)

    # Percentile curve
    percentile_5: list[float] = field(default_factory=list)
    percentile_25: list[float] = field(default_factory=list)
    percentile_50: list[float] = field(default_factory=list)
    percentile_75: list[float] = field(default_factory=list)
    percentile_95: list[float] = field(default_factory=list)

    # Input info
    n_simulations: int = N_SIMULATIONS
    months_forward: int = MONTHS_FORWARD
    initial_capital: float = 0.0
    data_source: str = ""                # "trades" or "synthetic"


def simulate_from_trades(
    trade_returns: list[float],
    initial_capital: float = 20000.0,
    trades_per_month: float = 4.0,
    n_simulations: int = N_SIMULATIONS,
    months: int = MONTHS_FORWARD,
) -> DistributionResult:
    """
    Monte Carlo simulation using resampled past trade returns.

    Args:
        trade_returns: List of trade P&L percentages (e.g., [2.5, -1.0, 3.2, ...])
        initial_capital: Starting capital
        trades_per_month: Average trades per month
        n_simulations: Number of simulation paths
        months: Forward simulation months

    Returns:
        DistributionResult with full distribution analysis
    """
    if len(trade_returns) < MIN_TRADES_FOR_SIMULATION:
        return _synthetic_simulation(initial_capital, n_simulations, months)

    returns = np.array(trade_returns, dtype=float)
    trades_per_step = max(1, int(trades_per_month))

    # Run Monte Carlo
    final_values = np.zeros(n_simulations)
    max_drawdowns = np.zeros(n_simulations)
    monthly_returns_all = np.zeros((n_simulations, months))
    equity_paths = np.zeros((n_simulations, months + 1))

    for sim in range(n_simulations):
        capital = initial_capital
        peak = capital
        max_dd = 0.0
        equity_paths[sim, 0] = capital

        for m in range(months):
            # Resample trades for this month
            sampled_returns = np.random.choice(returns, size=trades_per_step, replace=True)
            monthly_pnl = 0.0

            for ret_pct in sampled_returns:
                trade_pnl = capital * (ret_pct / 100)
                monthly_pnl += trade_pnl

            capital += monthly_pnl
            capital = max(capital, 0)  # Can't go below 0

            monthly_returns_all[sim, m] = (monthly_pnl / max(equity_paths[sim, m], 1)) * 100

            if capital > peak:
                peak = capital
            dd = ((peak - capital) / peak * 100) if peak > 0 else 0.0
            if dd > max_dd:
                max_dd = dd

            equity_paths[sim, m + 1] = capital

        final_values[sim] = capital
        max_drawdowns[sim] = max_dd

    # Compute statistics
    final_returns = ((final_values - initial_capital) / initial_capital) * 100

    result = DistributionResult(
        expected_return_pct=round(float(np.mean(final_returns)), 2),
        best_case_pct=round(float(np.percentile(final_returns, 95)), 2),
        worst_case_pct=round(float(np.percentile(final_returns, 5)), 2),
        std_dev_pct=round(float(np.std(final_returns)), 2),
        upper_1sd_pct=round(float(np.mean(final_returns) + np.std(final_returns)), 2),
        lower_1sd_pct=round(float(np.mean(final_returns) - np.std(final_returns)), 2),
        initial_capital=initial_capital,
        n_simulations=n_simulations,
        months_forward=months,
        data_source="trades",
    )

    # Risk metrics
    all_monthly = monthly_returns_all.flatten()
    result.prob_negative_month = round(float(np.mean(all_monthly < 0) * 100), 1)
    result.prob_loss_5pct = round(float(np.mean(final_returns < -5) * 100), 1)
    result.prob_gain_10pct = round(float(np.mean(final_returns > 10) * 100), 1)
    result.max_drawdown_median = round(float(np.median(max_drawdowns)), 2)
    result.value_at_risk_95 = round(float(np.percentile(final_returns, 5)), 2)

    # Distribution shape
    result.skewness = round(float(_skewness(final_returns)), 3)
    result.kurtosis = round(float(_kurtosis(final_returns)), 3)

    # Histogram
    counts, bin_edges = np.histogram(final_returns, bins=30)
    result.histogram_bins = [round(float(b), 2) for b in bin_edges[:-1]]
    result.histogram_counts = [int(c) for c in counts]

    # Percentile curves (equity paths over time)
    for m in range(months + 1):
        month_values = equity_paths[:, m]
        result.percentile_5.append(round(float(np.percentile(month_values, 5)), 2))
        result.percentile_25.append(round(float(np.percentile(month_values, 25)), 2))
        result.percentile_50.append(round(float(np.percentile(month_values, 50)), 2))
        result.percentile_75.append(round(float(np.percentile(month_values, 75)), 2))
        result.percentile_95.append(round(float(np.percentile(month_values, 95)), 2))

    return result


def _synthetic_simulation(
    initial_capital: float,
    n_simulations: int,
    months: int,
) -> DistributionResult:
    """
    Fallback Monte Carlo using synthetic return distribution
    (based on typical NIFTY small-capital trading stats).
    """
    # Typical monthly returns: mean ~2%, std ~8, slight negative skew
    monthly_mean = 2.0
    monthly_std = 8.0

    final_values = np.zeros(n_simulations)
    monthly_returns_all = np.zeros((n_simulations, months))
    equity_paths = np.zeros((n_simulations, months + 1))
    max_drawdowns = np.zeros(n_simulations)

    for sim in range(n_simulations):
        capital = initial_capital
        peak = capital
        max_dd = 0.0
        equity_paths[sim, 0] = capital

        for m in range(months):
            ret = np.random.normal(monthly_mean, monthly_std)
            pnl = capital * (ret / 100)
            capital += pnl
            capital = max(capital, 0)

            monthly_returns_all[sim, m] = ret

            if capital > peak:
                peak = capital
            dd = ((peak - capital) / peak * 100) if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd

            equity_paths[sim, m + 1] = capital

        final_values[sim] = capital
        max_drawdowns[sim] = max_dd

    final_returns = ((final_values - initial_capital) / initial_capital) * 100

    result = DistributionResult(
        expected_return_pct=round(float(np.mean(final_returns)), 2),
        best_case_pct=round(float(np.percentile(final_returns, 95)), 2),
        worst_case_pct=round(float(np.percentile(final_returns, 5)), 2),
        std_dev_pct=round(float(np.std(final_returns)), 2),
        upper_1sd_pct=round(float(np.mean(final_returns) + np.std(final_returns)), 2),
        lower_1sd_pct=round(float(np.mean(final_returns) - np.std(final_returns)), 2),
        initial_capital=initial_capital,
        n_simulations=n_simulations,
        months_forward=months,
        data_source="synthetic",
    )

    all_monthly = monthly_returns_all.flatten()
    result.prob_negative_month = round(float(np.mean(all_monthly < 0) * 100), 1)
    result.prob_loss_5pct = round(float(np.mean(final_returns < -5) * 100), 1)
    result.prob_gain_10pct = round(float(np.mean(final_returns > 10) * 100), 1)
    result.max_drawdown_median = round(float(np.median(max_drawdowns)), 2)
    result.value_at_risk_95 = round(float(np.percentile(final_returns, 5)), 2)

    result.skewness = round(float(_skewness(final_returns)), 3)
    result.kurtosis = round(float(_kurtosis(final_returns)), 3)

    counts, bin_edges = np.histogram(final_returns, bins=30)
    result.histogram_bins = [round(float(b), 2) for b in bin_edges[:-1]]
    result.histogram_counts = [int(c) for c in counts]

    for m in range(months + 1):
        month_values = equity_paths[:, m]
        result.percentile_5.append(round(float(np.percentile(month_values, 5)), 2))
        result.percentile_25.append(round(float(np.percentile(month_values, 25)), 2))
        result.percentile_50.append(round(float(np.percentile(month_values, 50)), 2))
        result.percentile_75.append(round(float(np.percentile(month_values, 75)), 2))
        result.percentile_95.append(round(float(np.percentile(month_values, 95)), 2))

    return result


def _skewness(data: np.ndarray) -> float:
    """Compute skewness of a distribution."""
    n = len(data)
    if n < 3:
        return 0.0
    mean = np.mean(data)
    std = np.std(data, ddof=1)
    if std == 0:
        return 0.0
    return float(np.mean(((data - mean) / std) ** 3))


def _kurtosis(data: np.ndarray) -> float:
    """Compute excess kurtosis of a distribution."""
    n = len(data)
    if n < 4:
        return 0.0
    mean = np.mean(data)
    std = np.std(data, ddof=1)
    if std == 0:
        return 0.0
    return float(np.mean(((data - mean) / std) ** 4) - 3)
