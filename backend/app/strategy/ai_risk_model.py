"""
AI Adaptive Risk Model — LightGBM / XGBoost ensemble for risk prediction.

The AI model is trained on historical macro snapshots + subsequent market returns
to predict:
  1. P(risk-on regime next 5 days)
  2. P(risk-off regime next 5 days)
  3. Expected equity return (5-day forward)
  4. Expected gold return (5-day forward)

Blending:
  Final Risk Score = 0.70 × Rule-Based Score + 0.30 × AI Adjustment

The model auto-trains on startup using available historical data.
If training data is insufficient, the AI component returns neutral (no effect).
"""

import logging
import os
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Lazy imports — only load ML libs when actually needed
_lgb = None
_xgb = None


def _import_ml():
    global _lgb, _xgb
    if _lgb is None:
        try:
            import lightgbm as lgb
            _lgb = lgb
        except ImportError:
            logger.warning("LightGBM not installed — AI risk model disabled")
    if _xgb is None:
        try:
            import xgboost as xgb
            _xgb = xgb
        except ImportError:
            logger.warning("XGBoost not installed — AI risk model disabled")


MODEL_DIR = Path(__file__).parent.parent.parent / "data" / "models"
LGB_MODEL_PATH = MODEL_DIR / "lgb_risk_model.pkl"
XGB_MODEL_PATH = MODEL_DIR / "xgb_risk_model.pkl"
FEATURE_COLS_PATH = MODEL_DIR / "feature_cols.pkl"

# Blend weights
RULE_BASED_WEIGHT = 0.70
AI_WEIGHT = 0.30


@dataclass
class AIRiskPrediction:
    """Output from the AI risk model."""
    ai_risk_score: float = 50.0        # 0-100 risk from AI
    p_risk_on: float = 0.5             # probability of risk-on
    p_risk_off: float = 0.5            # probability of risk-off
    expected_equity_return: float = 0.0 # 5-day expected %
    expected_gold_return: float = 0.0   # 5-day expected %
    confidence: float = 0.0            # model confidence 0-1
    model_available: bool = False
    blend_rule_weight: float = RULE_BASED_WEIGHT
    blend_ai_weight: float = AI_WEIGHT


# ── Feature Engineering ──────────────────────────────────

FEATURE_NAMES = [
    "vix", "vix_sma10", "vix_rising",
    "nifty_dist_200dma_pct", "nifty_dist_50dma_pct",
    "nifty_50dma_slope", "nifty_lower_highs",
    "breadth_pct_above_50dma",
    "sp500_above_200dma", "dxy_breakout", "oil_spike",
    "gold_above_50dma", "gold_rs_vs_nifty",
    "atr_expansion", "gap_frequency",
    "vix_percentile_20d", "nifty_return_5d", "nifty_return_20d",
    "nifty_volatility_20d",
]


def _macro_to_features(macro: dict) -> dict:
    """Convert a macro snapshot dict to a feature vector dict."""
    nifty_close = macro.get("nifty_close", 0)
    nifty_200 = macro.get("nifty_200dma", 1)
    nifty_50 = macro.get("nifty_50dma", 1)

    features = {
        "vix": macro.get("vix", 15.0),
        "vix_sma10": macro.get("vix_sma10", 15.0),
        "vix_rising": int(macro.get("vix_rising", False)),
        "nifty_dist_200dma_pct": ((nifty_close - nifty_200) / nifty_200 * 100) if nifty_200 > 0 else 0,
        "nifty_dist_50dma_pct": ((nifty_close - nifty_50) / nifty_50 * 100) if nifty_50 > 0 else 0,
        "nifty_50dma_slope": macro.get("nifty_50dma_slope", 0),
        "nifty_lower_highs": int(macro.get("nifty_lower_highs", False)),
        "breadth_pct_above_50dma": macro.get("breadth_pct_above_50dma", 50.0),
        "sp500_above_200dma": int(macro.get("sp500_above_200dma", True)),
        "dxy_breakout": int(macro.get("dxy_breakout", False)),
        "oil_spike": int(macro.get("oil_spike", False)),
        "gold_above_50dma": int(macro.get("gold_above_50dma", False)),
        "gold_rs_vs_nifty": macro.get("gold_rs_vs_nifty", 0.0),
        "atr_expansion": int(macro.get("atr_expansion", False)),
        "gap_frequency": macro.get("gap_frequency", 0),
        # These are estimated from available data; in live mode they come from cache
        "vix_percentile_20d": macro.get("vix_percentile_20d", 50.0),
        "nifty_return_5d": macro.get("nifty_return_5d", 0.0),
        "nifty_return_20d": macro.get("nifty_return_20d", 0.0),
        "nifty_volatility_20d": macro.get("nifty_volatility_20d", 0.15),
    }
    return features


