import { useState, useEffect } from "react";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer,
} from "recharts";
import {
  StatCard, Card, Badge, Loader, ErrorMsg,
  SkeletonCard, RiskGauge, RegimeBadge, AllocationDonut,
} from "../components/UI";
import { fetchDashboard, aiMarketBrief } from "../api";
import { Sparkles, RefreshCw } from "lucide-react";

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

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [brief, setBrief] = useState(null);
  const [briefLoading, setBriefLoading] = useState(false);

  useEffect(() => {
    fetchDashboard()
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const loadBrief = () => {
    setBriefLoading(true);
    aiMarketBrief()
      .then(setBrief)
      .catch(() => setBrief({ brief: "Unable to generate AI brief. Check backend connection." }))
      .finally(() => setBriefLoading(false));
  };

  if (loading) return (
    <div className="space-y-6 animate-fade-in">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[...Array(8)].map((_, i) => <SkeletonCard key={i} />)}
      </div>
    </div>
  );
  if (error) return <ErrorMsg message={error} />;
  if (!data) return null;

  const {
    portfolio: p, open_trades, recent_scans, equity_curve,
    regime_ok, risk, allocation, macro, deployment,
    ai_risk, top_ranked, blended_risk_score, why_no_trades,
    governor, volatility_metrics, smart_cash,
  } = data;

  const equityAllowed = allocation?.equity_allowed ?? regime_ok;
  const effectiveRisk = blended_risk_score ?? risk?.total_risk_score ?? 0;
  const stabilityScore = 100 - effectiveRisk;

  return (
    <div className="space-y-6 animate-fade-in">
      {/* ── Header ── */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Dashboard</h2>
          <p className="text-xs text-muted mt-0.5 font-medium">
            Dynamic Multi-Asset Capital Deployment Engine
          </p>
        </div>
        <div className="flex items-center gap-3">
          {governor?.is_active && (
            <Badge variant={governor.severity === "EMERGENCY" ? "danger" : "warning"}>
              Governor: {governor.severity}
            </Badge>
          )}
          {risk && <RegimeBadge regime={risk.regime} />}
          {ai_risk?.model_available && (
            <Badge variant="purple">AI: {ai_risk.confidence > 0.5 ? "High" : "Low"} Conf</Badge>
          )}
        </div>
      </div>

      {/* ── AI Morning Brief ── */}
      <div className="glass-card overflow-hidden">
        <div className="flex items-center justify-between px-5 py-3 border-b border-gold/10">
          <div className="flex items-center gap-2">
            <Sparkles size={14} className="text-gold" />
            <h3 className="text-[10px] font-semibold uppercase tracking-[0.15em] text-gold font-mono">AI Market Brief</h3>
          </div>
          <button
            onClick={loadBrief}
            disabled={briefLoading}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[10px] font-semibold text-gold/70 hover:text-gold hover:bg-gold/10 transition-all font-mono disabled:opacity-40"
          >
            <RefreshCw size={11} className={briefLoading ? "animate-spin" : ""} />
            {brief ? "Refresh" : "Generate"}
          </button>
        </div>
        <div className="p-5">
          {brief ? (
            <div className="text-[13px] text-gray-300 leading-relaxed ai-markdown space-y-1.5">
              {brief.brief.split("\n").map((line, i) => {
                if (line.startsWith("### "))
                  return <h4 key={i} className="text-gold font-semibold text-sm mt-2 mb-0.5">{line.slice(4)}</h4>;
                if (line.startsWith("- ") || line.startsWith("* "))
                  return <div key={i} className="flex gap-2 pl-1"><span className="text-gold/40">•</span><span dangerouslySetInnerHTML={{ __html: line.slice(2).replace(/\*\*(.+?)\*\*/g, '<strong class="text-gray-100">$1</strong>') }} /></div>;
                if (line.trim() === "") return <div key={i} className="h-1" />;
                return <p key={i} dangerouslySetInnerHTML={{ __html: line.replace(/\*\*(.+?)\*\*/g, '<strong class="text-gray-100">$1</strong>') }} />;
              })}
            </div>
          ) : briefLoading ? (
            <div className="flex items-center gap-2 py-4 justify-center">
              <div className="flex gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-gold/60 animate-bounce" style={{ animationDelay: "0ms" }} />
                <span className="w-1.5 h-1.5 rounded-full bg-gold/60 animate-bounce" style={{ animationDelay: "150ms" }} />
                <span className="w-1.5 h-1.5 rounded-full bg-gold/60 animate-bounce" style={{ animationDelay: "300ms" }} />
              </div>
              <span className="text-[11px] text-muted font-mono">Generating market intelligence...</span>
            </div>
          ) : (
            <p className="text-center text-muted text-sm py-3">Click "Generate" for an AI-powered market brief with live data</p>
          )}
        </div>
      </div>

      {/* ── Equity Warning ── */}
      {!equityAllowed && (
        <div className="glass-card border-red-500/30 p-4 flex items-start gap-3">
          <div className="w-8 h-8 rounded-full bg-red-500/10 flex items-center justify-center flex-shrink-0 mt-0.5">
            <span className="text-red-400 text-sm font-bold">!</span>
          </div>
          <div>
            <p className="text-red-400 font-semibold text-sm">Equity Trading Disabled</p>
            <p className="text-red-400/70 text-xs mt-1 leading-relaxed">
              {allocation?.reason || "Market regime too risky for equity positions. Capital shifted to gold & cash."}
            </p>
          </div>
        </div>
      )}

      {/* ── Risk + Allocation Panel ── */}
      {(risk || allocation || ai_risk) && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {risk && (
            <Card title="Risk Score">
              <div className="flex flex-col items-center">
                <RiskGauge score={effectiveRisk} label={blended_risk_score ? "Blended (Rule + AI)" : "Rule-Based"} />
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

          <Card title="Stability Score">
            <div className="flex flex-col items-center">
              <RiskGauge score={stabilityScore} label="Market Stability" />
              <p className="text-[11px] text-muted mt-3 text-center leading-relaxed">
                {stabilityScore >= 75 ? "Excellent conditions for deployment" :
                 stabilityScore >= 55 ? "Moderate — deploy with caution" :
                 stabilityScore >= 35 ? "Elevated risk — reduce equity" :
                 "High risk — capital preservation mode"}
              </p>
            </div>
          </Card>

          {allocation && (
            <Card title="Capital Allocation">
              <AllocationDonut
                equity={allocation.equity_pct}
                gold={allocation.gold_pct}
                silver={allocation.silver_pct}
                cash={allocation.cash_pct}
              />
              <div className="mt-4 space-y-1.5 text-xs">
                {[
                  ["Equity", allocation.equity_amount, "text-blue-400"],
                  ["Gold", allocation.gold_amount, "text-amber-400"],
                  ["Cash", allocation.cash_amount, "text-emerald-400"],
                ].map(([label, amt, color]) => (
                  <div key={label} className="flex justify-between text-muted">
                    <span>{label}</span>
                    <span className={`font-mono font-semibold ${color}`}>
                      ₹{amt?.toLocaleString("en-IN")}
                    </span>
                  </div>
                ))}
              </div>
              {allocation.rebalance_needed && (
                <div className="mt-3 px-3 py-1.5 bg-amber-500/10 border border-amber-500/20 rounded-lg text-amber-400 text-[11px] font-medium">
                  Rebalance recommended — regime changed
                </div>
              )}
            </Card>
          )}

          {ai_risk && (
            <Card title="AI Risk Model">
              {ai_risk.model_available ? (
                <div className="space-y-3">
                  {[
                    ["P(Risk-On)", ai_risk.p_risk_on, "bg-emerald-500", "text-emerald-400"],
                    ["P(Risk-Off)", ai_risk.p_risk_off, "bg-red-500", "text-red-400"],
                  ].map(([label, val, barColor, textColor]) => (
                    <div key={label} className="flex justify-between items-center gap-3">
                      <span className="text-xs text-muted w-20">{label}</span>
                      <div className="flex-1 bg-gray-800 rounded-full h-1.5">
                        <div className={`h-1.5 rounded-full ${barColor}`} style={{ width: `${val * 100}%` }} />
                      </div>
                      <span className={`text-xs font-mono font-semibold ${textColor} w-10 text-right`}>{(val * 100).toFixed(0)}%</span>
                    </div>
                  ))}
                  <div className="border-t border-border/40 pt-3 space-y-1.5 text-xs">
                    {[
                      ["AI Risk Score", ai_risk.ai_risk_score.toFixed(1)],
                      ["Confidence", `${(ai_risk.confidence * 100).toFixed(0)}%`],
                      ["Blend", `${(ai_risk.blend_rule_weight * 100).toFixed(0)}% Rule / ${(ai_risk.blend_ai_weight * 100).toFixed(0)}% AI`],
                    ].map(([l, v]) => (
                      <div key={l} className="flex justify-between text-muted">
                        <span>{l}</span>
                        <span className="text-gray-200 font-mono">{v}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="text-center py-6">
                  <p className="text-muted text-sm">AI model not trained yet</p>
                  <p className="text-gray-600 text-xs mt-1">Using rule-based risk score only</p>
                </div>
              )}
            </Card>
          )}
        </div>
      )}

      {/* ── Market Pulse ── */}
      {macro && (
        <Card title="Market Pulse">
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
            {[
              { label: "NIFTY", value: `₹${macro.nifty_close?.toLocaleString("en-IN")}`, ok: macro.nifty_above_200dma, sub: macro.nifty_above_200dma ? "▲ 200DMA" : "▼ 200DMA" },
              { label: "VIX", value: macro.vix?.toFixed(1), ok: macro.vix < 18, sub: macro.vix_rising ? "Rising" : "Falling" },
              { label: "Breadth", value: `${macro.breadth_pct_above_50dma?.toFixed(0)}%`, ok: macro.breadth_pct_above_50dma > 50, sub: ">50 DMA" },
              { label: "S&P 500", value: macro.sp500_above_200dma ? "Above" : "Below", ok: macro.sp500_above_200dma, sub: "200DMA" },
              { label: "DXY", value: macro.dxy_breakout ? "Breakout" : "Normal", ok: !macro.dxy_breakout },
              { label: "Oil", value: macro.oil_spike ? "Spike" : "Normal", ok: !macro.oil_spike },
              { label: "Gold", value: macro.gold_above_50dma ? "Strong" : "Weak", ok: null, sub: macro.gold_above_50dma ? "▲ 50DMA" : "▼ 50DMA" },
            ].map((m) => (
              <div key={m.label} className="bg-base/50 rounded-lg p-3 border border-border/30">
                <div className="text-[10px] font-semibold uppercase tracking-widest text-muted mb-1">{m.label}</div>
                <div className={`text-sm font-bold font-mono ${m.ok === true ? "text-emerald-400" : m.ok === false ? "text-red-400" : "text-amber-400"}`}>
                  {m.value}
                </div>
                {m.sub && <div className="text-[10px] text-muted mt-0.5">{m.sub}</div>}
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* ── Why No Trades ── */}
      {why_no_trades && (
        <Card title="Trade Status">
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-full bg-amber-500/10 flex items-center justify-center flex-shrink-0">
              <span className="text-amber-400 text-sm">?</span>
            </div>
            <p className="text-gray-300 text-sm leading-relaxed">{why_no_trades}</p>
          </div>
        </Card>
      )}

      {/* ── Deployment Picks ── */}
      {deployment && deployment.stock_picks?.length > 0 && (
        <Card title="Equity Deployment">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {deployment.stock_picks.map((s, i) => (
              <div key={i} className="bg-base/50 rounded-lg p-3.5 border border-border/30 hover:border-blue-500/30 transition-colors">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-bold text-gray-100 text-sm">{s.clean_symbol}</span>
                  <Badge variant="success">₹{s.amount.toLocaleString("en-IN")}</Badge>
                </div>
                <div className="text-xs text-muted font-mono">
                  {s.quantity} shares @ ₹{s.price.toLocaleString("en-IN")} &middot; {s.weight_pct}%
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* ── Top Ranked ── */}
      {top_ranked && top_ranked.length > 0 && (
        <Card title="Top Ranked Stocks">
          <div className="flex gap-3 overflow-x-auto pb-2">
            {top_ranked.map((r) => (
              <div key={r.symbol} className="bg-base/50 rounded-lg p-3.5 border border-border/30 min-w-[150px] hover:border-blue-500/30 transition-colors">
                <div className="flex items-center gap-2 mb-1.5">
                  <span className="text-blue-400 font-bold text-xs font-mono">#{r.rank}</span>
                  <span className="font-semibold text-gray-100 text-sm">{r.clean_symbol}</span>
                </div>
                <p className="text-xs text-muted font-mono">₹{r.price?.toLocaleString("en-IN")}</p>
                <p className={`text-sm font-bold font-mono mt-1 ${r.composite >= 70 ? "text-emerald-400" : r.composite >= 50 ? "text-amber-400" : "text-muted"}`}>
                  {r.composite.toFixed(1)}/100
                </p>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* ── Stats Grid ── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          label="Capital"
          value={`₹${p.current_capital.toLocaleString("en-IN")}`}
          color={p.current_capital >= p.initial_capital ? "text-profit" : "text-loss"}
        />
        <StatCard
          label="Total Return"
          value={`${p.total_return_pct >= 0 ? "+" : ""}${p.total_return_pct}%`}
          color={p.total_return_pct >= 0 ? "text-profit" : "text-loss"}
        />
        <StatCard
          label="Win Rate"
          value={`${p.win_rate}%`}
          sub={`${p.winning_trades}W / ${p.losing_trades}L`}
          color={p.win_rate >= 60 ? "text-profit" : "text-amber"}
        />
        <StatCard label="Max Drawdown" value={`${p.max_drawdown_pct}%`} color="text-loss" />
        <StatCard label="CAGR" value={`${p.cagr}%`} />
        <StatCard label="Profit Factor" value={p.profit_factor || "—"} />
        <StatCard label="Avg Win" value={`₹${p.avg_win.toFixed(0)}`} color="text-profit" />
        <StatCard label="Avg Loss" value={`₹${p.avg_loss.toFixed(0)}`} color="text-loss" />
      </div>

      {/* ── Equity Curve ── */}
      <Card title="Equity Curve">
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={equity_curve}>
              <defs>
                <linearGradient id="eqGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.25} />
                  <stop offset="100%" stopColor="#3b82f6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(30,41,59,0.5)" vertical={false} />
              <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#64748b" }} tickLine={false} axisLine={false} />
              <YAxis tick={{ fontSize: 10, fill: "#64748b" }} tickLine={false} axisLine={false} width={50} />
              <Tooltip {...CHART_TOOLTIP} />
              <Area type="monotone" dataKey="equity" stroke="#3b82f6" fill="url(#eqGrad)" strokeWidth={2} dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </Card>

      {/* ── Open Trades & Candidates ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card title={`Open Trades (${open_trades.length}/3)`}>
          {open_trades.length === 0 ? (
            <p className="text-muted text-sm py-4 text-center">No open trades</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="pro-table w-full">
                <thead>
                  <tr>
                    <th className="text-left">Symbol</th>
                    <th className="text-right">Entry</th>
                    <th className="text-right">SL</th>
                    <th className="text-right">Target</th>
                    <th className="text-right">Qty</th>
                  </tr>
                </thead>
                <tbody>
                  {open_trades.map((t) => (
                    <tr key={t.id}>
                      <td className="font-semibold text-gray-100">{t.symbol}</td>
                      <td className="text-right font-mono">₹{t.entry_price}</td>
                      <td className="text-right font-mono text-loss">₹{t.stop_loss}</td>
                      <td className="text-right font-mono text-profit">₹{t.target}</td>
                      <td className="text-right font-mono">{t.quantity}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        <Card title={`Scan Candidates (${recent_scans.length})`}>
          {recent_scans.length === 0 ? (
            <div className="text-center py-6">
              <p className="text-muted text-sm">No candidates found</p>
              <p className="text-gray-600 text-xs mt-1">
                {!equityAllowed ? "Equity disabled in current regime." : "Run the scanner to find setups."}
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="pro-table w-full">
                <thead>
                  <tr>
                    <th className="text-left">Symbol</th>
                    <th className="text-right">Price</th>
                    <th className="text-right">RSI</th>
                    <th className="text-right">Vol</th>
                  </tr>
                </thead>
                <tbody>
                  {recent_scans.map((s) => (
                    <tr key={s.id}>
                      <td className="font-semibold text-gray-100">{s.symbol}</td>
                      <td className="text-right font-mono">₹{s.price?.toFixed(2)}</td>
                      <td className="text-right font-mono">{s.rsi?.toFixed(1)}</td>
                      <td className="text-right font-mono">{s.volume_ratio?.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
