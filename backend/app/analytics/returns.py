"""Price-return calculations for stock analysis."""

from collections.abc import Sequence

import numpy as np
import pandas as pd

PriceInput = pd.Series | Sequence[float]


def _price_series(prices: PriceInput) -> pd.Series:
    series = prices.copy() if isinstance(prices, pd.Series) else pd.Series(prices)
    series = pd.to_numeric(series, errors="coerce").astype("float64")
    if series.empty:
        raise ValueError("At least one price is required.")
    if series.isna().any() or (series <= 0).any():
        raise ValueError("Prices must be numeric, non-null, and greater than zero.")
    return series


def simple_returns(prices: PriceInput) -> pd.Series:
    """Calculate decimal period-over-period returns (0.01 means 1%)."""

    return _price_series(prices).pct_change(fill_method=None)


def cumulative_returns(prices: PriceInput) -> pd.Series:
    """Calculate growth relative to the first price as decimal returns."""

    series = _price_series(prices)
    return series / float(series.iloc[0]) - 1


def total_return(prices: PriceInput) -> float | None:
    """Return total decimal price return between first and last observation."""

    series = _price_series(prices)
    if len(series) < 2:
        return None
    return round(float(series.iloc[-1] / series.iloc[0] - 1), 6)


def annualized_return(
    prices: PriceInput,
    periods_per_year: int = 252,
) -> float | None:
    """Annualize the geometric price return from regularly spaced observations."""

    if (
        isinstance(periods_per_year, bool)
        or not isinstance(periods_per_year, int)
        or periods_per_year < 1
    ):
        raise ValueError("periods_per_year must be a positive integer.")

    series = _price_series(prices)
    periods = len(series) - 1
    if periods < 1:
        return None
    growth = float(series.iloc[-1] / series.iloc[0])
    return round(float(np.power(growth, periods_per_year / periods) - 1), 6)
