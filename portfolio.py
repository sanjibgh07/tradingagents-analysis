"""Portfolio/risk layer with an optional skfolio accelerator.

The core fallback keeps the app usable without skfolio. When installed, a
future UI layer can route portfolio construction to skfolio for CVaR/risk
budgeting, clustering, constraints and walk-forward validation.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def inverse_volatility_weights(returns: pd.DataFrame, max_weight: float = 0.35) -> pd.Series:
    """Simple, deterministic risk-aware allocation fallback."""
    vol = returns.std(ddof=0).replace(0, np.nan).dropna()
    if vol.empty:
        return pd.Series(dtype=float)
    raw = 1.0 / vol
    weights = raw / raw.sum()
    for _ in range(10):
        capped = weights.clip(upper=max_weight)
        excess = float(capped.sum() - 1.0)
        if excess <= 1e-9:
            weights = capped / capped.sum()
            break
        free = capped < max_weight - 1e-12
        if not free.any():
            weights = capped / capped.sum()
            break
        capped.loc[free] += excess / int(free.sum())
        weights = capped
    return weights / weights.sum()


def optimize_portfolio(returns: pd.DataFrame, method: str = "inverse_volatility") -> pd.Series:
    """Return portfolio weights; uses skfolio when explicitly requested."""
    clean = returns.dropna(axis=1, how="all").dropna(how="all")
    if clean.empty:
        return pd.Series(dtype=float)

    if method == "skfolio_mean_risk":
        try:
            from skfolio import MeanRisk, RiskMeasure
            from skfolio.preprocessing import prices_to_returns

            model = MeanRisk(risk_measure=RiskMeasure.CVAR)
            model.fit(clean)
            return pd.Series(model.weights_, index=clean.columns)
        except ImportError as exc:
            raise RuntimeError("skfolio is not installed. Use inverse_volatility or add skfolio to requirements.") from exc

    if method == "equal_weight":
        return pd.Series(1.0 / len(clean.columns), index=clean.columns)

    return inverse_volatility_weights(clean)
