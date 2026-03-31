/* ─── Professional UI Component Library ──────────────── */

export function Card({ title, children, className = "", action, noPad = false }) {
  return (
    <div className={`glass-card animate-fade-in ${className}`}>
      {title && (
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-gold/10">
          <h3 className="text-[10px] font-semibold uppercase tracking-[0.15em] text-gold font-mono">{title}</h3>
          {action && action}
        </div>
      )}
      <div className={noPad ? "" : "p-5"}>{children}</div>
    </div>
  );
}

export function StatCard({ label, value, sub, color = "text-gray-100", icon }) {
  return (
    <div className="glass-card p-4 group">
      <div className="flex items-center justify-between mb-1">
        <p className="text-[10px] font-semibold uppercase tracking-widest text-muted">{label}</p>
        {icon && <span className="text-muted/50 group-hover:text-muted transition-colors">{icon}</span>}
      </div>
      <p className={`stat-value text-xl mt-1 ${color}`}>{value}</p>
      {sub && <p className="text-[11px] text-muted mt-1.5 font-medium">{sub}</p>}
    </div>
  );
}

export function Badge({ children, variant = "default" }) {
  const colors = {
    default: "bg-surface-2 text-gray-300 border-gold/10",
    success: "bg-matrix/10 text-matrix border-matrix/20",
    danger: "bg-red-500/10 text-red-400 border-red-500/20",
    warning: "bg-amber-500/10 text-amber-400 border-amber-500/20",
    info: "bg-gold/10 text-gold border-gold/20",
    purple: "bg-purple-500/10 text-purple-400 border-purple-500/20",
  };
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-md text-[11px] font-semibold border font-mono ${colors[variant]}`}>
      {children}
    </span>
  );
}

export function Loader() {
  return (
    <div className="flex flex-col items-center justify-center py-16 gap-3">
      <div className="relative">
        <div className="w-10 h-10 border-2 border-gold/20 rounded-full" />
        <div className="absolute inset-0 w-10 h-10 border-2 border-transparent border-t-gold rounded-full animate-spin" />
      </div>
      <span className="text-xs text-matrix font-mono animate-pulse">Loading data<span className="cursor-blink"></span></span>
    </div>
  );
}

export function ErrorMsg({ message }) {
  return (
    <div className="glass-card border-red-500/30 p-4 animate-fade-in">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-full bg-red-500/10 flex items-center justify-center flex-shrink-0">
          <span className="text-red-400 text-sm">!</span>
        </div>
        <p className="text-red-400 text-sm font-medium">{message}</p>
      </div>
    </div>
  );
}

export function Skeleton({ className = "" }) {
  return (
    <div className={`bg-gradient-to-r from-surface-2/40 via-gold/5 to-surface-2/40 bg-[length:200%_100%] animate-shimmer rounded ${className}`} />
  );
}

export function SkeletonCard() {
  return (
    <div className="glass-card p-4 space-y-3">
      <Skeleton className="h-3 w-20" />
      <Skeleton className="h-7 w-28" />
      <Skeleton className="h-3 w-16" />
    </div>
  );
}

/* ─── Risk Gauge (redesigned) ─────────────────────────── */
export function RiskGauge({ score = 0, label = "" }) {
  const angle = (score / 100) * 180 - 90;
  const getColor = (s) => {
    if (s <= 25) return "#00ff41";
    if (s <= 45) return "#00cc33";
    if (s <= 65) return "#cfb57e";
    if (s <= 80) return "#ff9500";
    return "#ff3232";
  };
  const color = getColor(score);

  return (
    <div className="flex flex-col items-center">
      <svg viewBox="0 0 120 70" className="w-36">
        {/* Background arc */}
        <path
          d="M10 60 A50 50 0 0 1 110 60"
          fill="none"
          stroke="rgba(30,41,59,0.6)"
          strokeWidth="8"
          strokeLinecap="round"
        />
        {/* Filled arc */}
        <path
          d="M10 60 A50 50 0 0 1 110 60"
          fill="none"
          stroke={color}
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={`${(score / 100) * 157} 157`}
          style={{ filter: `drop-shadow(0 0 6px ${color}40)` }}
        />
        {/* Needle */}
        <line
          x1="60" y1="60"
          x2={60 + 35 * Math.cos((angle * Math.PI) / 180)}
          y2={60 - 35 * Math.sin((angle * Math.PI) / 180)}
          stroke={color} strokeWidth="2" strokeLinecap="round"
        />
        <circle cx="60" cy="60" r="3" fill={color} />
        <text x="60" y="55" textAnchor="middle" fill={color} fontSize="16" fontWeight="bold" fontFamily="IBM Plex Mono, monospace">
          {score}
        </text>
      </svg>
      {label && <span className="text-[11px] text-muted mt-1 font-medium">{label}</span>}
    </div>
  );
}

/* ─── Regime Badge (redesigned) ───────────────────────── */
const REGIME_STYLES = {
  STRONG_RISK_ON: { bg: "bg-emerald-500/15", border: "border-emerald-500/30", text: "text-emerald-400", label: "Strong Risk-On", dot: "bg-emerald-400" },
  MILD_RISK_ON:   { bg: "bg-lime-500/15", border: "border-lime-500/30", text: "text-lime-400", label: "Mild Risk-On", dot: "bg-lime-400" },
  NEUTRAL:        { bg: "bg-amber-500/15", border: "border-amber-500/30", text: "text-amber-400", label: "Neutral", dot: "bg-amber-400" },
  RISK_OFF:       { bg: "bg-orange-500/15", border: "border-orange-500/30", text: "text-orange-400", label: "Risk-Off", dot: "bg-orange-400" },
  EXTREME_RISK:   { bg: "bg-red-500/15", border: "border-red-500/30", text: "text-red-400", label: "Extreme Risk", dot: "bg-red-400" },
};

export function RegimeBadge({ regime }) {
  const style = REGIME_STYLES[regime] || REGIME_STYLES.NEUTRAL;
  return (
    <span className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-[11px] font-semibold border ${style.bg} ${style.border} ${style.text}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${style.dot} animate-pulse-slow`} />
      {style.label}
    </span>
  );
}

