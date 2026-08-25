"""Unit tests for simple and exponential moving averages."""

import pandas as pd
import pytest

from app.analytics.moving_averages import ema, moving_average_summary, sma


def test_sma_calculates_expected_values() -> None:
    result = sma([10.0, 20.0, 30.0, 40.0, 50.0], window=3)

    assert result.iloc[:2].isna().all()
    assert result.iloc[2:].tolist() == pytest.approx([20.0, 30.0, 40.0])


def test_ema_matches_pandas_exponential_average() -> None:
    prices = pd.Series([10.0, 20.0, 30.0, 40.0, 50.0])
    expected = prices.ewm(span=3, adjust=False, min_periods=3).mean()

    pd.testing.assert_series_equal(ema(prices, window=3), expected)


def test_moving_averages_preserve_custom_index() -> None:
    index = pd.date_range("2026-01-01", periods=5, freq="D")
    prices = pd.Series([10, 11, 12, 13, 14], index=index)

    assert sma(prices, 2).index.equals(index)
    assert ema(prices, 2).index.equals(index)


def test_summary_reports_bullish_trend_for_rising_prices() -> None:
    result = moving_average_summary(
        [float(value) for value in range(1, 61)],
        short_window=10,
        long_window=30,
    )

    assert result["latest_price"] == 60.0
    assert result["sma_10"] == pytest.approx(55.5)
    assert result["sma_30"] == pytest.approx(45.5)
    assert result["signal"] == "bullish"


def test_summary_reports_bearish_trend_for_falling_prices() -> None:
    prices = [float(value) for value in range(60, 0, -1)]

    assert moving_average_summary(prices, 10, 30)["signal"] == "bearish"


def test_summary_reports_insufficient_data() -> None:
    result = moving_average_summary([10.0, 11.0, 12.0], 2, 5)

    assert result["sma_2"] == pytest.approx(11.5)
    assert result["sma_5"] is None
    assert result["signal"] == "insufficient_data"


def test_summary_requires_short_window_smaller_than_long_window() -> None:
    with pytest.raises(ValueError, match="short_window"):
        moving_average_summary([10.0, 11.0, 12.0], 5, 5)


@pytest.mark.parametrize("window", [True, 0, -1, 2.5])
def test_moving_average_rejects_invalid_window(window: object) -> None:
    with pytest.raises(ValueError, match="positive integer"):
        sma([10.0, 11.0], window=window)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "prices",
    [[], [10.0, 0.0], [10.0, -2.0], [10.0, float("nan")], [10.0, "bad"]],
)
def test_moving_average_rejects_invalid_prices(prices: list[object]) -> None:
    with pytest.raises(ValueError):
        sma(prices, window=2)  # type: ignore[arg-type]
