"""Stock snapshot and historical-price API models."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from app.data_providers.base import DataStatus, PriceInterval, normalize_symbol


class StockSnapshotResponse(BaseModel):
    """Provider-neutral stock snapshot exposed by the API."""

    model_config = ConfigDict(from_attributes=True)
    symbol: str
    name: str = Field(min_length=1)
    exchange: str = Field(min_length=1)
    currency: str = Field(min_length=3, max_length=3)
    price: float = Field(gt=0)
    previous_close: float = Field(gt=0)
    volume: int = Field(ge=0)
    as_of: datetime
    source: str = Field(min_length=1)
    data_status: DataStatus
    market_cap_crore: float | None = Field(default=None, ge=0)
    pe: float | None = None
    roe: float | None = None
    debt_to_equity: float | None = Field(default=None, ge=0)
    revenue_growth: float | None = None
    profit_growth: float | None = None

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, value: str) -> str:
        return normalize_symbol(value)

    @computed_field
    @property
    def change(self) -> float:
        return round(self.price - self.previous_close, 4)

    @computed_field
    @property
    def change_percent(self) -> float:
        return round(self.change / self.previous_close * 100, 4)


class StockListResponse(BaseModel):
    stocks: list[StockSnapshotResponse]
    count: int = Field(ge=0)


class PriceBarResponse(BaseModel):
    """One chronological OHLCV bar."""

    model_config = ConfigDict(from_attributes=True)
    trading_date: date
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: int = Field(ge=0)


class StockHistoryResponse(BaseModel):
    symbol: str
    interval: PriceInterval
    start_date: date
    end_date: date
    bars: list[PriceBarResponse]
    source: str
    data_status: DataStatus
    warning: str | None = None

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, value: str) -> str:
        return normalize_symbol(value)


class StockSearchRequest(BaseModel):
    query: str | None = Field(default=None, min_length=1, max_length=50)
    exchange: str = Field(default="NSE", min_length=1, max_length=20)
    limit: int = Field(default=20, ge=1, le=100)


class DataStatusResponse(BaseModel):
    provider: str
    status: DataStatus
    exchange: str
    last_updated: datetime | None = None
    message: str | None = None
