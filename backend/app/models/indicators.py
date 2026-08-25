"""Technical-analysis and stock-comparison API models."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.data_providers.base import DataStatus, PriceInterval, normalize_symbol

RsiSignal = Literal["oversold", "neutral", "overbought", "insufficient_data"]
TrendSignal = Literal["bullish", "neutral", "bearish", "insufficient_data"]
ComparisonMetric = Literal[
    "price_return",
    "rsi",
    "revenue_growth",
    "profit_growth",
    "roe",
    "debt_to_equity",
    "pe",
]


class TechnicalIndicatorRequest(BaseModel):
    symbol: str
    start_date: date
    end_date: date
    interval: PriceInterval = "1d"
    short_window: int = Field(default=20, ge=2, le=200)
    long_window: int = Field(default=50, ge=3, le=500)
    rsi_window: int = Field(default=14, ge=2, le=100)

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, value: str) -> str:
        return normalize_symbol(value)

    @model_validator(mode="after")
    def validate_ranges(self) -> "TechnicalIndicatorRequest":
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date.")
        if self.short_window >= self.long_window:
            raise ValueError("short_window must be smaller than long_window.")
        return self


class MovingAverageResult(BaseModel):
    model_config = ConfigDict(extra="allow")
    latest_price: float = Field(gt=0)
    signal: TrendSignal


class IndicatorResult(BaseModel):
    model_config = ConfigDict(extra="allow")
    rsi_signal: RsiSignal


class ReturnResult(BaseModel):
    total_decimal: float | None = None
    annualized_decimal: float | None = None


class StockAnalysisResponse(BaseModel):
    symbol: str
    start_date: date
    end_date: date
    interval: PriceInterval
    observations: int = Field(ge=1)
    moving_averages: MovingAverageResult
    latest_indicators: IndicatorResult
    returns: ReturnResult
    source: str
    data_status: DataStatus
    as_of: date
    warning: str | None = None


class StockComparisonRequest(BaseModel):
    symbols: list[str] = Field(min_length=2, max_length=5)
    metrics: list[ComparisonMetric] = Field(min_length=1, max_length=7)
    start_date: date
    end_date: date
    interval: PriceInterval = "1d"

    @field_validator("symbols")
    @classmethod
    def validate_symbols(cls, values: list[str]) -> list[str]:
        normalized = [normalize_symbol(value) for value in values]
        if len(set(normalized)) != len(normalized):
            raise ValueError("Stock symbols must be unique.")
        return normalized

    @field_validator("metrics")
    @classmethod
    def unique_metrics(cls, values: list[ComparisonMetric]) -> list[ComparisonMetric]:
        return list(dict.fromkeys(values))

    @model_validator(mode="after")
    def validate_dates(self) -> "StockComparisonRequest":
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date.")
        return self


class StockComparisonRow(BaseModel):
    symbol: str
    name: str
    price_return_percent: float | None = None
    rsi_14: float | None = Field(default=None, ge=0, le=100)
    revenue_growth: float | None = None
    profit_growth: float | None = None
    roe: float | None = None
    debt_to_equity: float | None = Field(default=None, ge=0)
    pe: float | None = None


class StockComparisonResponse(BaseModel):
    symbols: list[str]
    metrics: list[ComparisonMetric]
    start_date: date
    end_date: date
    interval: PriceInterval
    comparison: list[StockComparisonRow]
    source: str
    data_status: DataStatus
    as_of: date
    warning: str | None = None
