import { useEffect, useMemo, useState } from "react";
import {
  Bell, BellRing, Plus, Trash2, RotateCcw, AlertTriangle, Activity, X,
} from "lucide-react";
import { Card, Badge, Loader, ErrorMsg, EmptyState, InsightTile } from "../components/UI";
import { fetchAlerts, createAlert, deleteAlert, resetAlert } from "../api";

/* ──────────────────────────────────────────────────────────────
   Alerts — server-side persistent alert manager.

   - Backend evaluates alerts on every list call (every 5s here)
     against fresh price + RSI data, so triggers fire even if the
     user closes the browser.
   - User can reset (re-arm) a triggered alert or delete it.
   ────────────────────────────────────────────────────────────── */

const KIND_OPTIONS = [
  { id: "above",     label: "Price crosses above", unit: "₹" },
  { id: "below",     label: "Price crosses below", unit: "₹" },
  { id: "rsi_above", label: "RSI crosses above",   unit: "" },
  { id: "rsi_below", label: "RSI crosses below",   unit: "" },
];

const KIND_META = Object.fromEntries(KIND_OPTIONS.map((k) => [k.id, k]));

function NewAlertForm({ onCreated, onClose }) {
  const [symbol, setSymbol] = useState("");
  const [kind, setKind] = useState("above");
  const [value, setValue] = useState("");
  const [note, setNote] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [err, setErr] = useState(null);

  const submit = async (e) => {
    e.preventDefault();
    setErr(null);
    const num = parseFloat(value);
    if (!symbol.trim() || Number.isNaN(num)) {
      setErr("Symbol and value are required.");
      return;
    }
    setSubmitting(true);
    try {
      const created = await createAlert({
        symbol: symbol.trim(),
        kind,
        value: num,
        note: note.trim() || null,
      });
      onCreated(created);
      setSymbol("");
      setValue("");
      setNote("");
    } catch (e) {
      setErr(e.message || "Failed to create alert");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={submit} className="space-y-3">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <label className="text-[10px] uppercase tracking-wider text-muted font-mono">Symbol</label>
          <input
            value={symbol}
            onChange={(e) => setSymbol(e.target.value.toUpperCase())}
            placeholder="RELIANCE"
            className="w-full mt-1 bg-base/80 border border-gold/20 rounded px-3 py-2 text-sm font-mono text-gold-bright focus:border-gold outline-none"
          />
        </div>
        <div>
          <label className="text-[10px] uppercase tracking-wider text-muted font-mono">Condition</label>
          <select
            value={kind}
            onChange={(e) => setKind(e.target.value)}
            className="w-full mt-1 bg-base/80 border border-gold/20 rounded px-3 py-2 text-sm text-gray-200 focus:border-gold outline-none"
          >
            {KIND_OPTIONS.map((k) => (
              <option key={k.id} value={k.id}>{k.label}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-[10px] uppercase tracking-wider text-muted font-mono">
            Threshold {KIND_META[kind].unit ? `(${KIND_META[kind].unit})` : ""}
          </label>
          <input
            type="number"
            step="0.01"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder={kind.startsWith("rsi") ? "70" : "1500"}
            className="w-full mt-1 bg-base/80 border border-gold/20 rounded px-3 py-2 text-sm font-mono text-gold-bright focus:border-gold outline-none"
          />
        </div>
        <div>
          <label className="text-[10px] uppercase tracking-wider text-muted font-mono">Note (optional)</label>
          <input
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Watch for breakout"
            className="w-full mt-1 bg-base/80 border border-gold/20 rounded px-3 py-2 text-sm text-gray-200 focus:border-gold outline-none"
          />
        </div>
      </div>

      {err && <p className="text-xs text-red-400">{err}</p>}

      <div className="flex items-center gap-2">
        <button
          type="submit"
          disabled={submitting}
          className="btn-primary disabled:opacity-50"
        >
          {submitting ? "Saving..." : "Create Alert"}
        </button>
        <button
          type="button"
          onClick={onClose}
          className="px-3 py-2 text-xs text-muted hover:text-gold transition-colors"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}

function AlertRow({ alert, onDelete, onReset }) {
  const meta = KIND_META[alert.kind] || { label: alert.kind, unit: "" };
  const triggered = alert.triggered;
  const triggeredAt = alert.triggered_at ? new Date(alert.triggered_at) : null;

  return (
    <tr className="hover:bg-gold/[0.04] transition-colors">
      <td>
        <div className="flex items-center gap-2">
          {triggered ? (
            <BellRing size={14} className="text-amber-400 animate-pulse" />
          ) : (
            <Bell size={14} className="text-muted" />
          )}
          <span className="font-semibold text-gold-bright">{alert.symbol}</span>
        </div>
      </td>
      <td className="text-gray-300 text-xs">{meta.label}</td>
      <td className="font-mono text-gray-200">
        {meta.unit}{alert.value}
      </td>
      <td>
        {triggered ? (
          <Badge variant="warning">Triggered</Badge>
        ) : (
          <Badge variant="success">Armed</Badge>
        )}
      </td>
      <td className="text-xs text-muted">
        {triggered && triggeredAt
          ? `${triggeredAt.toLocaleDateString()} ${triggeredAt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`
          : "—"}
      </td>
      <td className="text-xs font-mono text-gray-300">
        {triggered && alert.triggered_price != null ? `₹${alert.triggered_price.toFixed(2)}` : "—"}
      </td>
      <td className="text-xs text-muted max-w-[200px] truncate">{alert.note || "—"}</td>
      <td>
        <div className="flex items-center gap-1 justify-end">
          {triggered && (
            <button
              onClick={() => onReset(alert.id)}
              title="Re-arm alert"
              className="p-1.5 text-muted hover:text-matrix transition-colors"
            >
              <RotateCcw size={13} />
            </button>
          )}
          <button
            onClick={() => onDelete(alert.id)}
            title="Delete alert"
            className="p-1.5 text-muted hover:text-red-400 transition-colors"
          >
            <Trash2 size={13} />
          </button>
        </div>
      </td>
    </tr>
  );
}

export default function Alerts() {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [filter, setFilter] = useState("all"); // all / armed / triggered

  const load = async () => {
    try {
      const data = await fetchAlerts();
      setAlerts(data);
      setError(null);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  // Initial + every 30s while page open
  useEffect(() => {
    load();
    const t = setInterval(load, 30_000);
    return () => clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleDelete = async (id) => {
    if (!confirm("Delete this alert?")) return;
    try {
      await deleteAlert(id);
      setAlerts((cur) => cur.filter((a) => a.id !== id));
    } catch (e) {
      alert(`Delete failed: ${e.message}`);
    }
  };

  const handleReset = async (id) => {
    try {
      const updated = await resetAlert(id);
      setAlerts((cur) => cur.map((a) => (a.id === id ? updated : a)));
    } catch (e) {
      alert(`Reset failed: ${e.message}`);
    }
  };

  const handleCreated = (created) => {
    setAlerts((cur) => [created, ...cur]);
    setShowForm(false);
  };

  const filtered = useMemo(() => {
    if (filter === "armed") return alerts.filter((a) => !a.triggered);
    if (filter === "triggered") return alerts.filter((a) => a.triggered);
    return alerts;
  }, [alerts, filter]);

  const stats = useMemo(() => ({
    total: alerts.length,
    armed: alerts.filter((a) => !a.triggered).length,
    triggered: alerts.filter((a) => a.triggered).length,
  }), [alerts]);

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <Bell size={20} className="text-gold" />
            Alerts
          </h2>
          <p className="text-xs text-muted mt-0.5 font-medium">
            Server-side price &amp; RSI alerts. Evaluated automatically on every load.
          </p>
        </div>
        <button
          onClick={() => setShowForm((s) => !s)}
          className="btn-primary flex items-center gap-1.5"
        >
          {showForm ? <><X size={14} /> Close</> : <><Plus size={14} /> New Alert</>}
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-3">
        {[
          { label: "Total", value: stats.total, color: "text-gold" },
          { label: "Armed", value: stats.armed, color: "text-matrix" },
          { label: "Triggered", value: stats.triggered, color: "text-amber-400" },
        ].map((s) => (
          <div key={s.label} className="glass-card p-4">
            <p className="text-[10px] font-semibold uppercase tracking-widest text-muted">{s.label}</p>
            <p className={`stat-value text-2xl mt-1 ${s.color}`}>{s.value}</p>
          </div>
        ))}
      </div>

      {/* New form */}
      {showForm && (
        <Card title="Create New Alert">
          <NewAlertForm onCreated={handleCreated} onClose={() => setShowForm(false)} />
        </Card>
      )}

      {/* Filters */}
      <div className="flex items-center gap-2 text-xs">
        {[
          { id: "all",       label: `All (${stats.total})` },
          { id: "armed",     label: `Armed (${stats.armed})` },
          { id: "triggered", label: `Triggered (${stats.triggered})` },
        ].map((f) => (
          <button
            key={f.id}
            onClick={() => setFilter(f.id)}
            className={`px-3 py-1.5 rounded-md font-mono text-[11px] border transition-all ${
              filter === f.id
                ? "bg-gold/15 text-gold border-gold/30"
                : "bg-surface-2/40 text-muted border-gold/10 hover:text-gold-bright hover:border-gold/20"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Hint */}
      <InsightTile
        icon={<Activity size={14} />}
        title="How it works"
        body="Alerts are stored on the server and re-evaluated every time anyone hits the Alerts endpoint (or every 30s while this page is open). They keep firing even after you close the browser."
      />

      {/* Table */}
      <Card title={`Alerts (${filtered.length})`} noPad>
        {loading ? (
          <Loader />
        ) : error ? (
          <div className="p-4"><ErrorMsg message={error} /></div>
        ) : filtered.length === 0 ? (
          <EmptyState
            icon={<AlertTriangle size={32} />}
            title="No alerts yet"
            message={filter === "all" ? "Create your first price or RSI alert above." : "No alerts in this category."}
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="pro-table w-full">
              <thead>
                <tr>
                  <th className="text-left">Symbol</th>
                  <th className="text-left">Condition</th>
                  <th className="text-left">Threshold</th>
                  <th className="text-left">Status</th>
                  <th className="text-left">Triggered At</th>
                  <th className="text-left">Last Price</th>
                  <th className="text-left">Note</th>
                  <th className="text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((a) => (
                  <AlertRow
                    key={a.id}
                    alert={a}
                    onDelete={handleDelete}
                    onReset={handleReset}
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
