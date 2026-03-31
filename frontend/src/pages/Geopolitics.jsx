import { useState, useEffect } from "react";
import {
  Globe, AlertTriangle, Shield, TrendingUp, TrendingDown,
  ExternalLink, RefreshCw, ChevronRight, Zap, AlertCircle,
  Newspaper, Target, Clock,
} from "lucide-react";
import { fetchGeopoliticsOverview } from "../api";

const RISK_COLORS = {
  CRITICAL: { bg: "bg-red-500/10", border: "border-red-500/30", text: "text-red-400", glow: "shadow-glow-red" },
  HIGH: { bg: "bg-orange-500/10", border: "border-orange-500/30", text: "text-orange-400", glow: "" },
  ELEVATED: { bg: "bg-yellow-500/10", border: "border-yellow-500/30", text: "text-yellow-400", glow: "" },
  MODERATE: { bg: "bg-blue-500/10", border: "border-blue-500/30", text: "text-blue-400", glow: "" },
  LOW: { bg: "bg-emerald-500/10", border: "border-emerald-500/30", text: "text-emerald-400", glow: "" },
};

const ACTION_COLORS = {
  HEDGE: "text-yellow-400",
  DEFENSIVE: "text-orange-400",
  SELECTIVE: "text-blue-400",
  MONITOR: "text-muted",
};

