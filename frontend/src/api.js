const BASE = import.meta.env.VITE_API_URL || "/api";

/* ──────────────────────────────────────────────────────────────
   Lightweight client-side cache + in-flight request deduplication.

   - GET requests: cached with TTL (default 30s). Repeat calls
     within TTL return the cached payload instantly.
   - In-flight dedup: if the same GET is already pending, callers
     await the existing promise instead of firing a duplicate.
   - Mutations (POST/PUT/DELETE/PATCH): bypass cache and invalidate
     the entire cache (safe default — keeps data consistent).
   - Manual control: `invalidateCache(prefix?)` and per-call
     `{ cache: false }` or `{ ttl: 60_000 }` options.
   ────────────────────────────────────────────────────────────── */
const _cache = new Map();      // url -> { ts, ttl, data }
const _inflight = new Map();   // url -> Promise

const DEFAULT_TTL = 30_000;

export function invalidateCache(prefix) {
  if (!prefix) { _cache.clear(); return; }
  for (const k of _cache.keys()) {
    if (k.startsWith(prefix)) _cache.delete(k);
  }
}

async function request(url, options = {}) {
  const method = (options.method || "GET").toUpperCase();
  const useCache = options.cache !== false && method === "GET";
  const ttl = options.ttl ?? DEFAULT_TTL;

  if (useCache) {
    const hit = _cache.get(url);
    if (hit && Date.now() - hit.ts < hit.ttl) return hit.data;
    if (_inflight.has(url)) return _inflight.get(url);
  }

  const { cache: _c, ttl: _t, ...fetchOpts } = options;

  const p = (async () => {
    const res = await fetch(`${BASE}${url}`, {
      headers: { "Content-Type": "application/json", ...fetchOpts.headers },
      ...fetchOpts,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || "API Error");
    }
    const data = await res.json();
    if (useCache) _cache.set(url, { ts: Date.now(), ttl, data });
    if (method !== "GET") invalidateCache();   // mutations bust the cache
    return data;
  })();

  if (useCache) {
    _inflight.set(url, p);
    p.finally(() => _inflight.delete(url));
  }
  return p;
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
  // Live prices need fresh data — short TTL.
  return request(`/scanner/live-prices${q}`, { ttl: 10_000 });
};

// Test/debug exports
export const __cache = { invalidate: invalidateCache, _request: request };

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

// Alerts (server-side, persistent — evaluated on every list call)
export const fetchAlerts = (opts = {}) => {
  const params = new URLSearchParams();
  if (opts.evaluate === false) params.set("evaluate", "false");
  if (opts.includeTriggered === false) params.set("include_triggered", "false");
  const q = params.toString();
  // Short TTL so live evaluation isn't masked by cache.
  return request(`/alerts/${q ? `?${q}` : ""}`, { ttl: 5_000 });
};
export const createAlert = (data) =>
  request("/alerts/", { method: "POST", body: JSON.stringify(data) });
export const deleteAlert = (id) =>
  request(`/alerts/${id}`, { method: "DELETE" });
export const resetAlert = (id) =>
  request(`/alerts/${id}/reset`, { method: "POST" });

// Today's Signals digest (Dashboard surface)
export const fetchTodaysSignals = (limit = 8) =>
  request(`/signals/today?limit=${limit}`, { ttl: 30_000 });
