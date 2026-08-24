"""Technical-indicator calculations for the research agent."""

from datetime import date, timedelta
from typing import Any

import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import MACD, EMAIndicator, SMAIndicator
from ta.volatility import BollingerBands

from app.agents.tool_registry import register_tool
from app.agents.tool_schemas import TechnicalIndicatorArguments
from app.tools.stock_snapshot import build_price_history


def _number(value: Any) -> float | None:
    return None if pd.isna(value) else round(float(value), 4)


def calculate_indicators(closes: pd.Series, requested: list[str]) -> dict[str, Any]:
    results: dict[str, Any] = {}
    if "rsi" in requested:
        results["rsi_14"] = _number(RSIIndicator(closes, window=14).rsi().iloc[-1])
    if "sma" in requested:
        results["sma_20"] = _number(
            SMAIndicator(closes, window=20).sma_indicator().iloc[-1]
        )
    if "ema" in requested:
        results["ema_20"] = _number(
            EMAIndicator(closes, window=20).ema_indicator().iloc[-1]
        )
    if "macd" in requested:
        macd = MACD(closes)
        results["macd"] = {
            "line": _number(macd.macd().iloc[-1]),
            "signal": _number(macd.macd_signal().iloc[-1]),
            "histogram": _number(macd.macd_diff().iloc[-1]),
        }
    if "bollinger" in requested:
        bands = BollingerBands(closes, window=20, window_dev=2)
        results["bollinger_bands_20"] = {
            "upper": _number(bands.bollinger_hband().iloc[-1]),
            "middle": _number(bands.bollinger_mavg().iloc[-1]),
            "lower": _number(bands.bollinger_lband().iloc[-1]),
        }
    return results


async def indicator_values(
    symbol: str, interval: str, requested: list[str]
) -> dict[str, Any]:
    end_date = date.today()
    start_date = end_date - timedelta(days=180 if interval == "1d" else 500)
    bars = build_price_history(symbol, start_date, end_date, interval)
    closes = pd.Series([bar["close"] for bar in bars], dtype="float64")
    return {
        "symbol": symbol,
        "interval": interval,
        "last_close": _number(closes.iloc[-1]),
        "observations": len(closes),
        "indicators": calculate_indicators(closes, requested),
        "as_of": end_date.isoformat(),
        "source": "mock_provider (calculated locally)",
        "data_status": "mock",
        "warning": "Indicators use illustrative mock prices, not live market data.",
    }


@register_tool("get_technical_indicators")
async def get_technical_indicators(
    arguments: TechnicalIndicatorArguments,
) -> dict[str, Any]:
    return await indicator_values(
        arguments.symbol, arguments.interval, list(arguments.indicators)
    )
