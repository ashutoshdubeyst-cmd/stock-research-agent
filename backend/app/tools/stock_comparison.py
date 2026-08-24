"""Consistent side-by-side stock comparison tool."""

from datetime import date, timedelta
from typing import Any

import pandas as pd

from app.agents.tool_registry import register_tool
from app.agents.tool_schemas import CompareStocksArguments
from app.tools.stock_snapshot import build_price_history, get_stock_record
from app.tools.technical_indicators import calculate_indicators


def _history(symbol: str) -> list[dict[str, Any]]:
    today = date.today()
    return build_price_history(symbol, today - timedelta(days=90), today)


def _price_return(bars: list[dict[str, Any]]) -> float | None:
    if len(bars) < 2:
        return None
    return round((float(bars[-1]["close"]) / float(bars[0]["close"]) - 1) * 100, 2)


def _rsi(bars: list[dict[str, Any]]) -> float | None:
    closes = pd.Series([bar["close"] for bar in bars], dtype="float64")
    value = calculate_indicators(closes, ["rsi"])["rsi_14"]
    return float(value) if value is not None else None


@register_tool("compare_stocks")
async def compare_stocks(arguments: CompareStocksArguments) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for symbol in arguments.symbols:
        stock = get_stock_record(symbol)
        bars = _history(symbol)
        row: dict[str, Any] = {"symbol": symbol, "name": stock["name"]}
        for metric in arguments.metrics:
            if metric == "price_return":
                row["price_return_90d_percent"] = _price_return(bars)
            elif metric == "rsi":
                row["rsi_14"] = _rsi(bars)
            else:
                row[metric] = stock[metric]
        rows.append(row)
    return {
        "symbols": arguments.symbols,
        "metrics": arguments.metrics,
        "comparison": rows,
        "price_return_period_days": 90,
        "as_of": date.today().isoformat(),
        "source": "mock_provider (calculated locally)",
        "data_status": "mock",
        "warning": "Illustrative comparison only; not investment advice or live data.",
    }
