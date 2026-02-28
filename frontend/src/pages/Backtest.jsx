import { useState, useEffect } from "react";
import {
  AreaChart, Area, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine,
} from "recharts";
import {
  TrendingUp, TrendingDown, BarChart3, Target, Zap,
  DollarSign, Shield, Award, ArrowRight,
} from "lucide-react";
import { Card, StatCard, Loader, ErrorMsg, Badge, SkeletonCard } from "../components/UI";
import {
  runBacktest, fetchBacktestResults, fetchBacktestDetail,
  runAssetBacktest, runRecommendationBacktest,
} from "../api";
import { useCapital } from "../App";

const CHART_TOOLTIP = {
  contentStyle: {
    background: "rgba(17,24,39,0.95)",
    border: "1px solid rgba(30,41,59,0.8)",
    borderRadius: 8,
    fontSize: 12,
    backdropFilter: "blur(12px)",
    boxShadow: "0 4px 20px rgba(0,0,0,0.5)",
  },
  labelStyle: { color: "#64748b", fontSize: 11 },
};

const ASSET_OPTIONS = [
  { value: "gold", label: "Gold (COMEX)", icon: "🥇", color: "text-amber-400" },
  { value: "silver", label: "Silver (COMEX)", icon: "🥈", color: "text-gray-300" },
  { value: "equity", label: "NIFTY 50", icon: "📈", color: "text-emerald-400" },
  { value: "gold_etf", label: "Gold ETF (GOLDBEES)", icon: "🏦", color: "text-amber-400" },
  { value: "sp500", label: "S&P 500", icon: "🇺🇸", color: "text-blue-400" },
];

const YEAR_OPTIONS = [1, 2, 3, 5, 10];

