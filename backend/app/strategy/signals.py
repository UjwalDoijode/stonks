"""Core strategy signal logic — Pullback-to-20DMA swing setup."""

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Optional

from app.config import settings
from app.strategy.indicators import add_indicators


@dataclass
class Signal:
    symbol: str
    date: pd.Timestamp
    close: float
    entry_price: float      # prev candle high
    stop_loss: float         # recent swing low
    target: float
    risk_per_share: float
    dma_200: float
    dma_50: float
    dma_20: float
    rsi: float
    volume_ratio: float
    cci: float = 0.0
    supertrend: float = 0.0

    # Individual flags
    above_200dma: bool = False
    dma50_trending_up: bool = False
    pullback_to_20dma: bool = False
    rsi_in_zone: bool = False
    volume_contracting: bool = False
    entry_triggered: bool = False
    cci_in_zone: bool = False
    supertrend_bullish: bool = False

    @property
    def flags(self) -> list[bool]:
        return [
            self.above_200dma,
            self.dma50_trending_up,
            self.pullback_to_20dma,
            self.rsi_in_zone,
            self.volume_contracting,
            self.entry_triggered,
            self.cci_in_zone,
            self.supertrend_bullish,
        ]

    @property
    def criteria_met(self) -> int:
        return sum(self.flags)

    @property
    def is_valid(self) -> bool:
        return all(self.flags)

    @property
    def recommendation(self) -> str:
        """BUY (green), HOLD (neutral), AVOID (red)."""
        met = self.criteria_met
        if met >= 7:
            return "BUY"
        elif met <= 2:
            return "AVOID"
        return "HOLD"

    @property
    def reasoning(self) -> str:
        """Human-readable explanation of WHY this stock is BUY/HOLD/AVOID."""
        parts: list[str] = []
        rec = self.recommendation
        met = self.criteria_met
        symbol_clean = self.symbol.replace(".NS", "")

        # Header
        if rec == "BUY":
            parts.append(f"{symbol_clean} meets {met}/8 criteria — strong pullback setup detected.")
        elif rec == "AVOID":
            parts.append(f"{symbol_clean} meets only {met}/8 criteria — setup conditions are weak.")
        else:
            parts.append(f"{symbol_clean} meets {met}/8 criteria — partially formed setup, watch for improvement.")

        # Per-criteria reasoning
        if self.above_200dma:
            dist_pct = ((self.close - self.dma_200) / self.dma_200 * 100) if self.dma_200 else 0
            parts.append(f"✅ Trading above 200-DMA (₹{self.dma_200:.0f}) by {dist_pct:.1f}% — long-term uptrend intact.")
        else:
            parts.append(f"❌ Below 200-DMA (₹{self.dma_200:.0f}) — long-term trend is bearish, avoid longs.")

        if self.dma50_trending_up:
            parts.append(f"✅ 50-DMA (₹{self.dma_50:.0f}) is trending up — medium-term momentum is positive.")
        else:
            parts.append(f"❌ 50-DMA (₹{self.dma_50:.0f}) is flat/declining — medium-term momentum is weak.")

        if self.pullback_to_20dma:
            dist_20 = ((self.close - self.dma_20) / self.dma_20 * 100) if self.dma_20 else 0
            parts.append(f"✅ Price near 20-DMA (₹{self.dma_20:.0f}, {dist_20:+.1f}%) — healthy pullback zone for entry.")
        else:
            dist_20 = ((self.close - self.dma_20) / self.dma_20 * 100) if self.dma_20 else 0
            parts.append(f"❌ Price {dist_20:+.1f}% from 20-DMA — not in pullback zone (need within ±2%).")

        if self.rsi_in_zone:
            parts.append(f"✅ RSI at {self.rsi:.0f} — in the sweet spot (40-65) indicating controlled momentum.")
        else:
            if self.rsi > 65:
                parts.append(f"❌ RSI at {self.rsi:.0f} — overbought, risk of reversal.")
            else:
                parts.append(f"❌ RSI at {self.rsi:.0f} — oversold/weak, momentum lacking.")

        if self.volume_contracting:
            parts.append(f"✅ Volume ratio {self.volume_ratio:.2f}x — contracting volume on pullback (bullish sign).")
        else:
            parts.append(f"❌ Volume ratio {self.volume_ratio:.2f}x — volume is elevated, pullback may be distribution.")

        if self.entry_triggered:
            parts.append(f"✅ Entry triggered — close broke above previous high (₹{self.entry_price:.2f}).")
        else:
            parts.append(f"❌ Entry not yet triggered — waiting for close above ₹{self.entry_price:.2f}.")

        if self.cci_in_zone:
            parts.append(f"✅ CCI at {self.cci:.0f} — in bullish zone (-50 to +100), momentum building.")
        else:
            if self.cci > 100:
                parts.append(f"❌ CCI at {self.cci:.0f} — overbought (>100), may reverse soon.")
            elif self.cci < -100:
                parts.append(f"❌ CCI at {self.cci:.0f} — strong bearish momentum (<-100).")
            else:
                parts.append(f"❌ CCI at {self.cci:.0f} — weak zone for swing entry.")

        if self.supertrend_bullish:
            parts.append(f"✅ Supertrend is BULLISH — price above supertrend line (₹{self.supertrend:.0f}), trend supports longs.")
        else:
            parts.append(f"❌ Supertrend is BEARISH — price below supertrend line (₹{self.supertrend:.0f}), trend against longs.")

        # Risk-reward summary
        rr = (self.target - self.entry_price) / self.risk_per_share if self.risk_per_share > 0 else 0
        parts.append(f"📊 Entry ₹{self.entry_price:.2f} | Stop ₹{self.stop_loss:.2f} | Target ₹{self.target:.2f} | R:R {rr:.1f}:1")

        return " | ".join(parts)


