from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class StockSnapshotArguments(BaseModel):
    symbol: str = Field(min_length=1, max_length=30)

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return value.strip().upper()


class PriceHistoryArguments(StockSnapshotArguments):
    start_date: date
    end_date: date
    interval: Literal["1d", "1w"] = "1d"

    @field_validator("end_date")
    @classmethod
    def validate_date_order(cls, value: date, info: object) -> date:
        data = getattr(info, "data", {})
        start_date = data.get("start_date")
        if start_date is not None and value < start_date:
            raise ValueError("end_date must be on or after start_date")
        return value


class TechnicalIndicatorArguments(StockSnapshotArguments):
    interval: Literal["1d", "1w"] = "1d"
    indicators: list[Literal["rsi", "sma", "ema", "macd", "bollinger"]] = Field(
        min_length=1,
        max_length=5,
    )


class CompareStocksArguments(BaseModel):
    symbols: list[str] = Field(min_length=2, max_length=5)
    metrics: list[
        Literal[
            "price_return",
            "rsi",
            "revenue_growth",
            "profit_growth",
            "roe",
            "debt_to_equity",
            "pe",
        ]
    ] = Field(min_length=1, max_length=7)

    @field_validator("symbols")
    @classmethod
    def normalize_symbols(cls, values: list[str]) -> list[str]:
        normalized = [value.strip().upper() for value in values]
        if any(not value or len(value) > 30 for value in normalized):
            raise ValueError("Every stock symbol must contain 1 to 30 characters")
        if len(set(normalized)) != len(normalized):
            raise ValueError("Stock symbols must be unique")
        return normalized


TOOL_ARGUMENT_MODELS: dict[str, type[BaseModel]] = {
    "get_stock_snapshot": StockSnapshotArguments,
    "get_price_history": PriceHistoryArguments,
    "get_technical_indicators": TechnicalIndicatorArguments,
    "compare_stocks": CompareStocksArguments,
}


TOOL_SCHEMAS: dict[str, dict[str, object]] = {
    "get_stock_snapshot": {
        "type": "function",
        "function": {
            "name": "get_stock_snapshot",
            "description": (
                "Return a verified stock snapshot for one supported exchange symbol."
            ),
            "parameters": StockSnapshotArguments.model_json_schema(),
        },
    },
    "get_price_history": {
        "type": "function",
        "function": {
            "name": "get_price_history",
            "description": (
                "Return verified historical OHLCV bars for one stock and date range."
            ),
            "parameters": PriceHistoryArguments.model_json_schema(),
        },
    },
    "get_technical_indicators": {
        "type": "function",
        "function": {
            "name": "get_technical_indicators",
            "description": (
                "Calculate technical indicators using verified stored price data."
            ),
            "parameters": TechnicalIndicatorArguments.model_json_schema(),
        },
    },
    "compare_stocks": {
        "type": "function",
        "function": {
            "name": "compare_stocks",
            "description": (
                "Compare two to five stocks using consistent periods and metrics."
            ),
            "parameters": CompareStocksArguments.model_json_schema(),
        },
    },
}


def get_tool_schema(name: str) -> dict[str, object]:
    try:
        return TOOL_SCHEMAS[name]
    except KeyError as exc:
        raise KeyError(f"No tool schema is defined for {name!r}.") from exc
