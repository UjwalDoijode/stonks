import { useState, useEffect } from "react";
import {
  Newspaper, RefreshCw, ExternalLink, Sparkles, TrendingUp,
  TrendingDown, Minus, Globe, Filter, Clock, Zap,
} from "lucide-react";
import { fetchNews, fetchNewsAISummary } from "../api";

const CATEGORY_COLORS = {
  "Indian Markets": { bg: "bg-blue-500/10", text: "text-blue-400", border: "border-blue-500/20" },
  "Indian Finance": { bg: "bg-emerald-500/10", text: "text-emerald-400", border: "border-emerald-500/20" },
  "Indian Economy": { bg: "bg-amber-500/10", text: "text-amber-400", border: "border-amber-500/20" },
  "War": { bg: "bg-red-600/15", text: "text-red-400", border: "border-red-600/30" },
  "Geopolitics": { bg: "bg-orange-500/15", text: "text-orange-400", border: "border-orange-500/30" },
  "Global": { bg: "bg-purple-500/10", text: "text-purple-400", border: "border-purple-500/20" },
  "US Markets": { bg: "bg-cyan-500/10", text: "text-cyan-400", border: "border-cyan-500/20" },
};

const SENTIMENT_CFG = {
  bullish: { icon: TrendingUp, color: "text-emerald-400", bg: "bg-emerald-500/15", border: "border-emerald-500/30", label: "Bullish" },
  bearish: { icon: TrendingDown, color: "text-red-400", bg: "bg-red-500/15", border: "border-red-500/30", label: "Bearish" },
  mixed: { icon: Minus, color: "text-amber-400", bg: "bg-amber-500/15", border: "border-amber-500/30", label: "Mixed" },
  neutral: { icon: Minus, color: "text-gray-400", bg: "bg-gray-500/15", border: "border-gray-500/30", label: "Neutral" },
};

function formatTime(dateStr) {
  if (!dateStr) return "";
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return "";
    const now = new Date();
    const diff = (now - d) / 1000 / 60;
    if (diff < 60) return `${Math.round(diff)}m ago`;
    if (diff < 1440) return `${Math.round(diff / 60)}h ago`;
    return `${Math.round(diff / 1440)}d ago`;
  } catch {
    return "";
  }
}

