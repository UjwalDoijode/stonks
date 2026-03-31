import { useState, useEffect } from "react";
import {
  Bot, Play, BarChart3, ChevronDown, ChevronUp, Zap, Code,
  TrendingUp, Shield, Target, Clock, RefreshCw, Eye,
} from "lucide-react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from "recharts";
import { fetchAlgorithms, runAlgoBacktest, compareAlgorithms } from "../api";

const PERIODS = [
  { value: "1d", label: "1D" },
  { value: "3d", label: "3D" },
  { value: "1w", label: "1W" },
  { value: "1m", label: "1M" },
  { value: "3m", label: "3M" },
  { value: "6m", label: "6M" },
  { value: "1y", label: "1Y" },
  { value: "3y", label: "3Y" },
  { value: "5y", label: "5Y" },
];

const ALGO_ICONS = {
  rsi2_mean_reversion: "&#x21C4;",
  dual_momentum: "&#x2191;&#x2193;",
  turtle_breakout: "&#x1F422;",
  macd_rsi_crossover: "&#x2A2F;",
  bollinger_mean_reversion: "&#x2248;",
};

export default function AlgoTrading() {
  const [algos, setAlgos] = useState({});
  const [selectedAlgo, setSelectedAlgo] = useState(null);
  const [expandedAlgo, setExpandedAlgo] = useState(null);
  const [capital, setCapital] = useState(100000);
  const [symbol, setSymbol] = useState("^NSEI");
  const [period, setPeriod] = useState("3y");
  const [backtestResult, setBacktestResult] = useState(null);
  const [comparison, setComparison] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadingCompare, setLoadingCompare] = useState(false);
  const [tab, setTab] = useState("algos"); // algos | backtest | compare

  useEffect(() => {
    fetchAlgorithms()
      .then(d => setAlgos(d.algorithms || {}))
      .catch(() => {});
  }, []);

  const runBacktest = async (algoId) => {
    setLoading(true);
    setTab("backtest");
    setSelectedAlgo(algoId);
    try {
      const result = await runAlgoBacktest({
        algo_id: algoId,
        symbol,
        capital,
        period,
      });
      setBacktestResult(result);
    } catch (err) {
      setBacktestResult({ error: err.message });
    } finally {
      setLoading(false);
    }
  };

  const runComparison = async () => {
    setLoadingCompare(true);
    setTab("compare");
    try {
      const result = await compareAlgorithms(symbol, capital, period);
      setComparison(result);
    } catch (err) {
      setComparison({ error: err.message });
    } finally {
      setLoadingCompare(false);
    }
  };

  const algoList = Object.entries(algos);

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gold-bright font-display tracking-tight">
            Algorithmic Trading
          </h1>
          <p className="text-muted text-sm mt-1 font-mono">
            5 world-class algos &mdash; backtest with real market data
          </p>
        </div>
      </div>

      {/* Controls */}
      <div className="glass-card p-4">
        <div className="flex flex-wrap items-end gap-3">
          <div className="w-36">
            <label className="text-[10px] font-mono text-muted uppercase">Symbol</label>
            <input
              type="text"
              value={symbol}
              onChange={e => setSymbol(e.target.value.toUpperCase())}
              placeholder="^NSEI, RELIANCE, TCS..."
              className="w-full mt-1 bg-surface border border-gold/20 rounded px-3 py-2 text-sm font-mono text-gold-bright outline-none focus:border-gold/40"
            />
          </div>
          <div className="w-32">
            <label className="text-[10px] font-mono text-muted uppercase">Capital (₹)</label>
            <input
              type="number"
              value={capital}
              onChange={e => setCapital(Number(e.target.value))}
              className="w-full mt-1 bg-surface border border-gold/20 rounded px-3 py-2 text-sm font-mono text-gold-bright outline-none focus:border-gold/40"
            />
          </div>
          <div>
            <label className="text-[10px] font-mono text-muted uppercase">Period</label>
            <div className="flex mt-1 rounded overflow-hidden border border-gold/20">
              {PERIODS.map(p => (
                <button
                  key={p.value}
                  onClick={() => setPeriod(p.value)}
                  className={`px-2.5 py-2 text-[10px] font-mono font-semibold transition-colors ${
                    period === p.value
                      ? "bg-gold/15 text-gold"
                      : "bg-surface text-muted hover:text-gray-300"
                  }`}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>
          <button
            onClick={runComparison}
            disabled={loadingCompare}
            className="btn-primary flex items-center gap-2 py-2"
          >
            <BarChart3 size={14} />
            Compare All
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gold/10 pb-0">
        {[
          { id: "algos", label: "Algorithms", icon: Bot },
          { id: "backtest", label: "Backtest Results", icon: Play },
          { id: "compare", label: "Comparison", icon: BarChart3 },
        ].map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`flex items-center gap-2 px-4 py-2.5 text-xs font-mono transition-colors border-b-2 -mb-[1px] ${
              tab === t.id
                ? "border-gold text-gold"
                : "border-transparent text-muted hover:text-gray-300"
            }`}
          >
            <t.icon size={13} />
            {t.label}
          </button>
        ))}
      </div>

      {/* Algorithm Cards */}
      {tab === "algos" && (
        <div className="space-y-4">
          {algoList.map(([id, algo]) => {
            const isExpanded = expandedAlgo === id;
            return (
              <div key={id} className="glass-card overflow-hidden">
                <div
                  className="p-5 cursor-pointer"
                  onClick={() => setExpandedAlgo(isExpanded ? null : id)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-3">
                      <div className="w-10 h-10 rounded-lg bg-gold/10 flex items-center justify-center text-lg">
                        <span dangerouslySetInnerHTML={{ __html: ALGO_ICONS[id] || "&#x2699;" }} />
                      </div>
                      <div>
                        <h3 className="font-semibold text-gold-bright text-base">{algo.name}</h3>
                        <div className="flex items-center gap-2 mt-1">
                          <span className="pro-badge text-[9px]">{algo.type}</span>
                          <span className="text-[10px] font-mono text-muted">by {algo.author} ({algo.year})</span>
                        </div>
                        <p className="text-xs text-gray-400 mt-2 max-w-2xl leading-relaxed">
                          {algo.description}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={e => { e.stopPropagation(); runBacktest(id); }}
                        className="btn-primary flex items-center gap-1.5 text-xs py-1.5 px-3"
                      >
                        <Play size={12} />
                        Backtest
                      </button>
                      {isExpanded ? <ChevronUp size={16} className="text-muted" /> : <ChevronDown size={16} className="text-muted" />}
                    </div>
                  </div>
                </div>

                {/* Expanded: Full algo details */}
                {isExpanded && (
                  <div className="px-5 pb-5 border-t border-gold/10 pt-4 space-y-4 animate-fade-in">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {/* Rules */}
                      <div>
                        <h4 className="text-[10px] font-mono text-gold uppercase tracking-wider mb-2 flex items-center gap-1">
                          <Code size={10} />
                          Trading Rules
                        </h4>
                        <div className="space-y-1.5">
                          {algo.rules?.map((rule, i) => (
                            <div key={i} className="flex items-start gap-2 text-xs text-gray-300">
                              <span className="text-matrix font-mono">&gt;</span>
                              {rule}
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Risk & Performance */}
                      <div className="space-y-3">
                        <div>
                          <h4 className="text-[10px] font-mono text-gold uppercase tracking-wider mb-1.5 flex items-center gap-1">
                            <Shield size={10} />
                            Risk Management
                          </h4>
                          <p className="text-xs text-gray-400">{algo.risk_management}</p>
                        </div>
                        <div>
                          <h4 className="text-[10px] font-mono text-gold uppercase tracking-wider mb-1.5 flex items-center gap-1">
                            <TrendingUp size={10} />
                            Historical Performance
                          </h4>
                          <p className="text-xs text-gray-400">{algo.historical_performance}</p>
                        </div>
                        <div>
                          <h4 className="text-[10px] font-mono text-gold uppercase tracking-wider mb-1.5 flex items-center gap-1">
                            <Target size={10} />
                            Best For
                          </h4>
                          <p className="text-xs text-matrix">{algo.best_for}</p>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Backtest Results */}
      {tab === "backtest" && (
        <div className="space-y-4">
          {loading ? (
            <div className="glass-card p-12 text-center">
              <div className="text-matrix font-mono text-sm animate-pulse">
                Running backtest... <span className="cursor-blink" />
              </div>
            </div>
          ) : backtestResult?.error ? (
            <div className="glass-card p-6 text-center text-red-400 font-mono text-sm">
              {backtestResult.error}
            </div>
          ) : backtestResult ? (
            <>
              {/* No trades message */}
              {backtestResult.message && backtestResult.total_trades === 0 && (
                <div className="glass-card p-6 text-center border border-gold/20">
                  <div className="text-gold font-mono text-sm">{backtestResult.message}</div>
                </div>
              )}
              {/* Summary header */}
              <div className="glass-card p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-lg font-semibold text-gold-bright">{backtestResult.algorithm}</h3>
                    <span className="text-xs font-mono text-muted">
                      {backtestResult.symbol} &middot; {backtestResult.period} &middot; ₹{backtestResult.capital?.toLocaleString("en-IN")}
                    </span>
                  </div>
                  <div className={`text-2xl font-mono font-bold ${backtestResult.total_return_pct >= 0 ? "text-matrix" : "text-danger"}`}>
                    {backtestResult.total_return_pct >= 0 ? "+" : ""}{backtestResult.total_return_pct}%
                  </div>
                </div>
              </div>

              {/* Stats grid */}
              <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
                {[
                  { label: "Final Capital", value: `₹${backtestResult.final_capital?.toLocaleString("en-IN")}`, color: backtestResult.total_return_pct >= 0 ? "text-matrix" : "text-danger" },
                  { label: "Total P&L", value: `₹${backtestResult.total_pnl?.toLocaleString("en-IN")}`, color: backtestResult.total_pnl >= 0 ? "text-matrix" : "text-danger" },
                  { label: "Total Trades", value: backtestResult.total_trades },
                  { label: "Win Rate", value: `${backtestResult.win_rate}%`, color: backtestResult.win_rate >= 50 ? "text-matrix" : "text-danger" },
                  { label: "Profit Factor", value: backtestResult.profit_factor, color: backtestResult.profit_factor >= 1.5 ? "text-matrix" : "text-gold" },
                  { label: "Max Drawdown", value: `${backtestResult.max_drawdown_pct}%`, color: "text-danger" },
                  { label: "Avg Win", value: `₹${backtestResult.avg_win}`, color: "text-matrix" },
                  { label: "Avg Loss", value: `₹${backtestResult.avg_loss}`, color: "text-danger" },
                  { label: "Best Trade", value: `₹${backtestResult.best_trade}`, color: "text-matrix" },
                  { label: "Worst Trade", value: `₹${backtestResult.worst_trade}`, color: "text-danger" },
                  { label: "Avg Hold Days", value: `${backtestResult.avg_holding_days}d` },
                  { label: "Winners/Losers", value: `${backtestResult.winning_trades}/${backtestResult.losing_trades}` },
                ].map((s, i) => (
                  <div key={i} className="glass-card p-3">
                    <div className="text-[9px] font-mono text-muted uppercase tracking-wider">{s.label}</div>
                    <div className={`text-sm font-mono font-bold mt-1 ${s.color || "text-gray-200"}`}>{s.value}</div>
                  </div>
                ))}
              </div>

              {/* Equity Curve */}
              {backtestResult.equity_curve?.length > 1 && (
                <div className="glass-card p-4">
                  <h3 className="text-[10px] font-mono text-gold uppercase tracking-wider mb-3">Equity Curve</h3>
                  <ResponsiveContainer width="100%" height={300}>
                    <LineChart data={backtestResult.equity_curve}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(207,181,126,0.06)" />
                      <XAxis dataKey="date" tick={{ fill: "#5a6478", fontSize: 10, fontFamily: "IBM Plex Mono" }} />
                      <YAxis tick={{ fill: "#5a6478", fontSize: 10, fontFamily: "IBM Plex Mono" }} />
                      <Tooltip
                        contentStyle={{ background: "rgba(10,14,26,0.97)", border: "1px solid rgba(207,181,126,0.2)" }}
                        labelStyle={{ color: "#cfb57e", fontFamily: "IBM Plex Mono", fontSize: 11 }}
                        itemStyle={{ fontFamily: "IBM Plex Mono", fontSize: 11 }}
                      />
                      <Line
                        type="monotone"
                        dataKey="equity"
                        stroke="#00ff41"
                        strokeWidth={2}
                        dot={false}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              )}

              {/* Trade Log */}
              {backtestResult.trades?.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-gold uppercase tracking-wider font-mono mb-3">
                    Trade Log ({backtestResult.total_trades} trades)
                  </h3>
                  <div className="glass-card overflow-hidden">
                    <div className="overflow-x-auto max-h-80">
                      <table className="pro-table w-full">
                        <thead>
                          <tr>
                            <th>#</th>
                            <th>Entry</th>
                            <th>Exit</th>
                            <th>Entry ₹</th>
                            <th>Exit ₹</th>
                            <th>Qty</th>
                            <th>P&L</th>
                            <th>P&L %</th>
                          </tr>
                        </thead>
                        <tbody>
                          {backtestResult.trades.map((t, i) => (
                            <tr key={i}>
                              <td className="text-muted">{i + 1}</td>
                              <td>{t.entry_date}</td>
                              <td>{t.exit_date}</td>
                              <td>₹{t.entry_price}</td>
                              <td>₹{t.exit_price}</td>
                              <td>{t.quantity}</td>
                              <td className={t.pnl >= 0 ? "text-matrix" : "text-danger"}>
                                {t.pnl >= 0 ? "+" : ""}₹{t.pnl}
                              </td>
                              <td className={t.pnl_pct >= 0 ? "text-matrix" : "text-danger"}>
                                {t.pnl_pct >= 0 ? "+" : ""}{t.pnl_pct}%
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="glass-card p-12 text-center text-muted font-mono text-sm">
              Select an algorithm and click "Backtest" to run
            </div>
          )}
        </div>
      )}

      {/* Comparison Tab */}
      {tab === "compare" && (
        <div className="space-y-4">
          {loadingCompare ? (
            <div className="glass-card p-12 text-center">
              <div className="text-matrix font-mono text-sm animate-pulse">
                Comparing all algorithms... <span className="cursor-blink" />
              </div>
            </div>
          ) : comparison?.comparison ? (
            <>
              <div className="glass-card p-4">
                <span className="text-xs font-mono text-muted">
                  Comparing on {comparison.symbol} &middot; {comparison.period} &middot; ₹{comparison.capital?.toLocaleString("en-IN")}
                </span>
              </div>

              {/* Comparison Table */}
              <div className="glass-card overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="pro-table w-full">
                    <thead>
                      <tr>
                        <th>Algorithm</th>
                        <th>Return %</th>
                        <th>Final Capital</th>
                        <th>Win Rate</th>
                        <th>Trades</th>
                        <th>Max DD</th>
                        <th>Profit Factor</th>
                        <th>Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(comparison.comparison)
                        .sort(([, a], [, b]) => (b.total_return_pct || 0) - (a.total_return_pct || 0))
                        .map(([id, r], i) => (
                          <tr key={id}>
                            <td>
                              <div className="flex items-center gap-2">
                                {i === 0 && <span className="text-gold text-xs">&#x1F3C6;</span>}
                                <span className="font-semibold text-gold-bright">{r.name}</span>
                              </div>
                            </td>
                            <td className={(r.total_return_pct || 0) >= 0 ? "text-matrix font-semibold" : "text-danger font-semibold"}>
                              {r.error ? "Error" : `${r.total_return_pct >= 0 ? "+" : ""}${r.total_return_pct}%`}
                            </td>
                            <td>₹{r.final_capital?.toLocaleString("en-IN") || "—"}</td>
                            <td className={(r.win_rate || 0) >= 50 ? "text-matrix" : "text-danger"}>
                              {r.win_rate || 0}%
                            </td>
                            <td>{r.total_trades || 0}</td>
                            <td className="text-danger">{r.max_drawdown_pct || 0}%</td>
                            <td className={(r.profit_factor || 0) >= 1.5 ? "text-matrix" : "text-gold"}>
                              {r.profit_factor || 0}
                            </td>
                            <td>
                              <button
                                onClick={() => runBacktest(id)}
                                className="text-[10px] font-mono px-2 py-1 rounded bg-gold/10 text-gold hover:bg-gold/20 transition-colors"
                              >
                                Details
                              </button>
                            </td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Return Comparison Bar Chart */}
              <div className="glass-card p-4">
                <h3 className="text-[10px] font-mono text-gold uppercase tracking-wider mb-3">Return Comparison</h3>
                <ResponsiveContainer width="100%" height={250}>
                  <BarChart
                    data={Object.entries(comparison.comparison).map(([id, r]) => ({
                      name: r.name?.replace(" Strategy", "").replace(" System", ""),
                      return: r.total_return_pct || 0,
                      winRate: r.win_rate || 0,
                    }))}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(207,181,126,0.06)" />
                    <XAxis dataKey="name" tick={{ fill: "#5a6478", fontSize: 9, fontFamily: "IBM Plex Mono" }} />
                    <YAxis tick={{ fill: "#5a6478", fontSize: 10, fontFamily: "IBM Plex Mono" }} />
                    <Tooltip
                      contentStyle={{ background: "rgba(10,14,26,0.97)", border: "1px solid rgba(207,181,126,0.2)" }}
                      labelStyle={{ color: "#cfb57e", fontFamily: "IBM Plex Mono", fontSize: 11 }}
                    />
                    <Bar dataKey="return" fill="#cfb57e" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </>
          ) : (
            <div className="glass-card p-12 text-center text-muted font-mono text-sm">
              Click "Compare All" to run all algorithms on the same data
            </div>
          )}
        </div>
      )}
    </div>
  );
}
