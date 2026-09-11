"""Deterministic quant screener — pure pandas/numpy, no LLM anywhere.

Ranks a universe by risk-adjusted short-term momentum, then shortlists the
top names subject to a volatility ceiling set by the user's risk profile.
Every metric is computed only from data that existed at that time.
"""
import math

import numpy as np
import pandas as pd

# (lookback for ret1m, lookback for ret3m) in trading days
HORIZON_WINDOWS = {'short': (21, 63), 'medium': (21, 63), 'long': (21, 126)}

RISK_MAX_VOL = {'low': 0.45, 'medium': 0.70, 'high': 1.10}   # annualised vol ceiling
RISK_TOP_N = {'low': 4, 'medium': 5, 'high': 6}             # picks per market

MIN_DOLLAR_VOL = {'india': 2e7, 'crypto': 1e7}              # ₹2 cr/day stocks, $10M crypto
TRADING_DAYS = {'india': 252, 'crypto': 365}

# Composite weights: z(ret1m), z(ret3m), z(-volatility), z(liquidity)
HORIZON_WEIGHTS = {
    'short': (0.55, 0.35, -0.30, 0.10),
    'medium': (0.35, 0.45, -0.30, 0.10),
    'long': (0.20, 0.55, -0.25, 0.10),
}


def _rsi(close, window=14):
    """Cutler's RSI (simple rolling means) — no external TA dependency."""
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(window, min_periods=window).mean()
    loss = (-delta.clip(upper=0)).rolling(window, min_periods=window).mean()
    rs = gain / loss.replace(0, np.nan)
    out = 100 - 100 / (1 + rs)
    return float(out.iloc[-1]) if out.notna().iloc[-1] else 50.0


def _atr(df, window=14):
    """Average True Range (simple mean) over the last `window` days."""
    high, low, prev = df['High'], df['Low'], df['Close'].shift(1)
    tr = pd.concat([high - low,
                    (high - prev).abs(),
                    (low - prev).abs()], axis=1).max(axis=1)
    value = tr.rolling(window, min_periods=window).mean().dropna()
    return float(value.iloc[-1]) if len(value) else float('nan')


def compute_metrics(df, market):
    """Metric row for one ticker, or None when data/liquidity is unusable."""
    if df is None or len(df) < 60:
        return None
    try:
        close = df['Close'].astype(float).dropna()
        volume = df['Volume'].astype(float).reindex(close.index).fillna(0.0)
        if len(close) < 60 or close.iloc[-1] <= 0:
            return None
        td = TRADING_DAYS.get(market, 252)
        ret1 = float(close.iloc[-1] / close.iloc[-22] - 1.0)
        ret3 = float(close.iloc[-1] / close.iloc[-64] - 1.0)
        daily = close.pct_change().dropna()
        vol_ann = float(daily.std() * math.sqrt(td))
        if not np.isfinite(vol_ann) or vol_ann <= 0:
            return None
        avg_dollar_vol = float((close * volume).tail(20).mean())
        if avg_dollar_vol < MIN_DOLLAR_VOL.get(market, 0.0):
            return None
        peak = close.tail(90).max()
        max_dd90 = float(close.iloc[-1] / peak - 1.0) if peak > 0 else -1.0
        return {
            'close': float(close.iloc[-1]),
            'ret1m': ret1,
            'ret3m': ret3,
            'vol_ann': vol_ann,
            'avg_dollar_vol': avg_dollar_vol,
            'rsi14': _rsi(close),
            'atr14': _atr(df),
            'max_dd90': max_dd90,
        }
    except Exception:
        return None


def _z(series):
    """Population z-score, clipped to ±3 so one outlier cannot dominate."""
    s = pd.to_numeric(series, errors='coerce').astype(float)
    std = s.std(ddof=0)
    if not np.isfinite(std) or std == 0:
        return pd.Series(0.0, index=s.index)
    return ((s - s.mean()) / std).clip(-3, 3).fillna(0.0)


def score_universe(rows, horizon='short'):
    """rows = list of metric dicts that already carry 'ticker' and 'name'.

    Returns a DataFrame sorted best-first with a composite `score`.
    """
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    w1, w3, wv, wl = HORIZON_WEIGHTS.get(horizon, HORIZON_WEIGHTS['short'])
    df['score'] = (w1 * _z(df['ret1m'])
                   + w3 * _z(df['ret3m'])
                   + wv * _z(df['vol_ann'])      # weight is negative: low vol wins
                   + wl * _z(df['avg_dollar_vol'])
                   ).round(3)
    return df.sort_values('score', ascending=False).reset_index(drop=True)


def shortlist(scored, risk='medium', k=None):
    """Apply the risk-profile volatility ceiling and take the top-k rows."""
    if scored is None or scored.empty:
        return []
    capped = scored[scored['vol_ann'] <= RISK_MAX_VOL.get(risk, 0.70)]
    k = k or RISK_TOP_N.get(risk, 5)
    return capped.head(k).to_dict('records')