export default function Geopolitics() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedConflict, setSelectedConflict] = useState(null);

  const load = () => {
    setLoading(true);
    setError(null);
    fetchGeopoliticsOverview()
      .then(setData)
      .catch(err => setError(err.message || "Failed to load"))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-muted font-mono text-sm animate-pulse">
          <span className="text-matrix">&#9608;</span> Loading geopolitical intelligence...
        </div>
      </div>
    );
  }

  if (!data) return (
    <div className="text-center py-20">
      <div className="text-muted font-mono text-sm mb-3">{error || "Failed to load geopolitical data"}</div>
      <button onClick={load} className="btn-primary text-xs">Retry</button>
    </div>
  );

  const rc = RISK_COLORS[data.risk_level] || RISK_COLORS.MODERATE;

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gold-bright font-display tracking-tight">
            Geopolitical Intelligence
          </h1>
          <p className="text-muted text-sm mt-1 font-mono">
            Real-time conflict monitoring &amp; market impact analysis
          </p>
        </div>
        <button onClick={load} className="btn-primary flex items-center gap-2" disabled={loading}>
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          Refresh Intel
        </button>
      </div>

      {/* Risk Score Banner */}
      <div className={`glass-card p-5 ${rc.border} border`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className={`w-16 h-16 rounded-lg ${rc.bg} flex items-center justify-center ${rc.glow}`}>
              <span className={`text-2xl font-mono font-bold ${rc.text}`}>{data.risk_score}</span>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className={`text-lg font-bold ${rc.text}`}>{data.risk_level}</span>
                <span className="text-muted text-xs font-mono">RISK LEVEL</span>
              </div>
              <p className="text-sm text-gray-400 mt-1">{data.overall_action}</p>
            </div>
          </div>
          <div className="text-right">
            <div className="text-xs text-muted font-mono flex items-center gap-1">
              <Clock size={10} />
              {data.last_updated}
            </div>
            <div className="text-xs text-muted mt-1">
              {data.conflict_count} active conflicts &middot; {data.data_sources?.length} sources
            </div>
          </div>
        </div>
      </div>

      {/* Active Conflicts */}
      <div>
        <h2 className="text-sm font-semibold text-gold uppercase tracking-wider font-mono mb-3 flex items-center gap-2">
          <AlertTriangle size={14} />
          Active Conflicts &amp; Market Impact
        </h2>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {data.active_conflicts?.map((c, i) => {
            const isSelected = selectedConflict === i;
            const sev = c.severity === "HIGH" ? "border-red-500/30" : "border-yellow-500/30";
            return (
              <div
                key={i}
                className={`glass-card p-4 cursor-pointer transition-all ${sev} border ${isSelected ? "ring-1 ring-gold/30" : ""}`}
                onClick={() => setSelectedConflict(isSelected ? null : i)}
              >
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <h3 className="font-semibold text-white text-sm">{c.event}</h3>
                    <div className="flex items-center gap-2 mt-1">
                      <span className={`text-[10px] font-mono px-2 py-0.5 rounded ${
                        c.severity === "HIGH" ? "bg-red-500/15 text-red-400" : "bg-yellow-500/15 text-yellow-400"
                      }`}>
                        {c.severity}
                      </span>
                      <span className="text-[10px] font-mono text-muted">{c.status}</span>
                      <span className={`text-[10px] font-mono px-2 py-0.5 rounded bg-surface-2 ${ACTION_COLORS[c.portfolio_action] || "text-muted"}`}>
                        {c.portfolio_action}
                      </span>
                    </div>
                  </div>
                  <ChevronRight
                    size={14}
                    className={`text-muted transition-transform ${isSelected ? "rotate-90" : ""}`}
                  />
                </div>

                <p className="text-xs text-gray-400 mt-2">{c.impact}</p>
                <p className="text-xs text-muted mt-1 italic">{c.risk_direction}</p>

                {/* Expanded View */}
                {isSelected && (
                  <div className="mt-4 pt-3 border-t border-gold/10 space-y-3 animate-fade-in">
                    <div>
                      <h4 className="text-[10px] font-mono text-gold uppercase tracking-wider mb-2">
                        <Target size={10} className="inline mr-1" />
                        Actionable Suggestions
                      </h4>
                      <ul className="space-y-1.5">
                        {c.suggestions?.map((s, j) => (
                          <li key={j} className="flex items-start gap-2 text-xs text-gray-300">
                            <Zap size={10} className="text-gold mt-0.5 flex-shrink-0" />
                            {s}
                          </li>
                        ))}
                      </ul>
                    </div>
                    <div>
                      <h4 className="text-[10px] font-mono text-gold uppercase tracking-wider mb-1.5">
                        Assets to Watch
                      </h4>
                      <div className="flex flex-wrap gap-1.5">
                        {c.assets_to_watch?.map((a, j) => (
                          <span key={j} className="pro-badge text-[9px]">{a}</span>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Risk Headlines with Source & Suggestions */}
      <div>
        <h2 className="text-sm font-semibold text-gold uppercase tracking-wider font-mono mb-3 flex items-center gap-2">
          <Newspaper size={14} />
          Live Risk Headlines
        </h2>
        <div className="glass-card divide-y divide-gold/5">
          {data.risk_headlines?.length > 0 ? (
            data.risk_headlines.map((hl, i) => (
              <div key={i} className="p-4 hover:bg-gold/[0.02] transition-colors">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1">
                    <p className="text-sm text-gray-200">{hl.title}</p>
                    <div className="flex items-center gap-3 mt-1.5">
                      <span className="text-[10px] font-mono text-gold bg-gold/10 px-2 py-0.5 rounded">
                        {hl.source}
                      </span>
                      <span className={`text-[10px] font-mono ${
                        hl.score > 15 ? "text-red-400" : hl.score > 8 ? "text-yellow-400" : "text-muted"
                      }`}>
                        Risk: {hl.score}/30
                      </span>
                    </div>
                    {/* Suggestion */}
                    <div className="mt-2 flex items-start gap-1.5">
                      <Zap size={10} className="text-matrix mt-0.5 flex-shrink-0" />
                      <span className="text-[11px] text-matrix/80">{hl.suggestion}</span>
                    </div>
                  </div>
                </div>
              </div>
            ))
          ) : (
            <div className="p-8 text-center text-muted text-sm">
              No high-risk headlines detected. Markets appear calm.
            </div>
          )}
        </div>
      </div>

      {/* India Impact Events */}
      {data.india_impact_events?.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-gold uppercase tracking-wider font-mono mb-3 flex items-center gap-2">
            <Shield size={14} />
            India-Specific Risk Events
          </h2>
          <div className="glass-card p-4 space-y-2">
            {data.india_impact_events.map((evt, i) => (
              <div key={i} className="flex items-start gap-2 text-sm text-gray-300">
                <span className="text-orange-400">&#9670;</span>
                {evt}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Data Sources */}
      <div className="glass-card p-4">
        <h3 className="text-[10px] font-mono text-muted uppercase tracking-wider mb-2">Data Sources</h3>
        <div className="flex flex-wrap gap-2">
          {data.data_sources?.map((src, i) => (
            <span key={i} className="text-[10px] font-mono text-gold/60 bg-gold/5 px-2 py-1 rounded">
              {src}
            </span>
          ))}
          <span className="text-[10px] font-mono text-gold/60 bg-gold/5 px-2 py-1 rounded">
            + {data.known_events_db_count} known events DB
          </span>
        </div>
      </div>
    </div>
  );
}
