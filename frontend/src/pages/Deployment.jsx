import { useState, useEffect } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell,
} from "recharts";
import {
  Card, Badge, Loader, ErrorMsg, StatCard,
  RiskGauge, RegimeBadge,
} from "../components/UI";
import { fetchCapitalDeployment, fetchStockRankings } from "../api";

const ASSET_COLORS = {
  Equity: "#6366f1",
  Gold: "#eab308",
  Silver: "#94a3b8",
  Cash: "#22c55e",
};

export default function Deployment() {
  const [plan, setPlan] = useState(null);
  const [rankings, setRankings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    Promise.all([
      fetchCapitalDeployment().catch(() => null),
      fetchStockRankings(10).catch(() => null),
    ])
      .then(([dep, rank]) => {
        setPlan(dep);
        setRankings(rank);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Loader />;
  if (error) return <ErrorMsg message={error} />;
  if (!plan) return <ErrorMsg message="No deployment data available" />;

  const allocData = plan.assets.map((a) => ({
    name: a.asset,
    pct: a.allocation_pct,
    amount: a.amount,
    score: a.expected_score,
  }));

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Capital Deployment</h2>
          <p className="text-xs text-muted mt-0.5 font-medium">
            Dynamic allocation based on Expected Score = (Return / Volatility) × Confidence
          </p>
        </div>
        <div className="flex items-center gap-3">
          <RegimeBadge regime={plan.regime} />
          {plan.ai_confidence > 0 && (
            <Badge variant="info">
              AI Conf: {(plan.ai_confidence * 100).toFixed(0)}%
            </Badge>
          )}
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          label="Total Capital"
          value={`₹${plan.total_capital.toLocaleString("en-IN")}`}
        />
        <StatCard
          label="Blended Risk"
          value={plan.blended_risk_score.toFixed(1)}
          color={plan.blended_risk_score > 65 ? "text-loss" : plan.blended_risk_score > 45 ? "text-yellow-400" : "text-profit"}
        />
        <StatCard
          label="Deployed"
          value={`₹${plan.total_deployed.toLocaleString("en-IN")}`}
          color="text-accent"
        />
        <StatCard
          label="Cash Reserve"
          value={`₹${plan.cash_reserve.toLocaleString("en-IN")}`}
          color="text-green-400"
        />
      </div>

      {/* Rebalance Alert */}
      {plan.rebalance_needed && (
        <div className="glass-card border-amber-500/30 p-4 flex items-start gap-3">
          <div className="w-8 h-8 rounded-full bg-amber-500/10 flex items-center justify-center flex-shrink-0">
            <span className="text-amber-400 text-sm font-bold">⚡</span>
          </div>
          <div>
            <p className="text-amber-400 font-semibold text-sm">Rebalance Recommended</p>
            <p className="text-amber-400/70 text-xs mt-1">{plan.rebalance_reason}</p>
          </div>
        </div>
      )}

      {/* Why No Trades */}
      {plan.why_no_trades && (
        <Card title="Why No Equity Trades?">
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-full bg-amber-500/10 flex items-center justify-center flex-shrink-0">
              <span className="text-amber-400 text-sm">?</span>
            </div>
            <p className="text-gray-300 text-sm leading-relaxed">{plan.why_no_trades}</p>
          </div>
        </Card>
      )}

      {/* Asset Allocation Chart + Details */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card title="Dynamic Allocation (Expected Score Based)">
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={allocData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(30,41,59,0.5)" />
                <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 11, fill: "#64748b" }} tickLine={false} axisLine={false} />
                <YAxis dataKey="name" type="category" width={60} tick={{ fontSize: 12, fill: "#e2e8f0" }} tickLine={false} axisLine={false} />
                <Tooltip
                  contentStyle={{
                    background: "rgba(17,24,39,0.95)",
                    border: "1px solid rgba(30,41,59,0.8)",
                    borderRadius: 8,
                    fontSize: 12,
                    backdropFilter: "blur(12px)",
                  }}
                  formatter={(v, name) => [`${v}%`, name === "pct" ? "Allocation" : name]}
                />
                <Bar dataKey="pct" radius={[0, 4, 4, 0]}>
                  {allocData.map((entry, i) => (
                    <Cell key={i} fill={ASSET_COLORS[entry.name] || "#6366f1"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-3 space-y-2">
            {plan.assets.map((a, i) => (
              <div key={i} className="flex items-center justify-between text-xs border-t border-border/40 pt-2">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-sm" style={{ background: ASSET_COLORS[a.asset] || "#666", boxShadow: `0 0 6px ${ASSET_COLORS[a.asset]}30` }} />
                  <span className="text-gray-300 font-medium">{a.asset}</span>
                </div>
                <div className="flex items-center gap-4 font-mono">
                  <span className="text-muted">Score: {a.expected_score.toFixed(2)}</span>
                  <span className="text-gray-400">{a.allocation_pct}%</span>
                  <span className="text-gray-200 font-semibold">₹{a.amount.toLocaleString("en-IN")}</span>
                </div>
              </div>
            ))}
          </div>
        </Card>

        {/* Stock Picks */}
        <Card title={`Equity Picks (${plan.stock_picks.length})`}>
          {plan.stock_picks.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-muted text-sm">No stock picks in current regime</p>
              <p className="text-gray-600 text-xs mt-1">
                {plan.why_no_trades || "Equity allocation too low for individual positions"}
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {plan.stock_picks.map((s, i) => (
                <div key={i} className="bg-base/60 rounded-lg p-3.5 border border-border/30 hover:border-blue-500/30 transition-colors">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-blue-400 font-bold text-xs font-mono">#{i + 1}</span>
                      <span className="font-semibold text-gray-200">{s.clean_symbol}</span>
                    </div>
                    <Badge variant="success">₹{s.amount.toLocaleString("en-IN")}</Badge>
                  </div>
                  <div className="grid grid-cols-3 gap-2 text-xs">
                    <div>
                      <span className="text-muted text-[10px] uppercase tracking-wider">Price</span>
                      <p className="text-gray-300 font-mono">₹{s.price.toLocaleString("en-IN")}</p>
                    </div>
                    <div>
                      <span className="text-muted text-[10px] uppercase tracking-wider">Qty</span>
                      <p className="text-gray-300 font-mono">{s.quantity} shares</p>
                    </div>
                    <div>
                      <span className="text-muted text-[10px] uppercase tracking-wider">Weight</span>
                      <p className="text-gray-300 font-mono">{s.weight_pct}%</p>
                    </div>
                  </div>
                  <p className="text-xs text-muted mt-2 leading-relaxed">{s.reason}</p>
                </div>
              ))}
              {plan.brokerage_total > 0 && (
                <p className="text-xs text-gray-600 text-right">
                  Est. brokerage: ₹{plan.brokerage_total.toFixed(0)}
                </p>
              )}
            </div>
          )}
        </Card>
      </div>

      {/* Stock Rankings Table */}
      {rankings && rankings.length > 0 && (
        <Card title="NIFTY Stock Rankings (by Composite Score)">
          <div className="overflow-x-auto">
            <table className="pro-table w-full">
              <thead>
                <tr>
                  <th className="text-left">Rank</th>
                  <th className="text-left">Symbol</th>
                  <th className="text-right">Price</th>
                  <th className="text-right">Score</th>
                  <th className="text-right">RS 3M</th>
                  <th className="text-right">Mom 6M</th>
                  <th className="text-right">Vol-Adj</th>
                  <th className="text-right">Vol Str</th>
                  <th className="text-right">Trend</th>
                </tr>
              </thead>
              <tbody>
                {rankings.map((r) => (
                  <tr key={r.symbol}>
                    <td className="text-blue-400 font-bold font-mono">#{r.rank}</td>
                    <td className="font-semibold text-gray-200">{r.clean_symbol}</td>
                    <td className="text-right font-mono text-gray-300">₹{r.price?.toLocaleString("en-IN")}</td>
                    <td className="text-right">
                      <span className={`font-bold font-mono ${r.composite >= 70 ? "text-emerald-400" : r.composite >= 50 ? "text-amber-400" : "text-gray-400"}`}>
                        {r.composite.toFixed(1)}
                      </span>
                    </td>
                    <td className="text-right text-muted font-mono">{r.rs_3m.toFixed(1)}</td>
                    <td className="text-right text-muted font-mono">{r.momentum_6m.toFixed(1)}</td>
                    <td className="text-right text-muted font-mono">{r.vol_adj_return.toFixed(1)}</td>
                    <td className="text-right text-muted font-mono">{r.volume_strength.toFixed(1)}</td>
                    <td className="text-right text-muted font-mono">{r.trend_slope.toFixed(1)}</td>
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
