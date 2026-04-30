/* ──────────────────────────────────────────────────────────────
   Alerts engine — pure functions (testable).

   Alert shape:
   {
     id: string,              // uuid
     symbol: string,          // e.g. "RELIANCE"
     kind: "above" | "below" | "rsi_above" | "rsi_below",
     value: number,           // threshold
     note?: string,
     createdAt: number,       // ms epoch
     triggered: boolean,
     triggeredAt?: number,
     triggeredPrice?: number
   }
   ────────────────────────────────────────────────────────────── */

export const ALERT_KINDS = [
  { id: "above",     label: "Price crosses above", unit: "₹" },
  { id: "below",     label: "Price crosses below", unit: "₹" },
  { id: "rsi_above", label: "RSI crosses above",   unit: "" },
  { id: "rsi_below", label: "RSI crosses below",   unit: "" },
];

const STORAGE_KEY = "stonks_alerts_v1";

export function loadAlerts() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function saveAlerts(list) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(list));
  } catch { /* quota / private mode — ignore */ }
}

export function makeAlert({ symbol, kind, value, note }) {
  return {
    id: (crypto?.randomUUID && crypto.randomUUID()) || `a_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    symbol: String(symbol || "").toUpperCase().trim(),
    kind,
    value: Number(value),
    note: note || "",
    createdAt: Date.now(),
    triggered: false,
  };
}

/**
 * Decide whether an alert should fire given a market snapshot.
 * snapshot: { price?: number, rsi?: number }
 * Returns true when condition met. Pure function — easy to unit test.
 */
export function shouldFire(alert, snapshot) {
  if (!alert || alert.triggered || !snapshot) return false;
  const { kind, value } = alert;
  const { price, rsi } = snapshot;
  switch (kind) {
    case "above":     return typeof price === "number" && price >= value;
    case "below":     return typeof price === "number" && price <= value;
    case "rsi_above": return typeof rsi === "number" && rsi >= value;
    case "rsi_below": return typeof rsi === "number" && rsi <= value;
    default:          return false;
  }
}

/**
 * Evaluate every alert against a { symbol -> snapshot } map.
 * Returns a new array with `triggered`/`triggeredAt`/`triggeredPrice` updated.
 */
export function evaluateAlerts(alerts, snapshots) {
  if (!Array.isArray(alerts) || !alerts.length) return alerts || [];
  const now = Date.now();
  return alerts.map((a) => {
    if (a.triggered) return a;
    const snap = snapshots?.[a.symbol];
    if (snap && shouldFire(a, snap)) {
      return { ...a, triggered: true, triggeredAt: now, triggeredPrice: snap.price };
    }
    return a;
  });
}
