"""Simple and exponential moving-average calculations."""

from collections.abc import Sequence

import pandas as pd

PriceInput = pd.Series | Sequence[float]


def _price_series(prices: PriceInput) -> pd.Series:
    """Return validated numeric prices while preserving a Series index."""

    series = prices.copy() if isinstance(prices, pd.Series) else pd.Series(prices)
    series = pd.to_numeric(series, errors="coerce").astype("float64")
    if series.empty:
        raise ValueError("At least one price is required.")
    if series.isna().any():
        raise ValueError("Prices must contain only numeric, non-null values.")
    if (series <= 0).any():
        raise ValueError("Prices must be greater than zero.")
    return series


def _validate_window(window: int) -> None:
    if isinstance(window, bool) or not isinstance(window, int) or window < 1:
        raise ValueError("window must be a positive integer.")


def sma(prices: PriceInput, window: int = 20) -> pd.Series:
    """Calculate a simple moving average over ``window`` observations."""

    _validate_window(window)
    return _price_series(prices).rolling(window=window, min_periods=window).mean()


def ema(prices: PriceInput, window: int = 20) -> pd.Series:
    """Calculate an exponential moving average over ``window`` observations."""

    _validate_window(window)
    return (
        _price_series(prices).ewm(span=window, adjust=False, min_periods=window).mean()
    )


def moving_average_summary(
    prices: PriceInput,
    short_window: int = 20,
    long_window: int = 50,
) -> dict[str, float | str | None]:
    """Return latest averages and a descriptive trend/crossover signal."""

    if short_window >= long_window:
        raise ValueError("short_window must be smaller than long_window.")

    series = _price_series(prices)
    short_value = sma(series, short_window).iloc[-1]
    long_value = sma(series, long_window).iloc[-1]
    latest_price = float(series.iloc[-1])

    if pd.isna(short_value) or pd.isna(long_value):
        signal = "insufficient_data"
    elif short_value > long_value:
        signal = "bullish"
    elif short_value < long_value:
        signal = "bearish"
    else:
        signal = "neutral"

    return {
        "latest_price": round(latest_price, 4),
        f"sma_{short_window}": (
            None if pd.isna(short_value) else round(float(short_value), 4)
        ),
        f"sma_{long_window}": (
            None if pd.isna(long_value) else round(float(long_value), 4)
        ),
        "signal": signal,
    }
