"""Unit tests for Relative Strength Index calculations."""

import pandas as pd
import pytest

from app.analytics.rsi import calculate_rsi, latest_rsi, rsi_signal


def test_strictly_rising_prices_produce_rsi_of_100() -> None:
    prices = [100.0 + index for index in range(30)]

    assert latest_rsi(prices, window=14) == 100.0


def test_strictly_falling_prices_produce_rsi_of_zero() -> None:
    prices = [130.0 - index for index in range(30)]

    assert latest_rsi(prices, window=14) == 0.0


def test_flat_prices_produce_neutral_rsi() -> None:
    assert latest_rsi([100.0] * 30, window=14) == 50.0


def test_insufficient_history_returns_none_for_latest_rsi() -> None:
    assert latest_rsi([100.0, 101.0, 102.0], window=14) is None


def test_calculate_rsi_preserves_series_index() -> None:
    index = pd.date_range("2026-01-01", periods=20, freq="D")
    prices = pd.Series(range(100, 120), index=index, dtype="float64")

    result = calculate_rsi(prices, window=5)

    assert result.index.equals(index)
    assert result.iloc[:5].isna().all()


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, "insufficient_data"),
        (30.0, "oversold"),
        (50.0, "neutral"),
        (70.0, "overbought"),
    ],
)
def test_rsi_signal_boundaries(value: float | None, expected: str) -> None:
    assert rsi_signal(value) == expected


@pytest.mark.parametrize("value", [-0.01, 100.01])
def test_rsi_signal_rejects_values_outside_range(value: float) -> None:
    with pytest.raises(ValueError, match="between 0 and 100"):
        rsi_signal(value)


@pytest.mark.parametrize(
    "prices",
    [[], [100.0, 0.0], [100.0, -1.0], [100.0, float("nan")], [100.0, "bad"]],
)
def test_rsi_rejects_invalid_prices(prices: list[object]) -> None:
    with pytest.raises(ValueError):
        calculate_rsi(prices, window=2)  # type: ignore[arg-type]


@pytest.mark.parametrize("window", [True, 0, 1, -5, 2.5])
def test_rsi_rejects_invalid_window(window: object) -> None:
    with pytest.raises(ValueError):
        calculate_rsi([100.0, 101.0, 102.0], window=window)  # type: ignore[arg-type]
