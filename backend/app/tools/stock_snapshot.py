"""Stock snapshot and price-history tools using labeled mock MVP data."""

from datetime import date, timedelta
from typing import Any

from app.agents.tool_registry import register_tool
from app.agents.tool_schemas import PriceHistoryArguments, StockSnapshotArguments

MOCK_STOCKS: dict[str, dict[str, Any]] = {
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


def get_stock_record(symbol: str) -> dict[str, Any]:
    """Return one mock stock record or explain which symbols are supported."""
    normalized = symbol.strip().upper()
    try:
        return {"symbol": normalized, **MOCK_STOCKS[normalized]}
    except KeyError as exc:
        supported = ", ".join(sorted(MOCK_STOCKS))
        raise ValueError(
            f"No mock data for {normalized}. Supported: {supported}."
        ) from exc


def build_price_history(
    symbol: str, start_date: date, end_date: date, interval: str = "1d"
) -> list[dict[str, Any]]:
    """Build deterministic OHLCV bars for development and tests."""
    stock = get_stock_record(symbol)
    step = 7 if interval == "1w" else 1
    bars: list[dict[str, Any]] = []
    for offset in range(0, (end_date - start_date).days + 1, step):
        trading_date = start_date + timedelta(days=offset)
        if interval == "1d" and trading_date.weekday() >= 5:
            continue
        position = len(bars) + 1
        close = round(float(stock["price"]) * (1 + ((position % 11) - 5) * 0.003), 2)
        open_price = round(close * (0.997 + (position % 3) * 0.001), 2)
        bars.append(
            {
                "date": trading_date.isoformat(),
                "open": open_price,
                "high": round(max(open_price, close) * 1.006, 2),
                "low": round(min(open_price, close) * 0.994, 2),
                "close": close,
                "volume": int(stock["volume"]) + position * 12_500,
            }
        )
    return bars


@register_tool("get_stock_snapshot")
async def get_stock_snapshot(arguments: StockSnapshotArguments) -> dict[str, Any]:
    stock = get_stock_record(arguments.symbol)
    previous_close = float(stock["previous_close"])
    change = round(float(stock["price"]) - previous_close, 2)
    return {
        **stock,
        "change": change,
        "change_percent": round(change / previous_close * 100, 2),
        "as_of": date.today().isoformat(),
        "source": "mock_provider",
        "data_status": "mock",
        "warning": "Illustrative mock data; not current market data.",
    }


@register_tool("get_price_history")
async def get_price_history(arguments: PriceHistoryArguments) -> dict[str, Any]:
    bars = build_price_history(
        arguments.symbol, arguments.start_date, arguments.end_date, arguments.interval
    )
    return {
        "symbol": arguments.symbol,
        "interval": arguments.interval,
        "start_date": arguments.start_date.isoformat(),
        "end_date": arguments.end_date.isoformat(),
        "bars": bars,
        "count": len(bars),
        "as_of": arguments.end_date.isoformat(),
        "source": "mock_provider",
        "data_status": "mock",
        "warning": "Illustrative mock data; not current market data.",
    }
