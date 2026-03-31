import { useState, useEffect } from "react";
import {
  FileText, TrendingUp, TrendingDown, DollarSign, RefreshCw,
  Plus, Minus, RotateCcw, Search, ArrowUpRight, ArrowDownRight,
} from "lucide-react";
import { paperTrade, fetchPaperPortfolio, resetPaperAccount, searchStocks } from "../api";

export default function PaperTrading() {
  const [portfolio, setPortfolio] = useState(null);
  const [loading, setLoading] = useState(true);
  const [symbol, setSymbol] = useState("");
  const [quantity, setQuantity] = useState(1);
  const [action, setAction] = useState("BUY");
  const [tradeResult, setTradeResult] = useState(null);
  const [searching, setSearching] = useState(false);
  const [searchResults, setSearchResults] = useState([]);
  const [resetCapital, setResetCapital] = useState(100000);

  const loadPortfolio = () => {
    setLoading(true);
    fetchPaperPortfolio()
      .then(setPortfolio)
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(loadPortfolio, []);

  const handleTrade = async () => {
    if (!symbol.trim()) return;
    try {
      const result = await paperTrade({ symbol: symbol.toUpperCase(), action, quantity });
      setTradeResult(result);
      loadPortfolio();
      setTimeout(() => setTradeResult(null), 5000);
    } catch (err) {
      setTradeResult({ error: err.message });
      setTimeout(() => setTradeResult(null), 5000);
    }
  };

  const handleReset = async () => {
    try {
      await resetPaperAccount(resetCapital);
      loadPortfolio();
    } catch (err) {}
  };

  const handleSearch = async (q) => {
    setSymbol(q);
    if (q.length >= 2) {
      setSearching(true);
      try {
        const res = await searchStocks(q);
        setSearchResults(res.results || []);
      } catch {
        setSearchResults([]);
      } finally {
        setSearching(false);
      }
    } else {
      setSearchResults([]);
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gold-bright font-display tracking-tight">
            Paper Trading
          </h1>
          <p className="text-muted text-sm mt-1 font-mono">
            Practice trading with virtual money &mdash; zero risk
          </p>
        </div>
        <div className="flex items-center gap-2">
          <input
            type="number"
            value={resetCapital}
            onChange={e => setResetCapital(Number(e.target.value))}
            className="w-28 bg-surface border border-gold/20 rounded px-2 py-1.5 text-xs font-mono text-gold-bright outline-none"
            placeholder="Capital"
          />
          <button onClick={handleReset} className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-red-500/10 text-red-400 text-xs font-mono hover:bg-red-500/20 transition-colors border border-red-500/20">
            <RotateCcw size={12} />
            Reset
          </button>
        </div>
      </div>

      {/* Portfolio Summary */}
      {portfolio && (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
          {[
            { label: "Total Equity", value: `₹${portfolio.total_equity?.toLocaleString("en-IN")}`, color: "text-gold-bright" },
            { label: "Cash", value: `₹${portfolio.cash?.toLocaleString("en-IN")}`, color: "text-gray-300" },
            { label: "Invested", value: `₹${portfolio.total_invested?.toLocaleString("en-IN")}`, color: "text-gray-300" },
            { label: "Unrealized P&L", value: `₹${portfolio.unrealized_pnl?.toLocaleString("en-IN")}`, color: portfolio.unrealized_pnl >= 0 ? "text-matrix" : "text-danger" },
            { label: "Realized P&L", value: `₹${portfolio.realized_pnl?.toLocaleString("en-IN")}`, color: portfolio.realized_pnl >= 0 ? "text-matrix" : "text-danger" },
            { label: "Total Return", value: `${portfolio.total_return_pct}%`, color: portfolio.total_return_pct >= 0 ? "text-matrix" : "text-danger" },
          ].map((s, i) => (
            <div key={i} className="glass-card p-3">
              <div className="text-[9px] font-mono text-muted uppercase tracking-wider">{s.label}</div>
              <div className={`text-base font-mono font-bold mt-1 ${s.color}`}>{s.value}</div>
            </div>
          ))}
        </div>
      )}

      {/* Trade Entry */}
      <div className="glass-card p-5">
        <h2 className="text-sm font-semibold text-gold uppercase tracking-wider font-mono mb-4 flex items-center gap-2">
          <Plus size={14} />
          Execute Paper Trade
        </h2>

        {/* Trade result toast */}
        {tradeResult && (
          <div className={`mb-4 p-3 rounded text-xs font-mono border ${
            tradeResult.error
              ? "bg-red-500/10 border-red-500/30 text-red-400"
              : "bg-matrix/10 border-matrix/30 text-matrix"
          }`}>
            {tradeResult.error
              ? `Error: ${tradeResult.error}`
              : `${tradeResult.status} ${tradeResult.quantity} × ${tradeResult.symbol} @ ₹${tradeResult.price?.toFixed(2)}${tradeResult.pnl !== undefined ? ` | P&L: ₹${tradeResult.pnl}` : ""}`
            }
          </div>
        )}

        <div className="flex flex-wrap items-end gap-3">
          {/* Symbol search */}
          <div className="relative flex-1 min-w-[200px]">
            <label className="text-[10px] font-mono text-muted uppercase">Symbol</label>
            <div className="relative mt-1">
              <Search size={12} className="absolute left-2 top-1/2 -translate-y-1/2 text-muted" />
              <input
                type="text"
                value={symbol}
                onChange={e => handleSearch(e.target.value.toUpperCase())}
                placeholder="Search stock..."
                className="w-full bg-surface border border-gold/20 rounded pl-7 pr-3 py-2 text-sm font-mono text-gold-bright outline-none focus:border-gold/40"
              />
            </div>
            {searchResults.length > 0 && (
              <div className="absolute top-full left-0 right-0 mt-1 bg-surface-2 border border-gold/20 rounded max-h-40 overflow-y-auto z-20">
                {searchResults.slice(0, 8).map((r, i) => (
                  <button
                    key={i}
                    onClick={() => { setSymbol(r.symbol?.replace(".NS", "") || r); setSearchResults([]); }}
                    className="w-full text-left px-3 py-2 text-xs font-mono text-gray-300 hover:bg-gold/5 hover:text-gold transition-colors"
                  >
                    {r.symbol || r} <span className="text-muted">{r.name || ""}</span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Quantity */}
          <div className="w-28">
            <label className="text-[10px] font-mono text-muted uppercase">Quantity</label>
            <input
              type="number"
              min="1"
              value={quantity}
              onChange={e => setQuantity(Math.max(1, parseInt(e.target.value) || 1))}
              className="w-full mt-1 bg-surface border border-gold/20 rounded px-3 py-2 text-sm font-mono text-gold-bright outline-none focus:border-gold/40"
            />
          </div>

          {/* Action toggle */}
          <div>
            <label className="text-[10px] font-mono text-muted uppercase">Action</label>
            <div className="flex mt-1 rounded overflow-hidden border border-gold/20">
              <button
                onClick={() => setAction("BUY")}
                className={`px-4 py-2 text-xs font-mono font-semibold transition-colors ${
                  action === "BUY" ? "bg-matrix/15 text-matrix" : "bg-surface text-muted hover:text-gray-300"
                }`}
              >
                BUY
              </button>
              <button
                onClick={() => setAction("SELL")}
                className={`px-4 py-2 text-xs font-mono font-semibold transition-colors ${
                  action === "SELL" ? "bg-danger/15 text-danger" : "bg-surface text-muted hover:text-gray-300"
                }`}
              >
                SELL
              </button>
            </div>
          </div>

          <button onClick={handleTrade} className="btn-primary py-2">
            Execute
          </button>
        </div>
      </div>

      {/* Open Positions */}
      {portfolio?.positions?.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-gold uppercase tracking-wider font-mono mb-3">
            Open Positions ({portfolio.positions_count})
          </h2>
          <div className="glass-card overflow-hidden">
            <div className="overflow-x-auto">
              <table className="pro-table w-full">
                <thead>
                  <tr>
                    <th>Symbol</th>
                    <th>Qty</th>
                    <th>Avg Price</th>
                    <th>Current</th>
                    <th>Value</th>
                    <th>P&L</th>
                    <th>P&L %</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {portfolio.positions.map((p, i) => (
                    <tr key={i}>
                      <td className="font-semibold text-gold-bright">{p.symbol}</td>
                      <td>{p.quantity}</td>
                      <td>₹{p.avg_price?.toFixed(2)}</td>
                      <td>₹{p.current_price?.toFixed(2)}</td>
                      <td>₹{p.current_value?.toLocaleString("en-IN")}</td>
                      <td className={p.pnl >= 0 ? "text-matrix" : "text-danger"}>
                        {p.pnl >= 0 ? "+" : ""}₹{p.pnl?.toFixed(0)}
                      </td>
                      <td className={p.pnl_pct >= 0 ? "text-matrix" : "text-danger"}>
                        {p.pnl_pct >= 0 ? "+" : ""}{p.pnl_pct?.toFixed(2)}%
                      </td>
                      <td>
                        <button
                          onClick={() => { setSymbol(p.symbol); setQuantity(p.quantity); setAction("SELL"); }}
                          className="text-[10px] font-mono px-2 py-1 rounded bg-red-500/10 text-red-400 hover:bg-red-500/20 transition-colors"
                        >
                          SELL
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Trading Stats */}
      {portfolio?.stats?.total_trades > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { label: "Total Trades", value: portfolio.stats.total_trades },
            { label: "Win Rate", value: `${portfolio.stats.win_rate}%`, color: portfolio.stats.win_rate >= 50 ? "text-matrix" : "text-danger" },
            { label: "Avg Win", value: `₹${portfolio.stats.avg_win}`, color: "text-matrix" },
            { label: "Avg Loss", value: `₹${portfolio.stats.avg_loss}`, color: "text-danger" },
          ].map((s, i) => (
            <div key={i} className="glass-card p-3">
              <div className="text-[9px] font-mono text-muted uppercase tracking-wider">{s.label}</div>
              <div className={`text-lg font-mono font-bold mt-1 ${s.color || "text-gray-200"}`}>{s.value}</div>
            </div>
          ))}
        </div>
      )}

      {/* Closed Trades */}
      {portfolio?.closed_trades?.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-gold uppercase tracking-wider font-mono mb-3">
            Recent Closed Trades
          </h2>
          <div className="glass-card overflow-hidden">
            <div className="overflow-x-auto">
              <table className="pro-table w-full">
                <thead>
                  <tr>
                    <th>Symbol</th>
                    <th>Qty</th>
                    <th>Entry</th>
                    <th>Exit</th>
                    <th>P&L</th>
                    <th>P&L %</th>
                    <th>Exit Date</th>
                  </tr>
                </thead>
                <tbody>
                  {portfolio.closed_trades.map((t, i) => (
                    <tr key={i}>
                      <td className="font-semibold text-gold-bright">{t.symbol}</td>
                      <td>{t.quantity}</td>
                      <td>₹{t.entry_price?.toFixed(2)}</td>
                      <td>₹{t.exit_price?.toFixed(2)}</td>
                      <td className={t.pnl >= 0 ? "text-matrix" : "text-danger"}>
                        {t.pnl >= 0 ? "+" : ""}₹{t.pnl?.toFixed(0)}
                      </td>
                      <td className={t.pnl_pct >= 0 ? "text-matrix" : "text-danger"}>
                        {t.pnl_pct >= 0 ? "+" : ""}{t.pnl_pct?.toFixed(2)}%
                      </td>
                      <td className="text-muted">{t.exit_date}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
