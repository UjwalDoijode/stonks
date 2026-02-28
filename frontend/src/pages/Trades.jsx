import { useState, useEffect } from "react";
import { Card, Badge, Loader, ErrorMsg } from "../components/UI";
import { fetchTrades, createTrade, closeTrade } from "../api";

export default function Trades() {
  const [trades, setTrades] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    symbol: "",
    entry_date: new Date().toISOString().split("T")[0],
    entry_price: "",
    stop_loss: "",
    notes: "",
  });
  const [closeForm, setCloseForm] = useState({ id: null, exit_date: "", exit_price: "" });

  const load = () => {
    setLoading(true);
    fetchTrades()
      .then(setTrades)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    setError(null);
    try {
      await createTrade({
        ...form,
        entry_price: parseFloat(form.entry_price),
        stop_loss: parseFloat(form.stop_loss),
      });
      setShowForm(false);
      setForm({ symbol: "", entry_date: new Date().toISOString().split("T")[0], entry_price: "", stop_loss: "", notes: "" });
      load();
    } catch (e) {
      setError(e.message);
    }
  };

  const handleClose = async (e) => {
    e.preventDefault();
    setError(null);
    try {
      await closeTrade(closeForm.id, {
        exit_date: closeForm.exit_date,
        exit_price: parseFloat(closeForm.exit_price),
        status: "CLOSED_MANUAL",
      });
      setCloseForm({ id: null, exit_date: "", exit_price: "" });
      load();
    } catch (e) {
      setError(e.message);
    }
  };

  const openTrades = trades.filter((t) => t.status === "OPEN");
  const closedTrades = trades.filter((t) => t.status !== "OPEN");

  if (loading) return <Loader />;

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Trade Log</h2>
          <p className="text-xs text-muted mt-0.5 font-medium">Manual trade journal with P&L tracking</p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="btn-primary"
        >
          {showForm ? "Cancel" : "+ New Trade"}
        </button>
      </div>

      {error && <ErrorMsg message={error} />}

      {/* New Trade Form */}
      {showForm && (
        <Card title="New Trade Entry">
          <form onSubmit={handleCreate} className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <input
              placeholder="Symbol (e.g. RELIANCE)"
              value={form.symbol}
              onChange={(e) => setForm({ ...form, symbol: e.target.value.toUpperCase() })}
              className="bg-base border border-border rounded-lg px-3 py-2 text-sm font-mono focus:border-blue-500/40 outline-none transition-colors"
              required
            />
            <input
              type="date"
              value={form.entry_date}
              onChange={(e) => setForm({ ...form, entry_date: e.target.value })}
              className="bg-base border border-border rounded-lg px-3 py-2 text-sm focus:border-blue-500/40 outline-none transition-colors"
              required
            />
            <input
              type="number"
              step="0.01"
              placeholder="Entry Price"
              value={form.entry_price}
              onChange={(e) => setForm({ ...form, entry_price: e.target.value })}
              className="bg-base border border-border rounded-lg px-3 py-2 text-sm font-mono focus:border-blue-500/40 outline-none transition-colors"
              required
            />
            <input
              type="number"
              step="0.01"
              placeholder="Stop Loss"
              value={form.stop_loss}
              onChange={(e) => setForm({ ...form, stop_loss: e.target.value })}
              className="bg-base border border-border rounded-lg px-3 py-2 text-sm font-mono focus:border-blue-500/40 outline-none transition-colors"
              required
            />
            <button
              type="submit"
              className="btn-primary"
            >
              Log Trade
            </button>
          </form>
        </Card>
      )}

      {/* Open Trades */}
      <Card title={`Open Trades (${openTrades.length}/2)`}>
        {openTrades.length === 0 ? (
          <p className="text-muted text-sm py-4 text-center">No open trades</p>
        ) : (
          <table className="pro-table w-full">
            <thead>
              <tr>
                <th className="text-left py-2">Symbol</th>
                <th className="text-right">Entry</th>
                <th className="text-right">Qty</th>
                <th className="text-right">SL</th>
                <th className="text-right">Target</th>
                <th className="text-right">Risk ₹</th>
                <th className="text-right">Size ₹</th>
                <th className="text-center">Action</th>
              </tr>
            </thead>
            <tbody>
              {openTrades.map((t) => (
                <tr key={t.id}>
                  <td className="font-semibold text-gray-200">{t.symbol}</td>
                  <td className="text-right font-mono">₹{t.entry_price}</td>
                  <td className="text-right font-mono">{t.quantity}</td>
                  <td className="text-right font-mono text-loss">₹{t.stop_loss}</td>
                  <td className="text-right font-mono text-profit">₹{t.target}</td>
                  <td className="text-right font-mono">₹{t.risk_amount.toFixed(0)}</td>
                  <td className="text-right font-mono">₹{t.position_size.toFixed(0)}</td>
                  <td className="text-center">
                    {closeForm.id === t.id ? (
                      <form onSubmit={handleClose} className="flex gap-1">
                        <input
                          type="date"
                          value={closeForm.exit_date}
                          onChange={(e) =>
                            setCloseForm({ ...closeForm, exit_date: e.target.value })
                          }
                          className="bg-base border border-border rounded-lg px-1.5 py-1 text-xs w-28 focus:border-blue-500/40 outline-none"
                          required
                        />
                        <input
                          type="number"
                          step="0.01"
                          placeholder="Exit ₹"
                          value={closeForm.exit_price}
                          onChange={(e) =>
                            setCloseForm({ ...closeForm, exit_price: e.target.value })
                          }
                          className="bg-base border border-border rounded-lg px-1.5 py-1 text-xs w-20 font-mono focus:border-blue-500/40 outline-none"
                          required
                        />
                        <button
                          type="submit"
                          className="bg-red-500/80 text-white rounded-lg px-2 py-1 text-xs font-medium hover:bg-red-500/60 transition-colors"
                        >
                          Close
                        </button>
                      </form>
                    ) : (
                      <button
                        onClick={() =>
                          setCloseForm({
                            id: t.id,
                            exit_date: new Date().toISOString().split("T")[0],
                            exit_price: "",
                          })
                        }
                        className="text-xs text-amber-400 hover:text-amber-300 font-medium transition-colors"
                      >
                        Close Trade
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      {/* Closed Trades */}
      <Card title={`Closed Trades (${closedTrades.length})`}>
        {closedTrades.length === 0 ? (
          <p className="text-muted text-sm py-4 text-center">No closed trades yet</p>
        ) : (
          <div className="overflow-x-auto max-h-96 overflow-y-auto">
            <table className="pro-table w-full">
              <thead>
                <tr>
                  <th className="text-left py-2">Symbol</th>
                  <th className="text-right">Entry</th>
                  <th className="text-right">Exit</th>
                  <th className="text-right">Qty</th>
                  <th className="text-right">P&L</th>
                  <th className="text-right">R</th>
                  <th className="text-center">Status</th>
                </tr>
              </thead>
              <tbody>
                {closedTrades.map((t) => (
                  <tr key={t.id}>
                    <td className="font-semibold text-gray-200">{t.symbol}</td>
                    <td className="text-right font-mono">₹{t.entry_price}</td>
                    <td className="text-right font-mono">₹{t.exit_price}</td>
                    <td className="text-right font-mono">{t.quantity}</td>
                    <td
                      className={`text-right font-mono font-semibold ${
                        t.pnl >= 0 ? "text-profit" : "text-loss"
                      }`}
                    >
                      {t.pnl >= 0 ? "+" : ""}₹{t.pnl.toFixed(0)}
                    </td>
                    <td
                      className={`text-right font-mono ${
                        t.r_multiple >= 0 ? "text-profit" : "text-loss"
                      }`}
                    >
                      {t.r_multiple.toFixed(1)}R
                    </td>
                    <td className="text-center">
                      <Badge
                        variant={
                          t.status === "CLOSED_TP"
                            ? "success"
                            : t.status === "CLOSED_SL"
                            ? "danger"
                            : "warning"
                        }
                      >
                        {t.status.replace("CLOSED_", "")}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
