import { useState } from "react";
import { Card, Loader, ErrorMsg } from "../components/UI";
import { fetchSmartAdvice, fetchAIRecommendation } from "../api";
import { useCapital } from "../App";
import {
  Sparkles, TrendingUp, TrendingDown, Shield, AlertTriangle,
  DollarSign, Target, ArrowRight, Coins, Landmark, PiggyBank,
  RefreshCw, ChevronRight, BarChart3, Zap, Bot, Brain,
} from "lucide-react";

/* ─── Risk Level Badge ───────────────────────────────── */
function RiskBadge({ level, score }) {
  const cfg = {
    EXTREME:  { bg: "bg-red-500/15", border: "border-red-500/30", text: "text-red-400" },
    HIGH:     { bg: "bg-orange-500/15", border: "border-orange-500/30", text: "text-orange-400" },
    MODERATE: { bg: "bg-amber-500/15", border: "border-amber-500/30", text: "text-amber-400" },
    LOW:      { bg: "bg-emerald-500/15", border: "border-emerald-500/30", text: "text-emerald-400" },
  };
  const c = cfg[level] || cfg.LOW;
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-bold border ${c.bg} ${c.text} ${c.border}`}>
      <Shield size={12} /> {level} ({score}/100)
    </span>
  );
}

/* ─── Regime Badge ───────────────────────────────────── */
function RegimeBadge({ regime, label, confidence }) {
  const colors = {
    STRONG_RISK_ON:  "text-emerald-400 bg-emerald-500/10 border-emerald-500/30",
    MILD_RISK_ON:    "text-green-400 bg-green-500/10 border-green-500/30",
    NEUTRAL:         "text-amber-400 bg-amber-500/10 border-amber-500/30",
    RISK_OFF:        "text-orange-400 bg-orange-500/10 border-orange-500/30",
    EXTREME_RISK:    "text-red-400 bg-red-500/10 border-red-500/30",
  };
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-bold border ${colors[regime] || colors.NEUTRAL}`}>
      <BarChart3 size={12} /> {label} ({(confidence * 100).toFixed(0)}%)
    </span>
  );
}

/* ─── Type Icon ──────────────────────────────────────── */
function TypeIcon({ type }) {
  const map = {
    EQUITY: { icon: TrendingUp, color: "text-blue-400 bg-blue-500/10" },
    GOLD:   { icon: Coins, color: "text-yellow-400 bg-yellow-500/10" },
    SILVER: { icon: Coins, color: "text-gray-300 bg-gray-400/10" },
    CASH:   { icon: PiggyBank, color: "text-emerald-400 bg-emerald-500/10" },
  };
  const cfg = map[type] || map.CASH;
  const Icon = cfg.icon;
  return (
    <div className={`p-2.5 rounded-xl ${cfg.color}`}>
      <Icon size={20} />
    </div>
  );
}

/* ─── Confidence Dot ─────────────────────────────────── */
function ConfidenceDot({ level }) {
  const colors = {
    HIGH: "bg-emerald-400",
    MEDIUM: "bg-amber-400",
    LOW: "bg-gray-500",
  };
  return (
    <span className={`inline-block w-2 h-2 rounded-full ${colors[level] || colors.LOW}`} />
  );
}