export default function News() {
  const [articles, setArticles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState("all");
  const [sortBy, setSortBy] = useState("importance");  // "importance" or "recent"
  const [aiSummary, setAiSummary] = useState(null);
  const [aiLoading, setAiLoading] = useState(false);

  const loadNews = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchNews();
      setArticles(data.articles || []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const loadAISummary = async () => {
    setAiLoading(true);
    try {
      const data = await fetchNewsAISummary();
      setAiSummary(data);
    } catch {
      setAiSummary({ summary: "AI summary unavailable.", sentiment: "neutral" });
    } finally {
      setAiLoading(false);
    }
  };

  useEffect(() => { loadNews(); }, []);

  const categories = ["all", ...new Set(articles.map((a) => a.category))];
  let filtered = filter === "all" ? articles : articles.filter((a) => a.category === filter);
  
  // Apply sorting
  if (sortBy === "importance") {
    filtered = [...filtered].sort((a, b) => (b.importance || 0) - (a.importance || 0));
  } else if (sortBy === "recent") {
    filtered = [...filtered].sort((a, b) => new Date(b.published) - new Date(a.published));
  }

  const sentCfg = SENTIMENT_CFG[aiSummary?.sentiment] || SENTIMENT_CFG.neutral;
  const SentIcon = sentCfg.icon;

  return (
    <div className="space-y-5 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-gradient-to-br from-gold/20 to-gold/5 border border-gold/20">
            <Newspaper size={22} className="text-gold" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gold-bright font-display tracking-tight">Market News</h1>
            <p className="text-[11px] text-muted font-mono">Financial & global news · AI-powered analysis</p>
          </div>
        </div>
        <button
          onClick={loadNews}
          disabled={loading}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-medium text-muted hover:text-gold hover:bg-gold/10 transition-all border border-gold/10 hover:border-gold/20"
        >
          <RefreshCw size={12} className={loading ? "animate-spin" : ""} />
          Refresh
        </button>
      </div>

      {/* AI Summary */}
      <div className="glass-card overflow-hidden">
        <div className="flex items-center justify-between px-5 py-3 border-b border-gold/10">
          <div className="flex items-center gap-2">
            <Sparkles size={14} className="text-purple-400" />
            <h3 className="text-[10px] font-semibold uppercase tracking-[0.15em] text-gold font-mono">AI News Analysis</h3>
            {aiSummary && (
              <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold border ${sentCfg.bg} ${sentCfg.text} ${sentCfg.border}`}>
                <SentIcon size={10} /> {sentCfg.label}
              </span>
            )}
          </div>
          <button
            onClick={loadAISummary}
            disabled={aiLoading}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[10px] font-semibold text-gold/70 hover:text-gold hover:bg-gold/10 transition-all font-mono disabled:opacity-40"
          >
            <Sparkles size={11} className={aiLoading ? "animate-spin" : ""} />
            {aiSummary ? "Refresh" : "Generate"}
          </button>
        </div>
        <div className="p-5">
          {aiSummary ? (
            <div className="text-[13px] text-gray-300 leading-relaxed ai-markdown space-y-1.5">
              {aiSummary.summary.split("\n").map((line, i) => {
                if (line.startsWith("### "))
                  return <h4 key={i} className="text-gold font-semibold text-sm mt-2 mb-0.5">{line.slice(4)}</h4>;
                if (line.startsWith("- ") || line.startsWith("* "))
                  return <div key={i} className="flex gap-2 pl-1"><span className="text-gold/40">•</span><span dangerouslySetInnerHTML={{ __html: line.slice(2).replace(/\*\*(.+?)\*\*/g, '<strong class="text-gray-100">$1</strong>') }} /></div>;
                if (line.trim() === "") return <div key={i} className="h-1" />;
                return <p key={i} dangerouslySetInnerHTML={{ __html: line.replace(/\*\*(.+?)\*\*/g, '<strong class="text-gray-100">$1</strong>') }} />;
              })}
            </div>
          ) : aiLoading ? (
            <div className="flex items-center gap-2 py-4 justify-center">
              <div className="flex gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-purple-400/60 animate-bounce" style={{ animationDelay: "0ms" }} />
                <span className="w-1.5 h-1.5 rounded-full bg-purple-400/60 animate-bounce" style={{ animationDelay: "150ms" }} />
                <span className="w-1.5 h-1.5 rounded-full bg-purple-400/60 animate-bounce" style={{ animationDelay: "300ms" }} />
              </div>
              <span className="text-[11px] text-muted font-mono">Analyzing headlines...</span>
            </div>
          ) : (
            <p className="text-center text-muted text-sm py-2">Click "Generate" for AI-powered news analysis</p>
          )}
        </div>
      </div>

      {/* Category Filter */}
      <div className="flex gap-1.5 flex-wrap">
        {categories.map((cat) => {
          const cfg = CATEGORY_COLORS[cat] || {};
          const isActive = filter === cat;
          return (
            <button
              key={cat}
              onClick={() => setFilter(cat)}
              className={`px-3 py-1.5 rounded-lg text-[11px] font-semibold transition-all border ${
                isActive
                  ? `${cfg.bg || "bg-gold/15"} ${cfg.text || "text-gold"} ${cfg.border || "border-gold/30"}`
                  : "bg-surface-2/30 text-muted border-transparent hover:border-gold/10 hover:text-gray-300"
              }`}
            >
              {cat === "all" ? "All News" : cat}
              {cat !== "all" && (
                <span className="ml-1.5 text-[9px] opacity-60">
                  {articles.filter((a) => a.category === cat).length}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Sort Options */}
      <div className="flex items-center gap-2 px-3 py-2 bg-gold/5 border border-gold/10 rounded-lg w-fit">
        <Filter size={12} className="text-gold/60" />
        <span className="text-[10px] font-semibold text-gold/70 uppercase tracking-[0.1em]">Sort:</span>
        <button
          onClick={() => setSortBy("importance")}
          className={`px-2.5 py-1 rounded text-[10px] font-semibold transition-all ${
            sortBy === "importance"
              ? "bg-gold text-black"
              : "text-gold/70 hover:text-gold hover:bg-gold/10"
          }`}
        >
          <span className="flex items-center gap-1">
            <Zap size={10} />
            Important
          </span>
        </button>
        <button
          onClick={() => setSortBy("recent")}
          className={`px-2.5 py-1 rounded text-[10px] font-semibold transition-all ${
            sortBy === "recent"
              ? "bg-gold text-black"
              : "text-gold/70 hover:text-gold hover:bg-gold/10"
          }`}
        >
          <span className="flex items-center gap-1">
            <Clock size={10} />
            Recent
          </span>
        </button>
      </div>

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <div className="flex items-center gap-3">
            <RefreshCw size={16} className="text-gold animate-spin" />
            <span className="text-sm text-muted font-mono">Fetching news...</span>
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="glass-card p-4 border-red-500/20">
          <p className="text-red-400 text-sm">{error}</p>
        </div>
      )}

      {/* Articles */}
      {!loading && filtered.length === 0 && (
        <div className="glass-card p-8 text-center">
          <p className="text-muted text-sm">No news articles found. Try refreshing.</p>
        </div>
      )}

      <div className="space-y-2">
        {filtered.map((article, i) => {
          const catCfg = CATEGORY_COLORS[article.category] || {};
          const time = formatTime(article.published);
          const importance = article.importance || 0;
          
          // Importance indicator color
          let importanceColor = "bg-gray-400/20";
          let importanceText = "text-gray-400";
          if (importance >= 60) {
            importanceColor = "bg-red-500/20";
            importanceText = "text-red-400";
          } else if (importance >= 40) {
            importanceColor = "bg-amber-500/20";
            importanceText = "text-amber-400";
          } else if (importance >= 20) {
            importanceColor = "bg-green-500/20";
            importanceText = "text-green-400";
          }
          
          return (
            <a
              key={i}
              href={article.link}
              target="_blank"
              rel="noopener noreferrer"
              className="glass-card p-4 flex items-start gap-4 group hover:border-gold/25 transition-all cursor-pointer block relative"
            >
              {/* Importance indicator bar */}
              {importance > 0 && (
                <div className="absolute left-0 top-0 bottom-0 w-1 rounded-l" style={{
                  background: `linear-gradient(to bottom, ${importance >= 60 ? '#f87171' : importance >= 40 ? '#fbbf24' : '#4ade80'}, ${importance >= 60 ? '#dc2626' : importance >= 40 ? '#d97706' : '#22c55e'})`,
                  opacity: Math.min(importance / 100, 1)
                }} />
              )}
              
              <div className="text-2xl flex-shrink-0 mt-0.5">{article.icon}</div>
              <div className="flex-1 min-w-0">
                <h3 className="text-[13px] font-semibold text-gray-200 group-hover:text-gold-bright transition-colors leading-snug line-clamp-2">
                  {article.title}
                </h3>
                {article.description && (
                  <p className="text-[11px] text-muted mt-1 line-clamp-2 leading-relaxed">{article.description}</p>
                )}
                <div className="flex items-center gap-3 mt-2 flex-wrap">
                  <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-bold border ${catCfg.bg || ""} ${catCfg.text || "text-muted"} ${catCfg.border || "border-border"}`}>
                    {article.category}
                  </span>
                  {importance > 0 && (
                    <span className={`inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[9px] font-bold border ${importanceColor}`}>
                      <span className={`text-[8px] font-bold ${importanceText}`}>
                        ⚡ {importance}
                      </span>
                    </span>
                  )}
                  <span className="text-[10px] text-muted font-mono">{article.source}</span>
                  {time && (
                    <span className="flex items-center gap-1 text-[10px] text-muted/60 font-mono">
                      <Clock size={9} /> {time}
                    </span>
                  )}
                </div>
              </div>
              <ExternalLink size={14} className="text-muted/30 group-hover:text-gold/50 transition-colors flex-shrink-0 mt-1" />
            </a>
          );
        })}
      </div>
    </div>
  );
}
