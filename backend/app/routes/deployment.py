"""API routes for capital deployment, stock ranking, and AI risk prediction."""

import json
import asyncio
import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.database import get_db
from app.schemas import (
    CapitalDeploymentOut,
    AssetDeploymentOut,
    StockDeploymentOut,
    StockRankingOut,
    AIRiskProbabilityOut,
)
from app.models import (
    CapitalDeployment,
    StockRanking,
    AIRiskRecord,
    AllocationRecommendation,
)
from app.services import get_current_capital

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Deployment"])


# ─── Capital Deployment ────────────────────────────────
@router.get("/capital-deployment", response_model=CapitalDeploymentOut)
async def get_capital_deployment(db: AsyncSession = Depends(get_db)):
    """
    Compute full capital deployment plan:
    risk score → AI blend → stock ranking → deployment allocation.
    """
    try:
        from app.strategy.macro_data import get_macro_snapshot
        from app.strategy.risk_engine import compute_risk_score
        from app.strategy.ai_risk_model import predict_risk, blend_risk_scores
        from app.strategy.stock_ranker import get_top_ranked
        from app.strategy.deployment_engine import compute_deployment
        from app.config import settings

        # 1. Compute risk (offload sync I/O to thread)
        macro = await asyncio.to_thread(get_macro_snapshot)
        risk = await asyncio.to_thread(compute_risk_score, macro)

        # 2. AI prediction + blend
        ai_pred = await asyncio.to_thread(predict_risk, macro)
        blended = blend_risk_scores(risk.total_risk_score, ai_pred)

        # 3. Stock ranking
        ranked = await asyncio.to_thread(
            get_top_ranked,
            n=settings.TOP_RANKED_COUNT,
            universe_tier=settings.UNIVERSE_TIER,
            regime=risk.regime,
        )

        # 4. Get previous allocation for drift detection
        result = await db.execute(
            select(AllocationRecommendation)
            .order_by(desc(AllocationRecommendation.recommendation_date))
            .limit(1)
        )
        prev_alloc_row = result.scalar_one_or_none()
        prev_alloc = None
        if prev_alloc_row:
            prev_alloc = {
                "regime": prev_alloc_row.regime,
                "equity_pct": prev_alloc_row.equity_pct,
                "gold_pct": prev_alloc_row.gold_pct,
                "silver_pct": prev_alloc_row.silver_pct,
                "cash_pct": prev_alloc_row.cash_pct,
            }

        # 5. Capital
        capital = await get_current_capital(db)

        # 5b. Gather trades for governor + peak capital
        from app.models import Trade, PortfolioSnapshot
        trade_result = await db.execute(
            select(Trade).order_by(desc(Trade.entry_date)).limit(50)
        )
        recent_trades = trade_result.scalars().all()
        trade_dicts = [
            {"pnl": t.pnl, "pnl_pct": t.pnl_pct,
             "exit_date": str(t.exit_date) if t.exit_date else None,
             "status": t.status}
            for t in recent_trades
        ]
        peak_result = await db.execute(
            select(PortfolioSnapshot).order_by(desc(PortfolioSnapshot.equity)).limit(1)
        )
        peak_snap = peak_result.scalar_one_or_none()
        peak_capital = peak_snap.equity if peak_snap else settings.INITIAL_CAPITAL

        # 6. Compute deployment (with integrated risk controls)
        plan = compute_deployment(
            risk=risk,
            capital=capital,
            ranked_stocks=ranked,
            ai_pred=ai_pred,
            previous_allocation=prev_alloc,
            blended_risk_score=blended,
            trades_for_governor=trade_dicts,
            peak_capital=peak_capital,
        )

        # 7. Persist
        deploy_record = CapitalDeployment(
            deployment_date=date.today(),
            regime=plan.regime,
            blended_risk_score=plan.blended_risk_score,
            ai_confidence=plan.ai_confidence,
            total_capital=capital,
            equity_pct=next((a.allocation_pct for a in plan.assets if a.asset == "Equity"), 0),
            gold_pct=next((a.allocation_pct for a in plan.assets if a.asset == "Gold"), 0),
            silver_pct=next((a.allocation_pct for a in plan.assets if a.asset == "Silver"), 0),
            cash_pct=next((a.allocation_pct for a in plan.assets if a.asset == "Cash"), 0),
            equity_amount=next((a.amount for a in plan.assets if a.asset == "Equity"), 0),
            gold_amount=next((a.amount for a in plan.assets if a.asset == "Gold"), 0),
            silver_amount=next((a.amount for a in plan.assets if a.asset == "Silver"), 0),
            cash_amount=next((a.amount for a in plan.assets if a.asset == "Cash"), 0),
            stock_picks_json=json.dumps([
                {"symbol": s.symbol, "qty": s.quantity, "amount": s.amount, "price": s.price}
                for s in plan.stock_picks
            ]),
            rebalance_needed=plan.rebalance_needed,
            why_no_trades=plan.why_no_trades,
        )
        db.add(deploy_record)
        await db.commit()

        # 8. Build response
        return _plan_to_response(plan)

    except Exception as e:
        logger.error(f"Capital deployment error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── AI Risk Probability ──────────────────────────────
@router.get("/ai-risk-probability", response_model=AIRiskProbabilityOut)
async def get_ai_risk_probability(db: AsyncSession = Depends(get_db)):
    """Get AI risk prediction with probabilities and blended score."""
    try:
        from app.strategy.macro_data import get_macro_snapshot
        from app.strategy.risk_engine import compute_risk_score
        from app.strategy.ai_risk_model import predict_risk, blend_risk_scores

        macro = await asyncio.to_thread(get_macro_snapshot)
        risk = await asyncio.to_thread(compute_risk_score, macro)
        ai_pred = await asyncio.to_thread(predict_risk, macro)
        blended = blend_risk_scores(risk.total_risk_score, ai_pred)

        # Persist
        record = AIRiskRecord(
            prediction_date=date.today(),
            ai_risk_score=ai_pred.ai_risk_score,
            p_risk_on=ai_pred.p_risk_on,
            p_risk_off=ai_pred.p_risk_off,
            expected_equity_return=ai_pred.expected_equity_return,
            expected_gold_return=ai_pred.expected_gold_return,
            confidence=ai_pred.confidence,
            model_available=ai_pred.model_available,
            rule_based_score=risk.total_risk_score,
            blended_score=blended,
        )
        db.add(record)
        await db.commit()

        return AIRiskProbabilityOut(
            ai_risk_score=ai_pred.ai_risk_score,
            p_risk_on=ai_pred.p_risk_on,
            p_risk_off=ai_pred.p_risk_off,
            expected_equity_return=ai_pred.expected_equity_return,
            expected_gold_return=ai_pred.expected_gold_return,
            confidence=ai_pred.confidence,
            model_available=ai_pred.model_available,
            rule_based_score=risk.total_risk_score,
            blended_score=blended,
        )
    except Exception as e:
        logger.error(f"AI risk probability error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── Stock Rankings ────────────────────────────────────
@router.get("/stock-rankings", response_model=list[StockRankingOut])
async def get_stock_rankings(
    n: int = 10,
    tier: str = "100",
    db: AsyncSession = Depends(get_db),
):
    """Get top N ranked stocks from the specified universe tier."""
    try:
        from app.strategy.stock_ranker import get_top_ranked
        from app.strategy.macro_data import get_macro_snapshot
        from app.strategy.risk_engine import compute_risk_score

        macro = get_macro_snapshot()
        risk = compute_risk_score(macro)

        ranked = get_top_ranked(n=n, universe_tier=tier, regime=risk.regime)

        # Persist rankings
        for s in ranked:
            row = StockRanking(
                ranking_date=date.today(),
                symbol=s.clean_symbol,
                rank=s.rank,
                composite_score=s.composite,
                rs_3m=s.rs_3m,
                momentum_6m=s.momentum_6m,
                vol_adj_return=s.vol_adj_return,
                volume_strength=s.volume_strength,
                trend_slope=s.trend_slope,
                price=s.price,
            )
            db.add(row)
        await db.commit()

        return [
            StockRankingOut(
                symbol=s.symbol,
                clean_symbol=s.clean_symbol,
                price=s.price,
                rank=s.rank,
                composite=s.composite,
                rs_3m=s.rs_3m,
                momentum_6m=s.momentum_6m,
                vol_adj_return=s.vol_adj_return,
                volume_strength=s.volume_strength,
                trend_slope=s.trend_slope,
                raw_return_3m=s.raw_return_3m,
                raw_return_6m=s.raw_return_6m,
                raw_volatility=s.raw_volatility,
            )
            for s in ranked
        ]
    except Exception as e:
        logger.error(f"Stock rankings error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── Deployment History ────────────────────────────────
@router.get("/deployment-history")
async def get_deployment_history(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """Get recent deployment plan history."""
    result = await db.execute(
        select(CapitalDeployment)
        .order_by(desc(CapitalDeployment.deployment_date))
        .limit(limit)
    )
    rows = result.scalars().all()
    return [
        {
            "date": str(r.deployment_date),
            "regime": r.regime,
            "blended_risk_score": r.blended_risk_score,
            "ai_confidence": r.ai_confidence,
            "equity_pct": r.equity_pct,
            "gold_pct": r.gold_pct,
            "silver_pct": r.silver_pct,
            "cash_pct": r.cash_pct,
            "equity_amount": r.equity_amount,
            "total_capital": r.total_capital,
            "rebalance_needed": r.rebalance_needed,
        }
        for r in rows
    ]


# ─── AI Model Retrain ─────────────────────────────────
@router.post("/ai-retrain")
async def retrain_ai_model():
    """Manually trigger AI model retraining."""
    try:
        from app.strategy.ai_risk_model import train_models
        success = train_models(force=True)
        return {"retrained": success}
    except Exception as e:
        logger.error(f"AI retrain error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── Helpers ───────────────────────────────────────────

def _plan_to_response(plan) -> CapitalDeploymentOut:
    """Convert DeploymentPlan dataclass to Pydantic response."""
    return CapitalDeploymentOut(
        regime=plan.regime,
        regime_label=plan.regime_label,
        regime_confidence=plan.regime_confidence,
        total_capital=plan.total_capital,
        blended_risk_score=plan.blended_risk_score,
        ai_confidence=plan.ai_confidence,
        assets=[
            AssetDeploymentOut(
                asset=a.asset,
                expected_score=a.expected_score,
                allocation_pct=a.allocation_pct,
                amount=a.amount,
                instrument=a.instrument,
                stocks=[
                    StockDeploymentOut(
                        symbol=s.symbol,
                        clean_symbol=s.clean_symbol,
                        price=s.price,
                        quantity=s.quantity,
                        amount=s.amount,
                        weight_pct=s.weight_pct,
                        rank_score=s.rank_score,
                        expected_score=s.expected_score,
                        reason=s.reason,
                    ) for s in a.stocks
                ],
            ) for a in plan.assets
        ],
        stock_picks=[
            StockDeploymentOut(
                symbol=s.symbol,
                clean_symbol=s.clean_symbol,
                price=s.price,
                quantity=s.quantity,
                amount=s.amount,
                weight_pct=s.weight_pct,
                rank_score=s.rank_score,
                expected_score=s.expected_score,
                reason=s.reason,
            ) for s in plan.stock_picks
        ],
        total_deployed=plan.total_deployed,
        cash_reserve=plan.cash_reserve,
        why_no_trades=plan.why_no_trades,
        rebalance_needed=plan.rebalance_needed,
        rebalance_reason=plan.rebalance_reason,
        brokerage_total=plan.brokerage_total,
    )