def scan_symbol(symbol: str, df: pd.DataFrame) -> Optional[Signal]:
    """
    Scan a single symbol's OHLCV DataFrame for the pullback setup.
    Returns a Signal if the latest bar meets criteria, else None.
    """
    if df is None or len(df) < settings.DMA_LONG + 30:
        return None

    df = add_indicators(df)
    if df.empty:
        return None

    row = df.iloc[-1]
    prev = df.iloc[-2]

    # ── Individual Checks ────────────────────────────────
    above_200dma = row["close"] > row["dma_200"]
    dma50_trending_up = row["dma_50_slope"] > 0
    pullback_to_20dma = abs(row["dist_to_20dma_pct"]) <= 2.0  # within 2% of 20DMA
    rsi_in_zone = settings.RSI_LOW <= row["rsi"] <= settings.RSI_HIGH
    volume_contracting = row["volume_ratio"] < 0.8  # below-average volume
    entry_triggered = row["close"] > prev["high"]   # close > prev high
    cci_in_zone = -50 <= row["cci"] <= 100           # CCI sweet spot for pullback
    supertrend_bullish = row["supertrend_direction"] == 1  # price above supertrend

    # ── Risk calc ────────────────────────────────────────
    entry_price = prev["high"]
    stop_loss = row["swing_low"]
    risk_per_share = entry_price - stop_loss

    if risk_per_share <= 0:
        # Fallback: use 3% of entry as risk
        risk_per_share = entry_price * 0.03
        stop_loss = entry_price - risk_per_share

    target = entry_price + (risk_per_share * settings.TARGET_R_MULTIPLE)

    return Signal(
        symbol=symbol,
        date=df.index[-1],
        close=round(row["close"], 2),
        entry_price=round(entry_price, 2),
        stop_loss=round(stop_loss, 2),
        target=round(target, 2),
        risk_per_share=round(risk_per_share, 2),
        dma_200=round(row["dma_200"], 2),
        dma_50=round(row["dma_50"], 2),
        dma_20=round(row["dma_20"], 2),
        rsi=round(row["rsi"], 2),
        volume_ratio=round(row["volume_ratio"], 2),
        cci=round(float(row["cci"]), 2),
        supertrend=round(float(row["supertrend"]), 2) if not np.isnan(row["supertrend"]) else 0.0,
        above_200dma=above_200dma,
        dma50_trending_up=dma50_trending_up,
        pullback_to_20dma=pullback_to_20dma,
        rsi_in_zone=rsi_in_zone,
        volume_contracting=volume_contracting,
        entry_triggered=entry_triggered,
        cci_in_zone=cci_in_zone,
        supertrend_bullish=supertrend_bullish,
    )


def scan_all_signals(data_dict: dict[str, pd.DataFrame]) -> list[Signal]:
    """Scan entire universe and return valid signals only."""
    signals = []
    for symbol, df in data_dict.items():
        sig = scan_symbol(symbol, df)
        if sig and sig.is_valid:
            signals.append(sig)
    return signals