/* ─── Recommendation Card ────────────────────────────── */
function RecommendationCard({ rec, index }) {
  const isCash = rec.type === "CASH";
  const isEquity = rec.type === "EQUITY";
  const typeColors = {
    EQUITY: "border-blue-500/20 hover:border-blue-500/40",
    GOLD:   "border-yellow-500/20 hover:border-yellow-500/40",
    SILVER: "border-gray-400/20 hover:border-gray-400/40",
    CASH:   "border-emerald-500/20 hover:border-emerald-500/40",
  };

  return (
    <div className={`glass-card p-5 transition-all duration-200 ${typeColors[rec.type] || ""} animate-fade-in`}
      style={{ animationDelay: `${index * 80}ms` }}>
      <div className="flex items-start gap-4">
        <TypeIcon type={rec.type} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-3 mb-1">
            <div className="flex items-center gap-2.5">
              <span className="text-base font-bold text-gray-100">{rec.symbol}</span>
              <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                rec.action === "BUY" ? "bg-emerald-500/15 text-emerald-400 border-emerald-500/30"
                : "bg-blue-500/15 text-blue-400 border-blue-500/30"
              }`}>
                {rec.action}
              </span>
              <ConfidenceDot level={rec.confidence} />
            </div>
            <span className="text-lg font-bold font-mono text-gray-100">
              ₹{rec.amount.toLocaleString("en-IN", { maximumFractionDigits: 0 })}
            </span>
          </div>
          <p className="text-xs text-muted mb-2">{rec.name}</p>

          {!isCash && (
            <div className="flex items-center gap-4 text-[11px] text-gray-400">
              <span className="font-mono">
                <span className="text-muted">Price:</span>{" "}
                <span className="text-gray-200 font-semibold">₹{rec.price.toLocaleString("en-IN", { maximumFractionDigits: 2 })}</span>
              </span>
              <span className="text-gray-700">×</span>
              <span className="font-mono">
                <span className="text-muted">Qty:</span>{" "}
                <span className="text-gray-200 font-semibold">{rec.quantity}</span>
              </span>
              <span className="text-gray-700">|</span>
              <span className="font-mono">
                <span className="text-muted">Weight:</span>{" "}
                <span className="text-gray-200">{rec.weight_pct.toFixed(1)}%</span>
              </span>
              {isEquity && rec.rank_score > 0 && (
                <>
                  <span className="text-gray-700">|</span>
                  <span className="font-mono">
                    <span className="text-muted">Rank:</span>{" "}
                    <span className={`font-semibold ${rec.rank_score >= 70 ? "text-emerald-400" : rec.rank_score >= 50 ? "text-amber-400" : "text-gray-400"}`}>
                      {rec.rank_score.toFixed(0)}
                    </span>
                  </span>
                </>
              )}
            </div>
          )}

          {rec.reason && (
            <p className="text-[11px] text-gray-500 mt-2 leading-relaxed">{rec.reason}</p>
          )}
        </div>
      </div>
    </div>
  );
}

/* ─── Allocation Donut (pure CSS) ────────────────────── */
function AllocationRing({ breakdown }) {
  if (!breakdown) return null;
  const { equity_pct, gold_pct, silver_pct, cash_pct } = breakdown;
  const segments = [
    { label: "Equity", pct: equity_pct, color: "bg-blue-500", text: "text-blue-400" },
    { label: "Gold", pct: gold_pct, color: "bg-yellow-500", text: "text-yellow-400" },
    { label: "Silver", pct: silver_pct, color: "bg-gray-400", text: "text-gray-300" },
    { label: "Cash", pct: cash_pct, color: "bg-emerald-500", text: "text-emerald-400" },
  ].filter((s) => s.pct > 0);

  return (
    <div className="flex items-center gap-4 flex-wrap">
      {segments.map((s) => (
        <div key={s.label} className="flex items-center gap-2">
          <div className={`w-3 h-3 rounded-sm ${s.color}`} />
          <span className="text-[11px] text-muted">{s.label}</span>
          <span className={`text-[12px] font-bold font-mono ${s.text}`}>{s.pct.toFixed(1)}%</span>
        </div>
      ))}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════
   Smart Advisor Page
   ═══════════════════════════════════════════════════════ */
export default function Advisor() {
  const { capital: globalCapital } = useCapital();
  const [capital, setCapital] = useState(String(Math.round(globalCapital)));
  const [advice, setAdvice] = useState(null);
  const [aiRec, setAiRec] = useState(null);
  const [loading, setLoading] = useState(false);
  const [aiLoading, setAiLoading] = useState(false);
  const [error, setError] = useState(null);
  const [mode, setMode] = useState("ai"); // "ai" or "engine"

  const presets = [10000, 20000, 50000, 100000, 250000, 500000];

  const handleSubmit = async (amt) => {
    const amount = amt || parseFloat(capital);
    if (!amount || amount <= 0) return;
    setError(null);

    if (mode === "ai") {
      setAiLoading(true);
      setAiRec(null);
      try {
        const data = await fetchAIRecommendation(amount);
        setAiRec(data);
      } catch (e) {
        setError(e.message);
      } finally {
        setAiLoading(false);
      }
    } else {
      setLoading(true);
      setAdvice(null);
      try {
        const data = await fetchSmartAdvice(amount);
        setAdvice(data);
      } catch (e) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold tracking-tight flex items-center gap-3">
          <div className="p-2 rounded-xl bg-gradient-to-br from-purple-500/20 to-blue-500/20 border border-purple-500/20">
            <Sparkles size={22} className="text-purple-400" />
          </div>
          <span className="text-gradient">Smart Money Advisor</span>
        </h2>
        <p className="text-sm text-muted mt-1">
          AI-powered stock recommendations with real-time market intelligence
        </p>
        {/* Mode Toggle */}
        <div className="flex gap-2 mt-3">
          <button
            onClick={() => setMode("ai")}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold transition-all border ${
              mode === "ai"
                ? "bg-purple-500/15 text-purple-300 border-purple-500/30"
                : "bg-surface-2/30 text-muted border-transparent hover:border-gold/10"
            }`}
          >
            <Brain size={14} /> AI Picks
          </button>
          <button
            onClick={() => setMode("engine")}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold transition-all border ${
              mode === "engine"
                ? "bg-blue-500/15 text-blue-300 border-blue-500/30"
                : "bg-surface-2/30 text-muted border-transparent hover:border-gold/10"
            }`}
          >
            <Zap size={14} /> Quant Engine
          </button>
        </div>
      </div>

      {/* Input Section */}
      <div className="glass-card p-6">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1">
            <label className="text-[11px] font-semibold text-muted uppercase tracking-wider mb-2 block">
              Investment Amount (₹)
            </label>
            <div className="flex items-center glass-card px-4 py-3 focus-within:border-blue-500/40 transition-colors">
              <DollarSign size={18} className="text-muted mr-2" />
              <input
                type="number"
                value={capital}
                onChange={(e) => setCapital(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
                placeholder="Enter amount (e.g. 50000)"
                className="bg-transparent text-lg font-mono text-gray-200 placeholder-gray-600 outline-none flex-1"
                min="1000"
              />
            </div>
          </div>
          <div className="flex items-end">
            <button
              onClick={() => handleSubmit()}
              disabled={loading || aiLoading || !capital}
              className="btn-primary px-6 py-3 flex items-center gap-2 text-sm font-semibold disabled:opacity-50"
            >
              {(loading || aiLoading) ? (
                <>
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  {mode === "ai" ? "AI Thinking..." : "Analyzing..."}
                </>
              ) : (
                <>
                  {mode === "ai" ? <Brain size={16} /> : <Zap size={16} />}
                  {mode === "ai" ? "Get AI Picks" : "Get Recommendations"}
                </>
              )}
            </button>
          </div>
        </div>

        {/* Quick Presets */}
        <div className="flex gap-2 mt-4 flex-wrap">
          <span className="text-[10px] text-muted uppercase tracking-wider self-center mr-1">Quick:</span>
          {presets.map((p) => (
            <button
              key={p}
              onClick={() => { setCapital(String(p)); handleSubmit(p); }}
              disabled={loading}
              className="px-3 py-1.5 rounded-lg text-[11px] font-mono font-semibold bg-white/[0.03] border border-border/40 text-gray-400 hover:text-blue-400 hover:border-blue-500/30 hover:bg-blue-500/5 transition-all disabled:opacity-50"
            >
              ₹{p >= 100000 ? `${p / 100000}L` : `${(p / 1000).toFixed(0)}K`}
            </button>
          ))}
        </div>
      </div>

      {error && <ErrorMsg message={error} />}
      {(loading || aiLoading) && <Loader />}

      {/* AI Recommendation Result */}
      {aiRec && mode === "ai" && (
        <div className="space-y-4 animate-fade-in">
          <div className="glass-card p-6 border-purple-500/20">
            <div className="flex items-center gap-2 mb-4">
              <div className="p-2 rounded-lg bg-purple-500/15">
                <Brain size={18} className="text-purple-400" />
              </div>
              <div>
                <h3 className="text-base font-bold text-purple-300">AI Investment Plan</h3>
                <span className="text-[10px] font-mono text-muted">Powered by Gemini · {new Date(aiRec.timestamp).toLocaleString()}</span>
              </div>
            </div>
            <div className="text-[13px] text-gray-300 leading-relaxed ai-markdown space-y-1.5">
              {aiRec.recommendation.split("\n").map((line, i) => {
                if (line.startsWith("### "))
                  return <h4 key={i} className="text-gold font-bold text-sm mt-4 mb-1">{line.slice(4)}</h4>;
                if (line.startsWith("## "))
                  return <h3 key={i} className="text-gold-bright font-bold text-base mt-4 mb-1">{line.slice(3)}</h3>;
                if (line.startsWith("- **") || line.startsWith("* **"))
                  return (
                    <div key={i} className="flex gap-2 pl-2 py-0.5">
                      <span className="text-purple-400/60 mt-0.5">▸</span>
                      <span dangerouslySetInnerHTML={{ __html: line.slice(2).replace(/\*\*(.+?)\*\*/g, '<strong class="text-gray-100">$1</strong>') }} />
                    </div>
                  );
                if (line.startsWith("- ") || line.startsWith("* "))
                  return (
                    <div key={i} className="flex gap-2 pl-2 py-0.5">
                      <span className="text-gray-600">•</span>
                      <span dangerouslySetInnerHTML={{ __html: line.slice(2).replace(/\*\*(.+?)\*\*/g, '<strong class="text-gray-100">$1</strong>') }} />
                    </div>
                  );
                if (line.trim() === "") return <div key={i} className="h-2" />;
                return <p key={i} dangerouslySetInnerHTML={{ __html: line.replace(/\*\*(.+?)\*\*/g, '<strong class="text-gray-100">$1</strong>') }} />;
              })}
            </div>
          </div>
          {aiRec.market_data && (
            <div className="glass-card p-4 border-blue-500/10">
              <h4 className="text-[10px] font-semibold uppercase tracking-widest text-muted mb-2 font-mono">Live Market Data Used</h4>
              <pre className="text-[11px] text-gray-400 font-mono leading-relaxed whitespace-pre-wrap">{aiRec.market_data}</pre>
            </div>
          )}
        </div>
      )

      }

      {/* Engine Results */}
      {advice && mode === "engine" && (
        <div className="space-y-5 animate-fade-in">
          {/* AI Insight */}
          {advice.ai_insight && (
            <div className="glass-card p-5 border-purple-500/20">
              <div className="flex items-center gap-2 mb-3">
                <div className="p-1.5 rounded-lg bg-purple-500/15">
                  <Sparkles size={14} className="text-purple-400" />
                </div>
                <h3 className="text-sm font-bold text-purple-300">AI Analysis</h3>
                <span className="text-[9px] font-mono text-muted bg-surface-2 px-2 py-0.5 rounded">Gemini</span>
              </div>
              <div className="text-[13px] text-gray-300 leading-relaxed ai-markdown">
                {advice.ai_insight.split("\n").map((line, i) => {
                  if (line.trim() === "") return <div key={i} className="h-1" />;
                  if (line.startsWith("- ") || line.startsWith("* "))
                    return <div key={i} className="flex gap-2 ml-1"><span className="text-purple-400/50">•</span><span dangerouslySetInnerHTML={{ __html: line.slice(2).replace(/\*\*(.+?)\*\*/g, '<strong class="text-gray-100">$1</strong>') }} /></div>;
                  return <p key={i} dangerouslySetInnerHTML={{ __html: line.replace(/\*\*(.+?)\*\*/g, '<strong class="text-gray-100">$1</strong>') }} />;
                })}
              </div>
            </div>
          )}

          {/* Summary Banner */}
          <div className="glass-card p-5 border-blue-500/20">
            <div className="flex items-center gap-3 mb-3">
              <Target size={18} className="text-blue-400" />
              <h3 className="text-sm font-bold text-gray-100">Recommendation Summary</h3>
            </div>
            <p className="text-sm text-gray-300 font-medium leading-relaxed mb-4">{advice.summary}</p>

            {/* Key Metrics */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="bg-base/60 rounded-lg p-3 border border-border/30">
                <div className="text-[10px] text-muted uppercase tracking-wider mb-1">Capital</div>
                <div className="text-lg font-bold font-mono text-gray-100">
                  ₹{advice.capital.toLocaleString("en-IN")}
                </div>
              </div>
              <div className="bg-base/60 rounded-lg p-3 border border-border/30">
                <div className="text-[10px] text-muted uppercase tracking-wider mb-1">Deployed</div>
                <div className="text-lg font-bold font-mono text-emerald-400">
                  ₹{advice.total_invested.toLocaleString("en-IN", { maximumFractionDigits: 0 })}
                </div>
              </div>
              <div className="bg-base/60 rounded-lg p-3 border border-border/30">
                <div className="text-[10px] text-muted uppercase tracking-wider mb-1">Cash Reserve</div>
                <div className="text-lg font-bold font-mono text-blue-400">
                  ₹{advice.total_cash.toLocaleString("en-IN", { maximumFractionDigits: 0 })}
                </div>
              </div>
              <div className="bg-base/60 rounded-lg p-3 border border-border/30">
                <div className="text-[10px] text-muted uppercase tracking-wider mb-1">Brokerage Est.</div>
                <div className="text-lg font-bold font-mono text-gray-400">
                  ₹{advice.brokerage_estimate.toLocaleString("en-IN", { maximumFractionDigits: 0 })}
                </div>
              </div>
            </div>
          </div>

          {/* Risk Context */}
          {advice.risk_context && (
            <div className="glass-card p-5">
              <h3 className="text-sm font-bold mb-3 flex items-center gap-2">
                <Shield size={16} className="text-amber-400" /> Market Risk Context
              </h3>
              <div className="flex flex-wrap gap-3 mb-3">
                <RegimeBadge
                  regime={advice.risk_context.regime}
                  label={advice.risk_context.regime_label}
                  confidence={advice.risk_context.regime_confidence}
                />
                <RiskBadge
                  level={advice.risk_context.geo_risk_level}
                  score={advice.risk_context.geo_risk_score}
                />
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-[11px]">
                <div className="bg-base/40 rounded-lg p-2.5 border border-border/20">
                  <span className="text-muted">Risk Score</span>
                  <div className={`text-sm font-bold font-mono mt-0.5 ${
                    advice.risk_context.blended_risk_score >= 65 ? "text-red-400" :
                    advice.risk_context.blended_risk_score >= 45 ? "text-amber-400" : "text-emerald-400"
                  }`}>{advice.risk_context.blended_risk_score}/100</div>
                </div>
                <div className="bg-base/40 rounded-lg p-2.5 border border-border/20">
                  <span className="text-muted">AI Confidence</span>
                  <div className="text-sm font-bold font-mono mt-0.5 text-purple-400">{advice.risk_context.ai_confidence}%</div>
                </div>
                <div className="bg-base/40 rounded-lg p-2.5 border border-border/20">
                  <span className="text-muted">VIX</span>
                  <div className={`text-sm font-bold font-mono mt-0.5 ${
                    advice.risk_context.vix >= 25 ? "text-red-400" : advice.risk_context.vix >= 18 ? "text-amber-400" : "text-emerald-400"
                  }`}>{advice.risk_context.vix?.toFixed(1) || "N/A"}</div>
                </div>
                <div className="bg-base/40 rounded-lg p-2.5 border border-border/20">
                  <span className="text-muted">NIFTY Trend</span>
                  <div className={`text-sm font-bold mt-0.5 ${
                    advice.risk_context.nifty_trend === "Bullish" ? "text-emerald-400" : "text-red-400"
                  }`}>{advice.risk_context.nifty_trend}</div>
                </div>
              </div>
              {advice.risk_context.active_conflicts > 0 && (
                <div className="mt-3 flex items-center gap-2 text-[11px]">
                  <AlertTriangle size={12} className="text-orange-400" />
                  <span className="text-orange-400 font-medium">
                    {advice.risk_context.active_conflicts} active geopolitical conflict{advice.risk_context.active_conflicts > 1 ? "s" : ""} detected
                  </span>
                </div>
              )}
            </div>
          )}

          {/* Allocation Breakdown */}
          <div className="glass-card p-5">
            <h3 className="text-sm font-bold mb-3 flex items-center gap-2">
              <Landmark size={16} className="text-blue-400" /> Allocation Strategy
            </h3>
            <AllocationRing breakdown={advice.allocation_breakdown} />

            {/* Allocation bar */}
            <div className="mt-3 w-full h-3 rounded-full overflow-hidden flex bg-gray-800/60">
              {advice.allocation_breakdown.equity_pct > 0 && (
                <div className="bg-blue-500 h-full transition-all" style={{ width: `${advice.allocation_breakdown.equity_pct}%` }} />
              )}
              {advice.allocation_breakdown.gold_pct > 0 && (
                <div className="bg-yellow-500 h-full transition-all" style={{ width: `${advice.allocation_breakdown.gold_pct}%` }} />
              )}
              {advice.allocation_breakdown.silver_pct > 0 && (
                <div className="bg-gray-400 h-full transition-all" style={{ width: `${advice.allocation_breakdown.silver_pct}%` }} />
              )}
              {advice.allocation_breakdown.cash_pct > 0 && (
                <div className="bg-emerald-500 h-full transition-all" style={{ width: `${advice.allocation_breakdown.cash_pct}%` }} />
              )}
            </div>
          </div>

          {/* Individual Recommendations */}
          <div>
            <h3 className="text-sm font-bold mb-3 flex items-center gap-2">
              <ArrowRight size={16} className="text-emerald-400" />
              Specific Recommendations ({advice.recommendations.length})
            </h3>
            <div className="space-y-3">
              {advice.recommendations.map((rec, i) => (
                <RecommendationCard key={`${rec.symbol}-${i}`} rec={rec} index={i} />
              ))}
            </div>
          </div>

          {/* Why No Trades */}
          {advice.why_no_trades && (
            <div className="glass-card p-4 border-amber-500/20">
              <div className="flex items-start gap-2">
                <AlertTriangle size={16} className="text-amber-400 mt-0.5 shrink-0" />
                <p className="text-xs text-amber-300/80 leading-relaxed">{advice.why_no_trades}</p>
              </div>
            </div>
          )}

          {/* Timestamp */}
          <div className="text-center text-[10px] text-gray-600 font-mono">
            Generated at {new Date(advice.timestamp).toLocaleString()} • Real-time analysis
          </div>
        </div>
      )}
    </div>
  );
}
