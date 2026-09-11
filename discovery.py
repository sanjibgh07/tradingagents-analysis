"""Stock discovery and ranking layer for Sanjib Market Intelligence.

This module is intentionally independent from the TradingAgents deep-analysis
engine. It performs a fast, deterministic market scan first, so expensive LLM
research is reserved for a small candidate set.
"""

from __future__ import annotations

import io
import requests
import numpy as np
import pandas as pd
import yfinance as yf

NIFTY50 = [
    "ADANIENT.NS", "ADANIPORTS.NS", "APOLLOHOSP.NS", "ASIANPAINT.NS", "AXISBANK.NS",
    "BAJAJ-AUTO.NS", "BAJFINANCE.NS", "BAJAJFINSV.NS", "BEL.NS", "BHARTIARTL.NS",
    "CIPLA.NS", "COALINDIA.NS", "DRREDDY.NS", "EICHERMOT.NS", "ETERNAL.NS",
    "GRASIM.NS", "HCLTECH.NS", "HDFCBANK.NS", "HDFCLIFE.NS", "HEROMOTOCO.NS",
    "HINDALCO.NS", "HINDUNILVR.NS", "ICICIBANK.NS", "INDUSINDBK.NS", "INFY.NS",
    "ITC.NS", "JIOFIN.NS", "JSWSTEEL.NS", "KOTAKBANK.NS", "LT.NS",
    "M&M.NS", "MARUTI.NS", "MAXHEALTH.NS", "NESTLEIND.NS", "NTPC.NS",
    "ONGC.NS", "POWERGRID.NS", "RELIANCE.NS", "SBILIFE.NS", "SHRIRAMFIN.NS",
    "SBIN.NS", "SUNPHARMA.NS", "TATACONSUM.NS", "TATAMOTORS.NS", "TATASTEEL.NS",
    "TCS.NS", "TECHM.NS", "TITAN.NS", "TRENT.NS", "ULTRACEMCO.NS",
]


def _normalise_ticker(value: str) -> str:
    value = str(value).strip().upper()
    if not value:
        return value
    if value.endswith((".NS", ".BO")) or value.startswith("^"):
        return value
    return value + ".NS"


def load_universe(name: str) -> tuple[list[str], str]:
    """Return a ticker universe and its actual source status.

    NIFTY 50 is bundled for deterministic operation. NIFTY 500 is fetched from
    NSE's public constituent CSV; on source failure we fail safe to NIFTY 50
    rather than inventing or silently substituting symbols.
    """
    if name == "NIFTY 50":
        return NIFTY50.copy(), "Bundled NIFTY 50 universe"

    url = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "text/csv,*/*"}
    try:
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        df = pd.read_csv(io.BytesIO(r.content))
        col = next((c for c in df.columns if str(c).strip().lower() == "symbol"), None)
        if col is None:
            raise ValueError("NSE CSV has no Symbol column")
        symbols = [_normalise_ticker(x) for x in df[col].dropna().tolist()]
        symbols = list(dict.fromkeys(symbols))
        if len(symbols) < 100:
            raise ValueError("NSE universe unexpectedly small")
        return symbols, f"NSE NIFTY 500 constituent list ({len(symbols)} symbols)"
    except Exception as exc:
        return NIFTY50.copy(), f"NSE NIFTY 500 unavailable; safe fallback to NIFTY 50 ({type(exc).__name__})"


def _rsi(close: pd.Series, period: int = 14) -> float:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    value = 100 - (100 / (1 + rs.iloc[-1])) if len(rs.dropna()) else np.nan
    return float(value) if pd.notna(value) else np.nan