# ── Synthetic Training Data ──────────────────────────────

def _generate_training_data() -> tuple[pd.DataFrame, pd.Series]:
    """
    Generate training data from historical NIFTY + VIX data.
    Uses yfinance to fetch 5 years of data and constructs features/labels.
    Label: 1 if next 5 days return > 0 (risk-on), 0 otherwise (risk-off).
    """
    from app.strategy.macro_data import fetch_with_cache
    from app.config import settings

    nifty = fetch_with_cache(settings.NIFTY_SYMBOL, 5)
    vix = fetch_with_cache(settings.VIX_SYMBOL, 5)
    gold = fetch_with_cache(settings.GOLD_SYMBOL, 5)
    sp500 = fetch_with_cache(settings.SP500_SYMBOL, 5)

    if nifty is None or len(nifty) < 300:
        return pd.DataFrame(), pd.Series(dtype=float)

    nc = nifty["close"]

    # Build feature DataFrame daily
    rows = []
    for i in range(250, len(nc) - 5):
        close = float(nc.iloc[i])
        dma200 = float(nc.iloc[i - 199:i + 1].mean())
        dma50 = float(nc.iloc[i - 49:i + 1].mean())
        dma50_prev = float(nc.iloc[i - 59:i - 9].mean()) if i > 59 else dma50
        slope = dma50 - dma50_prev

        ret_5d = float(nc.iloc[i - 4:i + 1].pct_change().sum()) if i > 4 else 0
        ret_20d = float((nc.iloc[i] / nc.iloc[i - 20] - 1) * 100) if i > 20 else 0
        vol_20d = float(nc.iloc[i - 19:i + 1].pct_change().std() * np.sqrt(252)) if i > 20 else 0.15

        v = float(vix["close"].iloc[i]) if vix is not None and i < len(vix) else 15.0
        v_sma = float(vix["close"].iloc[max(0, i - 9):i + 1].mean()) if vix is not None and i < len(vix) else 15.0
        v_pct = 50.0
        if vix is not None and i >= 20 and i < len(vix):
            v_window = vix["close"].iloc[i - 19:i + 1]
            v_pct = float((v_window < v).sum() / len(v_window) * 100)

        g_above = False
        g_rs = 0.0
        if gold is not None and i < len(gold) and len(gold) > 50:
            gc = gold["close"]
            g_above = float(gc.iloc[i]) > float(gc.iloc[max(0, i - 49):i + 1].mean()) if i < len(gc) else False
            if i >= 20 and i < len(gc) and i < len(nc):
                g_ret = float(gc.iloc[i] / gc.iloc[i - 20] - 1)
                n_ret = float(nc.iloc[i] / nc.iloc[i - 20] - 1)
                g_rs = (g_ret - n_ret) * 100

        sp_above = True
        if sp500 is not None and i < len(sp500) and len(sp500) > 200:
            sc = sp500["close"]
            sp_above = float(sc.iloc[i]) > float(sc.iloc[max(0, i - 199):i + 1].mean()) if i < len(sc) else True

        # Rolling high for lower-highs detection
        h20 = float(nc.iloc[max(0, i - 19):i + 1].max())
        h20_prev = float(nc.iloc[max(0, i - 39):max(1, i - 19)].max()) if i > 39 else h20
        lower_highs = h20 < h20_prev * 0.99

        # Future return (label)
        future_ret = float((nc.iloc[i + 5] / nc.iloc[i] - 1) * 100)
        label = 1 if future_ret > 0 else 0

        rows.append({
            "vix": v,
            "vix_sma10": v_sma,
            "vix_rising": int(v > v_sma),
            "nifty_dist_200dma_pct": (close - dma200) / dma200 * 100 if dma200 > 0 else 0,
            "nifty_dist_50dma_pct": (close - dma50) / dma50 * 100 if dma50 > 0 else 0,
            "nifty_50dma_slope": slope,
            "nifty_lower_highs": int(lower_highs),
            "breadth_pct_above_50dma": 50.0,  # approximation for training
            "sp500_above_200dma": int(sp_above),
            "dxy_breakout": 0,  # simplified for training
            "oil_spike": 0,
            "gold_above_50dma": int(g_above),
            "gold_rs_vs_nifty": g_rs,
            "atr_expansion": 0,
            "gap_frequency": 0,
            "vix_percentile_20d": v_pct,
            "nifty_return_5d": ret_5d,
            "nifty_return_20d": ret_20d,
            "nifty_volatility_20d": vol_20d,
            "_label": label,
            "_future_ret": future_ret,
        })

    if not rows:
        return pd.DataFrame(), pd.Series(dtype=float)

    df = pd.DataFrame(rows)
    labels = df["_label"]
    features = df.drop(columns=["_label", "_future_ret"])
    return features, labels