/* ─── Allocation Donut (redesigned) ───────────────────── */
export function AllocationDonut({ equity = 0, gold = 0, silver = 0, cash = 0 }) {
  const total = equity + gold + silver + cash || 1;
  const segments = [
    { label: "Equity", pct: equity, color: "#cfb57e" },
    { label: "Gold", pct: gold, color: "#e8d5a8" },
    { label: "Silver", pct: silver, color: "#7a8599" },
    { label: "Cash", pct: cash, color: "#00ff41" },
  ].filter((s) => s.pct > 0);

  const radius = 40;
  const circumference = 2 * Math.PI * radius;
  let cumulative = 0;

  return (
    <div className="flex items-center gap-5">
      <svg viewBox="0 0 100 100" className="w-28 h-28">
        {segments.map((seg, i) => {
          const dash = (seg.pct / total) * circumference;
          const offset = -(cumulative / total) * circumference;
          cumulative += seg.pct;
          return (
            <circle
              key={i}
              cx="50" cy="50" r={radius}
              fill="none"
              stroke={seg.color}
              strokeWidth="10"
              strokeDasharray={`${dash} ${circumference - dash}`}
              strokeDashoffset={offset}
              transform="rotate(-90 50 50)"
              style={{ filter: `drop-shadow(0 0 4px ${seg.color}30)` }}
            />
          );
        })}
        {/* Center text */}
        <text x="50" y="48" textAnchor="middle" fill="#cfb57e" fontSize="14" fontWeight="bold" fontFamily="IBM Plex Mono, monospace">
          {equity}%
        </text>
        <text x="50" y="60" textAnchor="middle" fill="#64748b" fontSize="8" fontWeight="500">
          EQUITY
        </text>
      </svg>
      <div className="space-y-2">
        {segments.map((s, i) => (
          <div key={i} className="flex items-center gap-2.5 text-xs">
            <span className="w-2.5 h-2.5 rounded-sm" style={{ background: s.color, boxShadow: `0 0 6px ${s.color}30` }} />
            <span className="text-muted w-12">{s.label}</span>
            <span className="text-gray-200 font-semibold font-mono">{s.pct}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}
