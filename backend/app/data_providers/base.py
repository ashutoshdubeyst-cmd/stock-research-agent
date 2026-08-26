"""Contracts shared by all market-data providers."""

from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

DataStatus = Literal["mock", "end_of_day", "delayed", "real_time"]
PriceInterval = Literal["1d", "1w"]


class MarketDataError(RuntimeError):
    """Base exception for safe, provider-independent market-data failures."""


class ProviderAuthenticationError(MarketDataError):
    """Raised when provider credentials are missing, invalid, or expired."""


class InstrumentNotFoundError(MarketDataError):
    """Raised when a symbol cannot be mapped to a provider instrument."""


class ProviderResponseError(MarketDataError):
    """Raised when a provider returns an invalid or unsuccessful response."""


def normalize_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper()
    if not normalized or len(normalized) > 30:
        raise ValueError("A symbol must contain between 1 and 30 characters.")
    if not all(char.isalnum() or char in {"-", ".", "_"} for char in normalized):
        raise ValueError(
            "A symbol may contain only letters, numbers, '-', '.', and '_'."
        )
    return normalized


class StockSnapshot(BaseModel):
    """Provider-neutral point-in-time stock information."""

    model_config = ConfigDict(frozen=True)
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

    @field_validator("currency", "exchange")
    @classmethod
    def uppercase_code(cls, value: str) -> str:
        return value.strip().upper()

    @property
    def change(self) -> float:
        return round(self.price - self.previous_close, 4)

    @property
    def change_percent(self) -> float:
        return round(self.change / self.previous_close * 100, 4)


class Instrument(BaseModel):
    """Provider-neutral identity used to resolve symbols to provider keys."""

    model_config = ConfigDict(frozen=True)
    symbol: str
    name: str = Field(min_length=1)
    exchange: str = Field(min_length=1)
    instrument_key: str = Field(min_length=1)
    instrument_type: str = Field(min_length=1)

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, value: str) -> str:
        return normalize_symbol(value)

    @field_validator("exchange")
    @classmethod
    def uppercase_exchange(cls, value: str) -> str:
        return value.strip().upper()


class PriceBar(BaseModel):
    """One provider-neutral OHLCV price bar."""

    model_config = ConfigDict(frozen=True)
    symbol: str
    trading_date: date
    interval: PriceInterval = "1d"
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: int = Field(ge=0)
    source: str = Field(min_length=1)
    data_status: DataStatus

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, value: str) -> str:
        return normalize_symbol(value)

    @model_validator(mode="after")
    def validate_ohlc_range(self) -> "PriceBar":
        if self.high < max(self.open, self.close, self.low):
            raise ValueError("high must be the greatest OHLC value.")
        if self.low > min(self.open, self.close, self.high):
            raise ValueError("low must be the smallest OHLC value.")
        return self


class MarketDataProvider(ABC):
    """Asynchronous interface implemented by every market-data adapter."""

    name: str
    data_status: DataStatus

    async def __aenter__(self) -> "MarketDataProvider":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()

    async def close(self) -> None:
        """Release resources; providers without clients use this no-op."""
        return None

    @abstractmethod
    async def list_symbols(self, query: str | None = None) -> list[str]:
        """Return supported symbols, optionally filtered by symbol or name."""

    @abstractmethod
    async def get_snapshot(self, symbol: str) -> StockSnapshot:
        """Return the latest available stock snapshot."""

    @abstractmethod
    async def get_price_history(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        interval: PriceInterval = "1d",
    ) -> list[PriceBar]:
        """Return chronological OHLCV bars for an inclusive date range."""
