import { useState, useEffect } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, AreaChart, Area, LineChart, Line,
} from "recharts";
import { Card, StatCard, Badge, Loader, ErrorMsg } from "../components/UI";
import { fetchRiskOverview } from "../api";

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

const SEVERITY_COLORS = {
  NORMAL: "text-emerald-400",
  WARNING: "text-amber-400",
  CRITICAL: "text-orange-400",
  EMERGENCY: "text-red-400",
};

const SEVERITY_BG = {
  NORMAL: "bg-emerald-500/10 border-emerald-500/20",
  WARNING: "bg-amber-500/10 border-amber-500/20",
  CRITICAL: "bg-orange-500/10 border-orange-500/20",
  EMERGENCY: "bg-red-500/10 border-red-500/20",
};

export default function RiskDashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchRiskOverview()
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Loader />;
  if (error) return <ErrorMsg message={error} />;
  if (!data) return null;

  const { governor, volatility, opportunity, correlation, liquidity, feedback, smart_cash, monte_carlo } = data;

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Risk Control Center</h2>
          <p className="text-xs text-muted mt-0.5 font-medium">
            Comprehensive risk monitoring &amp; capital protection
          </p>
        </div>
        <Badge variant={governor?.severity === "NORMAL" ? "success" : governor?.severity === "WARNING" ? "warning" : "danger"}>
          Governor: {governor?.severity || "N/A"}
        </Badge>
      </div>

      {/* Governor Alert */}
      {governor?.is_active && (
        <div className={`glass-card border p-4 flex items-start gap-3 ${SEVERITY_BG[governor.severity] || ""}`}>
          <div className="w-8 h-8 rounded-full bg-red-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
            <span className="text-red-400 text-sm font-bold">!</span>
          </div>
          <div>
            <p className={`font-semibold text-sm ${SEVERITY_COLORS[governor.severity]}`}>
              Risk Governor Active — {governor.severity}
            </p>
            <p className="text-muted text-xs mt-1 leading-relaxed">
              Drawdown: {governor.drawdown_pct.toFixed(1)}% |
              Consecutive losses: {governor.consecutive_losses} |
              Monthly loss: {governor.monthly_loss_pct.toFixed(1)}%
              {governor.hard_stop_triggered && " | HARD STOP TRIGGERED — All equity paused"}
            </p>
          </div>
        </div>
      )}

      {/* Top Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          label="Portfolio Vol"
          value={`${volatility?.portfolio_vol?.toFixed(1) || 0}%`}
          sub={`Target: ${volatility?.target_vol || 12}%`}
          color={volatility?.portfolio_vol > volatility?.target_vol * 1.2 ? "text-loss" : "text-profit"}
        />
        <StatCard
          label="Vol Scaling"
          value={`${((volatility?.scaling_factor || 1) * 100).toFixed(0)}%`}
          sub={volatility?.scaling_factor < 1 ? "Equity reduced" : "Full allocation"}
          color={volatility?.scaling_factor < 0.8 ? "text-amber-400" : "text-gray-100"}
        />
        <StatCard
          label="Drawdown"
          value={`${governor?.drawdown_pct?.toFixed(1) || 0}%`}
          color={governor?.drawdown_triggered ? "text-loss" : "text-gray-100"}
        />
        <StatCard
          label="Win Rate"
          value={`${feedback?.win_rate?.toFixed(1) || 0}%`}
          sub={`${feedback?.winning_trades || 0}W / ${feedback?.losing_trades || 0}L`}
          color={feedback?.win_rate >= 60 ? "text-profit" : "text-amber-400"}
        />
      </div>

      {/* Governor + Volatility Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Governor */}
        <Card title="Portfolio Risk Governor">
          <div className="space-y-3">
            {[
              { label: "Drawdown Check", value: `${governor?.drawdown_pct?.toFixed(1)}%`, triggered: governor?.drawdown_triggered, threshold: "8%" },
              { label: "Consecutive Losses", value: governor?.consecutive_losses, triggered: governor?.equity_paused, threshold: "3" },
              { label: "Monthly Loss", value: `${governor?.monthly_loss_pct?.toFixed(1)}%`, triggered: governor?.monthly_loss_triggered, threshold: "5%" },
              { label: "Hard Stop", value: governor?.hard_stop_triggered ? "TRIGGERED" : "OK", triggered: governor?.hard_stop_triggered, threshold: "15%" },
            ].map((item) => (
              <div key={item.label} className="flex items-center justify-between py-2 border-b border-border/30 last:border-0">
                <div>
                  <span className="text-xs text-muted">{item.label}</span>
                  <span className="text-[10px] text-gray-600 ml-2">(limit: {item.threshold})</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`text-sm font-mono font-semibold ${item.triggered ? "text-red-400" : "text-emerald-400"}`}>
                    {item.value}
                  </span>
                  <div className={`w-2 h-2 rounded-full ${item.triggered ? "bg-red-400" : "bg-emerald-400"}`} />
                </div>
              </div>
            ))}
          </div>
        </Card>

        {/* Volatility */}
        <Card title="Volatility Targeting">
          <div className="space-y-4">
            {[
              { label: "Equity Vol", value: volatility?.equity_vol, color: "bg-blue-500" },
              { label: "Gold Vol", value: volatility?.gold_vol, color: "bg-amber-500" },
              { label: "Portfolio Vol", value: volatility?.portfolio_vol, color: "bg-purple-500" },
            ].map((item) => (
              <div key={item.label}>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-muted">{item.label}</span>
                  <span className="font-mono text-gray-300">{item.value?.toFixed(1)}%</span>
                </div>
                <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${item.color}`}
                    style={{ width: `${Math.min((item.value || 0) / 40 * 100, 100)}%` }}
                  />
                </div>
              </div>
            ))}
            <div className="border-t border-border/40 pt-3 text-xs text-muted">
              <p>{volatility?.reason}</p>
            </div>
          </div>
        </Card>
      </div>

      {/* Opportunity + Correlation Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Opportunity Filter */}
        <Card title="Opportunity Filter">
          <div className="space-y-2">
            {opportunity?.scores?.map((s) => (
              <div key={s.asset} className="flex items-center justify-between py-2 border-b border-border/30 last:border-0">
                <span className="text-xs font-medium text-gray-300">{s.asset}</span>
                <div className="flex items-center gap-3">
                  <span className="text-[11px] text-muted">
                    Ret: {s.expected_return?.toFixed(1)}% | DD: {s.max_drawdown?.toFixed(1)}%
                  </span>
                  <span className={`font-mono text-sm font-semibold ${s.passes_threshold ? "text-emerald-400" : "text-red-400"}`}>
                    {s.opportunity_score?.toFixed(2)}
                  </span>
                  <div className={`w-2 h-2 rounded-full ${s.passes_threshold ? "bg-emerald-400" : "bg-red-400"}`} />
                </div>
              </div>
            ))}
            {opportunity?.cash_boost_applied && (
              <div className="mt-2 px-3 py-1.5 bg-amber-500/10 border border-amber-500/20 rounded-lg text-amber-400 text-[11px] font-medium">
                Cash boosted — no asset passed opportunity threshold
              </div>
            )}
          </div>
        </Card>

        {/* Correlation Control */}
        {correlation && (
          <Card title="Correlation & Sector Control">
            <div className="space-y-3">
              <div className="flex justify-between text-xs">
                <span className="text-muted">Stocks Analyzed</span>
                <span className="font-mono text-gray-300">{correlation.original_count}</span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-muted">After Filter</span>
                <span className="font-mono text-emerald-400">{correlation.filtered_count}</span>
              </div>
              {correlation.removed_symbols?.length > 0 && (
                <div className="mt-2">
                  <p className="text-[11px] text-muted mb-1">Removed (correlated/sector limit):</p>
                  <div className="flex flex-wrap gap-1">
                    {correlation.removed_symbols.map((s) => (
                      <span key={s} className="px-2 py-0.5 bg-red-500/10 text-red-400 text-[10px] rounded-md border border-red-500/20">
                        {s}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              <div className="border-t border-border/40 pt-2 text-xs text-muted">
                <p>{correlation.reason}</p>
              </div>
            </div>
          </Card>
        )}
      </div>

      {/* Feedback + Smart Cash Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Adaptive Feedback */}
        <Card title="Adaptive AI Feedback">
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-xs">
              {[
                ["Total Trades", feedback?.total_trades || 0],
                ["Avg R-Multiple", feedback?.avg_r_multiple?.toFixed(2) || "—"],
                ["High Conf WR", `${feedback?.high_conf_win_rate?.toFixed(0) || 0}%`],
                ["Low Conf WR", `${feedback?.low_conf_win_rate?.toFixed(0) || 0}%`],
              ].map(([label, val]) => (
                <div key={label} className="flex justify-between">
                  <span className="text-muted">{label}</span>
                  <span className="text-gray-300 font-mono">{val}</span>
                </div>
              ))}
            </div>
            <div className="border-t border-border/40 pt-3">
              <p className="text-[11px] text-muted mb-2">Current Blend Weights</p>
              <div className="flex gap-2">
                <div className="flex-1 bg-blue-500/10 border border-blue-500/20 rounded-lg p-2 text-center">
                  <p className="text-blue-400 font-mono font-bold text-sm">
                    {((feedback?.current_rule_weight || 0.7) * 100).toFixed(0)}%
                  </p>
                  <p className="text-[10px] text-muted mt-0.5">Rule-Based</p>
                </div>
                <div className="flex-1 bg-purple-500/10 border border-purple-500/20 rounded-lg p-2 text-center">
                  <p className="text-purple-400 font-mono font-bold text-sm">
                    {((feedback?.current_ai_weight || 0.3) * 100).toFixed(0)}%
                  </p>
                  <p className="text-[10px] text-muted mt-0.5">AI Model</p>
                </div>
              </div>
              {feedback?.adaptation_active && (
                <Badge variant="info">Weights adapted from trade feedback</Badge>
              )}
            </div>
          </div>
        </Card>

        {/* Smart Cash */}
        {smart_cash && smart_cash.total_cash > 0 && (
          <Card title="Smart Cash Utilization">
            <div className="space-y-3">
              <div className="flex justify-between text-xs">
                <span className="text-muted">Total Cash</span>
                <span className="font-mono text-emerald-400 font-semibold">
                  ₹{smart_cash.total_cash?.toLocaleString("en-IN")}
                </span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-muted">Expected Yield</span>
                <span className="font-mono text-gray-300">{smart_cash.weighted_annual_yield}% p.a.</span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-muted">Monthly Income</span>
                <span className="font-mono text-emerald-400">₹{smart_cash.monthly_expected_income?.toLocaleString("en-IN")}</span>
              </div>
              <div className="border-t border-border/40 pt-3 space-y-2">
                {smart_cash.recommendations?.map((r, i) => (
                  <div key={i} className="flex items-center justify-between bg-base/50 rounded-lg p-2.5 border border-border/30">
                    <div>
                      <p className="text-xs font-medium text-gray-200">{r.name}</p>
                      <p className="text-[10px] text-muted">{r.annual_yield_pct}% p.a. · {r.risk_level}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-xs font-mono font-semibold text-gray-300">₹{r.amount?.toLocaleString("en-IN")}</p>
                      <p className="text-[10px] text-emerald-400">₹{r.monthly_yield}/mo</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </Card>
        )}
      </div>

      {/* Monte Carlo */}
      {monte_carlo && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard
              label="Expected Return"
              value={`${monte_carlo.expected_return >= 0 ? "+" : ""}${monte_carlo.expected_return?.toFixed(1)}%`}
              color={monte_carlo.expected_return >= 0 ? "text-profit" : "text-loss"}
            />
            <StatCard
              label="Best Case (95th)"
              value={`+${monte_carlo.best_case_return?.toFixed(1)}%`}
              color="text-emerald-400"
            />
            <StatCard
              label="Worst Case (5th)"
              value={`${monte_carlo.worst_case_return?.toFixed(1)}%`}
              color="text-red-400"
            />
            <StatCard
              label="VaR (95%)"
              value={`${monte_carlo.var_95?.toFixed(1)}%`}
              sub={`P(loss): ${(monte_carlo.prob_negative_month * 100).toFixed(0)}%`}
              color="text-amber-400"
            />
          </div>

          {/* Monte Carlo Distribution Chart */}
          {monte_carlo.histogram_bins?.length > 0 && (
            <Card title="Return Distribution (Monte Carlo · 5000 paths)">
              <div className="h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={monte_carlo.histogram_bins.map((bin, i) => ({
                      bin: `${(bin * 100).toFixed(0)}%`,
                      count: monte_carlo.histogram_counts?.[i] || 0,
                    }))}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(30,41,59,0.5)" vertical={false} />
                    <XAxis dataKey="bin" tick={{ fontSize: 9, fill: "#64748b" }} tickLine={false} axisLine={false} interval={2} />
                    <YAxis tick={{ fontSize: 9, fill: "#64748b" }} tickLine={false} axisLine={false} width={35} />
                    <Tooltip {...CHART_TOOLTIP} />
                    <Bar dataKey="count" fill="#3b82f6" radius={[2, 2, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>
          )}

          {/* Percentile Fan */}
          {monte_carlo.percentile_curves && Object.keys(monte_carlo.percentile_curves).length > 0 && (
            <Card title="Percentile Fan (12-month forward)">
              <div className="h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart
                    data={
                      (monte_carlo.percentile_curves.p50 || []).map((_, i) => ({
                        month: i,
                        p5: monte_carlo.percentile_curves.p5?.[i] || 0,
                        p25: monte_carlo.percentile_curves.p25?.[i] || 0,
                        p50: monte_carlo.percentile_curves.p50?.[i] || 0,
                        p75: monte_carlo.percentile_curves.p75?.[i] || 0,
                        p95: monte_carlo.percentile_curves.p95?.[i] || 0,
                      }))
                    }
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(30,41,59,0.5)" vertical={false} />
                    <XAxis dataKey="month" tick={{ fontSize: 10, fill: "#64748b" }} tickLine={false} label={{ value: "Month", position: "insideBottom", offset: -5, fontSize: 10, fill: "#64748b" }} />
                    <YAxis tick={{ fontSize: 10, fill: "#64748b" }} tickLine={false} axisLine={false} width={50} tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`} />
                    <Tooltip {...CHART_TOOLTIP} />
                    <Area type="monotone" dataKey="p5" stroke="none" fill="#ef4444" fillOpacity={0.1} />
                    <Area type="monotone" dataKey="p25" stroke="none" fill="#f59e0b" fillOpacity={0.15} />
                    <Area type="monotone" dataKey="p50" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.2} strokeWidth={2} />
                    <Area type="monotone" dataKey="p75" stroke="none" fill="#10b981" fillOpacity={0.15} />
                    <Area type="monotone" dataKey="p95" stroke="none" fill="#10b981" fillOpacity={0.1} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
              <div className="flex justify-center gap-4 mt-2 text-[10px] text-muted">
                {[["5th", "#ef4444"], ["25th", "#f59e0b"], ["50th (median)", "#3b82f6"], ["75th", "#10b981"], ["95th", "#10b981"]].map(([l, c]) => (
                  <div key={l} className="flex items-center gap-1">
                    <div className="w-2 h-2 rounded-full" style={{ backgroundColor: c }} />
                    <span>{l}</span>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </>
      )}

      {/* Liquidity */}
      {liquidity && liquidity.rejected?.length > 0 && (
        <Card title="Liquidity Filter — Rejected Stocks">
          <div className="overflow-x-auto">
            <table className="pro-table w-full">
              <thead>
                <tr>
                  <th className="text-left">Symbol</th>
                  <th className="text-right">Avg Volume</th>
                  <th className="text-right">Turnover</th>
                  <th className="text-right">Spread</th>
                  <th className="text-left">Reason</th>
                </tr>
              </thead>
              <tbody>
                {liquidity.rejected.map((r) => (
                  <tr key={r.symbol}>
                    <td className="font-semibold text-red-400">{r.symbol}</td>
                    <td className="text-right font-mono">{r.avg_daily_volume?.toLocaleString()}</td>
                    <td className="text-right font-mono">₹{(r.avg_daily_turnover / 100000)?.toFixed(1)}L</td>
                    <td className="text-right font-mono">{r.estimated_spread_pct?.toFixed(2)}%</td>
                    <td className="text-xs text-muted">{r.rejection_reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
