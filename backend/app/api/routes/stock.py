from datetime import date, timedelta
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.dependencies import SettingsDep


router = APIRouter(prefix="/stocks", tags=["stocks"])


# Development-only records. Replace this dictionary with StockService after the
# provider and database layers are implemented.
MOCK_STOCKS: dict[str, dict[str, str | float]] = {
    "TCS": {
        "name": "Tata Consultancy Services Limited",
        "exchange": "NSE",
        "currency": "INR",
        "price": 3045.20,
        "change_percent": -0.35,
    },
    "INFY": {
        "name": "Infosys Limited",
        "exchange": "NSE",
        "currency": "INR",
        "price": 1422.75,
        "change_percent": 0.82,
    },
    "RELIANCE": {
        "name": "Reliance Industries Limited",
        "exchange": "NSE",
        "currency": "INR",
        "price": 1428.40,
        "change_percent": 1.15,
    },
}


class StockSummary(BaseModel):
    symbol: str
    name: str
    exchange: str
    currency: str
    price: float = Field(gt=0)
    change_percent: float
    data_status: Literal["mock"] = "mock"
    source: str = "mock_provider"


class PriceBar(BaseModel):
    trading_date: date
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: int = Field(ge=0)


class StockHistoryResponse(BaseModel):
    symbol: str
    interval: Literal["1d"] = "1d"
    data_status: Literal["mock"] = "mock"
    source: str = "mock_provider"
    bars: list[PriceBar]
    warning: str = "Illustrative mock data; not current market data."


def normalize_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper()
    if not normalized or len(normalized) > 30:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A valid stock symbol is required.",
        )
    return normalized


def get_mock_stock(symbol: str) -> StockSummary:
    normalized = normalize_symbol(symbol)
    record = MOCK_STOCKS.get(normalized)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No mock data is available for symbol {normalized}.",
        )
    return StockSummary(symbol=normalized, **record)


@router.get("", response_model=list[StockSummary], summary="List supported stocks")
async def list_stocks(
    settings: SettingsDep,
    query: str | None = Query(default=None, max_length=50),
) -> list[StockSummary]:
    """List stocks currently available from the mock provider."""

    if settings.market_data_provider != "mock":
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=(
                f"The {settings.market_data_provider} stock adapter has not been "
                "implemented yet."
            ),
        )

    results = [get_mock_stock(symbol) for symbol in sorted(MOCK_STOCKS)]
    if query:
        term = query.strip().lower()
        results = [
            item
            for item in results
            if term in item.symbol.lower() or term in item.name.lower()
        ]
    return results


@router.get(
    "/{symbol}",
    response_model=StockSummary,
    summary="Get a stock snapshot",
)
async def get_stock(symbol: str, settings: SettingsDep) -> StockSummary:
    """Return a clearly labeled mock stock snapshot."""

    if settings.market_data_provider != "mock":
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=(
                f"The {settings.market_data_provider} stock adapter has not been "
                "implemented yet."
            ),
        )
    return get_mock_stock(symbol)


@router.get(
    "/{symbol}/history",
    response_model=StockHistoryResponse,
    summary="Get mock daily price history",
)
async def get_stock_history(
    symbol: str,
    settings: SettingsDep,
    days: int = Query(default=30, ge=5, le=90),
) -> StockHistoryResponse:
    """Generate deterministic mock bars for frontend and analytics development."""

    if settings.market_data_provider != "mock":
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=(
                f"The {settings.market_data_provider} stock adapter has not been "
                "implemented yet."
            ),
        )

    stock = get_mock_stock(symbol)
    today = date.today()
    bars: list[PriceBar] = []

    # This deterministic pattern is intentionally not a market simulation.
    for offset in range(days - 1, -1, -1):
        trading_date = today - timedelta(days=offset)
        variation = ((days - offset) % 9 - 4) * 0.0025
        close = round(stock.price * (1 + variation), 2)
        open_price = round(close * 0.998, 2)
        high = round(max(open_price, close) * 1.004, 2)
        low = round(min(open_price, close) * 0.996, 2)
        bars.append(
            PriceBar(
                trading_date=trading_date,
                open=open_price,
                high=high,
                low=low,
                close=close,
                volume=1_000_000 + (days - offset) * 12_500,
            )
        )

    return StockHistoryResponse(symbol=stock.symbol, bars=bars)