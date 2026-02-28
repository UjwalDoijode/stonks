import { useState, useEffect, useRef, useCallback } from "react";
import { Card, Badge, Loader, ErrorMsg, SkeletonCard } from "../components/UI";
import StockDetailModal from "../components/StockDetailModal";
import {
  runScan, fetchLatestScan, fetchRegime, fetchSentiment,
  searchStocks, fetchLivePrices, fetchSectors, fetchWatchlist, fetchGeoRisk,
  fetchCommodityPrices,
} from "../api";
import {
  Search, RefreshCw, TrendingUp, TrendingDown, ChevronDown, ChevronUp,
  Shield, AlertTriangle, Target, Crosshair, BarChart3, Zap, Award, Eye,
  Coins,
} from "lucide-react";

/* ─── Sentiment Bar ──────────────────────────────────── */
function SentimentGauge({ score }) {
  const clamp = Math.max(0, Math.min(100, score));
  const color =
    clamp >= 75 ? "bg-emerald-500" : clamp >= 55 ? "bg-amber-500" : clamp >= 40 ? "bg-gray-400" : "bg-red-500";
  return (
    <div className="w-full bg-gray-800/60 rounded-full h-2 overflow-hidden">
      <div className={`h-full rounded-full transition-all duration-700 ${color}`} style={{ width: `${clamp}%` }} />
    </div>
  );
}

/* ─── Sentiment Card ─────────────────────────────────── */
const SENTIMENT_COLORS = {
  BULLISH:  { bg: "bg-emerald-500/8", border: "border-emerald-500/30", text: "text-emerald-400", icon: "🟢" },
  CAUTIOUS: { bg: "bg-amber-500/8",   border: "border-amber-500/30",   text: "text-amber-400",   icon: "🟡" },
  NEUTRAL:  { bg: "bg-gray-500/8",    border: "border-gray-500/30",    text: "text-gray-300",    icon: "⚪" },
  BEARISH:  { bg: "bg-red-500/8",     border: "border-red-500/30",     text: "text-red-400",     icon: "🔴" },
};