def _one_stock(ticker: str, df: pd.DataFrame, benchmark: pd.Series | None) -> dict | None:
    if df is None or df.empty:
        return None
    close = df["Close"].dropna()
    volume = df["Volume"].dropna() if "Volume" in df else pd.Series(dtype=float)
    if len(close) < 60:
        return None

    price = float(close.iloc[-1])
    ret_21 = float(close.iloc[-1] / close.iloc[-22] - 1) if len(close) >= 22 else np.nan
    ret_63 = float(close.iloc[-1] / close.iloc[-64] - 1) if len(close) >= 64 else np.nan
    sma20 = float(close.rolling(20).mean().iloc[-1])
    sma50 = float(close.rolling(50).mean().iloc[-1])
    rsi = _rsi(close)
    vol_ratio = float(volume.iloc[-5:].mean() / volume.iloc[-30:].mean()) if len(volume) >= 30 and volume.iloc[-30:].mean() else np.nan
    vol20 = float(close.pct_change().tail(20).std() * np.sqrt(252))
    high20 = float(close.tail(20).max())
    drawdown20 = float(price / high20 - 1) if high20 else np.nan
    rel3m = np.nan
    if benchmark is not None and len(benchmark.dropna()) >= 64:
        b = benchmark.dropna()
        bench_ret = float(b.iloc[-1] / b.iloc[-64] - 1)
        rel3m = ret_63 - bench_ret

    return {
        "Ticker": ticker,
        "Price": price,
        "Return 1M %": ret_21 * 100,
        "Return 3M %": ret_63 * 100,
        "Above SMA20": price > sma20,
        "Above SMA50": price > sma50,
        "RSI14": rsi,
        "Volume Ratio": vol_ratio,
        "Rel. Strength 3M %": rel3m * 100 if pd.notna(rel3m) else np.nan,
        "Volatility %": vol20 * 100,
        "Drawdown 20D %": drawdown20 * 100,
    }


def _pct_rank(series: pd.Series, higher_is_better: bool = True) -> pd.Series:
    result = series.rank(pct=True, ascending=higher_is_better)
    return result.fillna(0.5) * 100


def rank_stocks(universe: list[str], period: str = "6mo", batch_size: int = 80) -> pd.DataFrame:
    """Fast deterministic ranking using only information available up to now.

    The score is a discovery score, not a BUY/SELL recommendation. The current
    version deliberately leaves LLM/fundamental judgment to the deep-analysis
    engine that consumes the shortlist.
    """
    universe = list(dict.fromkeys(_normalise_ticker(x) for x in universe if str(x).strip()))
    if not universe:
        return pd.DataFrame()

    benchmark_df = yf.download("^NSEI", period=period, progress=False, auto_adjust=True, threads=False)
    if isinstance(benchmark_df.columns, pd.MultiIndex):
        benchmark_df.columns = benchmark_df.columns.get_level_values(0)
    benchmark = benchmark_df["Close"].squeeze() if not benchmark_df.empty and "Close" in benchmark_df else None

    rows: list[dict] = []
    for start in range(0, len(universe), batch_size):
        batch = universe[start:start + batch_size]
        data = yf.download(batch, period=period, progress=False, auto_adjust=True, threads=True, group_by="ticker")
        for ticker in batch:
            try:
                if isinstance(data.columns, pd.MultiIndex):
                    if ticker not in data.columns.get_level_values(0):
                        continue
                    frame = data[ticker].copy()
                else:
                    frame = data.copy() if len(batch) == 1 else pd.DataFrame()
                row = _one_stock(ticker, frame, benchmark)
                if row:
                    rows.append(row)
            except Exception:
                continue

    result = pd.DataFrame(rows)
    if result.empty:
        return result

    result["Momentum"] = (_pct_rank(result["Return 1M %"]) * 0.45 + _pct_rank(result["Return 3M %"]) * 0.55)
    result["Trend"] = (
        _pct_rank(result["Above SMA20"].astype(int)) * 0.35
        + _pct_rank(result["Above SMA50"].astype(int)) * 0.65
    )
    rsi_distance = (result["RSI14"] - 55).abs()
    result["RSI Quality"] = _pct_rank(-rsi_distance)
    result["Volume Quality"] = _pct_rank(result["Volume Ratio"])
    result["Relative Strength"] = _pct_rank(result["Rel. Strength 3M %"])
    result["Risk Quality"] = _pct_rank(-result["Volatility %"]) * 0.6 + _pct_rank(result["Drawdown 20D %"]) * 0.4

    result["Discovery Score"] = (
        result["Momentum"] * 0.25
        + result["Trend"] * 0.25
        + result["RSI Quality"] * 0.10
        + result["Volume Quality"] * 0.10
        + result["Relative Strength"] * 0.20
        + result["Risk Quality"] * 0.10
    ).round(1)

    result["Screen"] = np.select(
        [result["Discovery Score"] >= 75, result["Discovery Score"] >= 60],
        ["Strong candidate", "Watch candidate"],
        default="Lower priority",
    )
    result = result.sort_values(["Discovery Score", "Return 3M %"], ascending=False).reset_index(drop=True)
    result.insert(0, "Rank", np.arange(1, len(result) + 1))

    visible = [
        "Rank", "Ticker", "Discovery Score", "Screen", "Price", "Return 1M %",
        "Return 3M %", "RSI14", "Volume Ratio", "Rel. Strength 3M %",
        "Volatility %", "Drawdown 20D %",
    ]
    return result[visible]
