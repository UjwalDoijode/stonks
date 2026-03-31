# Stonks - AI-Powered Trading Terminal

A full-stack AI trading intelligence platform built for Indian markets (NIFTY 500).
Gemini AI assistant, expert stock scanning, 6-algorithm backtesting lab, real-time news aggregation, 8-layer risk control, and a professional dark terminal UI.

**Python 3.12** | **FastAPI 0.104** | **React 18** | **Vite 5** | **Tailwind CSS 3.4** | **Gemini AI 2.5 Flash** | **LightGBM + XGBoost**

> **Capital Target**: Configurable starting capital (default Rs 20,000) - editable live from the sidebar.

---

## Table of Contents

- [Features](#features)
- [Pages](#pages)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [Docker Deployment](#docker-deployment)
- [Project Structure](#project-structure)
- [API Reference](#api-reference)
- [Risk Control Pipeline](#risk-control-pipeline)
- [Configuration](#configuration)
- [Scheduled Jobs](#scheduled-jobs)
- [Notes](#notes)
- [License](#license)

---

## Features

### Gemini AI Assistant
- **Chat with AI** - Ask anything about markets, get real-time data-enriched answers
- Auto-detects stock symbols and enriches responses with live price, RSI, 50/200 DMA, PE ratio
- **Deep stock analysis** - Detailed technical + fundamental breakdown with entry/target/stop-loss
- **Morning market brief** - AI-generated daily market overview with actionable trade ideas
- Powered by **Google Gemini 2.5 Flash** with 60s thinking time

### Expert Stock Scanner
- Scans **NIFTY 100** universe for pullback-to-20DMA swing setups
- **8-criteria signal engine**: 200 DMA trend, 50 DMA slope, 20 DMA proximity, RSI zone, volume contraction, entry trigger, CCI momentum, Supertrend direction
- AI-powered recommendations: **RECOMMENDED / BUY / HOLD / AVOID** with conviction scores (0-100)
- Per-stock trade intelligence: entry price, stop-loss, 3 targets, R:R ratio
- **Live price refresh** - All stock cards update with current prices via refresh button or 30s auto-refresh

### Smart Money Advisor
- **AI Picks mode** - Gemini generates specific stock recommendations with entry/target/stop-loss using live market data and system-ranked stocks
- **Quant Engine mode** - Rule-based recommendations using risk scoring, stock ranking, and deployment engine
- Both modes consider market regime, VIX, geopolitical risk, and earnings momentum
- Specific actionable output: "Buy X shares of SYMBOL at Rs Y"

### Market News
- Aggregates financial news from **5 RSS sources**: Moneycontrol, Economic Times, LiveMint, Reuters, CNBC
- Category filtering: Indian Markets, Indian Economy, Indian Finance, Global, US Markets
- **AI news analysis** - Gemini summarises top headlines with sentiment detection (Bullish/Bearish/Mixed)

### Algo Lab (6 Strategies)
- **Trend Pullback Master** - Buy pullbacks to 20-EMA in strong uptrends
- **Buy the Dip** - RSI(2) oversold + price near lower Bollinger Band
- **3-Down Reversal** - Three consecutive red candles into reversal entry
- **Momentum Breakout Pro** - 52-week high breakouts with volume confirmation
- **Bear Market Short Seller** - Short when below 200-SMA + death cross + RSI(5) overbought
- **Adaptive All-Weather** - Auto-switches long/short based on bull/bear regime detection
- Compare all algos side-by-side across 1M-5Y periods

### Geopolitical & Macro Risk Intelligence
- Real-time conflict tracking: Russia-Ukraine, Iran-Israel, US-China, India border, Red Sea
- Live RSS news scanning from Reuters, CNBC, BBC, Economic Times, Livemint
- 40+ risk-keyword scoring engine for headlines
- Market proxy analysis: VIX Fear, Safe Haven Flow, Oil Shock, Currency Stress
- Defensive positioning recommendations (RISK_ON / DEFENSIVE / CASH)

### Multi-Asset Backtesting
- **Individual asset backtests**: Gold, Silver, NIFTY 50, S&P 500, Gold ETF, Silver ETF
- **Recommendation backtest**: Monthly rotation of top 5 momentum stocks vs NIFTY benchmark
- **Swing trade backtest**: Full pullback strategy simulation across NIFTY 100
- Equity curves, CAGR, Sharpe ratio, max drawdown, alpha vs benchmark

### AI Risk Model
- **LightGBM + XGBoost** ensemble for market regime detection
- Features: VIX, Gold, Oil, DXY, Yield Spread, moving averages, RSI, momentum
- Dynamic 70/30 rule-to-AI blending with adaptive feedback loop

### 8-Layer Risk Control Pipeline
1. **Risk Governor** - Drawdown circuit breaker, loss streak pause, hard stop
2. **Volatility Targeting** - Scale equity allocation to 12% annualised vol target
3. **Opportunity Filter** - Return/drawdown ratio gate per asset class
4. **Correlation Control** - Sector dedup + correlation penalty on stock picks
5. **Liquidity Filter** - Volume, turnover, spread checks to avoid illiquid traps
6. **Adaptive Feedback** - Auto-adjusts rule vs AI weighting based on trade outcomes
7. **Monte Carlo Simulation** - 5000-path forward projection with percentile fan charts
8. **Smart Cash** - Deploys idle cash to Liquid ETFs / overnight funds for yield

### Market Indicators (Real-Time)
- **Commodities**: Gold, Silver, Crude Oil, Brent Crude, Natural Gas
- **Volatility**: India VIX with fear/calm badges
- **Forex**: USD/INR exchange rate
- **ETFs**: Gold ETF (GOLDBEES), Silver ETF (SILVERBEES)
- **Macro**: India 10Y Bond Yield (inflation proxy)

---

## Pages

The app has **9 focused pages** accessible from the sidebar:

| Page | Description |
|------|-------------|
| **Dashboard** | Portfolio overview, equity curve, AI morning brief, governor status |
| **AI Assistant** | Chat with Gemini AI about markets, stocks, strategies |
| **Scanner** | NIFTY 100 stock scanner with live prices, sector heatmap, sentiment, geo risk |
| **Smart Advisor** | AI Picks + Quant Engine stock recommendations with specific trade setups |
| **Risk Control** | Unified 8-module risk dashboard (governor, vol targeting, Monte Carlo, etc.) |
| **Algo Lab** | Backtest 6 trading algorithms, compare performance side-by-side |
| **Trades** | Trade journal with entry/exit logging and P&L tracking |
| **Backtest** | Multi-asset backtesting (Gold, Silver, NIFTY, S&P 500, strategies) |
| **News** | Financial news from 5 sources with AI-powered summary and sentiment |

---

## Architecture

```
+-----------------------------------------------------+
|                   Frontend (React)                    |
|  Dashboard | AI Chat | Scanner | Advisor | Algo Lab  |
|  Risk | Trades | Backtest | News                     |
+-------------------------+---------------------------+
                          | REST API (JSON)
+-------------------------v---------------------------+
|                  FastAPI Backend                      |
|                                                      |
|  Routes --> Services --> Strategy Engine              |
|                              |                       |
|   +--------------------------------------------------+
|   |           Risk Control Pipeline                  |
|   |  Governor -> Vol Target -> Opp Filter ->         |
|   |  Correlation -> Liquidity -> Feedback ->         |
|   |  Monte Carlo -> Smart Cash                       |
|   +--------------------------------------------------+
|                              |                       |
|   +--------------------------------------------------+
|   |  AI Models (LightGBM + XGBoost + Gemini 2.5)    |
|   +--------------------------------------------------+
|                              |                       |
|   +--------------------------------------------------+
|   |  Data Layer (yfinance + RSS + SQLite + Gemini)   |
|   +--------------------------------------------------+
+------------------------------------------------------+
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.12, FastAPI 0.104, SQLAlchemy 2.0 (async), SQLite (aiosqlite) |
| **Frontend** | React 18, Vite 5, Tailwind CSS 3.4, Recharts 2.10, Lucide Icons |
| **AI/ML** | Google Gemini 2.5 Flash, LightGBM 4.2, XGBoost 2.0, scikit-learn 1.3 |
| **Data** | yfinance (market data), RSS feeds (5 sources), httpx (async HTTP) |
| **Scheduling** | APScheduler (daily risk scoring, weekly AI retraining) |
| **Deployment** | Docker, Docker Compose, Nginx (reverse proxy) |

---

## Getting Started

### Prerequisites

- **Python 3.12+** - [Download](https://www.python.org/downloads/)
- **Node.js 18+** - [Download](https://nodejs.org/)
- **Gemini API Key** - [Get one free](https://aistudio.google.com/apikey)

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

# Create .env file with your Gemini API key
echo GEMINI_API_KEY=your_key_here > .env

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
3. Click **Run Expert Scan** - downloads and analyses NIFTY 100 stocks (takes 2-3 min on first run)
4. Try the **AI Assistant** - ask "How is the market today?" for a live data-enriched response
5. Check **Smart Advisor** - enter your capital and get AI-powered stock picks

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
|-- backend/
|   |-- app/
|   |   |-- main.py                # FastAPI entry point + schedulers
|   |   |-- config.py              # All settings (loaded from .env)
|   |   |-- models.py              # SQLAlchemy models
|   |   |-- schemas.py             # Pydantic schemas (~60 models)
|   |   |-- services.py            # Core business logic
|   |   |-- database.py            # Async SQLite engine
|   |   |-- routes/
|   |   |   |-- scanner.py         # Stock scanner, search, sectors, live prices, commodities
|   |   |   |-- ai_chat.py         # Gemini AI chat, deep analysis, morning brief
|   |   |   |-- advisor.py         # AI Picks + Quant Engine recommendations
|   |   |   |-- news.py            # RSS news aggregation + AI summary
|   |   |   |-- algo_trading.py    # 6-algorithm backtesting engine
|   |   |   |-- portfolio.py       # Dashboard, equity curve
|   |   |   |-- trades.py          # Trade CRUD
|   |   |   |-- backtest.py        # Asset & recommendation backtests
|   |   |   |-- risk_allocation.py # Risk scoring, allocation, macro
|   |   |   |-- risk_overview.py   # Unified risk control dashboard
|   |   |   |-- deployment.py      # Capital deployment engine
|   |   |   +-- ...
|   |   +-- strategy/
|   |       |-- signals.py         # 8-criteria signal engine
|   |       |-- market_intelligence.py  # Expert analysis & recommendations
|   |       |-- news_intelligence.py    # RSS geo-risk scoring
|   |       |-- ai_risk_model.py   # LightGBM/XGBoost ensemble
|   |       |-- risk_engine.py     # Multi-factor risk scoring
|   |       |-- stock_ranker.py    # Multi-factor stock ranking
|   |       |-- risk_governor.py   # Drawdown circuit breaker (Part 1)
|   |       |-- volatility_targeting.py # Vol-adjusted scaling (Part 2)
|   |       |-- monte_carlo.py     # Forward simulation (Part 7)
|   |       |-- smart_cash.py      # Idle cash optimisation (Part 8)
|   |       +-- ...                # 20+ strategy modules
|   |-- .env                       # GEMINI_API_KEY (not committed)
|   |-- requirements.txt
|   +-- Dockerfile
|-- frontend/
|   |-- src/
|   |   |-- App.jsx                # Router + CapitalContext
|   |   |-- api.js                 # Backend API client (~35 endpoints)
|   |   |-- components/
|   |   |   |-- Sidebar.jsx        # 9-page navigation
|   |   |   |-- StockDetailModal.jsx # Stock analysis modal with chart
|   |   |   +-- UI.jsx             # Shared components
|   |   +-- pages/
|   |       |-- Dashboard.jsx      # Portfolio + AI morning brief
|   |       |-- AIChat.jsx         # Gemini AI chat interface
|   |       |-- Scanner.jsx        # Stock scanner + live prices
|   |       |-- Advisor.jsx        # AI Picks + Quant Engine
|   |       |-- RiskDashboard.jsx  # 8-module risk centre
|   |       |-- AlgoTrading.jsx    # 6-strategy algo lab
|   |       |-- Trades.jsx         # Trade journal
|   |       |-- Backtest.jsx       # Multi-asset backtesting
|   |       +-- News.jsx           # Financial news + AI summary
|   |-- package.json
|   +-- vite.config.js
|-- docker-compose.yml
|-- nginx.conf
+-- .gitignore
```

---

## API Reference

### AI & Intelligence

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/ai/chat` | Chat with Gemini AI (auto-enriches with stock data) |
| POST | `/api/ai/analyze` | Deep AI analysis of a specific stock |
| GET | `/api/ai/brief` | AI morning market brief with live data |
| GET | `/api/advisor/ai-recommend?capital=` | Gemini AI stock recommendations |
| GET | `/api/news` | Aggregated news from 5 RSS sources |
| GET | `/api/news/ai-summary` | AI-powered news summary with sentiment |

### Scanner & Market Data

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/scanner/run` | Run expert scan on NIFTY 100 |
| GET | `/api/scanner/latest` | Latest scan results |
| GET | `/api/scanner/search?q=` | Search stocks by name/symbol |
| GET | `/api/scanner/live-prices?symbols=` | Live prices for symbols |
| GET | `/api/scanner/sectors` | Sector heatmap data |
| GET | `/api/scanner/commodities` | Gold, Silver, Oil, VIX, USD/INR |
| GET | `/api/scanner/sentiment` | Market sentiment composite score |
| GET | `/api/scanner/geo-risk` | Geopolitical risk assessment + live news |
| GET | `/api/scanner/regime` | Current market regime |

### Algo Trading

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/algo-trading/algorithms` | List all 6 algorithms |
| POST | `/api/algo-trading/backtest` | Backtest a specific algorithm |
| POST | `/api/algo-trading/compare` | Compare all algorithms |

### Risk & Allocation

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/risk-score` | Multi-factor risk score |
| GET | `/api/allocation` | Current optimal allocation |
| GET | `/api/macro-status` | Macro indicator dashboard |
| GET | `/api/deployment` | Full capital deployment plan |
| GET | `/api/risk-overview` | All 8 risk modules in one call |
| GET | `/api/governor-status` | Risk governor status |
| GET | `/api/monte-carlo` | Monte Carlo simulation |
| GET | `/api/advisor/recommend?capital=` | Quant engine recommendations |

### Portfolio & Trades

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/dashboard` | Full dashboard data |
| GET | `/api/portfolio/stats` | Portfolio statistics |
| GET | `/api/equity-curve` | Equity curve data points |
| POST | `/api/trades` | Open a new trade |
| PUT | `/api/trades/{id}/close` | Close a trade |
| GET | `/api/trades` | List all trades |

### Backtesting

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/backtest/asset` | Backtest individual asset |
| POST | `/api/backtest/recommendation` | Backtest recommendation strategy |
| POST | `/api/backtest/run` | Run swing trade backtest |
| POST | `/api/backtest/allocation` | Backtest allocation strategy |

---

## Risk Control Pipeline

The deployment engine runs every allocation through an 8-stage risk pipeline:

```
Input Capital & Regime
        |
        v
+-- 1. Risk Governor -------------------------+
|  Drawdown > 8%? -> Cut equity 50%           |
|  3 consecutive losses? -> Pause 7 days      |
|  Monthly loss > 5%? -> Force defensive       |
|  Drawdown > 15%? -> Full cash (STOP)        |
+---------------------------------------------+
        |
        v
+-- 2. Volatility Targeting -------------------+
|  Portfolio vol > 12% target?                 |
|  -> Scale down equity proportionally         |
+---------------------------------------------+
        |
        v
+-- 3. Opportunity Filter ---------------------+
|  Expected return / drawdown < 0.5?           |
|  -> Boost cash, skip asset class             |
+---------------------------------------------+
        |
        v
+-- 4. Correlation Control --------------------+
|  Max 2 stocks per sector                     |
|  Penalise corr > 0.75 between picks         |
+---------------------------------------------+
        |
        v
+-- 5. Liquidity Filter -----------------------+
|  Avg volume < 50K? -> Reject                 |
|  Daily turnover < Rs 50L? -> Reject          |
+---------------------------------------------+
        |
        v
+-- 6. Adaptive Feedback ----------------------+
|  Track trade outcomes by confidence level    |
|  Auto-adjust rule vs AI weighting            |
+---------------------------------------------+
        |
        v
+-- 7. Monte Carlo Simulation -----------------+
|  5000 forward paths from trade history       |
|  VaR 95%, percentile fan charts              |
+---------------------------------------------+
        |
        v
+-- 8. Smart Cash -----------------------------+
|  Deploy idle cash to Liquid ETFs             |
|  Target ~5-7% yield on idle capital          |
+---------------------------------------------+
        |
        v
  Final Deployment Plan
  (Equity picks + Gold + Cash + Yields)
```

---

## Configuration

Key settings in `backend/app/config.py` (all overridable via `.env`):

| Setting | Default | Description |
|---------|---------|-------------|
| `GEMINI_API_KEY` | (required) | Google Gemini API key for AI features |
| `INITIAL_CAPITAL` | Rs 20,000 | Starting capital (editable from sidebar) |
| `RISK_PER_TRADE_PCT` | 1.5% | Max risk per trade |
| `MAX_SIMULTANEOUS_TRADES` | 3 | Max concurrent positions |
| `TARGET_R_MULTIPLE` | 2.0 | Risk-reward target |
| `RSI_LOW / RSI_HIGH` | 40 / 65 | RSI range for pullback signals |
| `UNIVERSE_TIER` | 100 | Default scan tier (50/100/200/500) |
| `GOVERNOR_DRAWDOWN_LIMIT` | 8% | Drawdown trigger for equity cut |
| `GOVERNOR_HARD_STOP` | 15% | Drawdown trigger for full cash |
| `VOL_TARGET_ANNUAL` | 12% | Portfolio volatility target |
| `AI_BLEND_RULE_WEIGHT` | 0.70 | Rule-based weight in blending |
| `AI_BLEND_AI_WEIGHT` | 0.30 | AI model weight in blending |

---

## Scheduled Jobs

| Job | Schedule | Description |
|-----|----------|-------------|
| Risk Score Update | Daily 9:00 AM (Mon-Fri) | Refresh macro risk components |
| Stock Scan | Friday 3:30 PM | Weekly universe scan |
| Volatility Update | Daily 6:00 PM (Mon-Fri) | Recalculate vol metrics |
| AI Model Retrain | Sunday 6:00 AM | Weekly model retraining |

---

## Notes

- Market data sourced from **Yahoo Finance** via yfinance - may have 15-minute delay during market hours
- The AI risk model auto-trains on first run (~30 seconds)
- Gemini AI requires a valid API key in `backend/.env` - get one free at [Google AI Studio](https://aistudio.google.com/apikey)
- RSS news feeds require internet connectivity
- Designed for **Indian market** (NSE/BSE) stocks; supports international indices in backtesting
- SQLite database is auto-created on first run - no external DB setup needed
- **This is a research/educational tool - not financial advice**

---

## Author

**Ujwal Doijode** - [GitHub](https://github.com/UjwalDoijode)

---

## License

MIT