function SentimentCard({ sentiment }) {
  if (!sentiment) return null;
  const s = SENTIMENT_COLORS[sentiment.overall_sentiment] || SENTIMENT_COLORS.NEUTRAL;
  const components = [
    { label: "NIFTY Trend", value: sentiment.nifty_trend, score: sentiment.nifty_trend_score },
    { label: "VIX", value: sentiment.vix_status, score: sentiment.vix_score },
    { label: "Breadth", value: sentiment.breadth_status, score: sentiment.breadth_score },
    { label: "Global", value: sentiment.global_status, score: sentiment.global_score },
    { label: "FII/DII", value: sentiment.fii_proxy_status, score: sentiment.fii_proxy_score },
  ];
  return (
    <div className={`glass-card overflow-hidden ${s.border} border animate-fade-in`}>
      <div className="p-5">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <span className="text-2xl">{s.icon}</span>
            <div>
              <h3 className="text-sm font-bold">Market Sentiment</h3>
              <span className={`text-[11px] font-semibold uppercase tracking-wider ${s.text}`}>{sentiment.overall_sentiment}</span>
            </div>
          </div>
          <div className="text-right">
            <div className={`text-3xl font-bold font-mono ${s.text}`}>{sentiment.sentiment_score}</div>
            <div className="text-[10px] text-muted">/ 100</div>
          </div>
        </div>
        <SentimentGauge score={sentiment.sentiment_score} />
        <p className="text-xs text-muted mt-3 leading-relaxed">{sentiment.summary}</p>
        <div className="grid grid-cols-5 gap-2 mt-4">
          {components.map((c) => {
            const cColor = c.score >= 65 ? "text-emerald-400" : c.score >= 40 ? "text-amber-400" : "text-red-400";
            return (
              <div key={c.label} className="text-center bg-base/60 rounded-lg p-2.5 border border-border/30">
                <div className="text-[9px] text-muted uppercase tracking-wider font-medium">{c.label}</div>
                <div className={`text-sm font-bold font-mono mt-0.5 ${cColor}`}>{c.score}</div>
                <div className="text-[10px] text-muted truncate mt-0.5" title={c.value}>{c.value}</div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

/* ─── Geopolitical Risk Card ─────────────────────────── */
const GEO_RISK_STYLES = {
  EXTREME: { bg: "bg-red-500/10", border: "border-red-500/40", text: "text-red-400", icon: AlertTriangle },
  HIGH:    { bg: "bg-orange-500/10", border: "border-orange-500/40", text: "text-orange-400", icon: Shield },
  MODERATE:{ bg: "bg-amber-500/10", border: "border-amber-500/40", text: "text-amber-400", icon: Shield },
  LOW:     { bg: "bg-emerald-500/10", border: "border-emerald-500/40", text: "text-emerald-400", icon: Shield },
};

function GeoRiskCard({ geoRisk }) {
  if (!geoRisk) return null;
  const style = GEO_RISK_STYLES[geoRisk.risk_level] || GEO_RISK_STYLES.LOW;
  const Icon = style.icon;
  return (
    <div className={`glass-card overflow-hidden ${style.border} border animate-fade-in`}>
      <div className="p-5">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${style.bg}`}>
              <Icon size={18} className={style.text} />
            </div>
            <div>
              <h3 className="text-sm font-bold">Geopolitical & Macro Risk</h3>
              <span className={`text-[11px] font-semibold uppercase tracking-wider ${style.text}`}>
                {geoRisk.risk_level} RISK
              </span>
            </div>
          </div>
          <div className="text-right">
            <div className={`text-3xl font-bold font-mono ${style.text}`}>{geoRisk.risk_score}</div>
            <div className="text-[10px] text-muted">/ 100</div>
          </div>
        </div>
        <div className="w-full bg-gray-800/60 rounded-full h-2 overflow-hidden mb-3">
          <div
            className={`h-full rounded-full transition-all duration-700 ${
              geoRisk.risk_score >= 70 ? "bg-red-500" : geoRisk.risk_score >= 50 ? "bg-orange-500" :
              geoRisk.risk_score >= 30 ? "bg-amber-500" : "bg-emerald-500"
            }`}
            style={{ width: `${geoRisk.risk_score}%` }}
          />
        </div>
        <div className="flex gap-3 mb-3 flex-wrap">
          {[
            { label: "VIX Fear", active: geoRisk.vix_fear },
            { label: "Safe Haven", active: geoRisk.safe_haven_flow },
            { label: "Oil Shock", active: geoRisk.oil_shock },
            { label: "USD Stress", active: geoRisk.currency_stress },
          ].map(({ label, active }) => (
            <span key={label} className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
              active ? "bg-red-500/15 text-red-400 border-red-500/30" : "bg-gray-800/40 text-gray-600 border-gray-700/30"
            }`}>
              {active ? "⚠️" : "✓"} {label}
            </span>
          ))}
        </div>
        {/* Active Conflicts Section */}
        {geoRisk.active_conflicts?.length > 0 && (
          <div className="mb-3">
            <span className="text-[10px] text-muted uppercase tracking-wider font-semibold block mb-1.5">Active Conflicts</span>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
              {geoRisk.active_conflicts.map((c, i) => (
                <div key={i} className={`px-2.5 py-1.5 rounded-lg text-[11px] border ${
                  c.severity === "HIGH" ? "bg-red-500/10 border-red-500/25 text-red-300" :
                  c.severity === "MODERATE" ? "bg-orange-500/10 border-orange-500/25 text-orange-300" :
                  "bg-amber-500/10 border-amber-500/25 text-amber-300"
                }`}>
                  <span className="font-bold">{c.name}</span>
                  <span className="text-gray-500 ml-1.5">({c.status})</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Risk Headlines from News */}
        {geoRisk.risk_headlines?.length > 0 && (
          <div className="mb-3">
            <span className="text-[10px] text-muted uppercase tracking-wider font-semibold block mb-1.5">
              Live Risk Headlines ({geoRisk.risk_headlines.length})
            </span>
            <div className="space-y-1 max-h-28 overflow-y-auto pr-1">
              {geoRisk.risk_headlines.slice(0, 8).map((h, i) => (
                <div key={i} className="flex items-start gap-1.5 text-[11px] leading-snug">
                  <span className="text-red-500/70 mt-0.5 shrink-0">•</span>
                  <span className="text-gray-400">{h.title || h}</span>
                  {h.risk_score && (
                    <span className="text-[9px] text-red-400/60 font-mono shrink-0 ml-auto">{h.risk_score}</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Existing events */}
        <div className="space-y-1.5 max-h-32 overflow-y-auto">
          {geoRisk.events?.map((event, i) => (
            <p key={i} className="text-xs text-muted leading-relaxed">{event}</p>
          ))}
        </div>
        <div className="mt-3 pt-3 border-t border-border/30 flex items-center justify-between">
          <div>
            <span className="text-[10px] text-muted uppercase tracking-wider">Recommended Bias: </span>
            <span className={`text-[11px] font-bold ${
              geoRisk.defense_bias === "CASH" ? "text-red-400" :
              geoRisk.defense_bias === "DEFENSIVE" ? "text-amber-400" :
              geoRisk.defense_bias === "RISK_ON" ? "text-emerald-400" : "text-gray-300"
            }`}>
              {geoRisk.defense_bias}
            </span>
          </div>
          {geoRisk.news_risk_score > 0 && (
            <span className="text-[10px] text-muted font-mono">
              News Risk: <span className={`font-bold ${
                geoRisk.news_risk_score >= 60 ? "text-red-400" : geoRisk.news_risk_score >= 30 ? "text-amber-400" : "text-emerald-400"
              }`}>{geoRisk.news_risk_score}/100</span>
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

/* ─── Recommendation Badge ───────────────────────────── */
function RecommendationBadge({ rec }) {
  const cfg = {
    RECOMMENDED: { bg: "bg-blue-500/15", text: "text-blue-400", border: "border-blue-500/30", icon: "⭐" },
    BUY:   { bg: "bg-emerald-500/15", text: "text-emerald-400", border: "border-emerald-500/30", icon: "🟢" },
    AVOID: { bg: "bg-red-500/15",     text: "text-red-400",     border: "border-red-500/30", icon: "🔴" },
    HOLD:  { bg: "bg-gray-500/15",    text: "text-gray-400",    border: "border-gray-500/30", icon: "⏸️" },
  };
  const c = cfg[rec] || cfg.HOLD;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold border uppercase tracking-wider ${c.bg} ${c.text} ${c.border}`}>
      <span>{c.icon}</span> {rec}
    </span>
  );
}

/* ─── Conviction Badge ───────────────────────────────── */
function ConvictionBadge({ conviction, score }) {
  const colors = {
    HIGH: "text-emerald-400 bg-emerald-500/10 border-emerald-500/30",
    MEDIUM: "text-amber-400 bg-amber-500/10 border-amber-500/30",
    LOW: "text-gray-400 bg-gray-500/10 border-gray-500/30",
  };
  return (
    <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold border ${colors[conviction] || colors.LOW}`}>
      {score?.toFixed(0)}%
    </span>
  );
}

/* ─── Criteria indicator ─────────────────────────────── */
function CriteriaDots({ count }) {
  return (
    <div className="flex gap-0.5">
      {[...Array(8)].map((_, i) => (
        <div key={i} className={`w-1.5 h-1.5 rounded-full transition-colors ${i < count ? "bg-emerald-400" : "bg-gray-700"}`} />
      ))}
    </div>
  );
}

/* ─── Earnings Badge ─────────────────────────────────── */
function EarningsBadge({ momentum, score }) {
  const cfg = {
    STRONG:   { color: "text-emerald-400", bg: "bg-emerald-500/10" },
    POSITIVE: { color: "text-green-400", bg: "bg-green-500/10" },
    NEUTRAL:  { color: "text-gray-400", bg: "bg-gray-500/10" },
    WEAK:     { color: "text-amber-400", bg: "bg-amber-500/10" },
    NEGATIVE: { color: "text-red-400", bg: "bg-red-500/10" },
  };
  const c = cfg[momentum] || cfg.NEUTRAL;
  return (
    <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${c.color} ${c.bg}`} title={`Earnings Score: ${score}`}>
      {momentum}
    </span>
  );
}

/* ─── Row background ─────────────────────────────────── */
function rowBgClass(rec) {
  if (rec === "RECOMMENDED") return "bg-blue-500/[0.04] hover:bg-blue-500/[0.08] border-l-2 border-l-blue-500/60";
  if (rec === "BUY") return "bg-emerald-500/[0.03] hover:bg-emerald-500/[0.08] border-l-2 border-l-emerald-500/50";
  if (rec === "AVOID") return "bg-red-500/[0.03] hover:bg-red-500/[0.08] border-l-2 border-l-red-500/50";
  return "hover:bg-white/[0.03] border-l-2 border-l-transparent";
}

/* ─── Sector Heatmap ─────────────────────────────────── */
function SectorHeatmap({ sectors }) {
  if (!sectors || sectors.length === 0) return null;
  const maxAbs = Math.max(...sectors.map((s) => Math.abs(s.change_1d)), 1);
  return (
    <Card title="Sector Heatmap">
      <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 gap-2">
        {sectors.map((s) => {
          const intensity = Math.min(Math.abs(s.change_1d) / maxAbs, 1);
          const isPositive = s.change_1d >= 0;
          const bg = isPositive
            ? `rgba(16, 185, 129, ${0.05 + intensity * 0.35})`
            : `rgba(239, 68, 68, ${0.05 + intensity * 0.35})`;
          const textColor = isPositive ? "text-emerald-400" : "text-red-400";
          return (
            <div key={s.sector} className="rounded-lg p-3 text-center border border-border/30 hover:border-border/60 transition-all cursor-default" style={{ background: bg }}>
              <div className="text-[10px] font-bold text-gray-200 uppercase tracking-wider">{s.sector}</div>
              <div className={`text-lg font-bold font-mono ${textColor}`}>{s.change_1d >= 0 ? "+" : ""}{s.change_1d}%</div>
              <div className="text-[10px] text-muted mt-0.5 font-mono">1W: {s.change_1w >= 0 ? "+" : ""}{s.change_1w}%</div>
              <div className="text-[10px] text-muted truncate">{s.top_stock} ({s.top_stock_change >= 0 ? "+" : ""}{s.top_stock_change}%)</div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}

/* ─── Commodities Ticker ─────────────────────────────── */
function CommoditiesTicker({ commodities }) {
  if (!commodities || commodities.length === 0) return null;

  const cfg = {
    "Gold":         { icon: "🥇", border: "border-yellow-500/20", label: "text-yellow-400" },
    "Silver":       { icon: "🥈", border: "border-gray-400/20",   label: "text-gray-300" },
    "Crude Oil":    { icon: "🛢️", border: "border-orange-500/20", label: "text-orange-400" },
    "Brent Crude":  { icon: "🛢️", border: "border-orange-500/20", label: "text-orange-300" },
    "Natural Gas":  { icon: "🔥", border: "border-blue-500/20",   label: "text-blue-400" },
    "India VIX":    { icon: "⚡", border: "border-purple-500/20", label: "text-purple-400" },
    "USD/INR":      { icon: "💱", border: "border-green-500/20",  label: "text-green-400" },
    "Inflation":    { icon: "📈", border: "border-pink-500/20",   label: "text-pink-400" },
    "Gold ETF":     { icon: "🏅", border: "border-yellow-500/20", label: "text-yellow-300" },
    "Silver ETF":   { icon: "🪙", border: "border-gray-400/20",   label: "text-gray-300" },
  };

  // VIX: red when high, green when low (inverse of normal)
  const getVixColor = (price) =>
    price >= 25 ? "text-red-400" : price >= 18 ? "text-amber-400" : "text-emerald-400";

  // Inflation (bond yield): higher = more inflation pressure = red
  const getInflationColor = (price) =>
    price >= 7.5 ? "text-red-400" : price >= 6.5 ? "text-amber-400" : "text-emerald-400";

  return (
    <div className="flex flex-wrap gap-2.5 pb-2">
      {commodities.map((c) => {
        const style = cfg[c.name] || { icon: "📊", border: "border-border/30", label: "text-gray-400" };
        const isVix = c.type === "vix";
        const isMacro = c.type === "macro";
        const isForex = c.type === "forex";
        const isSpecial = isVix || isMacro || isForex;

        // For VIX and inflation, rising is BAD (show red), falling is GOOD (show green)
        // For forex (USD/INR), rising rupee weakness = red
        const changeColor = (isVix || isMacro || isForex)
          ? (c.change_pct >= 0 ? "text-red-400" : "text-emerald-400")
          : (c.change_pct >= 0 ? "text-emerald-400" : "text-red-400");
        const ChangIcon = c.change_pct >= 0 ? TrendingUp : TrendingDown;

        const priceColor = isVix
          ? getVixColor(c.price)
          : isMacro
          ? getInflationColor(c.price)
          : isForex
          ? "text-green-300"
          : "text-gray-100";

        return (
          <div key={c.symbol}
            className={`flex-shrink-0 glass-card px-4 py-2.5 min-w-[140px] border ${style.border}`}>
            <div className="flex items-center gap-1.5 mb-0.5">
              <span className="text-sm">{style.icon}</span>
              <span className={`text-[10px] font-bold uppercase tracking-wider ${style.label}`}>{c.name}</span>
              {c.type === "etf" && (
                <span className="text-[8px] px-1 py-0.5 rounded bg-blue-500/10 text-blue-400 font-bold border border-blue-500/20">ETF</span>
              )}
              {isVix && (
                <span className={`text-[8px] px-1 py-0.5 rounded font-bold border ${
                  c.price >= 25 ? "bg-red-500/10 text-red-400 border-red-500/20"
                  : c.price >= 18 ? "bg-amber-500/10 text-amber-400 border-amber-500/20"
                  : "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                }`}>
                  {c.price >= 25 ? "FEAR" : c.price >= 18 ? "CAUTION" : "CALM"}
                </span>
              )}
              {isMacro && (
                <span className="text-[8px] px-1 py-0.5 rounded bg-pink-500/10 text-pink-400 font-bold border border-pink-500/20">10Y</span>
              )}
              {isForex && (
                <span className="text-[8px] px-1 py-0.5 rounded bg-green-500/10 text-green-400 font-bold border border-green-500/20">FX</span>
              )}
            </div>
            <div className={`text-sm font-bold font-mono mt-0.5 ${priceColor}`}>
              {c.currency}{c.price.toLocaleString(
                c.currency === "₹" ? "en-IN" : "en-US",
                { maximumFractionDigits: isSpecial ? 2 : 2 }
              )}{c.unit && !isSpecial && c.type !== "etf"
                ? <span className="text-[9px] text-gray-600 font-normal ml-0.5">/{c.unit}</span>
                : isSpecial ? <span className="text-[9px] text-gray-600 font-normal ml-0.5">{c.unit}</span>
                : null}
            </div>
            {isMacro ? (
              <div className="text-xs font-medium font-mono flex items-center gap-0.5 text-gray-500">
                <span className="text-[10px]">{c.last_updated}</span>
              </div>
            ) : (
              <div className={`text-xs font-medium font-mono flex items-center gap-0.5 ${changeColor}`}>
                <ChangIcon size={10} />
                {c.change_pct >= 0 ? "+" : ""}{c.change_pct}%
                {isVix && c.change_pct > 0 && <span className="text-[9px] ml-0.5 text-red-400/70">↑risk</span>}
                {isVix && c.change_pct < 0 && <span className="text-[9px] ml-0.5 text-emerald-400/70">↓risk</span>}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

/* ─── Live Price Ticker ──────────────────────────────── */
function LivePriceTicker({ prices, onStockClick }) {
  if (!prices || prices.length === 0) return null;
  return (
    <div className="flex gap-2.5 overflow-x-auto pb-2 scrollbar-thin">
      {prices.map((p) => (
        <button key={p.symbol} onClick={() => onStockClick(p.symbol)}
          className="flex-shrink-0 glass-card px-3.5 py-2 hover:border-blue-500/30 transition-colors min-w-[120px]">
          <div className="text-[10px] font-bold text-gray-200 uppercase tracking-wider">{p.symbol}</div>
          <div className="text-sm font-bold font-mono mt-0.5">₹{p.price}</div>
          <div className={`text-xs font-medium font-mono flex items-center gap-0.5 ${p.change_pct >= 0 ? "text-emerald-400" : "text-red-400"}`}>
            {p.change_pct >= 0 ? <TrendingUp size={10} /> : <TrendingDown size={10} />}
            {p.change_pct >= 0 ? "+" : ""}{p.change_pct}%
          </div>
        </button>
      ))}
    </div>
  );
}

/* ─── Search Bar ─────────────────────────────────────── */
function SearchBar({ onSelect }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const debounceRef = useRef(null);
  const wrapperRef = useRef(null);

  useEffect(() => {
    function handleClick(e) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target)) setShowDropdown(false);
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const handleSearch = useCallback((q) => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (q.length < 1) { setResults([]); setShowDropdown(false); return; }
    debounceRef.current = setTimeout(async () => {
      setSearching(true);
      try {
        const res = await searchStocks(q);
        setResults(res);
        setShowDropdown(true);
      } catch { setResults([]); } finally { setSearching(false); }
    }, 300);
  }, []);

  return (
    <div className="relative" ref={wrapperRef}>
      <div className="flex items-center glass-card px-4 py-2.5 focus-within:border-blue-500/40 transition-colors">
        <Search size={16} className="text-muted mr-3 flex-shrink-0" />
        <input type="text" value={query}
          onChange={(e) => { setQuery(e.target.value); handleSearch(e.target.value); }}
          placeholder="Search any stock (e.g. RELIANCE, TCS)..."
          className="bg-transparent text-sm text-gray-200 placeholder-gray-600 outline-none flex-1" />
        {searching && <div className="animate-spin h-4 w-4 border-2 border-transparent border-t-blue-400 rounded-full" />}
      </div>
      {showDropdown && results.length > 0 && (
        <div className="absolute top-full left-0 right-0 mt-1 glass-card shadow-2xl z-50 max-h-72 overflow-y-auto">
          {results.map((r) => (
            <button key={r.symbol} onClick={() => { setQuery(""); setShowDropdown(false); setResults([]); onSelect(r.clean_symbol); }}
              className="w-full flex items-center justify-between px-4 py-2.5 hover:bg-white/[0.04] border-b border-border/30 last:border-0 transition-colors">
              <div className="text-left">
                <span className="text-sm font-bold text-gray-200">{r.clean_symbol}</span>
                <span className="text-xs text-muted ml-2">{r.name}</span>
                {r.sector && <span className="text-[10px] text-blue-400 ml-2">({r.sector})</span>}
              </div>
              <div className="text-right">
                <div className="text-sm font-mono font-medium">₹{r.price}</div>
                <div className={`text-xs font-mono ${r.change_pct >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                  {r.change_pct >= 0 ? "+" : ""}{r.change_pct}%
                </div>
              </div>
            </button>
          ))}
        </div>
      )}
      {showDropdown && results.length === 0 && query.length > 0 && !searching && (
        <div className="absolute top-full left-0 right-0 mt-1 glass-card shadow-2xl z-50 p-4 text-sm text-muted text-center">
          No stocks found for "{query}"
        </div>
      )}
    </div>
  );
}

/* ─── Reasoning Tooltip ──────────────────────────────── */
function ReasoningPreview({ reasoning, primaryReason }) {
  const [expanded, setExpanded] = useState(false);
  const display = primaryReason || reasoning;
  if (!display) return <span className="text-gray-600 text-xs">—</span>;

  const parts = reasoning ? reasoning.split(" | ") : [display];
  const summary = primaryReason || parts[0];

  return (
    <div className="text-left">
      <p className="text-xs text-muted">{summary}</p>
      {expanded && (
        <div className="mt-1 space-y-0.5">
          {parts.slice(primaryReason ? 0 : 1).map((p, i) => (
            <p key={i} className="text-[11px] text-gray-600">{p}</p>
          ))}
        </div>
      )}
      <button onClick={(e) => { e.stopPropagation(); setExpanded(!expanded); }}
        className="text-[10px] text-blue-400 hover:text-blue-300 mt-0.5 flex items-center gap-0.5 font-medium">
        {expanded ? <><ChevronUp size={10} /> Less</> : <><ChevronDown size={10} /> Details</>}
      </button>
    </div>
  );
}

/* ─── Trade Setup Mini Card ──────────────────────────── */
function TradeSetupMini({ stock }) {
  if (!stock.entry_price && !stock.target_1) return null;
  const entry = stock.entry_price || stock.prev_high;
  const sl = stock.stop_loss_price || stock.swing_low;
  const t1 = stock.target_1;
  const t2 = stock.target_2;
  if (!entry || !sl) return null;
  return (
    <div className="flex gap-2 text-[10px] font-mono">
      <span className="text-amber-400" title="Entry">E:₹{entry?.toFixed(0)}</span>
      <span className="text-red-400" title="Stop Loss">SL:₹{sl?.toFixed(0)}</span>
      {t1 && <span className="text-emerald-400" title="Target 1">T1:₹{t1?.toFixed(0)}</span>}
      {t2 && <span className="text-blue-400" title="Target 2">T2:₹{t2?.toFixed(0)}</span>}
    </div>
  );
}

/* ─── Stock Table (Enhanced) ─────────────────────────── */
function StockTable({ stocks, showReasoning = true, showTargets = true, onStockClick }) {
  if (stocks.length === 0) return <p className="text-muted text-sm py-4 text-center">No stocks in this category.</p>;
  return (
    <div className="overflow-x-auto">
      <table className="pro-table w-full">
        <thead>
          <tr>
            <th className="text-left">Symbol</th>
            <th className="text-center">Signal</th>
            <th className="text-center">Score</th>
            <th className="text-right">Price</th>
            {showTargets && <>
              <th className="text-right">Entry</th>
              <th className="text-right">SL</th>
              <th className="text-right">Target</th>
              <th className="text-center">Risk%</th>
              <th className="text-center">Reward%</th>
              <th className="text-center">R:R</th>
            </>}
            <th className="text-center">Earnings</th>
            <th className="text-right">RSI</th>
            <th className="text-right">CCI</th>
            <th className="text-center">ST</th>
            {showReasoning && <th className="text-left min-w-[200px]">Analysis</th>}
          </tr>
        </thead>
        <tbody>
          {stocks.map((s) => (
            <tr key={s.id} className={`cursor-pointer transition-colors ${rowBgClass(s.recommendation)}`}
              onClick={() => onStockClick(s.symbol)}>
              <td>
                <div className="flex flex-col">
                  <span className={`font-bold ${
                    s.recommendation === "RECOMMENDED" ? "text-blue-400" :
                    s.recommendation === "BUY" ? "text-emerald-400" :
                    s.recommendation === "AVOID" ? "text-red-400" : "text-gray-200"
                  }`}>{s.symbol}</span>
                  {s.category_tag && (
                    <span className="text-[9px] text-muted truncate max-w-[100px]">{s.category_tag}</span>
                  )}
                </div>
              </td>
              <td className="text-center">
                <div className="flex flex-col items-center gap-1">
                  <RecommendationBadge rec={s.recommendation} />
                  <ConvictionBadge conviction={s.conviction} score={s.conviction_score} />
                </div>
              </td>
              <td className="text-center"><CriteriaDots count={s.criteria_met} /></td>
              <td className="text-right font-mono font-medium">₹{s.price?.toFixed(2)}</td>
              {showTargets && <>
                <td className="text-right font-mono text-amber-400">
                  ₹{(s.entry_price || s.prev_high)?.toFixed(1)}
                </td>
                <td className="text-right font-mono text-red-400">
                  ₹{(s.stop_loss_price || s.swing_low)?.toFixed(1)}
                </td>
                <td className="text-right font-mono text-emerald-400">
                  {s.target_2 ? `₹${s.target_2?.toFixed(1)}` : s.target_1 ? `₹${s.target_1?.toFixed(1)}` : "—"}
                </td>
                <td className="text-center">
                  {s.risk_pct ? (
                    <span className="text-red-400 font-mono text-xs">-{s.risk_pct?.toFixed(1)}%</span>
                  ) : "—"}
                </td>
                <td className="text-center">
                  {s.reward_pct ? (
                    <span className="text-emerald-400 font-mono text-xs">+{s.reward_pct?.toFixed(1)}%</span>
                  ) : "—"}
                </td>
                <td className="text-center">
                  {s.risk_reward ? (
                    <span className="text-blue-400 font-mono text-xs font-bold">{s.risk_reward}</span>
                  ) : "—"}
                </td>
              </>}
              <td className="text-center">
                <EarningsBadge momentum={s.earnings_momentum} score={s.earnings_score} />
              </td>
              <td className="text-right font-mono">{s.rsi?.toFixed(1)}</td>
              <td className="text-right font-mono">{s.cci?.toFixed(0) ?? '—'}</td>
              <td className="text-center">
                {s.supertrend_bullish != null ? (
                  <span className={`text-[10px] font-bold ${s.supertrend_bullish ? 'text-emerald-400' : 'text-red-400'}`}>
                    {s.supertrend_bullish ? '▲' : '▼'}
                  </span>
                ) : '—'}
              </td>
              {showReasoning && (
                <td><ReasoningPreview reasoning={s.reasoning} primaryReason={s.primary_reason} /></td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ─── Recommended Stock Card (Premium Display) ───────── */
function RecommendedStockCard({ stock, onStockClick }) {
  const entry = stock.entry_price || stock.prev_high;
  const sl = stock.stop_loss_price || stock.swing_low;
  return (
    <div
      onClick={() => onStockClick(stock.symbol)}
      className="glass-card p-4 cursor-pointer hover:border-blue-500/40 transition-all group animate-fade-in"
    >
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-lg font-bold text-blue-400">{stock.symbol}</span>
            <RecommendationBadge rec={stock.recommendation} />
          </div>
          {stock.category_tag && (
            <span className="text-[10px] text-muted mt-0.5 block">{stock.category_tag}</span>
          )}
        </div>
        <div className="text-right">
          <div className="text-lg font-bold font-mono">₹{stock.price?.toFixed(2)}</div>
          <ConvictionBadge conviction={stock.conviction} score={stock.conviction_score} />
        </div>
      </div>

      {/* Trade Setup */}
      <div className="grid grid-cols-3 gap-2 mb-3">
        <div className="bg-base/60 rounded-lg p-2 border border-border/30 text-center">
          <div className="text-[9px] text-muted uppercase tracking-wider">Entry</div>
          <div className="text-sm font-bold font-mono text-amber-400">₹{entry?.toFixed(1)}</div>
        </div>
        <div className="bg-base/60 rounded-lg p-2 border border-red-500/20 text-center">
          <div className="text-[9px] text-muted uppercase tracking-wider">Stop Loss</div>
          <div className="text-sm font-bold font-mono text-red-400">₹{sl?.toFixed(1)}</div>
          {stock.risk_pct > 0 && <div className="text-[9px] text-red-400/70 font-mono">-{stock.risk_pct?.toFixed(1)}%</div>}
        </div>
        <div className="bg-base/60 rounded-lg p-2 border border-emerald-500/20 text-center">
          <div className="text-[9px] text-muted uppercase tracking-wider">Target</div>
          <div className="text-sm font-bold font-mono text-emerald-400">₹{stock.target_2?.toFixed(1) || "—"}</div>
          {stock.reward_pct > 0 && <div className="text-[9px] text-emerald-400/70 font-mono">+{stock.reward_pct?.toFixed(1)}%</div>}
        </div>
      </div>

      {/* Multiple targets row */}
      {stock.target_1 && (
        <div className="flex gap-2 mb-3 text-[10px]">
          <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 font-mono">
            T1: ₹{stock.target_1?.toFixed(0)} (+{((stock.target_1 - stock.price) / stock.price * 100).toFixed(1)}%)
          </span>
          {stock.target_2 && (
            <span className="px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 font-mono">
              T2: ₹{stock.target_2?.toFixed(0)} (+{((stock.target_2 - stock.price) / stock.price * 100).toFixed(1)}%)
            </span>
          )}
          {stock.target_3 && (
            <span className="px-2 py-0.5 rounded bg-purple-500/10 text-purple-400 font-mono">
              T3: ₹{stock.target_3?.toFixed(0)} (+{((stock.target_3 - stock.price) / stock.price * 100).toFixed(1)}%)
            </span>
          )}
          {stock.risk_reward && (
            <span className="px-2 py-0.5 rounded bg-gray-500/10 text-gray-300 font-mono font-bold">
              R:R {stock.risk_reward}
            </span>
          )}
        </div>
      )}

      {/* Analysis row */}
      <div className="flex gap-2 items-center flex-wrap mb-2">
        <EarningsBadge momentum={stock.earnings_momentum} score={stock.earnings_score} />
        <CriteriaDots count={stock.criteria_met} />
        <span className="text-[10px] text-muted font-mono">RSI: {stock.rsi?.toFixed(0)}</span>
        <span className="text-[10px] text-muted font-mono">CCI: {stock.cci?.toFixed(0) ?? '—'}</span>
        {stock.supertrend_bullish != null && (
          <span className={`text-[10px] font-mono font-bold ${stock.supertrend_bullish ? 'text-emerald-400' : 'text-red-400'}`}>
            ST {stock.supertrend_bullish ? '▲' : '▼'}
          </span>
        )}
        {stock.risk_warning && (
          <span className="text-[10px] text-amber-400 flex items-center gap-0.5">
            <AlertTriangle size={10} /> {stock.risk_warning}
          </span>
        )}
      </div>

      {/* Primary Reason */}
      <p className="text-xs text-muted leading-relaxed">{stock.primary_reason || stock.reasoning?.split(" | ")[0]}</p>
      {stock.quarterly_trend && (
        <p className="text-[11px] text-gray-600 mt-1">{stock.quarterly_trend}</p>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════
   Main Scanner Component
   ═══════════════════════════════════════════════════════ */
export default function Scanner() {
  const [results, setResults] = useState([]);
  const [regime, setRegime] = useState(null);
  const [sentiment, setSentiment] = useState(null);
  const [geoRisk, setGeoRisk] = useState(null);
  const [sectors, setSectors] = useState([]);
  const [livePrices, setLivePrices] = useState([]);
  const [commodities, setCommodities] = useState([]);
  const [watchlist, setWatchlist] = useState([]);
  const [loading, setLoading] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [scanTime, setScanTime] = useState(null);
  const [error, setError] = useState(null);
  const [selectedStock, setSelectedStock] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [lastRefresh, setLastRefresh] = useState(null);
  const refreshRef = useRef(null);

  // Initial load
  useEffect(() => {
    setLoading(true);
    Promise.all([
      fetchLatestScan(),
      fetchRegime(),
      fetchSentiment(),
      fetchGeoRisk().catch(() => null),
      fetchSectors().catch(() => []),
      fetchWatchlist().catch(() => []),
      fetchCommodityPrices().catch(() => []),
    ])
      .then(([scans, reg, sent, geo, sec, wl, comm]) => {
        setResults(scans);
        setRegime(reg);
        setSentiment(sent);
        setGeoRisk(geo);
        setSectors(sec);
        setWatchlist(wl);
        setCommodities(comm);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  // Live price auto-refresh
  const refreshLivePrices = useCallback(async () => {
    try {
      const topSymbols = [...new Set(
        results
          .filter((r) => r.recommendation === "RECOMMENDED" || r.recommendation === "BUY")
          .map((r) => r.symbol)
      )].join(",");
      if (topSymbols) {
        const prices = await fetchLivePrices(topSymbols);
        setLivePrices(prices);
        setLastRefresh(new Date().toLocaleTimeString());
      }
    } catch { /* silently ignore */ }
  }, [results]);

  useEffect(() => {
    if (results.length > 0) refreshLivePrices();
  }, [results, refreshLivePrices]);

  useEffect(() => {
    if (autoRefresh && results.length > 0) {
      refreshRef.current = setInterval(refreshLivePrices, 30000);
      return () => clearInterval(refreshRef.current);
    }
    return () => clearInterval(refreshRef.current);
  }, [autoRefresh, results, refreshLivePrices]);

  const handleScan = async () => {
    setScanning(true);
    setError(null);
    const t0 = Date.now();
    try {
      const [res, sent, geo, sec] = await Promise.all([
        runScan(),
        fetchSentiment(),
        fetchGeoRisk().catch(() => null),
        fetchSectors().catch(() => []),
      ]);
      setScanTime(((Date.now() - t0) / 1000).toFixed(1));
      setResults(res);
      setSentiment(sent);
      setGeoRisk(geo);
      setSectors(sec);
    } catch (e) {
      setError(e.message);
    } finally {
      setScanning(false);
    }
  };

  const handleStockClick = (symbol) => setSelectedStock(symbol);

  // Categorize results
  const recommendedStocks = results.filter((r) => r.recommendation === "RECOMMENDED");
  const buyStocks = results.filter((r) => r.recommendation === "BUY");
  const holdStocks = results.filter((r) => r.recommendation === "HOLD");
  const avoidStocks = results.filter((r) => r.recommendation === "AVOID");

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Expert Scanner</h2>
          <p className="text-xs text-muted mt-0.5 font-medium">
            NIFTY 100 &middot; Targets & Stop Loss &middot; Earnings &middot; Geo Risk &middot; AI Reasoning
          </p>
        </div>
        <div className="flex gap-3 items-center flex-wrap">
          {regime && (
            <Badge variant={regime.above_200dma ? "success" : "danger"}>
              NIFTY: ₹{regime.nifty_close} | 200DMA: ₹{regime.nifty_200dma}
            </Badge>
          )}
          {geoRisk && (
            <Badge variant={
              geoRisk.risk_level === "EXTREME" ? "danger" :
              geoRisk.risk_level === "HIGH" ? "warning" : "info"
            }>
              <Shield size={10} className="mr-1" />
              Geo: {geoRisk.risk_level}
            </Badge>
          )}
          {scanTime && <span className="text-[10px] text-muted font-mono">⚡ {scanTime}s</span>}
          <button onClick={handleScan} disabled={scanning}
            className="btn-primary disabled:opacity-50 flex items-center gap-2">
            {scanning ? (
              <>
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Scanning...
              </>
            ) : (
              <><Zap size={14} /> Run Expert Scan</>
            )}
          </button>
        </div>
      </div>

      {/* Search Bar */}
      <SearchBar onSelect={handleStockClick} />

      {error && <ErrorMsg message={error} />}
      {loading && <Loader />}

      {/* Commodities Ticker (Gold, Silver, Crude Oil, VIX, Inflation) */}
      {commodities.length > 0 && (
        <div>
          <h4 className="text-[11px] font-semibold text-muted uppercase tracking-wider flex items-center gap-2 mb-2">
            <Coins size={13} className="text-yellow-400" />
            Market Indicators — Real-Time
            <span className="text-gray-700 normal-case font-normal text-[10px]">Gold · Silver · Oil · Gas · VIX · USD/INR · Inflation · ETFs</span>
          </h4>
          <CommoditiesTicker commodities={commodities} />
        </div>
      )}

      {/* Live Price Ticker */}
      {livePrices.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-2">
            <h4 className="text-[11px] font-semibold text-muted uppercase tracking-wider flex items-center gap-2">
              Live Prices (Top Picks)
              {lastRefresh && <span className="text-gray-600 font-mono normal-case">Updated {lastRefresh}</span>}
            </h4>
            <div className="flex items-center gap-2">
              <button onClick={refreshLivePrices} className="p-1 hover:bg-white/[0.05] rounded transition-colors" title="Refresh now">
                <RefreshCw size={12} className="text-muted" />
              </button>
              <label className="flex items-center gap-1.5 text-[10px] text-muted cursor-pointer">
                <input type="checkbox" checked={autoRefresh} onChange={(e) => setAutoRefresh(e.target.checked)}
                  className="rounded border-gray-600 bg-gray-800 text-blue-500 w-3 h-3" />
                Auto (30s)
              </label>
            </div>
          </div>
          <LivePriceTicker prices={livePrices} onStockClick={handleStockClick} />
        </div>
      )}

      {/* Intelligence Panels (Sentiment + Geo Risk side by side) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <SentimentCard sentiment={sentiment} />
        <GeoRiskCard geoRisk={geoRisk} />
      </div>

      {/* Sector Heatmap */}
      <SectorHeatmap sectors={sectors} />

      {/* Summary Badges */}
      {results.length > 0 && (
        <div className="flex gap-3 flex-wrap text-xs">
          {[
            { label: "RECOMMENDED", count: recommendedStocks.length, color: "blue" },
            { label: "BUY", count: buyStocks.length, color: "emerald" },
            { label: "HOLD", count: holdStocks.length, color: "gray" },
            { label: "AVOID", count: avoidStocks.length, color: "red" },
          ].map(({ label, count, color }) => (
            <div key={label} className={`flex items-center gap-2 bg-${color}-500/10 border border-${color}-500/20 rounded-lg px-3 py-1.5`}>
              <span className={`w-2 h-2 rounded-full bg-${color}-400`} />
              <span className={`text-${color}-400 font-semibold font-mono`}>{count}</span>
              <span className="text-muted">{label}</span>
            </div>
          ))}
          <div className="flex items-center text-muted ml-2 font-mono">Total: {results.length}</div>
        </div>
      )}

      {/* ⭐ RECOMMENDED — Premium Cards */}
      {recommendedStocks.length > 0 && (
        <div>
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 rounded-lg bg-gradient-to-br from-blue-500/20 to-purple-500/20">
              <Award size={18} className="text-blue-400" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-blue-400">
                Expert Recommended ({recommendedStocks.length})
              </h3>
              <p className="text-[11px] text-muted">
                High-conviction picks based on technicals, earnings momentum & market conditions
              </p>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {recommendedStocks.map((s) => (
              <RecommendedStockCard key={s.id} stock={s} onStockClick={handleStockClick} />
            ))}
          </div>
        </div>
      )}

      {/* BUY Picks */}
      <Card title={
        <div className="flex items-center gap-2">
          <Crosshair size={16} className="text-emerald-400" />
          <span>Buy Signals ({buyStocks.length})</span>
        </div>
      }>
        <StockTable stocks={buyStocks} onStockClick={handleStockClick} />
      </Card>

      {/* HOLD = Watchlist */}
      <Card title={
        <div className="flex items-center gap-2">
          <Eye size={16} className="text-gray-400" />
          <span>Watchlist — Hold ({holdStocks.length})</span>
        </div>
      }>
        <div className="max-h-96 overflow-y-auto">
          <StockTable stocks={holdStocks} onStockClick={handleStockClick} showTargets={false} />
        </div>
      </Card>

      {/* AVOID = Red Zone */}
      <Card title={`Avoid (${avoidStocks.length})`}>
        <div className="max-h-64 overflow-y-auto">
          <StockTable stocks={avoidStocks} onStockClick={handleStockClick} showReasoning={false} showTargets={false} />
        </div>
      </Card>

      {/* Stock Detail Modal */}
      {selectedStock && (
        <StockDetailModal
          symbol={selectedStock}
          onClose={() => setSelectedStock(null)}
          watchlist={watchlist}
          onWatchlistChange={() => fetchWatchlist().then(setWatchlist).catch(() => {})}
        />
      )}
    </div>
  );
}
