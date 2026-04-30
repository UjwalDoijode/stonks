import { useEffect, useMemo, useState } from "react";
import {
  Target, TrendingUp, Activity, Volume2, Crosshair,
  CheckCircle2, XCircle, AlertTriangle, Filter, RefreshCw, Search,
} from "lucide-react";
import {
  Card, Badge, Loader, ErrorMsg, EmptyState,
  ChangePill, TrendBadge, InsightTile,
} from "../components/UI";
import { fetchCandidates, runScan, invalidateCache } from "../api";

/* ──────────────────────────────────────────────────────────────
   Signals — Decision Support page.

   Surfaces the existing 8-criteria signal engine (signals.py) with
   transparent WHY explanations. Pure presentation: no fake AI, just
   rule-based reasoning users can verify and trust.

   Criteria (from backend Signal class):
     1. above_200dma         – long-term uptrend
     2. dma50_trending_up    – medium-term momentum
     3. pullback_to_20dma    – entry zone (not chasing)
     4. rsi_in_zone          – not oversold / not overbought
     5. volume_contracting   – reversal-friendly tape
     6. entry_triggered      – previous-bar high break
     7. cci_in_zone          – CCI between -50 and +100
     8. supertrend_bullish   – ATR trend filter
   ────────────────────────────────────────────────────────────── */

const CRITERIA = [
  { key: "above_200dma",       label: "Above 200 DMA",       icon: TrendingUp,   why: "Long-term uptrend intact — institutions are accumulating." },
  { key: "dma50_trending_up",  label: "50 DMA Rising",        icon: Activity,     why: "Medium-term momentum confirmed by rising 50-day average." },
  { key: "pullback_to_20dma",  label: "Pullback to 20 DMA",   icon: Target,       why: "Price near short-term mean — better risk/reward than chasing." },
  { key: "rsi_in_zone",        label: "RSI in Zone",          icon: Activity,     why: "RSI neither oversold nor overbought — room to move." },
  { key: "volume_contracting", label: "Volume Contracting",   icon: Volume2,      why: "Sellers exhausted; classic reversal tape." },
  { key: "entry_triggered",    label: "Entry Triggered",      icon: Crosshair,    why: "Price broke previous candle's high — momentum confirmed." },
  { key: "cci_in_zone",        label: "CCI Healthy",          icon: Activity,     why: "CCI between −50 and +100 — strong but not extended." },
  { key: "supertrend_bullish", label: "Supertrend Bullish",   icon: TrendingUp,   why: "ATR-based trend filter agrees with the long side." },
];

