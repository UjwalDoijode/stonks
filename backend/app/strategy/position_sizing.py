"""Risk-based position sizing calculator."""

import math
from dataclasses import dataclass
from app.config import settings


@dataclass
class PositionSize:
    capital: float
    risk_amount: float
    risk_per_share: float
    quantity: int
    position_size: float
    target_price: float
    reward_amount: float
    risk_reward_ratio: float
    capital_used_pct: float


def calculate_position_size(
    capital: float,
    entry_price: float,
    stop_loss: float,
    risk_pct: float = None,
) -> PositionSize:
    """
    Calculate position size based on fixed-percentage risk model.

    Risk Amount = Capital × Risk%
    Quantity = Risk Amount / (Entry − Stop)
    Position Size = Quantity × Entry
    """
    if risk_pct is None:
        risk_pct = settings.RISK_PER_TRADE_PCT

    risk_amount = capital * (risk_pct / 100)
    risk_per_share = entry_price - stop_loss

    if risk_per_share <= 0:
        raise ValueError("Stop loss must be below entry price for LONG trades")

    raw_qty = risk_amount / risk_per_share
    quantity = math.floor(raw_qty)

    if quantity <= 0:
        quantity = 1  # minimum 1 share

    position_size = quantity * entry_price
    target_price = entry_price + (risk_per_share * settings.TARGET_R_MULTIPLE)
    reward_amount = quantity * risk_per_share * settings.TARGET_R_MULTIPLE
    capital_used_pct = (position_size / capital) * 100

    return PositionSize(
        capital=round(capital, 2),
        risk_amount=round(risk_amount, 2),
        risk_per_share=round(risk_per_share, 2),
        quantity=quantity,
        position_size=round(position_size, 2),
        target_price=round(target_price, 2),
        reward_amount=round(reward_amount, 2),
        risk_reward_ratio=round(settings.TARGET_R_MULTIPLE, 2),
        capital_used_pct=round(capital_used_pct, 2),
    )
