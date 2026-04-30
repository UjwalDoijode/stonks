import { describe, it, expect } from "vitest";
import {
  shouldFire,
  evaluateAlerts,
  makeAlert,
  loadAlerts,
  saveAlerts,
  ALERT_KINDS,
} from "../src/lib/alerts.js";

describe("ALERT_KINDS", () => {
  it("exposes the four supported kinds", () => {
    expect(ALERT_KINDS.map((k) => k.id).sort()).toEqual(
      ["above", "below", "rsi_above", "rsi_below"].sort()
    );
  });
});

describe("makeAlert()", () => {
  it("normalizes the symbol to upper-case and trimmed", () => {
    const a = makeAlert({ symbol: "  reliance  ", kind: "above", value: 1500 });
    expect(a.symbol).toBe("RELIANCE");
    expect(a.kind).toBe("above");
    expect(a.value).toBe(1500);
    expect(a.triggered).toBe(false);
    expect(typeof a.id).toBe("string");
    expect(a.id.length).toBeGreaterThan(0);
  });

  it("coerces value to a number", () => {
    const a = makeAlert({ symbol: "TCS", kind: "below", value: "3500" });
    expect(a.value).toBe(3500);
  });
});

describe("shouldFire()", () => {
  const base = makeAlert({ symbol: "RELIANCE", kind: "above", value: 1500 });

  it("fires when price meets the 'above' threshold", () => {
    expect(shouldFire(base, { price: 1500 })).toBe(true);
    expect(shouldFire(base, { price: 1501 })).toBe(true);
  });

  it("does NOT fire when price is below the 'above' threshold", () => {
    expect(shouldFire(base, { price: 1499 })).toBe(false);
  });

  it("fires when price meets the 'below' threshold", () => {
    const a = makeAlert({ symbol: "TCS", kind: "below", value: 3000 });
    expect(shouldFire(a, { price: 3000 })).toBe(true);
    expect(shouldFire(a, { price: 2999 })).toBe(true);
    expect(shouldFire(a, { price: 3001 })).toBe(false);
  });

  it("evaluates RSI bounds", () => {
    const upper = makeAlert({ symbol: "INFY", kind: "rsi_above", value: 70 });
    const lower = makeAlert({ symbol: "INFY", kind: "rsi_below", value: 30 });
    expect(shouldFire(upper, { rsi: 71 })).toBe(true);
    expect(shouldFire(upper, { rsi: 69 })).toBe(false);
    expect(shouldFire(lower, { rsi: 29 })).toBe(true);
    expect(shouldFire(lower, { rsi: 31 })).toBe(false);
  });

  it("does not fire if the relevant value is missing", () => {
    expect(shouldFire(base, {})).toBe(false);
    const r = makeAlert({ symbol: "X", kind: "rsi_above", value: 50 });
    expect(shouldFire(r, { price: 100 })).toBe(false);
  });

  it("never re-fires an already-triggered alert", () => {
    const a = { ...base, triggered: true };
    expect(shouldFire(a, { price: 9999 })).toBe(false);
  });

  it("returns false for unknown kinds", () => {
    expect(shouldFire({ kind: "weird", value: 1, triggered: false }, { price: 5 })).toBe(false);
  });
});

describe("evaluateAlerts()", () => {
  it("marks matching alerts triggered with timestamp + price", () => {
    const a = makeAlert({ symbol: "RELIANCE", kind: "above", value: 1500 });
    const b = makeAlert({ symbol: "TCS", kind: "above", value: 5000 });
    const out = evaluateAlerts([a, b], { RELIANCE: { price: 1600 }, TCS: { price: 4000 } });
    const fired = out.find((x) => x.id === a.id);
    const unfired = out.find((x) => x.id === b.id);
    expect(fired.triggered).toBe(true);
    expect(fired.triggeredPrice).toBe(1600);
    expect(typeof fired.triggeredAt).toBe("number");
    expect(unfired.triggered).toBe(false);
  });

  it("is a no-op when alerts list is empty / missing", () => {
    expect(evaluateAlerts([], {})).toEqual([]);
    expect(evaluateAlerts(null, {})).toEqual([]);
  });

  it("preserves already-triggered alerts unchanged", () => {
    const a = { ...makeAlert({ symbol: "X", kind: "above", value: 1 }), triggered: true, triggeredAt: 123 };
    const out = evaluateAlerts([a], { X: { price: 999 } });
    expect(out[0].triggeredAt).toBe(123);
  });
});

describe("loadAlerts() / saveAlerts()", () => {
  it("round-trips a list through localStorage", () => {
    const a = makeAlert({ symbol: "RELIANCE", kind: "below", value: 1000 });
    saveAlerts([a]);
    const loaded = loadAlerts();
    expect(loaded).toHaveLength(1);
    expect(loaded[0].symbol).toBe("RELIANCE");
  });

  it("returns [] when storage is empty", () => {
    localStorage.clear();
    expect(loadAlerts()).toEqual([]);
  });

  it("returns [] when storage contains garbage", () => {
    localStorage.setItem("stonks_alerts_v1", "{not json");
    expect(loadAlerts()).toEqual([]);
  });
});
