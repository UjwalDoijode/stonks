import { useState, useEffect } from "react";
import {
  X, TrendingUp, TrendingDown, Target, ShieldAlert, Star, StarOff,
  Award, BarChart3, AlertTriangle, Crosshair, Shield,
} from "lucide-react";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts";
import { fetchStockDetail, addToWatchlist, removeFromWatchlist } from "../api";
import { Loader, ErrorMsg } from "./UI";

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

function CriteriaRow({ label, passed, detail }) {
  return (
    <div className={`flex items-center justify-between py-2 px-3 rounded-lg ${passed ? "bg-emerald-500/[0.06] border border-emerald-500/10" : "bg-red-500/[0.06] border border-red-500/10"}`}>
      <div className="flex items-center gap-2">
        <span className={`text-xs ${passed ? "text-emerald-400" : "text-red-400"}`}>{passed ? "✓" : "✗"}</span>
        <span className="text-xs text-gray-300 font-medium">{label}</span>
      </div>
      <span className="text-[11px] text-muted font-mono">{detail}</span>
    </div>
  );
}

function RecommendationBanner({ stock }) {
  const recColors = {
    RECOMMENDED: { bg: "from-blue-500/20 to-purple-500/20", border: "border-blue-500/40", text: "text-blue-400", icon: Award },
    BUY: { bg: "from-emerald-500/20 to-green-500/20", border: "border-emerald-500/40", text: "text-emerald-400", icon: TrendingUp },
    AVOID: { bg: "from-red-500/20 to-orange-500/20", border: "border-red-500/40", text: "text-red-400", icon: AlertTriangle },
    HOLD: { bg: "from-gray-500/20 to-gray-600/20", border: "border-gray-500/40", text: "text-gray-400", icon: Shield },
  };
  const r = recColors[stock.recommendation] || recColors.HOLD;
  const Icon = r.icon;

  return (
    <div className={`bg-gradient-to-r ${r.bg} border ${r.border} rounded-xl p-4`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-black/20">
            <Icon size={20} className={r.text} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className={`text-lg font-bold uppercase ${r.text}`}>{stock.recommendation}</span>
              {stock.conviction && (
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                  stock.conviction === "HIGH" ? "bg-emerald-500/20 text-emerald-400" :
                  stock.conviction === "MEDIUM" ? "bg-amber-500/20 text-amber-400" :
                  "bg-gray-500/20 text-gray-400"
                }`}>
                  {stock.conviction} CONVICTION
                </span>
              )}
            </div>
            {stock.category_tag && (
              <span className="text-xs text-muted">{stock.category_tag}</span>
            )}
          </div>
        </div>
        {stock.conviction_score > 0 && (
          <div className="text-right">
            <div className={`text-2xl font-bold font-mono ${r.text}`}>{stock.conviction_score?.toFixed(0)}</div>
            <div className="text-[9px] text-muted">SCORE / 100</div>
          </div>
        )}
      </div>
      {stock.primary_reason && (
        <p className="text-sm text-gray-300 mt-2">{stock.primary_reason}</p>
      )}
      {stock.risk_warning && (
        <div className="flex items-center gap-1.5 mt-2 text-amber-400 text-xs">
          <AlertTriangle size={12} />
          <span>{stock.risk_warning}</span>
        </div>
      )}
    </div>
  );
}

export default function StockDetailModal({ symbol, onClose, watchlist = [], onWatchlistChange }) {
  const [stock, setStock] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isInWatchlist, setIsInWatchlist] = useState(false);

  useEffect(() => {
    if (!symbol) return;
    setLoading(true);
    setError(null);
    fetchStockDetail(symbol)
      .then((data) => {
        setStock(data);
        setIsInWatchlist(watchlist.some((w) => w.symbol === data.clean_symbol));
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [symbol]);

  const handleWatchlistToggle = async () => {
    if (!stock) return;
    try {
      if (isInWatchlist) {
        await removeFromWatchlist(stock.clean_symbol);
        setIsInWatchlist(false);
      } else {
        await addToWatchlist(stock.clean_symbol);
        setIsInWatchlist(true);
      }
      if (onWatchlistChange) onWatchlistChange();
    } catch { /* ignore */ }
  };

  if (!symbol) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm" onClick={onClose}>
      <div className="glass-card w-full max-w-3xl max-h-[90vh] overflow-y-auto shadow-2xl animate-slide-up"
        onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="sticky top-0 bg-surface/95 backdrop-blur-md border-b border-border/60 p-4 flex items-center justify-between z-10">
          <div className="flex items-center gap-3">
            <h2 className="text-xl font-bold">{stock?.clean_symbol || symbol}</h2>
            {stock && <span className="text-xs text-muted">{stock.name}</span>}
          </div>
          <div className="flex items-center gap-1.5">
            {stock && (
              <button onClick={handleWatchlistToggle}
                className="p-2 hover:bg-white/[0.05] rounded-lg transition-colors"
                title={isInWatchlist ? "Remove from watchlist" : "Add to watchlist"}>
                {isInWatchlist ? <Star size={16} className="text-amber-400 fill-amber-400" /> : <StarOff size={16} className="text-muted" />}
              </button>
            )}
            <button onClick={onClose} className="p-2 hover:bg-white/[0.05] rounded-lg transition-colors">
              <X size={18} className="text-muted" />
            </button>
          </div>
        </div>

        <div className="p-5 space-y-5">
          {loading && <Loader />}
          {error && <ErrorMsg message={error} />}

          {stock && !loading && (
            <>
              {/* Recommendation Banner */}
              <RecommendationBanner stock={stock} />

              {/* Price Banner */}
              <div className="flex items-end gap-6 flex-wrap">
                <div>
                  <div className="text-3xl font-bold font-mono">₹{stock.price?.toFixed(2)}</div>
                  <div className={`flex items-center gap-1 text-sm font-semibold font-mono ${stock.change_pct >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                    {stock.change_pct >= 0 ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
                    {stock.change_pct >= 0 ? "+" : ""}{stock.change_pct?.toFixed(2)}%
                  </div>
                </div>
                <div className="flex gap-5 text-xs text-muted mb-1 flex-wrap font-mono">
                  <div>Day: ₹{stock.day_low?.toFixed(0)} — ₹{stock.day_high?.toFixed(0)}</div>
                  <div>52W: ₹{stock.week_52_low?.toFixed(0)} — ₹{stock.week_52_high?.toFixed(0)}</div>
                  <div>Vol: {(stock.volume / 1e6).toFixed(2)}M</div>
                  {stock.pe_ratio && <div>P/E: {stock.pe_ratio?.toFixed(1)}</div>}
                </div>
              </div>

              {/* Info Tags */}
              <div className="flex gap-2 flex-wrap">
                {stock.sector && (
                  <span className="px-2.5 py-1 bg-blue-500/10 text-blue-400 border border-blue-500/20 rounded-md text-[10px] font-semibold uppercase tracking-wider">{stock.sector}</span>
                )}
                {stock.industry && (
                  <span className="px-2.5 py-1 bg-purple-500/10 text-purple-400 border border-purple-500/20 rounded-md text-[10px] font-semibold uppercase tracking-wider">{stock.industry}</span>
                )}
                {stock.market_cap && (
                  <span className="px-2.5 py-1 bg-gray-800/60 text-gray-300 border border-border/40 rounded-md text-[10px] font-mono font-semibold">
                    MCap: ₹{(stock.market_cap / 1e10).toFixed(0)}K Cr
                  </span>
                )}
                {stock.geo_risk_level && stock.geo_risk_level !== "LOW" && (
                  <span className={`px-2.5 py-1 rounded-md text-[10px] font-semibold uppercase tracking-wider border ${
                    stock.geo_risk_level === "EXTREME" ? "bg-red-500/10 text-red-400 border-red-500/20" :
                    stock.geo_risk_level === "HIGH" ? "bg-orange-500/10 text-orange-400 border-orange-500/20" :
                    "bg-amber-500/10 text-amber-400 border-amber-500/20"
                  }`}>
                    <Shield size={10} className="inline mr-1" />Geo Risk: {stock.geo_risk_level}
                  </span>
                )}
              </div>

              {/* Trade Setup — Enhanced with Multiple Targets */}
              {(stock.entry_price || stock.target_1) && (
                <div className="bg-base/60 rounded-xl p-4 border border-border/30">
                  <h4 className="text-[10px] font-semibold text-muted uppercase tracking-widest mb-3 flex items-center gap-2">
                    <Crosshair size={12} className="text-blue-400" />
                    Trade Setup — Entry, Targets & Stop Loss
                  </h4>
                  <div className="grid grid-cols-3 gap-3 mb-3">
                    <div className="bg-amber-500/[0.06] border border-amber-500/20 rounded-lg p-3 text-center">
                      <div className="text-[9px] text-muted uppercase tracking-wider mb-0.5">Entry Price</div>
                      <div className="text-lg font-bold font-mono text-amber-400">₹{stock.entry_price?.toFixed(2)}</div>
                    </div>
                    <div className="bg-red-500/[0.06] border border-red-500/20 rounded-lg p-3 text-center">
                      <div className="text-[9px] text-muted uppercase tracking-wider mb-0.5">Stop Loss</div>
                      <div className="text-lg font-bold font-mono text-red-400">₹{(stock.stop_loss || stock.stop_loss_price)?.toFixed(2)}</div>
                      {stock.risk_pct > 0 && (
                        <div className="text-xs text-red-400/70 font-mono mt-0.5">-{stock.risk_pct?.toFixed(1)}% risk</div>
                      )}
                    </div>
                    <div className="bg-emerald-500/[0.06] border border-emerald-500/20 rounded-lg p-3 text-center">
                      <div className="text-[9px] text-muted uppercase tracking-wider mb-0.5">Primary Target</div>
                      <div className="text-lg font-bold font-mono text-emerald-400">₹{(stock.target_2 || stock.target)?.toFixed(2)}</div>
                      {stock.reward_pct > 0 && (
                        <div className="text-xs text-emerald-400/70 font-mono mt-0.5">+{stock.reward_pct?.toFixed(1)}% reward</div>
                      )}
                    </div>
                  </div>

                  {/* Multiple Targets */}
                  {stock.target_1 && (
                    <div className="grid grid-cols-3 gap-2 mb-3">
                      <div className="bg-gray-800/40 rounded-lg p-2 text-center border border-border/20">
                        <div className="text-[9px] text-muted uppercase">T1 (1.5R)</div>
                        <div className="font-mono font-bold text-emerald-400">₹{stock.target_1?.toFixed(1)}</div>
                        <div className="text-[10px] text-emerald-400/60 font-mono">
                          +{((stock.target_1 - stock.price) / stock.price * 100).toFixed(1)}%
                        </div>
                      </div>
                      {stock.target_2 && (
                        <div className="bg-gray-800/40 rounded-lg p-2 text-center border border-blue-500/20">
                          <div className="text-[9px] text-blue-400 uppercase font-semibold">T2 (2R)</div>
                          <div className="font-mono font-bold text-blue-400">₹{stock.target_2?.toFixed(1)}</div>
                          <div className="text-[10px] text-blue-400/60 font-mono">
                            +{((stock.target_2 - stock.price) / stock.price * 100).toFixed(1)}%
                          </div>
                        </div>
                      )}
                      {stock.target_3 && (
                        <div className="bg-gray-800/40 rounded-lg p-2 text-center border border-purple-500/20">
                          <div className="text-[9px] text-purple-400 uppercase">T3 (3R)</div>
                          <div className="font-mono font-bold text-purple-400">₹{stock.target_3?.toFixed(1)}</div>
                          <div className="text-[10px] text-purple-400/60 font-mono">
                            +{((stock.target_3 - stock.price) / stock.price * 100).toFixed(1)}%
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {/* R:R ratio bar */}
                  {stock.risk_reward && (
                    <div className="bg-blue-500/[0.06] border border-blue-500/20 rounded-lg p-3 flex items-center justify-between">
                      <span className="text-xs text-muted font-medium">Risk : Reward Ratio</span>
                      <span className="text-blue-400 font-bold font-mono text-lg">{stock.risk_reward}</span>
                    </div>
                  )}

                  {/* Support & Resistance */}
                  {(stock.support_levels?.length > 0 || stock.resistance_levels?.length > 0) && (
                    <div className="grid grid-cols-2 gap-3 mt-3">
                      {stock.support_levels?.length > 0 && (
                        <div>
                          <div className="text-[9px] text-muted uppercase tracking-wider mb-1.5 font-semibold">Support Levels</div>
                          <div className="flex gap-1.5 flex-wrap">
                            {stock.support_levels.map((s, i) => (
                              <span key={i} className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 text-[10px] font-mono border border-emerald-500/20">
                                ₹{s}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                      {stock.resistance_levels?.length > 0 && (
                        <div>
                          <div className="text-[9px] text-muted uppercase tracking-wider mb-1.5 font-semibold">Resistance Levels</div>
                          <div className="flex gap-1.5 flex-wrap">
                            {stock.resistance_levels.map((r, i) => (
                              <span key={i} className="px-2 py-0.5 rounded bg-red-500/10 text-red-400 text-[10px] font-mono border border-red-500/20">
                                ₹{r}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* Earnings Momentum */}
              {stock.earnings_momentum && stock.earnings_momentum !== "NEUTRAL" && (
                <div className={`rounded-xl p-4 border ${
                  ["STRONG", "POSITIVE"].includes(stock.earnings_momentum)
                    ? "bg-emerald-500/[0.04] border-emerald-500/20"
                    : "bg-red-500/[0.04] border-red-500/20"
                }`}>
                  <h4 className="text-[10px] font-semibold text-muted uppercase tracking-widest mb-2 flex items-center gap-2">
                    <BarChart3 size={12} className="text-blue-400" />
                    Quarterly Earnings Momentum
                  </h4>
                  <div className="flex items-center gap-3">
                    <span className={`px-2.5 py-1 rounded-lg text-sm font-bold ${
                      ["STRONG", "POSITIVE"].includes(stock.earnings_momentum) ? "bg-emerald-500/15 text-emerald-400" :
                      stock.earnings_momentum === "WEAK" ? "bg-amber-500/15 text-amber-400" :
                      "bg-red-500/15 text-red-400"
                    }`}>
                      {stock.earnings_momentum}
                    </span>
                    <span className="font-mono text-sm text-muted">{stock.earnings_score?.toFixed(0)}/100</span>
                  </div>
                  {stock.quarterly_trend && (
                    <p className="text-xs text-muted mt-2 leading-relaxed">{stock.quarterly_trend}</p>
                  )}
                </div>
              )}

              {/* 6-Month Price Chart */}
              {stock.price_history && stock.price_history.length > 0 && (
                <div className="bg-base/60 rounded-xl p-4 border border-border/30">
                  <h4 className="text-[10px] font-semibold text-muted uppercase tracking-widest mb-3">6-Month Price History</h4>
                  <ResponsiveContainer width="100%" height={220}>
                    <LineChart data={stock.price_history}>
                      <XAxis dataKey="date" tick={{ fill: "#64748b", fontSize: 10 }}
                        tickFormatter={(d) => d.slice(5)}
                        interval={Math.floor(stock.price_history.length / 6)}
                        tickLine={false} axisLine={false} />
                      <YAxis domain={["auto", "auto"]} tick={{ fill: "#64748b", fontSize: 10 }}
                        width={55} tickFormatter={(v) => `₹${v}`} tickLine={false} axisLine={false} />
                      <Tooltip {...CHART_TOOLTIP} formatter={(v) => [`₹${v}`, "Price"]} />
                      {stock.dma_200 && <ReferenceLine y={stock.dma_200} stroke="#f59e0b" strokeDasharray="5 5" label={{ value: "200 DMA", fill: "#f59e0b", fontSize: 10 }} />}
                      {stock.entry_price && <ReferenceLine y={stock.entry_price} stroke="#10b981" strokeDasharray="3 3" label={{ value: "Entry", fill: "#10b981", fontSize: 10 }} />}
                      {(stock.stop_loss || stock.stop_loss_price) && <ReferenceLine y={stock.stop_loss || stock.stop_loss_price} stroke="#ef4444" strokeDasharray="3 3" label={{ value: "Stop", fill: "#ef4444", fontSize: 10 }} />}
                      {stock.target_2 && <ReferenceLine y={stock.target_2} stroke="#3b82f6" strokeDasharray="3 3" label={{ value: "Target", fill: "#3b82f6", fontSize: 10 }} />}
                      <Line type="monotone" dataKey="price" stroke="#3b82f6" dot={false} strokeWidth={2} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              )}

              {/* Signal Criteria + Quick Stats */}
              {stock.dma_200 !== null && stock.dma_200 !== undefined && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <h4 className="text-[10px] font-semibold text-muted uppercase tracking-widest mb-3 flex items-center gap-2">
                      <Target size={12} className="text-blue-400" /> Signal Criteria ({stock.criteria_met}/6)
                    </h4>
                    <CriteriaRow label="Above 200-DMA" passed={stock.above_200dma} detail={`₹${stock.dma_200?.toFixed(0)}`} />
                    <CriteriaRow label="50-DMA Trending Up" passed={stock.dma50_trending_up} detail={`₹${stock.dma_50?.toFixed(0)}`} />
                    <CriteriaRow label="Pullback to 20-DMA" passed={stock.pullback_to_20dma} detail={`₹${stock.dma_20?.toFixed(0)}`} />
                    <CriteriaRow label="RSI in Zone (40-65)" passed={stock.rsi_in_zone} detail={stock.rsi?.toFixed(1)} />
                    <CriteriaRow label="Volume Contracting" passed={stock.volume_contracting} detail={`${stock.volume_ratio?.toFixed(2)}x`} />
                    <CriteriaRow label="Entry Triggered" passed={stock.entry_triggered} detail={`₹${stock.entry_price?.toFixed(0)}`} />
                  </div>

                  {/* Quick P&L Calculator */}
                  <div className="space-y-3">
                    <h4 className="text-[10px] font-semibold text-muted uppercase tracking-widest mb-3 flex items-center gap-2">
                      <ShieldAlert size={12} className="text-blue-400" /> Potential P&L (per ₹20K)
                    </h4>
                    {stock.entry_price && stock.risk_pct > 0 && (() => {
                      const capital = 20000;
                      const qty = Math.floor(capital / stock.entry_price);
                      const invested = qty * stock.entry_price;
                      const lossAmt = qty * (stock.entry_price - (stock.stop_loss || stock.stop_loss_price || stock.entry_price * 0.95));
                      const profitT1 = stock.target_1 ? qty * (stock.target_1 - stock.entry_price) : 0;
                      const profitT2 = stock.target_2 ? qty * (stock.target_2 - stock.entry_price) : 0;
                      const profitT3 = stock.target_3 ? qty * (stock.target_3 - stock.entry_price) : 0;
                      return (
                        <div className="space-y-2">
                          <div className="flex justify-between text-xs bg-base/60 rounded-lg p-2.5 border border-border/30">
                            <span className="text-muted">Quantity</span>
                            <span className="font-mono font-bold">{qty} shares @ ₹{stock.entry_price?.toFixed(1)}</span>
                          </div>
                          <div className="flex justify-between text-xs bg-base/60 rounded-lg p-2.5 border border-border/30">
                            <span className="text-muted">Invested</span>
                            <span className="font-mono font-bold">₹{invested?.toFixed(0)}</span>
                          </div>
                          <div className="flex justify-between text-xs bg-red-500/[0.06] rounded-lg p-2.5 border border-red-500/20">
                            <span className="text-muted">If SL Hit</span>
                            <span className="font-mono font-bold text-red-400">-₹{lossAmt?.toFixed(0)}</span>
                          </div>
                          {profitT1 > 0 && (
                            <div className="flex justify-between text-xs bg-emerald-500/[0.06] rounded-lg p-2.5 border border-emerald-500/20">
                              <span className="text-muted">If T1 Hit</span>
                              <span className="font-mono font-bold text-emerald-400">+₹{profitT1?.toFixed(0)}</span>
                            </div>
                          )}
                          {profitT2 > 0 && (
                            <div className="flex justify-between text-xs bg-blue-500/[0.06] rounded-lg p-2.5 border border-blue-500/20">
                              <span className="text-muted">If T2 Hit</span>
                              <span className="font-mono font-bold text-blue-400">+₹{profitT2?.toFixed(0)}</span>
                            </div>
                          )}
                          {profitT3 > 0 && (
                            <div className="flex justify-between text-xs bg-purple-500/[0.06] rounded-lg p-2.5 border border-purple-500/20">
                              <span className="text-muted">If T3 Hit</span>
                              <span className="font-mono font-bold text-purple-400">+₹{profitT3?.toFixed(0)}</span>
                            </div>
                          )}
                        </div>
                      );
                    })()}
                  </div>
                </div>
              )}

              {/* Full Analysis Reasoning */}
              {(stock.reasons?.length > 0 || stock.reasoning) && (
                <div className="bg-base/60 rounded-xl p-5 border border-border/30">
                  <h4 className="text-[10px] font-semibold text-muted uppercase tracking-widest mb-3">Expert Analysis</h4>
                  <div className="space-y-2">
                    {stock.reasons?.length > 0
                      ? stock.reasons.map((r, i) => (
                          <p key={i} className="text-sm text-gray-400 leading-relaxed">{r}</p>
                        ))
                      : stock.reasoning?.split(" | ").map((part, i) => (
                          <p key={i} className="text-sm text-gray-400 leading-relaxed">{part}</p>
                        ))
                    }
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
