import { useEffect, useState } from "react";
import { Zap, Bell, ArrowRight, Target } from "lucide-react";
import { fetchTodaysSignals } from "../api";
import { Badge, Skeleton } from "./UI";

/* ──────────────────────────────────────────────────────────────
   TodaysSignalsWidget — at-a-glance "what should I do today"
   surface for the Dashboard. Shows top conviction picks plus
   counts of open trades and freshly triggered alerts.
   ────────────────────────────────────────────────────────────── */

export default function TodaysSignalsWidget({ onNavigate }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchTodaysSignals(5)
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="glass-card overflow-hidden">
      <div className="flex items-center justify-between px-5 py-3 border-b border-gold/10">
        <div className="flex items-center gap-2">
          <Zap size={14} className="text-gold" />
          <h3 className="text-[10px] font-semibold uppercase tracking-[0.15em] text-gold font-mono">
            Today&apos;s Signals
          </h3>
        </div>
        <div className="flex items-center gap-2 text-[10px] font-mono text-muted">
          {data?.scan_date && <span>scan: {data.scan_date}</span>}
        </div>
      </div>

      <div className="p-5">
        {loading ? (
          <div className="space-y-2">
            {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-10 w-full" />)}
          </div>
        ) : !data ? (
          <p className="text-center text-muted text-sm py-3">No signal data yet — run the scanner.</p>
        ) : (
          <>
            {/* Counters */}
            <div className="grid grid-cols-3 gap-3 mb-4">
              <button
                onClick={() => onNavigate?.("scanner")}
                className="bg-base/50 hover:bg-base/70 transition-colors rounded-lg p-3 border border-border/30 text-left group"
              >
                <p className="text-[10px] font-semibold uppercase tracking-widest text-muted">Top Picks</p>
                <p className="text-xl font-bold font-mono text-gold-bright mt-1">{data.top_signals?.length ?? 0}</p>
              </button>
              <button
                onClick={() => onNavigate?.("trades")}
                className="bg-base/50 hover:bg-base/70 transition-colors rounded-lg p-3 border border-border/30 text-left group"
              >
                <p className="text-[10px] font-semibold uppercase tracking-widest text-muted">Open Trades</p>
                <p className="text-xl font-bold font-mono text-matrix mt-1">{data.open_trades ?? 0}</p>
              </button>
              <button
                onClick={() => onNavigate?.("alerts")}
                className="bg-base/50 hover:bg-base/70 transition-colors rounded-lg p-3 border border-border/30 text-left group relative"
              >
                <p className="text-[10px] font-semibold uppercase tracking-widest text-muted flex items-center gap-1">
                  <Bell size={10} /> Alerts Fired
                </p>
                <p className={`text-xl font-bold font-mono mt-1 ${data.triggered_alerts_count > 0 ? "text-amber-400 animate-pulse" : "text-muted"}`}>
                  {data.triggered_alerts_count ?? 0}
                </p>
              </button>
            </div>

            {/* Top picks list */}
            {data.top_signals?.length > 0 ? (
              <div className="space-y-1.5">
                {data.top_signals.slice(0, 5).map((s) => (
                  <button
                    key={s.symbol}
                    onClick={() => onNavigate?.("scanner")}
                    className="w-full flex items-center gap-3 px-3 py-2 rounded border border-border/30 bg-base/30 hover:border-gold/30 hover:bg-base/50 transition-all text-left group"
                  >
                    <div className="flex items-center gap-2 flex-1 min-w-0">
                      <Target size={12} className="text-gold flex-shrink-0" />
                      <span className="font-semibold text-sm text-gold-bright truncate">{s.symbol}</span>
                      <Badge variant={s.recommendation === "BUY" ? "success" : "info"}>
                        {s.recommendation}
                      </Badge>
                    </div>
                    <div className="flex items-center gap-3 text-[11px] font-mono">
                      {s.price != null && <span className="text-gray-300">₹{s.price.toFixed(2)}</span>}
                      {s.conviction_score != null && (
                        <span className={s.conviction_score >= 70 ? "text-matrix" : s.conviction_score >= 50 ? "text-gold" : "text-amber-400"}>
                          {Math.round(s.conviction_score)}
                        </span>
                      )}
                      {s.risk_reward && <span className="text-muted">{s.risk_reward}</span>}
                      <ArrowRight size={12} className="text-muted group-hover:text-gold transition-colors" />
                    </div>
                  </button>
                ))}
              </div>
            ) : (
              <p className="text-center text-muted text-sm py-3">
                No high-conviction picks today. Equity may be disabled by current regime.
              </p>
            )}
          </>
        )}
      </div>
    </div>
  );
}