export default function Backtest() {
  // Tab state
  const [activeTab, setActiveTab] = useState("asset"); // 'asset' | 'recommendation' | 'swing'

  // Asset backtest state
  const [assetType, setAssetType] = useState("gold");
  const [assetYears, setAssetYears] = useState(5);
  const { capital: globalCapital } = useCapital();
  const [assetCapital, setAssetCapital] = useState(String(Math.round(globalCapital)));
  const [assetResult, setAssetResult] = useState(null);
  const [assetLoading, setAssetLoading] = useState(false);
  const [assetError, setAssetError] = useState(null);

  // Recommendation backtest state
  const [recYears, setRecYears] = useState(3);
  const [recCapital, setRecCapital] = useState(String(Math.round(globalCapital)));
  const [recResult, setRecResult] = useState(null);
  const [recLoading, setRecLoading] = useState(false);
  const [recError, setRecError] = useState(null);

  // Swing backtest state (existing)
  const [results, setResults] = useState([]);
  const [detail, setDetail] = useState(null);
  const [swingLoading, setSwingLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [swingError, setSwingError] = useState(null);
  const [form, setForm] = useState({ initial_capital: String(Math.round(globalCapital)) });

  useEffect(() => {
    fetchBacktestResults()
      .then(setResults)
      .catch(() => {})
      .finally(() => setSwingLoading(false));
  }, []);

  // ── Asset Backtest Handler ──
  const handleAssetBacktest = async () => {
    setAssetLoading(true);
    setAssetError(null);
    try {
      const res = await runAssetBacktest(assetType, assetYears, parseFloat(assetCapital));
      setAssetResult(res);
    } catch (e) {
      setAssetError(e.message);
    } finally {
      setAssetLoading(false);
    }
  };

  // ── Recommendation Backtest Handler ──
  const handleRecBacktest = async () => {
    setRecLoading(true);
    setRecError(null);
    try {
      const res = await runRecommendationBacktest(recYears, parseFloat(recCapital));
      setRecResult(res);
    } catch (e) {
      setRecError(e.message);
    } finally {
      setRecLoading(false);
    }
  };

  // ── Swing Backtest Handler ──
  const handleSwingRun = async () => {
    setRunning(true);
    setSwingError(null);
    try {
      const res = await runBacktest({ initial_capital: parseFloat(form.initial_capital) });
      setResults((prev) => [res, ...prev]);
      const d = await fetchBacktestDetail(res.id);
      setDetail(d);
    } catch (e) {
      setSwingError(e.message);
    } finally {
      setRunning(false);
    }
  };

  const loadDetail = async (id) => {
    try {
      const d = await fetchBacktestDetail(id);
      setDetail(d);
    } catch (e) {
      setSwingError(e.message);
    }
  };

  const tabs = [
    { id: "asset", label: "Gold / Silver / Equity", icon: DollarSign },
    { id: "recommendation", label: "Recommendation Backtest", icon: Award },
    { id: "swing", label: "Swing Trade Backtest", icon: Target },
  ];

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Backtesting</h2>
        <p className="text-xs text-muted mt-0.5 font-medium">
          Test performance of Gold, Silver, Equity, or recommendation-based strategies
        </p>
      </div>

      {/* Tab Navigation */}
      <div className="flex gap-1 p-1 bg-base/60 rounded-xl border border-border/30">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all flex-1 justify-center ${
                activeTab === tab.id
                  ? "bg-blue-500/15 text-blue-400 border border-blue-500/30"
                  : "text-muted hover:text-gray-300 hover:bg-white/[0.03]"
              }`}
            >
              <Icon size={14} />
              <span className="hidden md:inline">{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* ════════════════════════════════════════════════════ */}
      {/* TAB 1: Asset Class Backtest */}
      {/* ════════════════════════════════════════════════════ */}
      {activeTab === "asset" && (
        <div className="space-y-5 animate-slide-up">
          {/* Controls */}
          <Card>
            <div className="flex flex-wrap items-end gap-4">
              <div>
                <label className="text-[10px] text-muted uppercase tracking-wider font-semibold block mb-1.5">Asset</label>
                <select
                  value={assetType}
                  onChange={(e) => setAssetType(e.target.value)}
                  className="bg-base border border-border rounded-lg px-3 py-2 text-sm font-medium focus:border-blue-500/40 outline-none transition-colors min-w-[180px]"
                >
                  {ASSET_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.icon} {opt.label}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-[10px] text-muted uppercase tracking-wider font-semibold block mb-1.5">Period</label>
                <div className="flex gap-1.5">
                  {YEAR_OPTIONS.map((yr) => (
                    <button
                      key={yr}
                      onClick={() => setAssetYears(yr)}
                      className={`px-3 py-2 rounded-lg text-sm font-mono font-medium transition-all ${
                        assetYears === yr
                          ? "bg-blue-500/15 text-blue-400 border border-blue-500/30"
                          : "bg-base border border-border text-muted hover:text-gray-300"
                      }`}
                    >
                      {yr}Y
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="text-[10px] text-muted uppercase tracking-wider font-semibold block mb-1.5">Capital (₹)</label>
                <input
                  type="number"
                  value={assetCapital}
                  onChange={(e) => setAssetCapital(e.target.value)}
                  className="bg-base border border-border rounded-lg px-3 py-2 text-sm font-mono w-28 focus:border-blue-500/40 outline-none transition-colors"
                />
              </div>
              <button
                onClick={handleAssetBacktest}
                disabled={assetLoading}
                className="btn-primary disabled:opacity-50 flex items-center gap-2"
              >
                {assetLoading ? (
                  <>
                    <div className="h-4 w-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Running...
                  </>
                ) : (
                  <>
                    <Zap size={14} />
                    Run Backtest
                  </>
                )}
              </button>
            </div>
          </Card>

          {assetError && <ErrorMsg message={assetError} />}

          {assetLoading && (
            <Card>
              <div className="text-center py-10">
                <Loader />
                <p className="text-muted mt-4 text-sm">
                  Fetching {ASSET_OPTIONS.find(o => o.value === assetType)?.label} data for {assetYears} years...
                </p>
              </div>
            </Card>
          )}

          {assetResult && !assetLoading && (
            <div className="space-y-4 animate-slide-up">
              {/* Asset Header */}
              <div className="glass-card p-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="text-3xl">{ASSET_OPTIONS.find(o => o.value === assetType)?.icon}</span>
                  <div>
                    <h3 className="text-lg font-bold">{assetResult.asset}</h3>
                    <span className="text-xs text-muted font-mono">{assetResult.symbol} &bull; {assetResult.start_date} → {assetResult.end_date}</span>
                  </div>
                </div>
                <div className="text-right">
                  <div className={`text-3xl font-bold font-mono ${assetResult.total_return_pct >= 0 ? "text-profit" : "text-loss"}`}>
                    {assetResult.total_return_pct >= 0 ? "+" : ""}{assetResult.total_return_pct}%
                  </div>
                  <div className="text-xs text-muted">Total Return</div>
                </div>
              </div>

              {/* Stats Grid */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <StatCard label="Initial" value={`₹${Number(assetResult.initial_capital).toLocaleString("en-IN")}`} />
                <StatCard
                  label="Final Value"
                  value={`₹${Number(assetResult.final_value).toLocaleString("en-IN")}`}
                  color={assetResult.final_value >= assetResult.initial_capital ? "text-profit" : "text-loss"}
                />
                <StatCard label="CAGR" value={`${assetResult.cagr}%`} color={assetResult.cagr >= 0 ? "text-profit" : "text-loss"} />
                <StatCard label="Max Drawdown" value={`${assetResult.max_drawdown_pct}%`} color="text-loss" />
                <StatCard label="Current Price" value={`${assetResult.current_price?.toLocaleString()}`} />
                <StatCard label="Start Price" value={`${assetResult.start_price?.toLocaleString()}`} />
                <StatCard label="Sharpe Ratio" value={assetResult.sharpe_ratio} />
                <StatCard label="Volatility" value={`${assetResult.annualised_volatility}%`} />
                <StatCard label="Best Year" value={`${assetResult.best_year_pct}%`} color="text-profit" />
                <StatCard label="Worst Year" value={`${assetResult.worst_year_pct}%`} color="text-loss" />
              </div>

              {/* Performance Chart */}
              {assetResult.curve?.length > 0 && (
                <Card title={`${assetResult.asset} — ${assetYears}Y Performance`}>
                  <div className="h-80">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={assetResult.curve}>
                        <defs>
                          <linearGradient id="assetGrad" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor={assetResult.total_return_pct >= 0 ? "#10b981" : "#ef4444"} stopOpacity={0.25} />
                            <stop offset="95%" stopColor={assetResult.total_return_pct >= 0 ? "#10b981" : "#ef4444"} stopOpacity={0} />
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(30,41,59,0.5)" vertical={false} />
                        <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#64748b" }} tickLine={false} axisLine={false}
                          tickFormatter={(d) => d.slice(0, 7)} interval={Math.floor(assetResult.curve.length / 8)} />
                        <YAxis tick={{ fontSize: 11, fill: "#64748b" }} tickLine={false} axisLine={false} width={55}
                          tickFormatter={(v) => `₹${(v/1000).toFixed(0)}K`} />
                        <Tooltip {...CHART_TOOLTIP} formatter={(v) => [`₹${Number(v).toLocaleString()}`, "Value"]} />
                        <ReferenceLine y={assetResult.initial_capital} stroke="#64748b" strokeDasharray="4 4"
                          label={{ value: "Initial", fill: "#64748b", fontSize: 10 }} />
                        <Area type="monotone" dataKey="value" stroke={assetResult.total_return_pct >= 0 ? "#10b981" : "#ef4444"}
                          fill="url(#assetGrad)" strokeWidth={2} dot={false} />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </Card>
              )}

              {/* Return % Chart */}
              {assetResult.curve?.length > 0 && (
                <Card title="Cumulative Return (%)">
                  <div className="h-56">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={assetResult.curve}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(30,41,59,0.5)" vertical={false} />
                        <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#64748b" }} tickLine={false} axisLine={false}
                          tickFormatter={(d) => d.slice(0, 7)} interval={Math.floor(assetResult.curve.length / 8)} />
                        <YAxis tick={{ fontSize: 11, fill: "#64748b" }} tickLine={false} axisLine={false} width={45}
                          tickFormatter={(v) => `${v}%`} />
                        <Tooltip {...CHART_TOOLTIP} formatter={(v) => [`${v}%`, "Return"]} />
                        <ReferenceLine y={0} stroke="#64748b" strokeDasharray="4 4" />
                        <Line type="monotone" dataKey="return_pct" stroke="#3b82f6" dot={false} strokeWidth={2} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </Card>
              )}
            </div>
          )}

          {!assetResult && !assetLoading && (
            <Card>
              <div className="text-center py-12">
                <DollarSign size={48} className="text-muted mx-auto mb-4 opacity-50" />
                <h3 className="text-lg font-semibold mb-2">Asset Class Backtest</h3>
                <p className="text-sm text-muted max-w-md mx-auto leading-relaxed">
                  Select an asset (Gold, Silver, or Equity), choose a time period,
                  and see what your returns would have been with a buy-and-hold strategy.
                </p>
              </div>
            </Card>
          )}
        </div>
      )}

      {/* ════════════════════════════════════════════════════ */}
      {/* TAB 2: Recommendation Backtest */}
      {/* ════════════════════════════════════════════════════ */}
      {activeTab === "recommendation" && (
        <div className="space-y-5 animate-slide-up">
          <Card>
            <div className="flex flex-wrap items-end gap-4">
              <div>
                <label className="text-[10px] text-muted uppercase tracking-wider font-semibold block mb-1.5">Period</label>
                <div className="flex gap-1.5">
                  {[1, 2, 3, 5].map((yr) => (
                    <button
                      key={yr}
                      onClick={() => setRecYears(yr)}
                      className={`px-3 py-2 rounded-lg text-sm font-mono font-medium transition-all ${
                        recYears === yr
                          ? "bg-purple-500/15 text-purple-400 border border-purple-500/30"
                          : "bg-base border border-border text-muted hover:text-gray-300"
                      }`}
                    >
                      {yr}Y
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="text-[10px] text-muted uppercase tracking-wider font-semibold block mb-1.5">Capital (₹)</label>
                <input
                  type="number"
                  value={recCapital}
                  onChange={(e) => setRecCapital(e.target.value)}
                  className="bg-base border border-border rounded-lg px-3 py-2 text-sm font-mono w-28 focus:border-purple-500/40 outline-none"
                />
              </div>
              <button
                onClick={handleRecBacktest}
                disabled={recLoading}
                className="btn-primary disabled:opacity-50 flex items-center gap-2"
              >
                {recLoading ? (
                  <>
                    <div className="h-4 w-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Running...
                  </>
                ) : (
                  <>
                    <Award size={14} />
                    Run Recommendation Backtest
                  </>
                )}
              </button>
            </div>
            <p className="text-xs text-muted mt-3 leading-relaxed">
              Simulates monthly rotation: pick top 5 momentum stocks from NIFTY universe,
              hold for 1 month, then rotate. This shows what returns you'd get following our recommendations.
            </p>
          </Card>

          {recError && <ErrorMsg message={recError} />}

          {recLoading && (
            <Card>
              <div className="text-center py-10">
                <Loader />
                <p className="text-muted mt-4 text-sm">
                  Downloading ~40 stocks and simulating {recYears} years of monthly rotation...
                  <br />
                  <span className="text-gray-600">This may take a minute.</span>
                </p>
              </div>
            </Card>
          )}

          {recResult && !recLoading && (
            <div className="space-y-4 animate-slide-up">
              {/* Header Banner */}
              <div className={`glass-card p-5 bg-gradient-to-r ${
                recResult.total_return_pct > recResult.benchmark_return_pct
                  ? "from-emerald-500/10 to-blue-500/10 border-emerald-500/30"
                  : "from-red-500/10 to-gray-500/10 border-red-500/30"
              }`}>
                <div className="flex items-center justify-between flex-wrap gap-3">
                  <div>
                    <h3 className="text-lg font-bold">{recResult.strategy}</h3>
                    <span className="text-xs text-muted font-mono">{recResult.start_date} → {recResult.end_date}</span>
                  </div>
                  <div className="flex gap-6">
                    <div className="text-center">
                      <div className={`text-2xl font-bold font-mono ${recResult.total_return_pct >= 0 ? "text-profit" : "text-loss"}`}>
                        {recResult.total_return_pct >= 0 ? "+" : ""}{recResult.total_return_pct}%
                      </div>
                      <div className="text-[9px] text-muted uppercase">Strategy</div>
                    </div>
                    <div className="text-center">
                      <span className="text-muted text-sm">vs</span>
                    </div>
                    <div className="text-center">
                      <div className={`text-2xl font-bold font-mono ${recResult.benchmark_return_pct >= 0 ? "text-emerald-400/70" : "text-red-400/70"}`}>
                        {recResult.benchmark_return_pct >= 0 ? "+" : ""}{recResult.benchmark_return_pct}%
                      </div>
                      <div className="text-[9px] text-muted uppercase">NIFTY (Benchmark)</div>
                    </div>
                  </div>
                </div>
                <div className="mt-3 flex items-center gap-2">
                  <span className={`px-3 py-1 rounded-full text-xs font-bold ${
                    recResult.alpha > 0
                      ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/20"
                      : "bg-red-500/15 text-red-400 border border-red-500/20"
                  }`}>
                    Alpha: {recResult.alpha >= 0 ? "+" : ""}{recResult.alpha}%
                  </span>
                  <span className="text-xs text-muted">
                    {recResult.alpha > 0 ? "Our picks outperformed the market!" : "Market beat our picks in this period."}
                  </span>
                </div>
              </div>

              {/* Stats */}
              <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                <StatCard label="Final Capital" value={`₹${Number(recResult.final_capital).toLocaleString("en-IN")}`}
                  color={recResult.final_capital >= recResult.initial_capital ? "text-profit" : "text-loss"} />
                <StatCard label="CAGR" value={`${recResult.cagr}%`} color={recResult.cagr >= 0 ? "text-profit" : "text-loss"} />
                <StatCard label="Max Drawdown" value={`${recResult.max_drawdown_pct}%`} color="text-loss" />
                <StatCard label="Win Rate" value={`${recResult.win_rate}%`}
                  sub={`${recResult.winning_trades}W / ${recResult.losing_trades}L`}
                  color={recResult.win_rate >= 55 ? "text-profit" : "text-amber-400"} />
                <StatCard label="Sharpe" value={recResult.sharpe_ratio} />
              </div>

              {/* Equity Curve */}
              {recResult.curve?.length > 0 && (
                <Card title="Portfolio Growth — Recommendation Strategy">
                  <div className="h-72">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={recResult.curve}>
                        <defs>
                          <linearGradient id="recGrad" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.25} />
                            <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(30,41,59,0.5)" vertical={false} />
                        <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#64748b" }} tickLine={false} axisLine={false}
                          tickFormatter={(d) => d.slice(0, 7)} interval={Math.floor(recResult.curve.length / 8)} />
                        <YAxis tick={{ fontSize: 11, fill: "#64748b" }} tickLine={false} axisLine={false} width={55}
                          tickFormatter={(v) => `₹${(v/1000).toFixed(0)}K`} />
                        <Tooltip {...CHART_TOOLTIP} formatter={(v) => [`₹${Number(v).toLocaleString()}`, "Portfolio"]} />
                        <ReferenceLine y={recResult.initial_capital} stroke="#64748b" strokeDasharray="4 4"
                          label={{ value: "Initial", fill: "#64748b", fontSize: 10 }} />
                        <Area type="monotone" dataKey="value" stroke="#8b5cf6" fill="url(#recGrad)" strokeWidth={2} dot={false} />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </Card>
              )}
            </div>
          )}

          {!recResult && !recLoading && (
            <Card>
              <div className="text-center py-12">
                <Award size={48} className="text-muted mx-auto mb-4 opacity-50" />
                <h3 className="text-lg font-semibold mb-2">What If You Followed Our Picks?</h3>
                <p className="text-sm text-muted max-w-md mx-auto leading-relaxed">
                  This backtest simulates buying the top momentum stocks every month based on
                  our recommendation engine. See how much you would have made versus NIFTY.
                </p>
              </div>
            </Card>
          )}
        </div>
      )}

      {/* ════════════════════════════════════════════════════ */}
      {/* TAB 3: Swing Trade Backtest (existing) */}
      {/* ════════════════════════════════════════════════════ */}
      {activeTab === "swing" && (
        <div className="space-y-5 animate-slide-up">
          <Card>
            <div className="flex items-center justify-between flex-wrap gap-3">
              <p className="text-xs text-muted font-medium">
                Simulate swing trades on NIFTY 100 using pullback-to-20DMA strategy
              </p>
              <div className="flex gap-3 items-center">
                <input
                  type="number"
                  value={form.initial_capital}
                  onChange={(e) => setForm({ initial_capital: e.target.value })}
                  className="bg-base border border-border rounded-lg px-3 py-2 text-sm font-mono w-28 focus:border-blue-500/40 outline-none"
                  placeholder="Capital"
                />
                <button onClick={handleSwingRun} disabled={running} className="btn-primary disabled:opacity-50">
                  {running ? "Running..." : "Run Backtest"}
                </button>
              </div>
            </div>
          </Card>

          {swingError && <ErrorMsg message={swingError} />}

          {running && (
            <Card>
              <div className="text-center py-10">
                <Loader />
                <p className="text-muted mt-4 text-sm leading-relaxed">
                  Fetching data for ~100 stocks and simulating trades...
                  <br />
                  <span className="text-gray-600">This may take a few minutes.</span>
                </p>
              </div>
            </Card>
          )}

          {detail && (
            <div className="space-y-4 animate-slide-up">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <StatCard label="Final Capital" value={`₹${detail.summary.final_capital.toLocaleString("en-IN")}`}
                  color={detail.summary.final_capital >= detail.summary.initial_capital ? "text-profit" : "text-loss"} />
                <StatCard label="Total Return" value={`${detail.summary.total_return_pct}%`}
                  color={detail.summary.total_return_pct >= 0 ? "text-profit" : "text-loss"} />
                <StatCard label="Win Rate" value={`${detail.summary.win_rate}%`}
                  sub={`${detail.summary.winning_trades}W / ${detail.summary.losing_trades}L`}
                  color={detail.summary.win_rate >= 60 ? "text-profit" : "text-amber-400"} />
                <StatCard label="CAGR" value={`${detail.summary.cagr}%`} />
                <StatCard label="Max Drawdown" value={`${detail.summary.max_drawdown_pct}%`} color="text-loss" />
                <StatCard label="Profit Factor" value={detail.summary.profit_factor} />
                <StatCard label="Sharpe Ratio" value={detail.summary.sharpe_ratio} />
                <StatCard label="Total Trades" value={detail.summary.total_trades} />
              </div>

              {detail.equity_curve?.length > 0 && (
                <Card title="Backtest Equity Curve">
                  <div className="h-72">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={detail.equity_curve}>
                        <defs>
                          <linearGradient id="btGrad" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#10b981" stopOpacity={0.25} />
                            <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(30,41,59,0.5)" vertical={false} />
                        <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#64748b" }} tickLine={false} axisLine={false} />
                        <YAxis tick={{ fontSize: 11, fill: "#64748b" }} tickLine={false} axisLine={false} width={50} />
                        <Tooltip {...CHART_TOOLTIP} />
                        <Area type="monotone" dataKey="equity" stroke="#10b981" fill="url(#btGrad)" strokeWidth={2} dot={false} />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </Card>
              )}

              {detail.trades?.length > 0 && (
                <Card title={`Backtest Trades (${detail.trades.length})`}>
                  <div className="overflow-x-auto max-h-72 overflow-y-auto">
                    <table className="pro-table w-full">
                      <thead>
                        <tr>
                          <th className="text-left">Symbol</th>
                          <th className="text-right">Entry</th>
                          <th className="text-right">Exit</th>
                          <th className="text-right">Qty</th>
                          <th className="text-right">P&L</th>
                          <th className="text-right">R</th>
                          <th className="text-center">Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {detail.trades.map((t, i) => (
                          <tr key={i}>
                            <td className="font-semibold text-gray-200">{t.symbol?.replace(".NS", "")}</td>
                            <td className="text-right font-mono">
                              ₹{t.entry_price} <span className="text-gray-600 text-[10px]">({t.entry_date})</span>
                            </td>
                            <td className="text-right font-mono">
                              ₹{t.exit_price} <span className="text-gray-600 text-[10px]">({t.exit_date})</span>
                            </td>
                            <td className="text-right font-mono">{t.quantity}</td>
                            <td className={`text-right font-mono font-semibold ${t.pnl >= 0 ? "text-profit" : "text-loss"}`}>
                              {t.pnl >= 0 ? "+" : ""}₹{t.pnl?.toFixed(0)}
                            </td>
                            <td className={`text-right font-mono ${t.r_multiple >= 0 ? "text-profit" : "text-loss"}`}>
                              {t.r_multiple?.toFixed(1)}R
                            </td>
                            <td className="text-center">
                              <Badge variant={t.status === "CLOSED_TP" ? "success" : t.status === "CLOSED_SL" ? "danger" : "warning"}>
                                {t.status?.replace("CLOSED_", "")}
                              </Badge>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </Card>
              )}
            </div>
          )}

          {results.length > 0 && (
            <Card title="Previous Backtest Runs">
              <div className="overflow-x-auto">
                <table className="pro-table w-full">
                  <thead>
                    <tr>
                      <th className="text-left">Date</th>
                      <th className="text-right">Period</th>
                      <th className="text-right">Trades</th>
                      <th className="text-right">Win Rate</th>
                      <th className="text-right">Return</th>
                      <th className="text-center">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {results.map((r) => (
                      <tr key={r.id}>
                        <td className="font-mono text-muted">{new Date(r.run_date).toLocaleDateString()}</td>
                        <td className="text-right font-mono text-muted">{r.start_date} → {r.end_date}</td>
                        <td className="text-right font-mono">{r.total_trades}</td>
                        <td className="text-right font-mono">{r.win_rate}%</td>
                        <td className={`text-right font-mono font-semibold ${r.total_return_pct >= 0 ? "text-profit" : "text-loss"}`}>
                          {r.total_return_pct}%
                        </td>
                        <td className="text-center">
                          <button onClick={() => loadDetail(r.id)}
                            className="text-blue-400 hover:text-blue-300 text-xs font-semibold transition-colors">
                            View
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}
