import { useState } from "react";
import { Card, StatCard, ErrorMsg } from "../components/UI";
import { calcPositionSize } from "../api";

export default function PositionSizer() {
  const [form, setForm] = useState({
    capital: "20000",
    entry_price: "",
    stop_loss: "",
    risk_pct: "1.5",
  });
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleCalc = async (e) => {
    e.preventDefault();
    setError(null);
    try {
      const res = await calcPositionSize({
        capital: parseFloat(form.capital),
        entry_price: parseFloat(form.entry_price),
        stop_loss: parseFloat(form.stop_loss),
        risk_pct: parseFloat(form.risk_pct),
      });
      setResult(res);
    } catch (e) {
      setError(e.message);
    }
  };

  return (
    <div className="space-y-6 max-w-3xl animate-fade-in">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Position Size Calculator</h2>
        <p className="text-xs text-muted mt-0.5 font-medium">Risk-based position sizing with R:R ratio</p>
      </div>

      <Card title="Input">
        <form onSubmit={handleCalc} className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-[10px] text-muted mb-1 font-semibold uppercase tracking-wider">Capital (₹)</label>
            <input
              type="number"
              value={form.capital}
              onChange={(e) => setForm({ ...form, capital: e.target.value })}
              className="w-full bg-base border border-border rounded-lg px-3 py-2 text-sm font-mono focus:border-blue-500/40 outline-none transition-colors"
              required
            />
          </div>
          <div>
            <label className="block text-[10px] text-muted mb-1 font-semibold uppercase tracking-wider">
              Risk per Trade (%)
            </label>
            <input
              type="number"
              step="0.1"
              value={form.risk_pct}
              onChange={(e) => setForm({ ...form, risk_pct: e.target.value })}
              className="w-full bg-base border border-border rounded-lg px-3 py-2 text-sm font-mono focus:border-blue-500/40 outline-none transition-colors"
              required
            />
          </div>
          <div>
            <label className="block text-[10px] text-muted mb-1 font-semibold uppercase tracking-wider">Entry Price (₹)</label>
            <input
              type="number"
              step="0.01"
              value={form.entry_price}
              onChange={(e) => setForm({ ...form, entry_price: e.target.value })}
              className="w-full bg-base border border-border rounded-lg px-3 py-2 text-sm font-mono focus:border-blue-500/40 outline-none transition-colors"
              required
            />
          </div>
          <div>
            <label className="block text-[10px] text-muted mb-1 font-semibold uppercase tracking-wider">Stop Loss (₹)</label>
            <input
              type="number"
              step="0.01"
              value={form.stop_loss}
              onChange={(e) => setForm({ ...form, stop_loss: e.target.value })}
              className="w-full bg-base border border-border rounded-lg px-3 py-2 text-sm font-mono focus:border-blue-500/40 outline-none transition-colors"
              required
            />
          </div>
          <div className="col-span-2">
            <button type="submit" className="w-full btn-primary">Calculate</button>
          </div>
        </form>
      </Card>

      {error && <ErrorMsg message={error} />}

      {result && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard label="Quantity" value={result.quantity} color="text-accent" />
          <StatCard
            label="Position Size"
            value={`₹${result.position_size.toLocaleString("en-IN")}`}
          />
          <StatCard
            label="Risk Amount"
            value={`₹${result.risk_amount.toFixed(0)}`}
            color="text-loss"
          />
          <StatCard
            label="Risk/Share"
            value={`₹${result.risk_per_share.toFixed(2)}`}
          />
          <StatCard
            label="Target Price"
            value={`₹${result.target_price.toFixed(2)}`}
            color="text-profit"
          />
          <StatCard
            label="Reward"
            value={`₹${result.reward_amount.toFixed(0)}`}
            color="text-profit"
          />
          <StatCard label="R:R Ratio" value={`1:${result.risk_reward_ratio}`} />
          <StatCard
            label="Capital Used"
            value={`${result.capital_used_pct.toFixed(1)}%`}
            color={result.capital_used_pct > 50 ? "text-yellow-400" : "text-gray-100"}
          />
        </div>
      )}
    </div>
  );
}
