import { useState, useRef, useEffect } from "react";
import {
  LayoutDashboard, Search, ArrowLeftRight, Calculator,
  FlaskConical, TrendingUp, PieChart, Crosshair, Star,
  Activity, Sparkles, Shield, Pencil, Check, X,
} from "lucide-react";

const NAV = [
  { id: "dashboard",  label: "Dashboard",      icon: LayoutDashboard },
  { id: "risk",       label: "Risk Control",    icon: Shield },
  { id: "advisor",    label: "Smart Advisor",   icon: Sparkles },
  { id: "deployment", label: "Deployment",      icon: Crosshair },
  { id: "allocation", label: "Allocation",      icon: PieChart },
  { id: "scanner",    label: "Scanner",         icon: Search },
  { id: "watchlist",  label: "Watchlist",        icon: Star },
  { id: "trades",     label: "Trades",          icon: ArrowLeftRight },
  { id: "sizer",      label: "Position Sizer",  icon: Calculator },
  { id: "backtest",   label: "Backtest",        icon: FlaskConical },
  { id: "compounder", label: "Compounder",      icon: TrendingUp },
];

export default function Sidebar({ active, onNavigate, capital, setCapital }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const inputRef = useRef(null);

  useEffect(() => {
    if (editing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [editing]);

  const startEdit = () => {
    setDraft(String(Math.round(capital)));
    setEditing(true);
  };

  const confirmEdit = () => {
    const num = parseFloat(draft);
    if (!isNaN(num) && num >= 1000) {
      setCapital(num);
    }
    setEditing(false);
  };

  const cancelEdit = () => setEditing(false);

  const handleKeyDown = (e) => {
    if (e.key === "Enter") confirmEdit();
    if (e.key === "Escape") cancelEdit();
  };

  return (
    <aside className="w-60 bg-surface border-r border-border/60 flex flex-col select-none">
      {/* Logo */}
      <div className="px-5 pt-6 pb-4">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shadow-glow">
            <Activity size={16} className="text-white" />
          </div>
          <div>
            <h1 className="text-base font-bold text-white tracking-tight">Stonks</h1>
            <p className="text-[9px] font-semibold uppercase tracking-[0.15em] text-muted">Trading Engine</p>
          </div>
        </div>
      </div>

      {/* Divider */}
      <div className="mx-4 h-px bg-border/60 mb-2" />

      {/* Navigation */}
      <nav className="flex-1 px-3 py-2 space-y-0.5 overflow-y-auto">
        {NAV.map(({ id, label, icon: Icon }) => {
          const isActive = active === id;
          return (
            <button
              key={id}
              onClick={() => onNavigate(id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-[13px] font-medium transition-all duration-150 ${
                isActive
                  ? "bg-blue-500/10 text-blue-400 shadow-sm"
                  : "text-gray-400 hover:text-gray-200 hover:bg-white/[0.04]"
              }`}
            >
              <Icon size={16} strokeWidth={isActive ? 2.2 : 1.8} />
              <span>{label}</span>
              {isActive && (
                <div className="ml-auto w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse-slow" />
              )}
            </button>
          );
        })}
      </nav>

      {/* Bottom — Editable Capital */}
      <div className="px-4 py-4 border-t border-border/40">
        <div className="flex items-center justify-between text-[11px]">
          <span className="text-muted font-medium">Capital</span>
          {editing ? (
            <div className="flex items-center gap-1">
              <span className="text-gray-400 font-mono">₹</span>
              <input
                ref={inputRef}
                type="number"
                min="1000"
                step="1000"
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={handleKeyDown}
                onBlur={confirmEdit}
                className="w-20 bg-base/80 border border-blue-500/50 rounded px-1.5 py-0.5 text-[11px] font-mono font-semibold text-white outline-none focus:border-blue-400 text-right"
              />
              <button onClick={confirmEdit} className="p-0.5 text-emerald-400 hover:text-emerald-300 transition-colors">
                <Check size={12} />
              </button>
              <button onClick={cancelEdit} className="p-0.5 text-red-400 hover:text-red-300 transition-colors">
                <X size={12} />
              </button>
            </div>
          ) : (
            <button
              onClick={startEdit}
              className="group flex items-center gap-1.5 font-mono font-semibold text-gray-300 hover:text-blue-400 transition-colors cursor-pointer"
              title="Click to edit capital"
            >
              <span>₹{Math.round(capital).toLocaleString("en-IN")}</span>
              <Pencil size={10} className="text-muted opacity-0 group-hover:opacity-100 transition-opacity" />
            </button>
          )}
        </div>
        <div className="flex items-center justify-between text-[11px] mt-1">
          <span className="text-muted font-medium">Universe</span>
          <span className="pro-badge text-blue-400">NIFTY 500</span>
        </div>
      </div>
    </aside>
  );
}