# ── Model Training ───────────────────────────────────────

def train_models(force: bool = False) -> bool:
    """
    Train LightGBM + XGBoost models on historical data.
    Saves models to disk. Returns True if successfully trained.
    """
    _import_ml()

    if not force and LGB_MODEL_PATH.exists() and XGB_MODEL_PATH.exists():
        # Check model age
        age = datetime.now().timestamp() - LGB_MODEL_PATH.stat().st_mtime
        if age < 7 * 86400:  # retrain weekly
            logger.info("AI models are fresh (< 7 days old), skipping retrain")
            return True

    logger.info("Training AI risk models...")
    X, y = _generate_training_data()

    if len(X) < 100:
        logger.warning(f"Insufficient training data ({len(X)} rows). AI model disabled.")
        return False

    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    try:
        # Train-test split (temporal)
        split = int(len(X) * 0.8)
        X_train, X_test = X.iloc[:split], X.iloc[split:]
        y_train, y_test = y.iloc[:split], y.iloc[split:]

        # LightGBM
        if _lgb is not None:
            lgb_model = _lgb.LGBMClassifier(
                n_estimators=200,
                max_depth=5,
                learning_rate=0.05,
                num_leaves=31,
                min_child_samples=20,
                subsample=0.8,
                colsample_bytree=0.8,
                verbose=-1,
            )
            lgb_model.fit(X_train, y_train)
            with open(LGB_MODEL_PATH, "wb") as f:
                pickle.dump(lgb_model, f)
            acc = lgb_model.score(X_test, y_test)
            logger.info(f"LightGBM test accuracy: {acc:.3f}")

        # XGBoost
        if _xgb is not None:
            xgb_model = _xgb.XGBClassifier(
                n_estimators=200,
                max_depth=5,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                use_label_encoder=False,
                eval_metric="logloss",
                verbosity=0,
            )
            xgb_model.fit(X_train, y_train)
            with open(XGB_MODEL_PATH, "wb") as f:
                pickle.dump(xgb_model, f)
            acc = xgb_model.score(X_test, y_test)
            logger.info(f"XGBoost test accuracy: {acc:.3f}")

        # Save feature columns
        with open(FEATURE_COLS_PATH, "wb") as f:
            pickle.dump(list(X.columns), f)

        logger.info("AI risk models trained and saved successfully")
        return True

    except Exception as e:
        logger.error(f"Model training failed: {e}")
        return False


