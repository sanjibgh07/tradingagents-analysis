"""yfinance data layer for the goal-based portfolio mode.

All network access lives here so the rest of the package stays testable.
Everything degrades gracefully: a bad ticker is silently dropped, a failed
FX fetch falls back to a sensible constant.
"""
import pandas as pd
import yfinance as yf

HISTORY_PERIOD = '6mo'
FX_FALLBACK = 88.0


def fetch_history(tickers, period=HISTORY_PERIOD):
    """Download daily OHLCV for many tickers in one call.

    Returns {ticker: DataFrame[Open, High, Low, Close, Volume]}; tickers with
    no usable data are simply absent from the result.
    """
    frames = {}
    tickers = [t for t in dict.fromkeys(tickers or []) if t]
    if not tickers:
        return frames
    raw = yf.download(
        tickers,
        period=period,
        interval='1d',
        group_by='ticker',
        auto_adjust=True,
        progress=False,
        threads=True,
    )
    if raw is None or len(raw) == 0:
        return frames

    for ticker in tickers:
        sub = None
        if isinstance(raw.columns, pd.MultiIndex):
            level0 = raw.columns.get_level_values(0)
            if ticker in set(level0):
                sub = raw[ticker]
            elif set(level0) == {'Close'} or set(level0) == {'Adj Close'}:
                # Degenerate single-column batch; treat the frame as-is.
                sub = raw
        elif len(tickers) == 1:
            sub = raw
        if sub is None:
            continue
        sub = sub.dropna(how='all')
        if len(sub) > 0 and 'Close' in sub.columns:
            frames[ticker] = sub
    return frames


def fetch_fx_usdinr(fallback=FX_FALLBACK):
    """Latest USD/INR rate for converting USD-quoted crypto into INR."""
    try:
        raw = yf.download('USDINR=X', period='5d', interval='1d',
                          progress=False, auto_adjust=False, threads=False)
        if raw is None or len(raw) == 0:
            return fallback
        close = raw['Close']
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]
        value = float(close.dropna().iloc[-1])
        if 30.0 < value < 200.0:
            return value
    except Exception:
        pass
    return fallback
