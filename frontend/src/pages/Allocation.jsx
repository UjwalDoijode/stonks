import { useState, useEffect } from "react";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend,
} from "recharts";
import {
  Card, StatCard, Loader, ErrorMsg, RegimeBadge,
  RiskGauge, AllocationDonut, Badge, SkeletonCard,
} from "../components/UI";
import {
  fetchAllocation, fetchRiskScore, fetchMacroStatus,
  fetchRiskHistory, fetchRegimeHistory, runAllocBacktest,
} from "../api";

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

export default function Allocation() {
  const [alloc, setAlloc] = useState(null);
  const [risk, setRisk] = useState(null);
  const [macro, setMacro] = useState(null);
  const [riskHist, setRiskHist] = useState([]);
  const [regimeHist, setRegimeHist] = useState([]);
  const [backtest, setBacktest] = useState(null);
  const [btLoading, setBtLoading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    Promise.all([
      fetchAllocation().catch(() => null),
      fetchRiskScore().catch(() => null),
      fetchMacroStatus().catch(() => null),
      fetchRiskHistory(30).catch(() => []),
      fetchRegimeHistory(10).catch(() => []),
    ])
      .then(([a, r, m, rh, rgh]) => {
        setAlloc(a);
        setRisk(r);
        setMacro(m);
        setRiskHist(rh?.reverse?.() || []);
        setRegimeHist(rgh || []);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const handleBacktest = () => {
    setBtLoading(true);
    runAllocBacktest({ years: 5, initial_capital: 20000, use_deployment_scores: true })
      .then(setBacktest)
      .catch((e) => setError(e.message))
      .finally(() => setBtLoading(false));
  };

  if (loading) return (
    <div className="space-y-6 animate-fade-in">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[...Array(3)].map((_, i) => <SkeletonCard key={i} />)}
      </div>
    </div>
  );
  if (error) return <ErrorMsg message={error} />;

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Capital Allocation</h2>
          <p className="text-xs text-muted mt-0.5 font-medium">
            Regime-Based Dynamic Asset Allocation Engine
          </p>
        </div>
        {risk && <RegimeBadge regime={risk.regime} />}
      </div>

      {/* Top Panel: Risk + Allocation + Macro */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Risk */}
        {risk && (
          <Card title="Risk Score">
            <div className="flex flex-col items-center">
              <RiskGauge score={risk.total_risk_score} label={`Stability: ${risk.stability_score}%`} />
              <div className="grid grid-cols-2 gap-x-6 gap-y-1.5 mt-4 text-xs w-full">
                {[
                  ["Trend", risk.trend_risk, 25],
                  ["Volatility", risk.volatility_risk, 25],
                  ["Breadth", risk.breadth_risk, 20],
                  ["Global", risk.global_risk, 15],
                  ["Defensive", risk.defensive_signal, 15],
                ].map(([label, val, max]) => (
                  <div key={label} className="contents">
                    <span className="text-muted">{label}</span>
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-1 bg-gray-800 rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full bg-blue-500/60"
                          style={{ width: `${(val / max) * 100}%` }}
                        />
                      </div>
                      <span className="text-right text-gray-300 font-mono text-[11px] w-8">{val}/{max}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </Card>
        )}

        {/* Allocation */}
        {alloc && (
          <Card title="Current Allocation">
            <AllocationDonut
              equity={alloc.equity_pct}
              gold={alloc.gold_pct}
              silver={alloc.silver_pct}
              cash={alloc.cash_pct}
            />
            <div className="mt-4 space-y-1.5 text-xs">
              {[
                ["Total Capital", alloc.total_capital, "text-gray-200", true],
                ["Equity", alloc.equity_amount, "text-blue-400"],
                ["Gold", alloc.gold_amount, "text-amber-400"],
                ["Cash", alloc.cash_amount, "text-emerald-400"],
              ].map(([label, amt, color, isBold]) => (
                <div key={label} className="flex justify-between text-muted">
                  <span>{label}</span>
                  <span className={`font-mono font-semibold ${color} ${isBold ? "text-sm" : ""}`}>
                    ₹{amt?.toLocaleString("en-IN")}
                  </span>
                </div>
              ))}
            </div>
            {alloc.reason && (
              <p className="mt-3 text-[11px] text-muted leading-relaxed border-t border-border/40 pt-3 italic">
                {alloc.reason}
              </p>
            )}
          </Card>
        )}

        {/* Macro */}
        {macro && (
          <Card title="Macro Indicators">
            <div className="space-y-2.5 text-xs">
              {[
                ["NIFTY", `₹${macro.nifty_close?.toLocaleString("en-IN")}`, macro.nifty_above_200dma],
                ["VIX", macro.vix?.toFixed(1), macro.vix < 18],
                ["S&P 500", macro.sp500_above_200dma ? "Above 200DMA" : "Below", macro.sp500_above_200dma],
                ["DXY", macro.dxy_breakout ? "Breakout" : "Normal", !macro.dxy_breakout],
                ["Oil", macro.oil_spike ? "Spike" : "Normal", !macro.oil_spike],
                ["Gold", macro.gold_above_50dma ? "Strong" : "Weak", null],
                ["Breadth", `${macro.breadth_pct_above_50dma?.toFixed(0)}%`, macro.breadth_pct_above_50dma > 50],
              ].map(([label, val, ok], i) => (
                <div key={i} className="flex items-center justify-between">
                  <span className="text-muted">{label}</span>
                  <span className={`font-mono font-semibold ${ok === true ? "text-emerald-400" : ok === false ? "text-red-400" : "text-amber-400"}`}>
                    {val}
                  </span>
                </div>
              ))}
            </div>
          </Card>
        )}
      </div>

      {/* Risk Score History Chart */}
      {riskHist.length > 0 && (
        <Card title="Risk Score History (30 Days)">
          <div className="h-52">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={riskHist}>
                <defs>
                  <linearGradient id="riskGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#ef4444" stopOpacity={0.25} />
                    <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(30,41,59,0.5)" vertical={false} />
                <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#64748b" }} tickLine={false} axisLine={false} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: "#64748b" }} tickLine={false} axisLine={false} width={35} />
                <Tooltip {...CHART_TOOLTIP} />
                <Area type="monotone" dataKey="total_risk_score" stroke="#ef4444" fill="url(#riskGrad)" strokeWidth={2} dot={false} name="Risk Score" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card>
      )}

      {/* Regime Change Log */}
      {regimeHist.length > 0 && (
        <Card title="Regime Change History">
          <div className="overflow-x-auto">
            <table className="pro-table w-full">
              <thead>
                <tr>
                  <th className="text-left">Date</th>
                  <th className="text-left">From</th>
                  <th className="text-left">To</th>
                  <th className="text-right">Score</th>
                  <th className="text-left pl-3">Reason</th>
                </tr>
              </thead>
              <tbody>
                {regimeHist.map((r, i) => (
                  <tr key={i}>
                    <td className="font-mono text-muted">{r.date}</td>
                    <td className="text-muted">{r.previous_regime || "—"}</td>
                    <td><RegimeBadge regime={r.new_regime} /></td>
                    <td className="text-right font-mono text-gray-300">{r.risk_score?.toFixed(1)}</td>
                    <td className="pl-3 text-muted truncate max-w-[200px]">{r.trigger_reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Allocation Backtest */}
      <Card title="Allocation Backtest (5 Year)">
        {!backtest ? (
          <div className="text-center py-10">
            <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-blue-500/20 to-purple-500/20 border border-blue-500/20 flex items-center justify-center">
              <svg className="w-7 h-7 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
              </svg>
            </div>
            <p className="text-gray-300 text-sm font-medium mb-1">Momentum-Enhanced Backtest</p>
            <p className="text-muted text-xs mb-5 max-w-md mx-auto leading-relaxed">
              Simulates regime-based allocation with top-5 momentum stock picking, monthly rebalancing, and trailing stops over 5 years.
            </p>
            <button
              onClick={handleBacktest}
              disabled={btLoading}
              className="btn-primary disabled:opacity-50"
            >
              {btLoading ? (
                <span className="flex items-center gap-2">
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Downloading stocks & running...
                </span>
              ) : "Run Backtest"}
            </button>
          </div>
        ) : (
          <div className="space-y-5 animate-slide-up">
            {/* Hero Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <StatCard label="Final Capital" value={`₹${backtest.final_capital?.toLocaleString("en-IN")}`} color="text-profit" />
              <StatCard label="Total Return" value={`${backtest.total_return_pct}%`} color={backtest.total_return_pct >= 0 ? "text-profit" : "text-loss"} />
              <StatCard label="CAGR" value={`${backtest.cagr}%`} color={backtest.cagr >= 12 ? "text-profit" : "text-amber-400"} />
              <StatCard label="Max Drawdown" value={`${backtest.max_drawdown_pct}%`} color="text-loss" />
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <StatCard label="Sharpe Ratio" value={backtest.sharpe_ratio ?? "—"} color={backtest.sharpe_ratio >= 1 ? "text-profit" : "text-gray-100"} />
              <StatCard label="Sortino Ratio" value={backtest.sortino_ratio ?? "—"} />
              <StatCard label="Ann. Volatility" value={`${backtest.annualised_volatility ?? 0}%`} />
              <StatCard
                label="Benchmark (NIFTY)"
                value={`${backtest.benchmark_return_pct ?? 0}%`}
                color={backtest.total_return_pct > (backtest.benchmark_return_pct ?? 0) ? "text-emerald-400" : "text-red-400"}
                sub={backtest.total_return_pct > (backtest.benchmark_return_pct ?? 0) ? "Outperformed" : "Underperformed"}
              />
            </div>

            {/* Regime breakdown */}
            <div className="flex gap-3 flex-wrap text-xs">
              <span className="text-muted font-medium">
                Regime Changes: <span className="text-gray-200 font-mono">{backtest.regime_changes}</span>
              </span>
              {backtest.time_in_regimes && Object.entries(backtest.time_in_regimes).map(([k, v]) => (
                <span key={k} className="text-muted">
                  {k}: <span className="text-gray-200 font-mono">{v}%</span>
                </span>
              ))}
            </div>

            {/* Equity Curve Chart */}
            {backtest.curve?.length > 0 && (
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={backtest.curve}>
                    <defs>
                      <linearGradient id="totalGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#8b5cf6" stopOpacity={0.2} />
                        <stop offset="100%" stopColor="#8b5cf6" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(30,41,59,0.5)" vertical={false} />
                    <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#64748b" }} tickLine={false} axisLine={false} />
                    <YAxis tick={{ fontSize: 10, fill: "#64748b" }} tickLine={false} axisLine={false} width={50} />
                    <Tooltip {...CHART_TOOLTIP} />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                    <Area type="monotone" dataKey="equity_value" stroke="#3b82f6" fill="none" strokeWidth={1.5} dot={false} name="Equity" />
                    <Area type="monotone" dataKey="gold_value" stroke="#f59e0b" fill="none" strokeWidth={1.5} dot={false} name="Gold" />
                    <Area type="monotone" dataKey="cash_value" stroke="#10b981" fill="none" strokeWidth={1} dot={false} name="Cash" />
                    <Area type="monotone" dataKey="total_value" stroke="#8b5cf6" fill="url(#totalGrad)" strokeWidth={2.5} dot={false} name="Total" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        )}
      </Card>
    </div>
  );
}
