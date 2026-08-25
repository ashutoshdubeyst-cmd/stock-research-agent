"""Orchestrate market data and reusable financial calculations."""

import asyncio
from datetime import date
from typing import Any, Literal

from app.analytics.moving_averages import ema, moving_average_summary, sma
from app.analytics.returns import annualized_return, total_return
from app.analytics.rsi import latest_rsi, rsi_signal
from app.data_providers.base import PriceBar, PriceInterval
from app.services.stock_service import StockService

ComparisonMetric = Literal[
    "price_return",
    "rsi",
    "revenue_growth",
    "profit_growth",
    "roe",
    "debt_to_equity",
    "pe",
]


def _last_number(series: Any) -> float | None:
    """Return the last calculated value in a JSON-safe form."""

    value = series.iloc[-1]
    return None if value != value else round(float(value), 4)


class AnalyticsService:
    """Calculate indicators using consistently sourced price history."""

    def __init__(self, stock_service: StockService) -> None:
        self.stock_service = stock_service

    @staticmethod
    def _closing_prices(bars: list[PriceBar]) -> list[float]:
        if not bars:
            raise ValueError("No price history is available for this calculation.")
        return [bar.close for bar in bars]

    async def analyze_stock(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        interval: PriceInterval = "1d",
        short_window: int = 20,
        long_window: int = 50,
        rsi_window: int = 14,
    ) -> dict[str, Any]:
        """Return moving averages, RSI, and returns for one stock."""

        bars = await self.stock_service.get_price_history(
            symbol,
            start_date,
            end_date,
            interval,
        )
        prices = self._closing_prices(bars)
        rsi_value = latest_rsi(prices, rsi_window)
        periods_per_year = 252 if interval == "1d" else 52

        return {
            "symbol": bars[0].symbol,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "interval": interval,
            "observations": len(bars),
            "moving_averages": moving_average_summary(
                prices,
                short_window,
                long_window,
            ),
            "latest_indicators": {
                f"sma_{short_window}": _last_number(sma(prices, short_window)),
                f"ema_{short_window}": _last_number(ema(prices, short_window)),
                f"rsi_{rsi_window}": rsi_value,
                "rsi_signal": rsi_signal(rsi_value),
            },
            "returns": {
                "total_decimal": total_return(prices),
                "annualized_decimal": annualized_return(prices, periods_per_year),
            },
            "source": bars[-1].source,
            "data_status": bars[-1].data_status,
            "as_of": bars[-1].trading_date.isoformat(),
        }

    async def compare_stocks(
        self,
        symbols: list[str],
        metrics: list[ComparisonMetric],
        start_date: date,
        end_date: date,
        interval: PriceInterval = "1d",
    ) -> dict[str, Any]:
        """Compare two to five unique stocks over one consistent period."""

        normalized = [symbol.strip().upper() for symbol in symbols]
        if not 2 <= len(normalized) <= 5:
            raise ValueError("Provide between two and five stock symbols.")
        if len(set(normalized)) != len(normalized):
            raise ValueError("Stock symbols must be unique.")
        if not metrics:
            raise ValueError("At least one comparison metric is required.")

        snapshots, histories = await asyncio.gather(
            asyncio.gather(
                *(self.stock_service.get_snapshot(symbol) for symbol in normalized)
            ),
            asyncio.gather(
                *(
                    self.stock_service.get_price_history(
                        symbol,
                        start_date,
                        end_date,
                        interval,
                    )
                    for symbol in normalized
                )
            ),
        )

        rows: list[dict[str, Any]] = []
        for snapshot, bars in zip(snapshots, histories, strict=True):
            prices = self._closing_prices(bars)
            row: dict[str, Any] = {
                "symbol": snapshot.symbol,
                "name": snapshot.name,
            }
            for metric in metrics:
                if metric == "price_return":
                    value = total_return(prices)
                    row["price_return_percent"] = (
                        None if value is None else round(value * 100, 4)
                    )
                elif metric == "rsi":
                    row["rsi_14"] = latest_rsi(prices)
                else:
                    row[metric] = getattr(snapshot, metric)
            rows.append(row)

        first_history = histories[0]
        return {
            "symbols": normalized,
            "metrics": metrics,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "interval": interval,
            "comparison": rows,
            "source": first_history[-1].source,
            "data_status": first_history[-1].data_status,
            "as_of": first_history[-1].trading_date.isoformat(),
        }
