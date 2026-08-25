"""Deterministic market-data provider for local development and tests."""

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.data_providers.base import (
    DataStatus,
    MarketDataProvider,
    PriceBar,
    PriceInterval,
    StockSnapshot,
    normalize_symbol,
)

MOCK_STOCKS: dict[str, dict[str, str | int | float]] = {
    "TCS": {
        "name": "Tata Consultancy Services Limited",
        "exchange": "NSE",
        "currency": "INR",
        "price": 3045.20,
        "previous_close": 3055.90,
        "volume": 2_145_300,
        "market_cap_crore": 1_101_800.0,
        "pe": 23.8,
        "roe": 51.2,
        "debt_to_equity": 0.09,
        "revenue_growth": 5.6,
        "profit_growth": 4.4,
    },
    "INFY": {
        "name": "Infosys Limited",
        "exchange": "NSE",
        "currency": "INR",
        "price": 1422.75,
        "previous_close": 1411.18,
        "volume": 5_420_100,
        "market_cap_crore": 590_400.0,
        "pe": 21.7,
        "roe": 29.4,
        "debt_to_equity": 0.10,
        "revenue_growth": 6.1,
        "profit_growth": 7.2,
    },
    "RELIANCE": {
        "name": "Reliance Industries Limited",
        "exchange": "NSE",
        "currency": "INR",
        "price": 1428.40,
        "previous_close": 1412.16,
        "volume": 8_310_500,
        "market_cap_crore": 1_933_200.0,
        "pe": 24.6,
        "roe": 9.2,
        "debt_to_equity": 0.44,
        "revenue_growth": 7.4,
        "profit_growth": 3.8,
    },
}


class MockMarketDataProvider(MarketDataProvider):
    """Repeatable illustrative data that never claims to be live."""

    name = "mock_provider"
    data_status: DataStatus = "mock"

    def __init__(self, timezone: str = "Asia/Kolkata") -> None:
        self.timezone = ZoneInfo(timezone)

    def _record(self, symbol: str) -> tuple[str, dict[str, str | int | float]]:
        normalized = normalize_symbol(symbol)
        try:
            return normalized, MOCK_STOCKS[normalized]
        except KeyError as exc:
            supported = ", ".join(sorted(MOCK_STOCKS))
            raise LookupError(
                f"No mock data for {normalized}. Supported: {supported}."
            ) from exc

    async def list_symbols(self, query: str | None = None) -> list[str]:
        if not query or not query.strip():
            return sorted(MOCK_STOCKS)
        term = query.strip().lower()
        return [
            symbol
            for symbol, record in sorted(MOCK_STOCKS.items())
            if term in symbol.lower() or term in str(record["name"]).lower()
        ]

    async def get_snapshot(self, symbol: str) -> StockSnapshot:
        normalized, record = self._record(symbol)
        as_of = datetime.combine(date.today(), time(hour=15, minute=30), self.timezone)
        return StockSnapshot(
            symbol=normalized,
            as_of=as_of,
            source=self.name,
            data_status=self.data_status,
            **record,
        )

    async def get_price_history(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        interval: PriceInterval = "1d",
    ) -> list[PriceBar]:
        if end_date < start_date:
            raise ValueError("end_date must be on or after start_date.")
        if (end_date - start_date).days > 3650:
            raise ValueError("Mock history is limited to ten years per request.")
        normalized, record = self._record(symbol)
        step = 7 if interval == "1w" else 1
        bars: list[PriceBar] = []
        for offset in range(0, (end_date - start_date).days + 1, step):
            trading_date = start_date + timedelta(days=offset)
            if interval == "1d" and trading_date.weekday() >= 5:
                continue
            position = len(bars) + 1
            close = round(
                float(record["price"]) * (1 + ((position % 11) - 5) * 0.003), 2
            )
            open_price = round(close * (0.997 + (position % 3) * 0.001), 2)
            bars.append(
                PriceBar(
                    symbol=normalized,
                    trading_date=trading_date,
                    interval=interval,
                    open=open_price,
                    high=round(max(open_price, close) * 1.006, 2),
                    low=round(min(open_price, close) * 0.994, 2),
                    close=close,
                    volume=int(record["volume"]) + position * 12_500,
                    source=self.name,
                    data_status=self.data_status,
                )
            )
        return bars
