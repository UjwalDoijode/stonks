# Stonks — AI-Powered Swing Trading Terminal

<p align="center">
  <strong>A full-stack positional swing trading system built for Indian markets (NIFTY 500).</strong><br>
  AI-driven stock scanning, 8-layer risk control, real-time geopolitical intelligence, multi-asset backtesting, and a professional dark terminal UI.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12-blue?logo=python" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.104-009688?logo=fastapi" alt="FastAPI">
  <img src="https://img.shields.io/badge/React-18-61DAFB?logo=react" alt="React">
  <img src="https://img.shields.io/badge/Vite-5-646CFF?logo=vite" alt="Vite">
  <img src="https://img.shields.io/badge/TailwindCSS-3.4-06B6D4?logo=tailwindcss" alt="Tailwind">
  <img src="https://img.shields.io/badge/LightGBM-ML-green" alt="ML">
</p>

> **Capital Target**: Designed for ₹20,000 initial capital with intelligent position sizing.

---

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [Docker Deployment](#docker-deployment)
- [Project Structure](#project-structure)
- [API Reference](#api-reference)
- [Risk Control Pipeline](#risk-control-pipeline)
- [Configuration](#configuration)
- [Screenshots](#screenshots)
- [Scheduled Jobs](#scheduled-jobs)
- [Notes](#notes)
- [License](#license)

---

## Features

### 📊 Expert Stock Scanner
- Scans the **NIFTY 500** universe for pullback-to-20DMA swing setups
- 6-criteria signal engine: 200 DMA trend, 20 DMA proximity, RSI range, volume confirmation, ADR filter, risk/reward
- AI-powered recommendations: **RECOMMENDED / BUY / HOLD / AVOID** with conviction scores
- Per-stock trade intelligence: entry price, stop-loss, target, R:R ratio, expected P&L

### 🌍 Geopolitical & Macro Risk Intelligence
- Real-time conflict tracking: Russia-Ukraine, Iran-Israel, US-China, India border, Red Sea
- Live RSS news scanning from Reuters, CNBC, BBC, Economic Times, Livemint
- 40+ risk-keyword scoring engine for headlines
- Market proxy analysis: VIX Fear, Safe Haven Flow, Oil Shock, Currency Stress
- Defensive positioning recommendations (RISK_ON / DEFENSIVE / CASH)

### 📈 Multi-Asset Backtesting
- **Individual asset backtests**: Gold, Silver, NIFTY 50, S&P 500, Gold ETF, Silver ETF
- **Recommendation backtest**: Monthly rotation of top 5 momentum stocks vs NIFTY benchmark
- **Swing trade backtest**: Full pullback strategy simulation across NIFTY 100
- Equity curves, CAGR, Sharpe ratio, max drawdown, alpha vs benchmark

### 🤖 AI Risk Model
- **LightGBM + XGBoost** ensemble for market regime detection
- Features: VIX, Gold, Oil, DXY, Yield Spread, moving averages, RSI, momentum
- Dynamic 70/30 rule-to-AI blending with adaptive feedback loop

### 🛡️ 8-Layer Risk Control Pipeline
1. **Risk Governor** — Drawdown circuit breaker, loss streak pause, hard stop
2. **Volatility Targeting** — Scale equity allocation to 12% annualised vol target
3. **Opportunity Filter** — Return/drawdown ratio gate per asset class
4. **Correlation Control** — Sector dedup + correlation penalty on stock picks
5. **Liquidity Filter** — Volume, turnover, spread checks to avoid illiquid traps
6. **Adaptive Feedback** — Auto-adjusts rule vs AI weighting based on trade outcomes
7. **Monte Carlo Simulation** — 5000-path forward projection with percentile fan charts
8. **Smart Cash** — Deploys idle cash to Liquid ETFs / overnight funds for yield

### 💼 Capital Deployment Engine
- Dynamic allocation across Equity / Gold / Silver / Cash based on macro regime
- Stock ranking with multi-factor scoring (momentum, mean reversion, quality)
- Intelligent position sizing with Kelly Criterion integration
- Portfolio-level risk management (max 3 concurrent positions, 1.5% risk per trade)

### 📡 Market Indicators (Real-Time)
- **Commodities**: Gold, Silver, Crude Oil, Brent Crude, Natural Gas
- **Volatility**: India VIX with fear/calm badges
- **Forex**: USD/INR exchange rate
- **ETFs**: Gold ETF (GOLDBEES), Silver ETF (SILVERBEES)
- **Macro**: India CPI Inflation

### 🔥 Additional Features
- **Investment Advisor** — AI-generated buy/sell/hold actions for any capital amount
- **Sector Heatmap** — GICS sector performance visualisation
- **Watchlist** — Track favourite stocks with live prices
- **Compounding Simulator** — Project future returns with custom CAGR & monthly SIP
- **Position Sizer** — Calculate exact qty, risk, and reward for any setup
- **Risk Dashboard** — Unified view of all 8 risk control modules
- **Trade Journal** — Full entry/exit logging with P&L tracking

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Frontend (React)                   │
│  Dashboard │ Scanner │ Backtest │ Risk │ Advisor     │
└──────────────────────┬──────────────────────────────┘
                       │ REST API (JSON)
┌──────────────────────▼──────────────────────────────┐
│                 FastAPI Backend                       │
│                                                      │
│  Routes ──► Services ──► Strategy Engine              │
│                             │                        │
│   ┌─────────────────────────▼────────────────────┐   │
│   │           Risk Control Pipeline              │   │
│   │  Governor → Vol Target → Opp Filter →        │   │
│   │  Correlation → Liquidity → Feedback →        │   │
│   │  Monte Carlo → Smart Cash                    │   │
│   └──────────────────────────────────────────────┘   │
│                             │                        │
│   ┌─────────────────────────▼────────────────────┐   │
│   │  AI Models (LightGBM + XGBoost ensemble)     │   │
│   └──────────────────────────────────────────────┘   │
│                             │                        │
│   ┌─────────────────────────▼────────────────────┐   │
│   │  Data Layer (yfinance + RSS + SQLite)         │   │
│   └──────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.12, FastAPI 0.104, SQLAlchemy 2.0 (async), SQLite (aiosqlite) |
| **Frontend** | React 18, Vite 5, Tailwind CSS 3.4, Recharts 2.10, Lucide Icons |
| **ML/AI** | LightGBM 4.2, XGBoost 2.0, scikit-learn 1.3 |
| **Data** | yfinance (market data), RSS feeds (Reuters, BBC, CNBC) |
| **Scheduling** | APScheduler (daily risk scoring, weekly AI retraining) |
| **Deployment** | Docker, Docker Compose, Nginx (reverse proxy) |

---

## Getting Started

### Prerequisites

- **Python 3.12+** — [Download](https://www.python.org/downloads/)
- **Node.js 18+** — [Download](https://nodejs.org/)
- **Git** — [Download](https://git-scm.com/)

### 1. Clone the Repository

```bash
git clone https://github.com/UjwalDoijode/stonks.git
cd stonks
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment (recommended)
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The API will be available at **http://localhost:8000**  
Swagger docs at **http://localhost:8000/docs**

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install --legacy-peer-deps

# Start dev server
npm run dev
```

The app will be available at **http://localhost:5173**

### 4. First Run

1. Open **http://localhost:5173** in your browser
2. Navigate to the **Scanner** page
3. Click **Run Expert Scan** — this downloads data for NIFTY 500 stocks (takes 3–5 min on first run)
4. Stocks are categorised as RECOMMENDED / BUY / HOLD / AVOID with full trade setups

---

## Docker Deployment

```bash
# Build and run both services
docker-compose up --build -d

# Frontend: http://localhost:3000
# Backend:  http://localhost:8000
```

---

## Project Structure

```
stonks/
├── backend/
│   ├── app/
│   │   ├── main.py                # FastAPI entry point + schedulers
│   │   ├── config.py              # All settings (capital, risk, regime thresholds)
│   │   ├── models.py              # SQLAlchemy models (Trade, Snapshot, Watchlist, etc.)
│   │   ├── schemas.py             # Pydantic request/response schemas (~60 models)
│   │   ├── services.py            # Core business logic (scan, trade, portfolio)
│   │   ├── database.py            # Async SQLite engine
│   │   ├── routes/
│   │   │   ├── scanner.py         # Stock scanner, commodities, search, sectors
│   │   │   ├── portfolio.py       # Dashboard, equity curve, portfolio stats
│   │   │   ├── trades.py          # Trade CRUD (open, close, update)
│   │   │   ├── backtest.py        # Asset, recommendation, swing backtests
│   │   │   ├── risk_allocation.py # Risk scoring, allocation, macro status
│   │   │   ├── deployment.py      # Capital deployment engine
│   │   │   ├── advisor.py         # AI investment advisor
│   │   │   └── risk_overview.py   # Unified risk control dashboard
│   │   └── strategy/
│   │       ├── signals.py         # 6-criteria pullback signal engine
│   │       ├── market_intelligence.py  # Expert analysis & recommendations
│   │       ├── news_intelligence.py    # RSS geo-risk scoring
│   │       ├── ai_risk_model.py   # LightGBM/XGBoost ensemble
│   │       ├── risk_engine.py     # Multi-factor risk scoring
│   │       ├── allocation_engine.py    # Dynamic asset allocation
│   │       ├── deployment_engine.py    # Full deployment pipeline
│   │       ├── stock_ranker.py    # Multi-factor stock ranking
│   │       ├── position_sizing.py # Kelly criterion sizing
│   │       ├── risk_governor.py   # Drawdown circuit breaker (Part 1)
│   │       ├── volatility_targeting.py # Vol-adjusted scaling (Part 2)
│   │       ├── opportunity_filter.py   # Return/drawdown gate (Part 3)
│   │       ├── correlation_control.py  # Sector/correlation dedup (Part 4)
│   │       ├── liquidity_filter.py     # Volume/spread checks (Part 5)
│   │       ├── adaptive_feedback.py    # Trade outcome learning (Part 6)
│   │       ├── monte_carlo.py     # Forward simulation (Part 7)
│   │       ├── smart_cash.py      # Idle cash optimisation (Part 8)
│   │       ├── macro_data.py      # Macro indicator fetching
│   │       ├── indicators.py      # Technical indicators (RSI, MACD, BB)
│   │       ├── backtester.py      # Swing trade backtester
│   │       ├── asset_backtester.py     # Asset class backtesting
│   │       ├── allocation_backtester.py # Allocation strategy backtest
│   │       ├── cache_layer.py     # OHLCV data caching
│   │       ├── data_feed.py       # NIFTY 500 constituent data
│   │       └── universe.py        # Stock universe definitions
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.jsx                # Router & page layout
│   │   ├── api.js                 # Backend API client (~30 endpoints)
│   │   ├── main.jsx               # React entry
│   │   ├── index.css              # Tailwind + custom glass-morphism theme
│   │   ├── components/
│   │   │   ├── UI.jsx             # Shared components (Card, Badge, Loader, etc.)
│   │   │   ├── Sidebar.jsx        # Navigation sidebar
│   │   │   └── StockDetailModal.jsx # Detailed stock analysis modal
│   │   └── pages/
│   │       ├── Dashboard.jsx      # Portfolio overview + governor status
│   │       ├── Scanner.jsx        # Stock scanner + market indicators
│   │       ├── Backtest.jsx       # Multi-asset backtesting
│   │       ├── Allocation.jsx     # Asset allocation engine
│   │       ├── Deployment.jsx     # Capital deployment plan
│   │       ├── RiskDashboard.jsx  # 8-module risk control centre
│   │       ├── Advisor.jsx        # AI investment advisor
│   │       ├── PositionSizer.jsx  # Position sizing calculator
│   │       ├── Trades.jsx         # Trade journal
│   │       ├── Watchlist.jsx      # Stock watchlist
│   │       └── Compounder.jsx     # Compounding simulator
│   ├── package.json
│   ├── tailwind.config.js
│   └── vite.config.js
├── docker-compose.yml
├── Dockerfile
├── nginx.conf
├── .gitignore
└── README.md
```

---

## API Reference

### Scanner & Market Data

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/scanner/run` | Run expert scan on NIFTY 500 |
| GET | `/api/scanner/latest` | Latest scan results |
| GET | `/api/scanner/search?q=` | Search stocks by name/symbol |
| GET | `/api/scanner/live-prices?symbols=` | Live prices for symbols |
| GET | `/api/scanner/sectors` | Sector heatmap data |
| GET | `/api/scanner/commodities` | Gold, Silver, Oil, VIX, Nat Gas, USD/INR |
| GET | `/api/scanner/sentiment` | Market sentiment composite score |
| GET | `/api/scanner/geo-risk` | Geopolitical risk assessment + live news |
| GET | `/api/scanner/regime` | Current market regime |
| GET | `/api/scanner/watchlist` | Watchlist with live prices |

### Risk & Allocation

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/risk-score` | Multi-factor risk score |
| GET | `/api/allocation` | Current optimal allocation |
| GET | `/api/macro-status` | Macro indicator dashboard |
| GET | `/api/deployment` | Full capital deployment plan |
| GET | `/api/risk-overview` | All 8 risk control modules in one call |
| GET | `/api/governor-status` | Risk governor circuit breaker status |
| GET | `/api/monte-carlo` | Monte Carlo simulation results |
| GET | `/api/feedback-stats` | Adaptive feedback statistics |
| GET | `/api/smart-cash` | Smart cash utilisation plan |

### Portfolio & Trades

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/dashboard` | Full dashboard data (portfolio + risk + deployment) |
| GET | `/api/portfolio/stats` | Portfolio statistics |
| GET | `/api/equity-curve` | Equity curve data points |
| POST | `/api/trades` | Open a new trade |
| PUT | `/api/trades/{id}/close` | Close an existing trade |
| GET | `/api/trades` | List all trades |

### Backtesting

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/backtest/asset` | Backtest individual asset (Gold/Silver/NIFTY) |
| POST | `/api/backtest/recommendation` | Backtest recommendation strategy |
| POST | `/api/backtest/run` | Run swing trade backtest |
| POST | `/api/backtest/allocation` | Backtest allocation strategy |

### Advisor

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/advisor/recommend?capital=` | AI-generated investment recommendations |

---

## Risk Control Pipeline

The deployment engine runs every allocation through an 8-stage risk pipeline:

```
Input Capital & Regime
        │
        ▼
┌─ 1. Risk Governor ─────────────────────┐
│  Drawdown > 8%? → Cut equity 50%       │
│  3 consecutive losses? → Pause 7 days  │
│  Monthly loss > 5%? → Force defensive  │
│  Drawdown > 15%? → Full cash (STOP)    │
└────────────────────────────────────────┘
        │
        ▼
┌─ 2. Volatility Targeting ──────────────┐
│  Portfolio vol > 12% target?           │
│  → Scale down equity proportionally    │
└────────────────────────────────────────┘
        │
        ▼
┌─ 3. Opportunity Filter ───────────────┐
│  Expected return / drawdown < 0.5?     │
│  → Boost cash, skip asset class        │
└────────────────────────────────────────┘
        │
        ▼
┌─ 4. Correlation Control ──────────────┐
│  Max 2 stocks per sector               │
│  Penalise corr > 0.75 between picks   │
└────────────────────────────────────────┘
        │
        ▼
┌─ 5. Liquidity Filter ─────────────────┐
│  Avg volume < 50K? → Reject           │
│  Daily turnover < ₹50L? → Reject      │
│  Estimated spread > 0.5%? → Flag      │
└────────────────────────────────────────┘
        │
        ▼
┌─ 6. Adaptive Feedback ────────────────┐
│  Track high/low conf trade outcomes    │
│  Auto-adjust rule vs AI weighting      │
│  Default: 70% rules / 30% AI          │
└────────────────────────────────────────┘
        │
        ▼
┌─ 7. Monte Carlo Simulation ───────────┐
│  5000 forward paths from trade history │
│  VaR 95%, percentile fan charts        │
│  Probability of negative months        │
└────────────────────────────────────────┘
        │
        ▼
┌─ 8. Smart Cash ───────────────────────┐
│  Deploy idle cash to Liquid ETFs       │
│  Overnight funds, money market         │
│  Target ~5-7% yield on idle capital    │
└────────────────────────────────────────┘
        │
        ▼
  Final Deployment Plan
  (Equity picks + Gold + Cash + Yields)
```

---

## Configuration

Key settings in `backend/app/config.py` (all overridable via `.env`):

| Setting | Default | Description |
|---------|---------|-------------|
| `INITIAL_CAPITAL` | ₹20,000 | Starting capital |
| `RISK_PER_TRADE_PCT` | 1.5% | Max risk per trade |
| `MAX_SIMULTANEOUS_TRADES` | 3 | Max concurrent positions |
| `TARGET_R_MULTIPLE` | 2.0 | Risk-reward target |
| `RSI_LOW / RSI_HIGH` | 40 / 65 | RSI range for pullback signals |
| `UNIVERSE_TIER` | 100 | Default scan tier (50/100/200/500) |
| `GOVERNOR_DRAWDOWN_LIMIT` | 8% | Drawdown trigger for equity cut |
| `GOVERNOR_HARD_STOP` | 15% | Drawdown trigger for full cash |
| `VOL_TARGET_ANNUAL` | 12% | Portfolio volatility target |
| `OPPORTUNITY_MIN_SCORE` | 0.5 | Min return/drawdown ratio |
| `LIQUIDITY_MIN_TURNOVER` | ₹50L | Min daily turnover |
| `AI_BLEND_RULE_WEIGHT` | 0.70 | Rule-based weight in blending |
| `AI_BLEND_AI_WEIGHT` | 0.30 | AI model weight in blending |

---

## Screenshots

The app features a professional dark terminal UI with custom glass-morphism effects:

- **Scanner** — Stock cards with conviction badges, entry/SL/target, market indicators ticker
- **Dashboard** — Portfolio overview, equity curve, governor status badge, deployment summary
- **Risk Control** — 8-module risk centre: governor, volatility bars, Monte Carlo charts, correlation matrix
- **Backtest** — Asset class comparison, recommendation strategy vs benchmark, equity drawdown charts
- **Advisor** — AI-generated buy/sell/hold recommendations with quantity & amount
- **Sector Heatmap** — Colour-coded GICS sector performance grid

---

## Scheduled Jobs

| Job | Schedule | Description |
|-----|----------|-------------|
| Risk Score Update | Daily 9:00 AM (Mon–Fri) | Refresh macro risk components |
| Stock Scan | Friday 3:30 PM | Weekly universe scan |
| Volatility Update | Daily 6:00 PM (Mon–Fri) | Recalculate vol metrics |
| AI Model Retrain | Sunday 6:00 AM | Weekly model retraining |

---

## Notes

- Market data sourced from **Yahoo Finance** via yfinance — may have 15-minute delay during market hours
- The AI risk model auto-trains on first run (~30 seconds)
- RSS news feeds require internet connectivity
- Designed for **Indian market** (NSE/BSE) stocks; supports international indices in backtesting
- SQLite database is auto-created on first run — no external DB setup needed
- **This is a research/educational tool — not financial advice**

---

## Author

**Ujwal Doijode** — [GitHub](https://github.com/UjwalDoijode)

---

## License

MIT
