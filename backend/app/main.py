"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings
from app.database import init_db
from app.routes import scanner, trades, portfolio, backtest, risk_allocation, deployment, advisor
from app.routes import risk_overview, geopolitics, paper_trading, algo_trading

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def _scheduled_risk_update():
    """Background job: compute and cache risk score + AI blend."""
    try:
        from app.strategy.macro_data import get_macro_snapshot
        from app.strategy.risk_engine import compute_risk_score
        from app.strategy.ai_risk_model import predict_risk, blend_risk_scores

        macro = get_macro_snapshot()
        risk = compute_risk_score(macro)
        ai_pred = predict_risk(macro)
        blended = blend_risk_scores(risk.total_risk_score, ai_pred)
        logger.info(
            f"Scheduled risk update: rule={risk.total_risk_score}, "
            f"ai={ai_pred.ai_risk_score}, blended={blended}, regime={risk.regime}"
        )
    except Exception as e:
        logger.error(f"Scheduled risk update failed: {e}")


async def _scheduled_volatility_update():
    """Background job: update volatility metrics cache."""
    try:
        from app.strategy.volatility_targeting import compute_volatility_scaling
        vol = compute_volatility_scaling(equity_pct=50.0)
        logger.info(
            f"Scheduled vol update: portfolio_vol={vol.portfolio_vol:.1f}%, "
            f"scaling_factor={vol.scaling_factor:.2f}"
        )
    except Exception as e:
        logger.error(f"Scheduled volatility update failed: {e}")


async def _scheduled_ai_retrain():
    """Background job: weekly AI model retraining."""
    try:
        from app.strategy.ai_risk_model import train_models
        success = train_models(force=True)
        logger.info(f"Scheduled AI retrain: success={success}")
    except Exception as e:
        logger.error(f"Scheduled AI retrain failed: {e}")


async def _try_train_ai_model():
    """Attempt to train AI model on startup (non-blocking)."""
    try:
        from app.strategy.ai_risk_model import train_models
        train_models()
    except Exception as e:
        logger.warning(f"AI model training skipped: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database and scheduler on startup."""
    await init_db()

    # Train AI model (non-blocking, uses cached data if available)
    await _try_train_ai_model()

    # Start scheduler
    # Daily risk update at 9:30 AM (IST approximate — runs in server timezone)
    scheduler.add_job(_scheduled_risk_update, "cron", hour=9, minute=30, day_of_week="mon-fri",
                      id="daily_risk", replace_existing=True)
    # Daily volatility update at 6 PM
    scheduler.add_job(_scheduled_volatility_update, "cron", hour=18, minute=0, day_of_week="mon-fri",
                      id="daily_vol", replace_existing=True)
    # Weekly AI retrain on Sunday 6 AM
    scheduler.add_job(_scheduled_ai_retrain, "cron", hour=6, minute=0, day_of_week="sun",
                      id="weekly_ai_retrain", replace_existing=True)
    scheduler.start()
    logger.info("Background scheduler started (risk, vol, AI retrain)")

    yield

    scheduler.shutdown(wait=False)
    logger.info("Background scheduler stopped")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
)

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "https://*.github.io",
    ],
    allow_origin_regex=r"https://.*\.github\.io",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(scanner.router, prefix="/api")
app.include_router(trades.router, prefix="/api")
app.include_router(portfolio.router, prefix="/api")
app.include_router(backtest.router, prefix="/api")
app.include_router(risk_allocation.router, prefix="/api")
app.include_router(deployment.router, prefix="/api")
app.include_router(advisor.router, prefix="/api")
app.include_router(risk_overview.router, prefix="/api")
app.include_router(geopolitics.router)
app.include_router(paper_trading.router)
app.include_router(algo_trading.router)


@app.get("/api/capital")
async def get_capital():
    return {"capital": settings.INITIAL_CAPITAL}


@app.put("/api/capital")
async def set_capital(body: dict):
    new_capital = float(body.get("capital", settings.INITIAL_CAPITAL))
    if new_capital < 1000:
        from fastapi import HTTPException
        raise HTTPException(400, "Minimum capital is ₹1,000")
    settings.INITIAL_CAPITAL = new_capital
    return {"capital": settings.INITIAL_CAPITAL}


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.VERSION,
        "capital": settings.INITIAL_CAPITAL,
        "universe": settings.UNIVERSE,
    }
