import { useState, useRef, useEffect } from "react";
import {
  LayoutDashboard, Search, ArrowLeftRight, Calculator,
  FlaskConical, TrendingUp, PieChart, Crosshair, Star,
  Activity, Sparkles, Shield, Pencil, Check, X,
  Globe, FileText, Bot, MessageSquare, Newspaper,
} from "lucide-react";

const NAV = [
  { id: "dashboard",  label: "Dashboard",      icon: LayoutDashboard },
  { id: "ai",         label: "AI Assistant",    icon: Sparkles },
  { id: "scanner",    label: "Scanner",         icon: Search },
  { id: "advisor",    label: "Smart Advisor",   icon: MessageSquare },
  { id: "risk",       label: "Risk Control",    icon: Shield },
  { id: "algos",      label: "Algo Lab",        icon: Bot },
  { id: "trades",     label: "Trades",          icon: ArrowLeftRight },
  { id: "backtest",   label: "Backtest",        icon: FlaskConical },
  { id: "news",       label: "News",            icon: Newspaper },
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
    <aside className="w-60 bg-surface border-r border-gold/10 flex flex-col select-none relative overflow-hidden">
      {/* Subtle matrix rain background */}
      <div className="absolute inset-0 opacity-[0.02] pointer-events-none" style={{
        backgroundImage: `repeating-linear-gradient(0deg, transparent, transparent 20px, rgba(0,255,65,0.03) 20px, rgba(0,255,65,0.03) 21px)`,
      }} />

      {/* Logo */}
      <div className="px-5 pt-6 pb-4 relative z-10">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-gold to-gold-dark flex items-center justify-center shadow-glow-gold">
            <Activity size={16} className="text-base" />
          </div>
          <div>
            <h1 className="text-base font-bold text-gold-bright tracking-tight font-display">STONKS</h1>
            <p className="text-[8px] font-semibold uppercase tracking-[0.2em] text-matrix font-mono">Terminal v2.0</p>
          </div>
        </div>
      </div>

      {/* Divider */}
      <div className="mx-4 h-px bg-gradient-to-r from-transparent via-gold/20 to-transparent mb-2" />

      {/* Navigation */}
      <nav className="flex-1 px-3 py-2 space-y-0.5 overflow-y-auto relative z-10">
        {NAV.map(({ id, label, icon: Icon }) => {
          const isActive = active === id;
          return (
            <button
              key={id}
              onClick={() => onNavigate(id)}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-md text-[12px] font-medium transition-all duration-200 ${
                isActive
                  ? "bg-gold/10 text-gold border border-gold/20 shadow-sm"
                  : "text-muted hover:text-gold-bright hover:bg-gold/[0.04] border border-transparent"
              }`}
            >
              <Icon size={15} strokeWidth={isActive ? 2.2 : 1.6} />
              <span className="font-sans">{label}</span>
              {isActive && (
                <div className="ml-auto w-1.5 h-1.5 rounded-full bg-matrix shadow-glow-green status-live" />
              )}
            </button>
          );
        })}
      </nav>

      {/* Bottom — Editable Capital */}
      <div className="px-4 py-4 border-t border-gold/10 relative z-10">
        <div className="flex items-center justify-between text-[11px]">
          <span className="text-muted font-mono uppercase text-[9px] tracking-wider">Capital</span>
          {editing ? (
            <div className="flex items-center gap-1">
              <span className="text-gold font-mono">₹</span>
              <input
                ref={inputRef}
                type="number"
                min="1000"
                step="1000"
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={handleKeyDown}
                onBlur={confirmEdit}
                className="w-20 bg-base/80 border border-gold/30 rounded px-1.5 py-0.5 text-[11px] font-mono font-semibold text-gold-bright outline-none focus:border-gold text-right"
              />
              <button onClick={confirmEdit} className="p-0.5 text-matrix hover:text-matrix transition-colors">
                <Check size={12} />
              </button>
              <button onClick={cancelEdit} className="p-0.5 text-danger hover:text-danger transition-colors">
                <X size={12} />
              </button>
            </div>
          ) : (
            <button
              onClick={startEdit}
              className="group flex items-center gap-1.5 font-mono font-semibold text-gold hover:text-gold-bright transition-colors cursor-pointer"
              title="Click to edit capital"
            >
              <span>₹{Math.round(capital).toLocaleString("en-IN")}</span>
              <Pencil size={10} className="text-muted opacity-0 group-hover:opacity-100 transition-opacity" />
            </button>
          )}
        </div>
        <div className="flex items-center justify-between text-[11px] mt-1.5">
          <span className="text-muted font-mono uppercase text-[9px] tracking-wider">Universe</span>
          <span className="pro-badge">NIFTY 500</span>
        </div>
        <div className="flex items-center justify-between text-[11px] mt-1.5">
          <span className="text-muted font-mono uppercase text-[9px] tracking-wider">Status</span>
          <span className="flex items-center gap-1.5 font-mono text-[10px]">
            <span className="w-1.5 h-1.5 rounded-full bg-matrix status-live" />
            <span className="text-matrix">ONLINE</span>
          </span>
        </div>
      </div>
    </aside>
  );
}