# ── Prediction ───────────────────────────────────────────

_loaded_lgb = None
_loaded_xgb = None
_loaded_feature_cols = None


def _load_models():
    """Load trained models from disk."""
    global _loaded_lgb, _loaded_xgb, _loaded_feature_cols

    if _loaded_lgb is not None:
        return

    try:
        if LGB_MODEL_PATH.exists():
            with open(LGB_MODEL_PATH, "rb") as f:
                _loaded_lgb = pickle.load(f)
        if XGB_MODEL_PATH.exists():
            with open(XGB_MODEL_PATH, "rb") as f:
                _loaded_xgb = pickle.load(f)
        if FEATURE_COLS_PATH.exists():
            with open(FEATURE_COLS_PATH, "rb") as f:
                _loaded_feature_cols = pickle.load(f)
    except Exception as e:
        logger.error(f"Failed to load AI models: {e}")


def predict_risk(macro: dict) -> AIRiskPrediction:
    """
    Generate AI risk prediction from current macro snapshot.
    Returns AIRiskPrediction with probabilities and expected returns.
    """
    _load_models()

    if _loaded_lgb is None and _loaded_xgb is None:
        return AIRiskPrediction(model_available=False)

    try:
        features = _macro_to_features(macro)
        feature_cols = _loaded_feature_cols or list(features.keys())

        # Build feature vector
        X = pd.DataFrame([features])[feature_cols]

        predictions = []
        probabilities = []

        # LightGBM prediction
        if _loaded_lgb is not None:
            lgb_prob = _loaded_lgb.predict_proba(X)[0]
            predictions.append(lgb_prob)
            probabilities.append(lgb_prob[1])  # P(risk-on)

        # XGBoost prediction
        if _loaded_xgb is not None:
            xgb_prob = _loaded_xgb.predict_proba(X)[0]
            predictions.append(xgb_prob)
            probabilities.append(xgb_prob[1])

        # Ensemble average
        p_risk_on = float(np.mean(probabilities)) if probabilities else 0.5
        p_risk_off = 1.0 - p_risk_on

        # Convert to risk score (risk-off probability × 100)
        ai_risk_score = round(p_risk_off * 100, 1)

        # Confidence: how far from 50/50 the prediction is
        confidence = abs(p_risk_on - 0.5) * 2  # 0 to 1

        # Expected returns (rough estimation from probabilities)
        expected_equity = round((p_risk_on - 0.5) * 4.0, 2)  # ±2% range
        expected_gold = round((p_risk_off - 0.5) * 2.0, 2)   # inverse

        return AIRiskPrediction(
            ai_risk_score=ai_risk_score,
            p_risk_on=round(p_risk_on, 4),
            p_risk_off=round(p_risk_off, 4),
            expected_equity_return=expected_equity,
            expected_gold_return=expected_gold,
            confidence=round(confidence, 4),
            model_available=True,
        )

    except Exception as e:
        logger.error(f"AI prediction failed: {e}")
        return AIRiskPrediction(model_available=False)


def blend_risk_scores(rule_based_score: float, ai_prediction: AIRiskPrediction) -> float:
    """
    Blend rule-based risk score with AI risk score.
    Final = 70% rule-based + 30% AI.
    If AI not available, return rule-based as-is.
    """
    if not ai_prediction.model_available:
        return rule_based_score

    blended = (
        RULE_BASED_WEIGHT * rule_based_score +
        AI_WEIGHT * ai_prediction.ai_risk_score
    )
    return round(min(max(blended, 0), 100), 1)
