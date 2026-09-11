"""Walk-forward validation of the same momentum screen — honest and cost-aware.

The claim this module can defend: "if you had run this exact screen every
N days for the last 6 months, paying these costs, here is what it did versus
buy-and-hold of the benchmark." It validates the SCREEN, not any LLM output,
and past performance still does not guarantee future results.
"""
import math

import numpy as np
import pandas as pd

REBALANCE_DAYS = 14          # review cadence for a short-horizon plan
MOMENTUM_LOOKBACK = 21
VOL_LOOKBACK = 42
WARMUP_ROWS = 60
COSTS_PER_REBALANCE = {'india': 0.006, 'crypto': 0.010}     # conservative round trip
TRADING_DAYS = {'india': 252, 'crypto': 365}


def _portfolio_return(prices_row_then, prices_row_now, tickers):
    """Equal-weight return of `tickers` between two price rows (t -> t+hold)."""
    if not tickers:
        return 0.0
    rets = []
    for ticker in tickers:
        start, end = prices_row_then[ticker], prices_row_now[ticker]
        if np.isfinite(start) and np.isfinite(end) and start > 0:
            rets.append(end / start - 1.0)
    return float(np.mean(rets)) if rets else 0.0


def _pick_at(closes, t, k, max_vol):
    """Rank all tickers by 21-day momentum (42-day vol filter) using only
    data up to row `t`; return the top-k ticker list."""
    window = closes.iloc[max(0, t - MOMENTUM_LOOKBACK):t + 1]
    if len(window) < MOMENTUM_LOOKBACK + 1:
        return []
    rets = window.iloc[-1] / window.iloc[0] - 1.0
    daily = closes.iloc[max(0, t - VOL_LOOKBACK):t + 1].pct_change().dropna(how='all')
    vols = daily.std(ddof=0)
    td = math.sqrt(252)
    usable = rets[(vols * td <= max_vol) & rets.notna() & np.isfinite(rets)]
    if usable.empty:
        return []
    return list(usable.sort_values(ascending=False).head(k).index)


def walk_forward(closes, market, risk_max_vol=0.70, k=5,
                 step=REBALANCE_DAYS, hold=REBALANCE_DAYS, benchmark=None):
    """closes = DataFrame of Close prices (index=dates, columns=tickers).

    Returns {'dates','strategy','benchmark','total','bench_total',
             'max_dd','win_rate','n_rebalances'} — `strategy` is the net
    equity curve (costs deducted every rebalance).
    """
    if closes is None or len(closes) < WARMUP_ROWS + hold + 1:
        return None
    cost = COSTS_PER_REBALANCE.get(market, 0.006)
    equity = 1.0
    curve_dates, curve_values = [], []
    wins, trades = 0, 0

    t = WARMUP_ROWS
    while t + hold < len(closes):
        picks = _pick_at(closes, t, k, risk_max_vol)
        gross = _portfolio_return(closes.iloc[t], closes.iloc[t + hold], picks)
        net = (equity * (1.0 + gross)) * (1.0 - cost) - equity   # cost on full turnover
        equity += net
        wins += 1 if net > 0 else 0
        trades += 1
        curve_dates.append(closes.index[t + hold])
        curve_values.append(equity)
        t += step

    if not curve_values:
        return None
    curve = pd.Series(curve_values, index=curve_dates, name='strategy')
    running_peak = curve.cummax()
    max_dd = float((curve / running_peak - 1.0).min())

    bench_curve = None
    bench_total = None
    if benchmark and benchmark in closes.columns:
        seg = closes[benchmark].iloc[WARMUP_ROWS:t]  # same window as strategy
        seg = seg.dropna()
        if len(seg) > 1:
            bench_curve = seg / seg.iloc[0]
            bench_total = float(bench_curve.iloc[-1] - 1.0)

    return {
        'curve': curve,
        'bench_curve': bench_curve,
        'total': float(curve.iloc[-1] - 1.0),
        'bench_total': bench_total,
        'max_dd': max_dd,
        'win_rate': round(wins / trades, 3) if trades else 0.0,
        'n_rebalances': trades,
    }
