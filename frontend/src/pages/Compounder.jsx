import { useState } from "react";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer,
} from "recharts";
import { Card, StatCard, ErrorMsg } from "../components/UI";
import { simulateCompounding } from "../api";

export default function Compounder() {
  const [form, setForm] = useState({
    initial_capital: "20000",
    monthly_return_pct: "3",
    monthly_addition: "5000",
    years: "5",
  });
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleCalc = async (e) => {
    e.preventDefault();
    setError(null);
    try {
      const res = await simulateCompounding({
        initial_capital: parseFloat(form.initial_capital),
        monthly_return_pct: parseFloat(form.monthly_return_pct),
        monthly_addition: parseFloat(form.monthly_addition),
        years: parseInt(form.years),
      });
      setResult(res);
    } catch (e) {
      setError(e.message);
    }
  };

  return (
    <div className="space-y-6 max-w-4xl animate-fade-in">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Compounding Simulator</h2>
        <p className="text-xs text-muted mt-0.5 font-medium">Visualize the power of compound growth</p>
      </div>

      <Card title="Parameters">
        <form onSubmit={handleCalc} className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-[10px] text-muted mb-1 font-semibold uppercase tracking-wider">
              Initial Capital (₹)
            </label>
            <input
              type="number"
              value={form.initial_capital}
              onChange={(e) => setForm({ ...form, initial_capital: e.target.value })}
              className="w-full bg-base border border-border rounded-lg px-3 py-2 text-sm font-mono focus:border-blue-500/40 outline-none transition-colors"
              required
            />
          </div>
          <div>
            <label className="block text-[10px] text-muted mb-1 font-semibold uppercase tracking-wider">
              Monthly Return (%)
            </label>
            <input
              type="number"
              step="0.1"
              value={form.monthly_return_pct}
              onChange={(e) => setForm({ ...form, monthly_return_pct: e.target.value })}
              className="w-full bg-base border border-border rounded-lg px-3 py-2 text-sm font-mono focus:border-blue-500/40 outline-none transition-colors"
              required
            />
          </div>
          <div>
            <label className="block text-[10px] text-muted mb-1 font-semibold uppercase tracking-wider">
              Monthly Addition (₹)
            </label>
            <input
              type="number"
              value={form.monthly_addition}
              onChange={(e) => setForm({ ...form, monthly_addition: e.target.value })}
              className="w-full bg-base border border-border rounded-lg px-3 py-2 text-sm font-mono focus:border-blue-500/40 outline-none transition-colors"
              required
            />
          </div>
          <div>
            <label className="block text-[10px] text-muted mb-1 font-semibold uppercase tracking-wider">Years</label>
            <input
              type="number"
              min="1"
              max="30"
              value={form.years}
              onChange={(e) => setForm({ ...form, years: e.target.value })}
              className="w-full bg-base border border-border rounded-lg px-3 py-2 text-sm font-mono focus:border-blue-500/40 outline-none transition-colors"
              required
            />
          </div>
          <div className="col-span-2 md:col-span-4">
            <button type="submit" className="w-full btn-primary">Simulate</button>
          </div>
        </form>
      </Card>

      {error && <ErrorMsg message={error} />}

      {result && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard
              label="Final Capital"
              value={`₹${result.final_capital.toLocaleString("en-IN")}`}
              color="text-profit"
            />
            <StatCard
              label="Total Return"
              value={`${result.total_return_pct.toFixed(0)}%`}
              color="text-profit"
            />
            <StatCard label="CAGR" value={`${result.cagr.toFixed(1)}%`} />
            <StatCard
              label="Growth Multiple"
              value={`${(result.final_capital / result.initial_capital).toFixed(1)}x`}
              color="text-accent"
            />
          </div>

          <Card title="Growth Curve">
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={result.curve}>
                  <defs>
                    <linearGradient id="compGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(30,41,59,0.5)" vertical={false} />
                  <XAxis
                    dataKey="month"
                    tick={{ fontSize: 11, fill: "#64748b" }}
                    label={{ value: "Months", position: "insideBottom", fill: "#64748b", offset: -5 }}
                    tickLine={false} axisLine={false}
                  />
                  <YAxis tick={{ fontSize: 11, fill: "#64748b" }} tickLine={false} axisLine={false} width={60} />
                  <Tooltip
                    contentStyle={{
                      background: "rgba(17,24,39,0.95)",
                      border: "1px solid rgba(30,41,59,0.8)",
                      borderRadius: 8,
                      fontSize: 12,
                      backdropFilter: "blur(12px)",
                    }}
                    formatter={(val) => [`₹${val.toLocaleString("en-IN")}`, "Capital"]}
                    labelFormatter={(label) => `Month ${label}`}
                  />
                  <Area
                    type="monotone"
                    dataKey="capital"
                    stroke="#6366f1"
                    fill="url(#compGrad)"
                    strokeWidth={2}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
