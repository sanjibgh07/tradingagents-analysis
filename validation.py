"""Deterministic validation and backtesting layer for Sanjib Market Intelligence.

This layer is deliberately independent from the LLM/TradingAgents engine. It
measures simple discovery-style strategies with strict chronological splits,
transaction costs, and basic risk metrics so model/strategy ideas can be
validated before being used for live decision support.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import yfinance as yf


def load_prices(tickers: list[str], period: str = "5y") -> pd.DataFrame:
    """Load adjusted close prices for a set of Yahoo Finance tickers."""
    symbols = list(dict.fromkeys(str(t).strip().upper() for t in tickers if str(t).strip()))
    if not symbols:
        return pd.DataFrame()
    data = yf.download(
        symbols,
        period=period,
        auto_adjust=True,
        progress=False,
        threads=True,
        group_by="column",
    )
    if data is None or data.empty or "Close" not in data:
        return pd.DataFrame()
    close = data["Close"]
    if isinstance(close, pd.Series):
        close = close.to_frame(symbols[0])
    return close.dropna(how="all").sort_index()


def _annualized_sharpe(returns: pd.Series, periods: int = 252) -> float:
    returns = returns.dropna()
    if returns.empty or returns.std(ddof=0) == 0:
        return 0.0
    return float(np.sqrt(periods) * returns.mean() / returns.std(ddof=0))


def _max_drawdown(equity: pd.Series) -> float:
    peak = equity.cummax()
    dd = equity / peak - 1.0
    return float(dd.min()) if not dd.empty else 0.0


def backtest_momentum(
    prices: pd.DataFrame,
    lookback: int = 63,
    top_k: int = 5,
    rebalance_days: int = 21,
    transaction_cost_bps: float = 10.0,
) -> dict:
    """Backtest a simple top-K momentum portfolio using only past data.

    Signal at date t uses returns ending at t and positions are held starting
    with the next trading bar. This avoids look-ahead from the rebalance signal.
    """
    if prices.empty or len(prices) <= lookback + rebalance_days:
        raise ValueError("Not enough price history for the requested backtest.")
    prices = prices.ffill().dropna(how="all")
    daily_returns = prices.pct_change().fillna(0.0)
    equity = 1.0
    equity_curve = []
    prev_weights = pd.Series(0.0, index=prices.columns)
    cost = transaction_cost_bps / 10000.0

    for i in range(lookback, len(prices) - 1):
        if (i - lookback) % rebalance_days == 0:
            momentum = prices.iloc[i] / prices.iloc[i - lookback] - 1.0
            eligible = momentum.replace([np.inf, -np.inf], np.nan).dropna()
            selected = eligible.nlargest(min(top_k, len(eligible))).index
            weights = pd.Series(0.0, index=prices.columns)
            if len(selected):
                weights.loc[selected] = 1.0 / len(selected)
            turnover = float((weights - prev_weights).abs().sum())
            equity *= max(0.0, 1.0 - cost * turnover)
            prev_weights = weights

        next_ret = daily_returns.iloc[i + 1].fillna(0.0)
        portfolio_ret = float((prev_weights * next_ret).sum())
        equity *= 1.0 + portfolio_ret
        equity_curve.append((prices.index[i + 1], equity))

    curve = pd.Series(dict(equity_curve), dtype=float).sort_index()
    rets = curve.pct_change().dropna()
    total_return = float(curve.iloc[-1] - 1.0) if len(curve) else 0.0
    years = max(len(rets) / 252.0, 1 / 252.0)
    cagr = float(curve.iloc[-1] ** (1.0 / years) - 1.0) if len(curve) else 0.0

    return {
        "equity_curve": curve,
        "total_return": total_return,
        "cagr": cagr,
        "annualized_sharpe": _annualized_sharpe(rets),
        "max_drawdown": _max_drawdown(curve),
        "observations": int(len(curve)),
    }


def walk_forward_momentum(
    prices: pd.DataFrame,
    train_years: int = 3,
    test_years: int = 1,
    top_k_options: tuple[int, ...] = (3, 5, 8),
) -> pd.DataFrame:
    """Run rolling out-of-sample tests over several historical windows.

    The parameter choice is made only from each training window; the following
    test window is held out. This is the foundation for leakage-resistant model
    selection before adding more sophisticated optimizers.
    """
    if prices.empty:
        return pd.DataFrame()
    prices = prices.ffill().dropna(how="all")
    start = prices.index.min()
    end = prices.index.max()
    results = []
    cursor = start + pd.DateOffset(years=train_years)

    while cursor + pd.DateOffset(years=test_years) <= end:
        train_start = cursor - pd.DateOffset(years=train_years)
        test_end = cursor + pd.DateOffset(years=test_years)
        train = prices.loc[(prices.index >= train_start) & (prices.index < cursor)]
        test = prices.loc[(prices.index >= cursor) & (prices.index < test_end)]
        if len(train) < 300 or len(test) < 150:
            cursor += pd.DateOffset(years=test_years)
            continue

        candidates = []
        for k in top_k_options:
            try:
                bt = backtest_momentum(train, top_k=k)
                candidates.append((bt["annualized_sharpe"], k))
            except ValueError:
                continue
        if not candidates:
            cursor += pd.DateOffset(years=test_years)
            continue
        _, best_k = max(candidates)

        test_bt = backtest_momentum(
            pd.concat([train.tail(80), test]),
            top_k=best_k,
        )
        test_curve = test_bt["equity_curve"].loc[test.index.min():]
        if len(test_curve) < 2:
            cursor += pd.DateOffset(years=test_years)
            continue
        test_returns = test_curve.pct_change().dropna()
        results.append({
            "Train Start": train.index.min().date().isoformat(),
            "Train End": train.index.max().date().isoformat(),
            "Test Start": test.index.min().date().isoformat(),
            "Test End": test.index.max().date().isoformat(),
            "Selected Top K": best_k,
            "Test Return %": round(float(test_curve.iloc[-1] / test_curve.iloc[0] - 1.0) * 100, 2),
            "Test Sharpe": round(_annualized_sharpe(test_returns), 3),
            "Test Max Drawdown %": round(_max_drawdown(test_curve) * 100, 2),
        })
        cursor += pd.DateOffset(years=test_years)

    return pd.DataFrame(results)
