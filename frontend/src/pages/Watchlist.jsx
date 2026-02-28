import { useState, useEffect } from "react";
import { Card, Loader, ErrorMsg } from "../components/UI";
import StockDetailModal from "../components/StockDetailModal";
import { fetchWatchlist, addToWatchlist, removeFromWatchlist, searchStocks } from "../api";
import { Star, Trash2, Plus, Search, TrendingUp, TrendingDown } from "lucide-react";

export default function Watchlist() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedStock, setSelectedStock] = useState(null);
  const [showAdd, setShowAdd] = useState(false);
  const [addQuery, setAddQuery] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [searching, setSearching] = useState(false);

  const loadWatchlist = async () => {
    setLoading(true);
    try {
      const data = await fetchWatchlist();
      setItems(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadWatchlist(); }, []);

  const handleRemove = async (symbol) => {
    try {
      await removeFromWatchlist(symbol);
      setItems((prev) => prev.filter((i) => i.symbol !== symbol));
    } catch (e) {
      setError(e.message);
    }
  };

  const handleAdd = async (symbol) => {
    try {
      await addToWatchlist(symbol);
      setShowAdd(false);
      setAddQuery("");
      setSearchResults([]);
      await loadWatchlist();
    } catch (e) {
      setError(e.message);
    }
  };

  const handleSearch = async (q) => {
    setAddQuery(q);
    if (q.length < 1) { setSearchResults([]); return; }
    setSearching(true);
    try {
      const res = await searchStocks(q);
      setSearchResults(res);
    } catch {
      setSearchResults([]);
    } finally {
      setSearching(false);
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <Star size={22} className="text-amber-400" />
            Watchlist
          </h2>
          <p className="text-xs text-muted mt-0.5 font-medium">Track your favourite stocks with live prices</p>
        </div>
        <button
          onClick={() => setShowAdd(!showAdd)}
          className="btn-primary flex items-center gap-2"
        >
          <Plus size={16} />
          Add Stock
        </button>
      </div>

      {error && <ErrorMsg message={error} />}

      {/* Add Stock Search */}
      {showAdd && (
        <Card>
          <div className="flex items-center bg-base/60 border border-border rounded-lg px-4 py-2.5 mb-3 focus-within:border-blue-500/40 transition-colors">
            <Search size={16} className="text-muted mr-2.5 flex-shrink-0" />
            <input
              type="text"
              value={addQuery}
              onChange={(e) => handleSearch(e.target.value)}
              placeholder="Search stock to add (e.g. RELIANCE, TCS)..."
              className="bg-transparent text-sm text-gray-200 placeholder-gray-600 outline-none flex-1"
              autoFocus
            />
            {searching && <div className="animate-spin h-4 w-4 border-2 border-transparent border-t-blue-400 rounded-full" />}
          </div>
          {searchResults.length > 0 && (
            <div className="space-y-0.5 max-h-48 overflow-y-auto">
              {searchResults.map((r) => (
                <button
                  key={r.symbol}
                  onClick={() => handleAdd(r.clean_symbol)}
                  className="w-full flex items-center justify-between px-3 py-2.5 hover:bg-white/[0.04] rounded-lg transition-colors"
                >
                  <div>
                    <span className="text-sm font-bold text-gray-200">{r.clean_symbol}</span>
                    <span className="text-xs text-muted ml-2">{r.name}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-mono">₹{r.price}</span>
                    <Plus size={14} className="text-blue-400" />
                  </div>
                </button>
              ))}
            </div>
          )}
        </Card>
      )}

      {loading && <Loader />}

      {/* Empty state */}
      {!loading && items.length === 0 && (
        <Card>
          <div className="text-center py-16">
            <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-amber-500/20 to-amber-600/10 border border-amber-500/20 flex items-center justify-center">
              <Star size={28} className="text-amber-400/50" />
            </div>
            <p className="text-gray-300 text-sm font-medium">Your watchlist is empty</p>
            <p className="text-muted text-xs mt-1">
              Add stocks from the scanner or use the button above
            </p>
          </div>
        </Card>
      )}

      {/* Watchlist Grid */}
      {!loading && items.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
          {items.map((item) => (
            <div
              key={item.id}
              onClick={() => setSelectedStock(item.symbol)}
              className="glass-card p-4 hover:border-blue-500/30 cursor-pointer group transition-all"
            >
              <div className="flex items-start justify-between mb-2">
                <div>
                  <h3 className="font-bold text-gray-200 text-sm">{item.symbol}</h3>
                  {item.notes && (
                    <p className="text-[10px] text-gray-600 mt-0.5">{item.notes}</p>
                  )}
                </div>
                <button
                  onClick={(e) => { e.stopPropagation(); handleRemove(item.symbol); }}
                  className="p-1 opacity-0 group-hover:opacity-100 hover:bg-red-500/20 rounded-lg transition-all"
                  title="Remove"
                >
                  <Trash2 size={14} className="text-red-400" />
                </button>
              </div>
              {item.price ? (
                <>
                  <div className="text-xl font-bold font-mono">₹{item.price?.toFixed(2)}</div>
                  <div className={`text-sm font-medium font-mono flex items-center gap-1 ${(item.change_pct || 0) >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                    {(item.change_pct || 0) >= 0 ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
                    {(item.change_pct || 0) >= 0 ? "+" : ""}{item.change_pct?.toFixed(2)}%
                  </div>
                </>
              ) : (
                <div className="text-sm text-gray-600 mt-2">Price unavailable</div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Stock Detail Modal */}
      {selectedStock && (
        <StockDetailModal
          symbol={selectedStock}
          onClose={() => setSelectedStock(null)}
          watchlist={items}
          onWatchlistChange={loadWatchlist}
        />
      )}
    </div>
  );
}