function recoStyle(rec) {
  switch (rec) {
    case "BUY":         return { label: "BUY",         cls: "bg-matrix/15 text-matrix border-matrix/30" };
    case "RECOMMENDED": return { label: "RECOMMENDED", cls: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30" };
    case "HOLD":        return { label: "HOLD",        cls: "bg-amber-500/15 text-amber-400 border-amber-500/30" };
    case "AVOID":       return { label: "AVOID",       cls: "bg-red-500/15 text-red-400 border-red-500/30" };
    default:            return { label: rec || "—",    cls: "bg-surface-2 text-gray-300 border-gold/10" };
  }
}

function ConvictionBar({ score = 0 }) {
  const clamped = Math.max(0, Math.min(100, score));
  const color = clamped >= 70 ? "#00ff41" : clamped >= 45 ? "#cfb57e" : "#ff9500";
  return (
    <div className="w-full h-1.5 bg-surface-2 rounded overflow-hidden">
      <div
        className="h-full rounded transition-all duration-500"
        style={{ width: `${clamped}%`, background: color, boxShadow: `0 0 6px ${color}80` }}
      />
    </div>
  );
}

function SignalRow({ row, expanded, onToggle }) {
  const reco = recoStyle(row.recommendation);
  const flags = CRITERIA.map((c) => ({ ...c, met: !!row[c.key] }));
  const met = flags.filter((f) => f.met).length;

  return (
    <>
      <tr
        className="cursor-pointer hover:bg-gold/[0.04] transition-colors"
        onClick={onToggle}
      >
        <td className="font-semibold text-gold-bright">{row.symbol}</td>
        <td>
          <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold border ${reco.cls}`}>
            {reco.label}
          </span>
        </td>
        <td>
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs text-gray-200 w-8">{met}/8</span>
            <div className="flex gap-0.5">
              {flags.map((f, i) => (
                <span
                  key={i}
                  title={`${f.label}: ${f.met ? "✓" : "✗"}`}
                  className="w-1.5 h-3.5 rounded-sm"
                  style={{ background: f.met ? "#00ff41" : "rgba(90,100,120,0.3)" }}
                />
              ))}
            </div>
          </div>
        </td>
        <td>
          <div className="flex items-center gap-2">
            <span className="font-mono text-[11px] text-gray-300 w-10">{Math.round(row.conviction_score || 0)}</span>
            <div className="w-20"><ConvictionBar score={row.conviction_score || 0} /></div>
          </div>
        </td>
        <td className="font-mono text-gray-200">{row.price ? `₹${row.price.toFixed(2)}` : "—"}</td>
        <td className="font-mono text-gray-300">{row.rsi ? row.rsi.toFixed(1) : "—"}</td>
        <td>
          {row.risk_reward ? (
            <span className="font-mono text-[11px] text-gold">{row.risk_reward}</span>
          ) : <span className="text-muted">—</span>}
        </td>
      </tr>
      {expanded && (
        <tr className="bg-base/40">
          <td colSpan={7} className="!p-0">
            <div className="p-4 border-l-2 border-gold/30 animate-fade-in">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4">
                {flags.map((f) => {
                  const Icon = f.icon;
                  return (
                    <div
                      key={f.key}
                      className={`flex items-start gap-2.5 p-2.5 rounded border ${
                        f.met ? "border-matrix/25 bg-matrix/[0.04]" : "border-red-500/15 bg-red-500/[0.03]"
                      }`}
                    >
                      <Icon size={14} className={f.met ? "text-matrix mt-0.5" : "text-red-400/70 mt-0.5"} />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-[12px] font-semibold text-gray-200">{f.label}</span>
                          {f.met
                            ? <CheckCircle2 size={12} className="text-matrix" />
                            : <XCircle size={12} className="text-red-400/70" />}
                        </div>
                        <p className="text-[11px] text-muted mt-0.5">{f.why}</p>
                      </div>
                    </div>
                  );
                })}
              </div>

              {(row.entry_price || row.stop_loss_price || row.target_1) && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-3">
                  {row.entry_price != null && (
                    <div className="bg-surface-2/40 rounded p-2">
                      <p className="text-[9px] uppercase tracking-wider text-muted">Entry</p>
                      <p className="font-mono text-sm text-gold">₹{row.entry_price.toFixed(2)}</p>
                    </div>
                  )}
                  {row.stop_loss_price != null && (
                    <div className="bg-surface-2/40 rounded p-2">
                      <p className="text-[9px] uppercase tracking-wider text-muted">Stop</p>
                      <p className="font-mono text-sm text-red-400">₹{row.stop_loss_price.toFixed(2)}</p>
                    </div>
                  )}
                  {row.target_1 != null && (
                    <div className="bg-surface-2/40 rounded p-2">
                      <p className="text-[9px] uppercase tracking-wider text-muted">Target 1</p>
                      <p className="font-mono text-sm text-matrix">₹{row.target_1.toFixed(2)}</p>
                    </div>
                  )}
                  {row.target_2 != null && (
                    <div className="bg-surface-2/40 rounded p-2">
                      <p className="text-[9px] uppercase tracking-wider text-muted">Target 2</p>
                      <p className="font-mono text-sm text-matrix">₹{row.target_2.toFixed(2)}</p>
                    </div>
                  )}
                </div>
              )}

              {row.reasoning && (
                <InsightTile
                  icon={<Activity size={14} />}
                  title="Engine Reasoning"
                  body={row.reasoning}
                  tone="default"
                />
              )}
              {row.risk_warning && (
                <div className="mt-2">
                  <InsightTile
                    icon={<AlertTriangle size={14} />}
                    title="Risk Warning"
                    body={row.risk_warning}
                    tone="warning"
                  />
                </div>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

const FILTERS = [
  { id: "all",   label: "All" },
  { id: "buy",   label: "Buy / Recommended" },
  { id: "hold",  label: "Hold" },
  { id: "avoid", label: "Avoid" },
];

export default function Signals() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState(null);
  const [running, setRunning] = useState(false);
  const [filter, setFilter] = useState("all");
  const [query, setQuery] = useState("");
  const [expanded, setExpanded] = useState(null);

  const load = async () => {
    setLoading(true); setErr(null);
    try {
      const res = await fetchCandidates();
      setData(Array.isArray(res) ? res : (res.candidates || []));
    } catch (e) {
      setErr(e.message || "Failed to load signals");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const triggerScan = async () => {
    setRunning(true); setErr(null);
    try {
      await runScan();             // POST → busts cache
      invalidateCache("/scanner"); // belt-and-braces
      await load();
    } catch (e) {
      setErr(e.message || "Scan failed");
    } finally {
      setRunning(false);
    }
  };

  const rows = useMemo(() => {
    if (!data) return [];
    let r = data;
    if (filter === "buy")   r = r.filter((x) => x.recommendation === "BUY" || x.recommendation === "RECOMMENDED");
    if (filter === "hold")  r = r.filter((x) => x.recommendation === "HOLD");
    if (filter === "avoid") r = r.filter((x) => x.recommendation === "AVOID");
    if (query.trim()) {
      const q = query.trim().toUpperCase();
      r = r.filter((x) => x.symbol?.toUpperCase().includes(q));
    }
    return [...r].sort((a, b) => (b.conviction_score || 0) - (a.conviction_score || 0));
  }, [data, filter, query]);

  const summary = useMemo(() => {
    if (!data || !data.length) return null;
    const buys = data.filter((x) => x.recommendation === "BUY" || x.recommendation === "RECOMMENDED").length;
    const holds = data.filter((x) => x.recommendation === "HOLD").length;
    const avoids = data.filter((x) => x.recommendation === "AVOID").length;
    const avgConv = data.reduce((s, x) => s + (x.conviction_score || 0), 0) / data.length;
    return { buys, holds, avoids, avgConv, total: data.length };
  }, [data]);

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gradient font-display">Signal Engine</h1>
          <p className="text-[12px] text-muted mt-0.5">
            8-criteria rule-based signals — every recommendation is auditable. Click any row to see WHY.
          </p>
        </div>
        <button
          onClick={triggerScan}
          disabled={running}
          className="btn-primary flex items-center gap-2"
        >
          <RefreshCw size={13} className={running ? "animate-spin" : ""} />
          {running ? "Scanning…" : "Run Fresh Scan"}
        </button>
      </div>

      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="glass-card p-4">
            <p className="text-[10px] uppercase tracking-widest text-muted">Total Scanned</p>
            <p className="stat-value text-2xl text-gold mt-1">{summary.total}</p>
          </div>
          <div className="glass-card p-4">
            <p className="text-[10px] uppercase tracking-widest text-muted">Buy Signals</p>
            <p className="stat-value text-2xl text-matrix mt-1">{summary.buys}</p>
          </div>
          <div className="glass-card p-4">
            <p className="text-[10px] uppercase tracking-widest text-muted">Hold</p>
            <p className="stat-value text-2xl text-amber-400 mt-1">{summary.holds}</p>
          </div>
          <div className="glass-card p-4">
            <p className="text-[10px] uppercase tracking-widest text-muted">Avg Conviction</p>
            <p className="stat-value text-2xl text-gold-bright mt-1">{summary.avgConv.toFixed(1)}</p>
          </div>
        </div>
      )}

      <Card
        title="Live Signals"
        action={
          <div className="flex items-center gap-2">
            <div className="relative">
              <Search size={11} className="absolute left-2 top-1/2 -translate-y-1/2 text-muted" />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Filter symbol…"
                className="bg-base/80 border border-gold/15 rounded pl-6 pr-2 py-1 text-[11px] font-mono text-gray-200 outline-none focus:border-gold/40 w-32"
              />
            </div>
            <div className="flex items-center gap-1 bg-surface-2/50 rounded p-0.5">
              {FILTERS.map((f) => (
                <button
                  key={f.id}
                  onClick={() => setFilter(f.id)}
                  className={`px-2 py-0.5 text-[10px] font-semibold rounded transition-all ${
                    filter === f.id
                      ? "bg-gold/15 text-gold"
                      : "text-muted hover:text-gold-bright"
                  }`}
                >
                  {f.label}
                </button>
              ))}
            </div>
          </div>
        }
        noPad
      >
        {loading ? (
          <Loader />
        ) : err ? (
          <div className="p-4"><ErrorMsg message={err} /></div>
        ) : !rows.length ? (
          <EmptyState
            icon={<Filter size={36} />}
            title="No signals match"
            message="Try changing the filter or running a fresh scan."
          />
        ) : (
          <div className="overflow-auto max-h-[70vh]">
            <table className="pro-table w-full text-left">
              <thead>
                <tr>
                  <th>Symbol</th>
                  <th>Reco</th>
                  <th>Criteria Met</th>
                  <th>Conviction</th>
                  <th>Price</th>
                  <th>RSI</th>
                  <th>R:R</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <SignalRow
                    key={row.id || row.symbol}
                    row={row}
                    expanded={expanded === (row.id || row.symbol)}
                    onToggle={() =>
                      setExpanded(expanded === (row.id || row.symbol) ? null : (row.id || row.symbol))
                    }
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Card title="How To Read These Signals">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-[12px] text-gray-300">
          <div>
            <p className="font-semibold text-gold-bright mb-1">7–8 of 8 → BUY</p>
            <p className="text-muted">High-conviction setup. Trend, momentum, entry trigger and trend filter all align.</p>
          </div>
          <div>
            <p className="font-semibold text-amber-400 mb-1">3–6 of 8 → HOLD</p>
            <p className="text-muted">Mixed signals. Wait for more criteria to align before risking capital.</p>
          </div>
          <div>
            <p className="font-semibold text-red-400 mb-1">0–2 of 8 → AVOID</p>
            <p className="text-muted">Trend or structure broken. Don't try to catch falling knives.</p>
          </div>
        </div>
      </Card>
    </div>
  );
}
