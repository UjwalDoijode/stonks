"""Trade management routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.database import get_db
from app.models import Trade, TradeStatus
from app.schemas import TradeCreate, TradeClose, TradeOut
from app.services import create_trade, close_trade

router = APIRouter(prefix="/trades", tags=["Trades"])


@router.get("/", response_model=list[TradeOut])
async def list_trades(
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List all trades, optionally filtered by status."""
    query = select(Trade).order_by(desc(Trade.entry_date))
    if status:
        query = query.where(Trade.status == status)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/open", response_model=list[TradeOut])
async def list_open_trades(db: AsyncSession = Depends(get_db)):
    """List open trades only."""
    result = await db.execute(
        select(Trade)
        .where(Trade.status == TradeStatus.OPEN.value)
        .order_by(desc(Trade.entry_date))
    )
    return result.scalars().all()


@router.get("/{trade_id}", response_model=TradeOut)
async def get_trade(trade_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Trade).where(Trade.id == trade_id))
    trade = result.scalar_one_or_none()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    return trade


@router.post("/", response_model=TradeOut)
async def create_new_trade(
    payload: TradeCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new trade with automatic position sizing."""
    try:
        trade = await create_trade(
            db=db,
            symbol=payload.symbol,
            entry_date=payload.entry_date,
            entry_price=payload.entry_price,
            stop_loss=payload.stop_loss,
            notes=payload.notes,
        )
        return trade
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{trade_id}/close", response_model=TradeOut)
async def close_existing_trade(
    trade_id: int,
    payload: TradeClose,
    db: AsyncSession = Depends(get_db),
):
    """Close an existing open trade."""
    try:
        trade = await close_trade(
            db=db,
            trade_id=trade_id,
            exit_date=payload.exit_date,
            exit_price=payload.exit_price,
            status=payload.status.value,
        )
        return trade
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
