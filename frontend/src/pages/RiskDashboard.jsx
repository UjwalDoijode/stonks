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
    <div className="space-y-5 animate-fade-in">
      {/* Simplified Header */}
      <div>
        <h1 className="text-2xl font-bold text-gold-bright">Risk Control</h1>
        <p className="text-xs text-muted mt-1">Portfolio safety & drawdown protection</p>
      </div>

      {/* MAIN: Governor Status (Large & Clear) */}
      <div className={`glass-card p-6 border-2 ${
        governor?.severity === "NORMAL" ? "border-emerald-500/40 bg-emerald-500/5" :
        governor?.severity === "WARNING" ? "border-amber-500/40 bg-amber-500/5" :
        governor?.severity === "CRITICAL" ? "border-orange-500/40 bg-orange-500/5" :
        "border-red-600/40 bg-red-600/5"
      }`}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-bold uppercase tracking-wider text-gold">Risk Governor Status</h2>
          <div className={`px-3 py-1 rounded-lg text-sm font-bold ${
            governor?.severity === "NORMAL" ? "bg-emerald-500/20 text-emerald-400" :
            governor?.severity === "WARNING" ? "bg-amber-500/20 text-amber-400" :
            governor?.severity === "CRITICAL" ? "bg-orange-500/20 text-orange-400" :
            "bg-red-600/20 text-red-400"
          }`}>
            {governor?.severity || "UNKNOWN"}
          </div>
        </div>
        
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center">
            <p className="text-[11px] text-muted uppercase tracking-wider mb-1">Drawdown</p>
            <p className={`text-2xl font-bold font-mono ${governor?.drawdown_triggered ? "text-red-400" : "text-emerald-400"}`}>
              {governor?.drawdown_pct?.toFixed(1) || 0}%
            </p>
            <p className="text-[10px] text-muted/60 mt-0.5">Limit: 8%</p>
          </div>
          <div className="text-center">
            <p className="text-[11px] text-muted uppercase tracking-wider mb-1">Losses in a Row</p>
            <p className={`text-2xl font-bold font-mono ${governor?.consecutive_losses >= 3 ? "text-red-400" : "text-emerald-400"}`}>
              {governor?.consecutive_losses || 0}
            </p>
            <p className="text-[10px] text-muted/60 mt-0.5">Limit: 3</p>
          </div>
          <div className="text-center">
            <p className="text-[11px] text-muted uppercase tracking-wider mb-1">Monthly Loss</p>
            <p className={`text-2xl font-bold font-mono ${governor?.monthly_loss_triggered ? "text-red-400" : "text-emerald-400"}`}>
              {governor?.monthly_loss_pct?.toFixed(1) || 0}%
            </p>
            <p className="text-[10px] text-muted/60 mt-0.5">Limit: 5%</p>
          </div>
          <div className="text-center">
            <p className="text-[11px] text-muted uppercase tracking-wider mb-1">Emergency Stop</p>
            <p className={`text-2xl font-bold font-mono ${governor?.hard_stop_triggered ? "text-red-400" : "text-emerald-400"}`}>
              {governor?.hard_stop_triggered ? "HALT" : "OK"}
            </p>
            <p className="text-[10px] text-muted/60 mt-0.5">Limit: 15%</p>
          </div>
        </div>

        {governor?.hard_stop_triggered && (
          <div className="mt-4 p-3 bg-red-600/20 border border-red-600/40 rounded-lg">
            <p className="text-red-400 text-sm font-bold">🛑 HARD STOP TRIGGERED - All trading paused for safety</p>
          </div>
        )}
      </div>

      {/* Quick Stats (4 essential metrics) */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="glass-card p-4">
          <p className="text-[11px] text-muted uppercase tracking-wider mb-2">Portfolio Volatility</p>
          <p className={`text-2xl font-bold font-mono ${volatility?.portfolio_vol > volatility?.target_vol * 1.2 ? "text-amber-400" : "text-emerald-400"}`}>
            {volatility?.portfolio_vol?.toFixed(1)}%
          </p>
          <p className="text-[10px] text-muted/60 mt-1">Target: {volatility?.target_vol}%</p>
        </div>
        
        <div className="glass-card p-4">
          <p className="text-[11px] text-muted uppercase tracking-wider mb-2">Equity Allocation</p>
          <p className={`text-2xl font-bold font-mono ${volatility?.scaling_factor < 0.8 ? "text-amber-400" : "text-emerald-400"}`}>
            {((volatility?.scaling_factor || 1) * 100).toFixed(0)}%
          </p>
          <p className="text-[10px] text-muted/60 mt-1">{volatility?.scaling_factor < 1 ? "Reduced" : "Full"}</p>
        </div>
        
        <div className="glass-card p-4">
          <p className="text-[11px] text-muted uppercase tracking-wider mb-2">Win Rate</p>
          <p className={`text-2xl font-bold font-mono ${(feedback?.win_rate || 0) >= 60 ? "text-emerald-400" : "text-amber-400"}`}>
            {(feedback?.win_rate || 0).toFixed(0)}%
          </p>
          <p className="text-[10px] text-muted/60 mt-1">{feedback?.winning_trades || 0}W / {feedback?.losing_trades || 0}L</p>
        </div>

        <div className="glass-card p-4">
          <p className="text-[11px] text-muted uppercase tracking-wider mb-2">Cash Available</p>
          <p className="text-2xl font-bold text-emerald-400 font-mono">
            ₹{(smart_cash?.total_cash || 0)?.toLocaleString("en-IN")}
          </p>
          <p className="text-[10px] text-muted/60 mt-1">{smart_cash?.weighted_annual_yield}% yield</p>
        </div>
      </div>

      {/* Volatility Control (Simple) */}
      <Card title="Volatility Control">
        <p className="text-xs text-muted mb-4">How volatile the portfolio is vs target</p>
        <div className="space-y-4">
          {[
            { label: "Equity Volatility", value: volatility?.equity_vol, color: "bg-blue-500" },
            { label: "Gold Volatility", value: volatility?.gold_vol, color: "bg-amber-500" },
            { label: "Portfolio (Combined)", value: volatility?.portfolio_vol, color: "bg-purple-500" },
          ].map((item) => (
            <div key={item.label}>
              <div className="flex justify-between text-xs mb-2">
                <span className="font-medium text-gray-300">{item.label}</span>
                <span className="font-mono text-gray-400">{item.value?.toFixed(1)}%</span>
              </div>
              <div className="h-2 bg-gray-800/50 rounded-full overflow-hidden border border-gray-700/30">
                <div className={`h-full rounded-full ${item.color}`} style={{ width: `${Math.min((item.value || 0) / 40 * 100, 100)}%` }} />
              </div>
            </div>
          ))}
        </div>
        {volatility?.reason && (
          <p className="text-[11px] text-amber-400 mt-4 p-2 bg-amber-500/10 border border-amber-500/20 rounded-lg">
            📌 {volatility.reason}
          </p>
        )}
      </Card>

      {/* Opportunity Filter (Simplified) */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card title="Opportunity Filter">
          <p className="text-xs text-muted mb-3">Which assets are worth buying right now?</p>
          <div className="space-y-2">
            {opportunity?.scores?.map((s) => (
              <div key={s.asset} className={`p-3 rounded-lg border ${s.passes_threshold ? "bg-emerald-500/5 border-emerald-500/20" : "bg-red-500/5 border-red-500/20"}`}>
                <div className="flex justify-between items-start">
                  <div>
                    <p className="text-sm font-semibold text-gray-200 uppercase">{s.asset}</p>
                    <p className="text-xs text-muted mt-0.5">Return: {s.expected_return?.toFixed(1)}% | Risk (DD): {s.max_drawdown?.toFixed(1)}%</p>
                  </div>
                  <div className="text-right">
                    <p className={`text-lg font-bold font-mono ${s.passes_threshold ? "text-emerald-400" : "text-red-400"}`}>
                      {s.opportunity_score?.toFixed(2)}
                    </p>
                    <p className={`text-[10px] font-bold ${s.passes_threshold ? "text-emerald-400" : "text-red-400"}`}>
                      {s.passes_threshold ? "✓ BUY" : "✗ SKIP"}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
          {opportunity?.cash_boost_applied && (
            <div className="mt-3 p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg">
              <p className="text-amber-400 text-xs font-bold">💡 No good opportunities → Keep cash earning interest</p>
            </div>
          )}
        </Card>

        {/* Diversification (Simplified) */}
        {correlation && (
          <Card title="Stock Diversification">
            <p className="text-xs text-muted mb-4">Avoiding correlated stocks & sector overlap</p>
            <div className="space-y-3">
              <div className="p-3 bg-gray-800/30 rounded-lg border border-gray-700/30">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-xs font-medium text-gray-300">Initial Universe</span>
                  <span className="text-lg font-bold text-gray-400 font-mono">{correlation.original_count}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-xs font-medium text-gray-300">After Filtering</span>
                  <span className="text-lg font-bold text-emerald-400 font-mono">{correlation.filtered_count}</span>
                </div>
              </div>
              
              {correlation.removed_symbols?.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-red-400 mb-2">Removed (too correlated):</p>
                  <div className="flex flex-wrap gap-1">
                    {correlation.removed_symbols.slice(0, 3).map((s) => (
                      <span key={s} className="px-2 py-1 bg-red-500/10 text-red-400 text-[10px] rounded border border-red-500/20 font-mono">
                        {s}
                      </span>
                    ))}
                    {correlation.removed_symbols.length > 3 && (
                      <span className="px-2 py-1 text-red-400 text-[10px] font-bold">
                        +{correlation.removed_symbols.length - 3} more
                      </span>
                    )}
                  </div>
                </div>
              )}
              
              <p className="text-[11px] text-gray-400 p-2 bg-gray-800/20 rounded">
                📊 Diversification Score: <span className="font-bold text-gold">{correlation.diversification_score}/100</span>
              </p>
            </div>
          </Card>
        )}
      </div>

      {/* Smart Cash & Liquidity */}
      {smart_cash && smart_cash.total_cash > 0 && (
        <Card title="Smart Cash Allocation">
          <p className="text-xs text-muted mb-4">How your cash is earning returns safely</p>
          <div className="space-y-2">
            {smart_cash.recommendations?.slice(0, 3).map((r, i) => (
              <div key={i} className="p-3 bg-gray-800/30 rounded-lg border border-gray-700/30">
                <div className="flex justify-between items-start mb-1">
                  <p className="text-sm font-semibold text-gray-200">{r.name}</p>
                  <p className="font-mono font-bold text-emerald-400">₹{r.amount?.toLocaleString("en-IN")}</p>
                </div>
                <p className="text-xs text-muted">{r.annual_yield_pct}% p.a. → ₹{r.monthly_yield}/month</p>
              </div>
            ))}
          </div>
          <div className="mt-4 p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-lg">
            <p className="text-[11px] text-emerald-400 font-bold">
              💰 Total Yield: {smart_cash.weighted_annual_yield}% p.a. (₹{smart_cash.monthly_expected_income?.toLocaleString("en-IN")}/month)
            </p>
          </div>
        </Card>
      )}

      {/* Liquidity Filter (Simplified) */}
      {liquidity && liquidity.rejected?.length > 0 && (
        <Card title="Stocks Excluded (Low Liquidity)">
          <p className="text-xs text-muted mb-4">These stocks have too high trading spreads (~cost to buy/sell)</p>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {liquidity.rejected.slice(0, 5).map((r) => (
              <div key={r.symbol} className="p-2 bg-red-500/5 border border-red-500/20 rounded text-xs">
                <div className="flex justify-between items-start">
                  <p className="font-mono font-bold text-red-400">{r.symbol}</p>
                  <p className="text-red-400">Spread: {r.estimated_spread_pct?.toFixed(2)}%</p>
                </div>
                <p className="text-muted mt-0.5 text-[10px]">Volume: {r.avg_daily_volume?.toLocaleString()} | {r.rejection_reason}</p>
              </div>
            ))}
            {liquidity.rejected.length > 5 && (
              <p className="text-xs text-muted text-center py-2">+{liquidity.rejected.length - 5} more excluded</p>
            )}
          </div>
        </Card>
      )}
    </div>
  );
}
