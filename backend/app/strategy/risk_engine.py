"""
Risk Scoring Engine — computes a 0-100 composite risk score from 5 components.

Components:
  1. Trend Risk     (0-25)  — NIFTY vs 200 DMA, 50 DMA slope, lower highs
  2. Volatility Risk(0-25)  — VIX level, VIX trend, ATR expansion, gap frequency
  3. Breadth Risk   (0-20)  — % stocks above 50 DMA
  4. Global Risk    (0-15)  — US market, dollar, oil
  5. Defensive Conf (0-15)  — Gold strength

Total Risk Score = sum of components (0-100)
Stability Score  = 100 - Risk Score
"""

import logging
from dataclasses import dataclass
from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class RiskComponents:
    trend_risk: float = 0.0          # 0-25
    volatility_risk: float = 0.0     # 0-25
    breadth_risk: float = 0.0        # 0-20
    global_risk: float = 0.0         # 0-15
    defensive_signal: float = 0.0    # 0-15
    total_risk_score: float = 0.0    # 0-100
    stability_score: float = 100.0   # 100 - risk
    regime: str = "NEUTRAL"

    # Raw inputs for transparency
    raw: dict = None

    def __post_init__(self):
        if self.raw is None:
            self.raw = {}


def compute_risk_score(macro: dict) -> RiskComponents:
    """
    Compute the composite risk score from a macro snapshot dict.
    Each component is scored independently and clamped to its max.
    """

    # ── 1. TREND RISK (0-25) ────────────────────────────
    trend = 0.0

    # NIFTY below 200 DMA → +12
    if not macro.get("nifty_above_200dma", True):
        trend += 12.0
    else:
        # Even above 200DMA, measure distance (closer = riskier)
        nifty_close = macro.get("nifty_close", 0)
        nifty_200 = macro.get("nifty_200dma", 1)
        if nifty_200 > 0:
            dist_pct = ((nifty_close - nifty_200) / nifty_200) * 100
            if dist_pct < 2:
                trend += 4.0  # close to 200 DMA = shaky

    # 50 DMA slope negative → +8
    if macro.get("nifty_50dma_slope", 0) < 0:
        trend += 8.0

    # Lower highs structure → +5
    if macro.get("nifty_lower_highs", False):
        trend += 5.0

    trend = min(trend, 25.0)

    # ── 2. VOLATILITY RISK (0-25) ───────────────────────
    vol = 0.0

    vix = macro.get("vix", 15.0)
    if vix > settings.VIX_HIGH:
        vol += 10.0
    elif vix > settings.VIX_ELEVATED:
        vol += 5.0

    # VIX rising trend → +5
    if macro.get("vix_rising", False):
        vol += 5.0

    # ATR expansion → +5
    if macro.get("atr_expansion", False):
        vol += 5.0

    # Gap frequency (more than 3 gaps in 20 days → +5)
    if macro.get("gap_frequency", 0) > 3:
        vol += 5.0

    vol = min(vol, 25.0)

    # ── 3. BREADTH RISK (0-20) ──────────────────────────
    breadth = 0.0

    pct_above_50 = macro.get("breadth_pct_above_50dma", 50.0)
    if pct_above_50 < 30:
        breadth += 15.0
    elif pct_above_50 < 50:
        breadth += 8.0
    elif pct_above_50 < 60:
        breadth += 3.0

    # Additional: if very low breadth, extra risk
    if pct_above_50 < 20:
        breadth += 5.0

    breadth = min(breadth, 20.0)

    # ── 4. GLOBAL RISK (0-15) ───────────────────────────
    glob = 0.0

    # US market below 200 DMA → +6
    if not macro.get("sp500_above_200dma", True):
        glob += 6.0

    # Dollar strength breakout → +5
    if macro.get("dxy_breakout", False):
        glob += 5.0

    # Oil spike → +4
    if macro.get("oil_spike", False):
        glob += 4.0

    glob = min(glob, 15.0)

    # ── 5. DEFENSIVE CONFIRMATION (0-15) ────────────────
    # Higher = more risk indicated by gold outperformance
    defense = 0.0

    # Gold above 50 DMA → money flowing to safety → +8
    if macro.get("gold_above_50dma", False):
        defense += 8.0

    # Gold RS vs NIFTY positive → gold outperforming → +7
    gold_rs = macro.get("gold_rs_vs_nifty", 0.0)
    if gold_rs > 3.0:
        defense += 7.0
    elif gold_rs > 1.0:
        defense += 4.0

    defense = min(defense, 15.0)

    # ── TOTAL ───────────────────────────────────────────
    total = round(trend + vol + breadth + glob + defense, 1)
    total = min(total, 100.0)
    stability = round(100.0 - total, 1)

    regime = classify_regime(total)

    return RiskComponents(
        trend_risk=round(trend, 1),
        volatility_risk=round(vol, 1),
        breadth_risk=round(breadth, 1),
        global_risk=round(glob, 1),
        defensive_signal=round(defense, 1),
        total_risk_score=total,
        stability_score=stability,
        regime=regime,
        raw=macro,
    )


def classify_regime(risk_score: float) -> str:
    """Map risk score → regime label."""
    if risk_score <= settings.REGIME_STRONG_RISK_ON:
        return "STRONG_RISK_ON"
    elif risk_score <= settings.REGIME_MILD_RISK_ON:
        return "MILD_RISK_ON"
    elif risk_score <= settings.REGIME_NEUTRAL:
        return "NEUTRAL"
    elif risk_score <= settings.REGIME_RISK_OFF:
        return "RISK_OFF"
    else:
        return "EXTREME_RISK"


REGIME_LABELS = {
    "STRONG_RISK_ON": "Strong Risk-On",
    "MILD_RISK_ON": "Mild Risk-On",
    "NEUTRAL": "Neutral",
    "RISK_OFF": "Risk-Off",
    "EXTREME_RISK": "Extreme Risk",
}

REGIME_EQUITY_ALLOWED = {
    "STRONG_RISK_ON": True,
    "MILD_RISK_ON": True,
    "NEUTRAL": True,
    "RISK_OFF": True,
    "EXTREME_RISK": False,
}
