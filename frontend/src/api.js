const BASE = import.meta.env.VITE_API_URL || "/api";

async function request(url, options = {}) {
  const res = await fetch(`${BASE}${url}`, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "API Error");
  }
  return res.json();
}

// Dashboard
export const fetchDashboard = () => request("/dashboard");

// Scanner
export const runScan = () => request("/scanner/run", { method: "POST" });
export const fetchLatestScan = () => request("/scanner/latest");
export const fetchCandidates = () => request("/scanner/candidates");
export const fetchRegime = () => request("/scanner/regime");
export const fetchSentiment = () => request("/scanner/sentiment");
export const fetchGeoRisk = () => request("/scanner/geo-risk");

// Trades
export const fetchTrades = (status) =>
  request(`/trades/${status ? `?status=${status}` : ""}`);
export const fetchOpenTrades = () => request("/trades/open");
export const createTrade = (data) =>
  request("/trades/", { method: "POST", body: JSON.stringify(data) });
export const closeTrade = (id, data) =>
  request(`/trades/${id}/close`, { method: "PUT", body: JSON.stringify(data) });

// Portfolio
export const fetchPortfolioStats = () => request("/portfolio/stats");
export const fetchEquityCurve = () => request("/portfolio/equity-curve");

// Position Sizing
export const calcPositionSize = (data) =>
  request("/position-size", { method: "POST", body: JSON.stringify(data) });

// Backtest
export const runBacktest = (data) =>
  request("/backtest/run", { method: "POST", body: JSON.stringify(data) });
export const fetchBacktestResults = () => request("/backtest/results");
export const fetchBacktestDetail = (id) => request(`/backtest/results/${id}`);
export const runAssetBacktest = (assetType, years = 5, capital = 20000) =>
  request(`/backtest/asset?asset_type=${assetType}&years=${years}&initial_capital=${capital}`, { method: "POST" });
export const runRecommendationBacktest = (years = 3, capital = 20000) =>
  request(`/backtest/recommendation?years=${years}&initial_capital=${capital}`, { method: "POST" });

// Compounding
export const simulateCompounding = (data) =>
  request("/compounding", { method: "POST", body: JSON.stringify(data) });

// Risk & Allocation
export const fetchRiskScore = () => request("/risk-score");
export const fetchAllocation = () => request("/allocation");
export const fetchMacroStatus = () => request("/macro-status");
export const fetchRiskHistory = (limit = 30) => request(`/risk-history?limit=${limit}`);
export const fetchRegimeHistory = (limit = 20) => request(`/regime-history?limit=${limit}`);
export const runAllocBacktest = (data) =>
  request("/allocation-backtest", { method: "POST", body: JSON.stringify(data) });

// Capital Deployment
export const fetchCapitalDeployment = () => request("/capital-deployment");
export const fetchDeploymentHistory = (limit = 20) => request(`/deployment-history?limit=${limit}`);

// AI Risk
export const fetchAIRiskProbability = () => request("/ai-risk-probability");
export const retrainAIModel = () => request("/ai-retrain", { method: "POST" });

// Stock Rankings
export const fetchStockRankings = (n = 10, tier = "100") => request(`/stock-rankings?n=${n}&tier=${tier}`);

// Stock Search & Detail
export const searchStocks = (q) => request(`/scanner/search?q=${encodeURIComponent(q)}`);
export const fetchStockDetail = (symbol) => request(`/scanner/stock/${encodeURIComponent(symbol)}`);
export const fetchLivePrices = (symbols) => {
  const q = symbols ? `?symbols=${symbols}` : "";
  return request(`/scanner/live-prices${q}`);
};

// Watchlist
export const fetchWatchlist = () => request("/scanner/watchlist");
export const addToWatchlist = (symbol, notes) =>
  request("/scanner/watchlist", { method: "POST", body: JSON.stringify({ symbol, notes }) });
export const removeFromWatchlist = (symbol) =>
  request(`/scanner/watchlist/${encodeURIComponent(symbol)}`, { method: "DELETE" });

// Sectors
export const fetchSectors = () => request("/scanner/sectors");

// Commodities (Gold, Silver, Crude Oil)
export const fetchCommodityPrices = () => request("/scanner/commodities");

// Smart Money Advisor
export const fetchSmartAdvice = (capital) =>
  request(`/advisor/recommend?capital=${capital}`);
export const fetchAIRecommendation = (capital) =>
  request(`/advisor/ai-recommend?capital=${capital}`);

// Risk Overview (Parts 1-8)
export const fetchRiskOverview = () => request("/risk-overview");
export const fetchGovernorStatus = () => request("/governor-status");
export const fetchMonteCarlo = () => request("/monte-carlo");
export const fetchFeedbackStats = () => request("/feedback-stats");
export const fetchSmartCash = () => request("/smart-cash");

// Capital
export const fetchCapital = () => request("/capital");
export const updateCapital = (capital) =>
  request("/capital", { method: "PUT", body: JSON.stringify({ capital }) });

// Geopolitics
export const fetchGeopoliticsOverview = () => request("/geopolitics/overview");
export const fetchGeopoliticsConflicts = () => request("/geopolitics/conflicts");
export const fetchGeopoliticsHeadlines = () => request("/geopolitics/headlines");

// Paper Trading
export const paperTrade = (data) =>
  request("/paper/trade", { method: "POST", body: JSON.stringify(data) });
export const fetchPaperPortfolio = () => request("/paper/portfolio");
export const resetPaperAccount = (capital = 100000) =>
  request("/paper/reset", { method: "POST", body: JSON.stringify({ capital }) });

// Algo Trading
export const fetchAlgorithms = () => request("/algos");
export const fetchAlgorithm = (algoId) => request(`/algos/${algoId}`);
export const runAlgoBacktest = (data) =>
  request("/algos/backtest", { method: "POST", body: JSON.stringify(data) });
export const compareAlgorithms = (symbol = "^NSEI", capital = 100000, period = "1y") =>
  request(`/algos/compare?symbol=${encodeURIComponent(symbol)}&capital=${capital}&period=${period}`, { method: "POST" });

// AI Assistant
export const aiChat = (data) =>
  request("/ai/chat", { method: "POST", body: JSON.stringify(data) });
export const aiAnalyze = (data) =>
  request("/ai/analyze", { method: "POST", body: JSON.stringify(data) });
export const aiMarketBrief = () => request("/ai/brief");

// News
export const fetchNews = () => request("/news");
export const fetchNewsAISummary = () => request("/news/ai-summary");
