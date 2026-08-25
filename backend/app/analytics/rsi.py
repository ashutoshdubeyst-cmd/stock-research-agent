"""Relative Strength Index (RSI) calculations."""

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


def calculate_rsi(prices: PriceInput, window: int = 14) -> pd.Series:
    """Calculate Wilder's RSI, returning NaN until enough data exists."""

    if isinstance(window, bool) or not isinstance(window, int) or window < 2:
        raise ValueError("window must be an integer greater than one.")

    series = _price_series(prices)
    changes = series.diff()
    gains = changes.clip(lower=0)
    losses = -changes.clip(upper=0)
    alpha = 1 / window
    average_gain = gains.ewm(
        alpha=alpha,
        adjust=False,
        min_periods=window,
    ).mean()
    average_loss = losses.ewm(
        alpha=alpha,
        adjust=False,
        min_periods=window,
    ).mean()
    relative_strength = average_gain / average_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + relative_strength))
    rsi = rsi.mask((average_loss == 0) & (average_gain > 0), 100.0)
    return rsi.mask((average_loss == 0) & (average_gain == 0), 50.0)


def latest_rsi(prices: PriceInput, window: int = 14) -> float | None:
    """Return the latest RSI as a JSON-safe value."""

    value = calculate_rsi(prices, window).iloc[-1]
    return None if pd.isna(value) else round(float(value), 4)


def rsi_signal(value: float | None) -> str:
    """Classify an RSI value without treating it as investment advice."""

    if value is None:
        return "insufficient_data"
    if not 0 <= value <= 100:
        raise ValueError("RSI must be between 0 and 100.")
    if value >= 70:
        return "overbought"
    if value <= 30:
        return "oversold"
    return "neutral"
