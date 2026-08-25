"""Provider-independent stock market data operations."""

import asyncio
from datetime import date, timedelta

from app.data_providers.base import (
    MarketDataProvider,
    PriceBar,
    PriceInterval,
    StockSnapshot,
    normalize_symbol,
)


class StockService:
    """Validate requests and delegate market-data access to a provider."""

    def __init__(
        self, provider: MarketDataProvider, max_history_days: int = 3650
    ) -> None:
        if max_history_days < 1:
            raise ValueError("max_history_days must be positive.")
        self.provider = provider
        self.max_history_days = max_history_days

    async def list_symbols(self, query: str | None = None) -> list[str]:
        """Return normalized, unique symbols in alphabetical order."""

        symbols = await self.provider.list_symbols(query)
        return sorted({normalize_symbol(symbol) for symbol in symbols})

    async def list_snapshots(self, query: str | None = None) -> list[StockSnapshot]:
        """Return snapshots for all symbols matching the optional query."""

        symbols = await self.list_symbols(query)
        return list(
            await asyncio.gather(*(self.get_snapshot(symbol) for symbol in symbols))
        )

    async def get_snapshot(self, symbol: str) -> StockSnapshot:
        """Return a normalized snapshot for one symbol."""

        return await self.provider.get_snapshot(normalize_symbol(symbol))

    async def get_price_history(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        interval: PriceInterval = "1d",
    ) -> list[PriceBar]:
        """Return validated, chronological bars for an inclusive range."""

        normalized = normalize_symbol(symbol)
        if end_date < start_date:
            raise ValueError("end_date must be on or after start_date.")
        if end_date > date.today():
            raise ValueError("end_date cannot be in the future.")
        if (end_date - start_date).days > self.max_history_days:
            raise ValueError(
                f"History requests are limited to {self.max_history_days} days."
            )

        bars = await self.provider.get_price_history(
            normalized,
            start_date,
            end_date,
            interval,
        )
        ordered = sorted(bars, key=lambda bar: bar.trading_date)
        if len({bar.trading_date for bar in ordered}) != len(ordered):
            raise ValueError("The provider returned duplicate price-bar dates.")
        return ordered

    async def get_recent_history(
        self,
        symbol: str,
        days: int = 90,
        interval: PriceInterval = "1d",
        as_of: date | None = None,
    ) -> list[PriceBar]:
        """Convenience method for a recent lookback ending at ``as_of``."""

        if days < 1 or days > self.max_history_days:
            raise ValueError(f"days must be between 1 and {self.max_history_days}.")
        end_date = as_of or date.today()
        return await self.get_price_history(
            symbol,
            end_date - timedelta(days=days),
            end_date,
            interval,
        )

    async def close(self) -> None:
        """Release resources owned by the selected provider."""

        await self.provider.close()
