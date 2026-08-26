"""Read-only Upstox market-data adapter using official HTTP APIs."""

from datetime import UTC, date, datetime
from typing import Any
from urllib.parse import quote

import httpx

from app.data_providers.base import (
    Instrument,
    InstrumentNotFoundError,
    MarketDataProvider,
    PriceBar,
    PriceInterval,
    ProviderAuthenticationError,
    ProviderResponseError,
    StockSnapshot,
    normalize_symbol,
)

UPSTOX_API_URL = "https://api.upstox.com"
DEFAULT_SYMBOLS = ("TCS", "INFY", "RELIANCE")


class UpstoxMarketDataProvider(MarketDataProvider):
    """Resolve NSE symbols and retrieve Upstox quotes and V3 candles."""

    name = "upstox"
    data_status = "real_time"

    def __init__(
        self,
        access_token: str,
        *,
        exchange: str = "NSE",
        timeout_seconds: float = 20.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        token = access_token.strip()
        if not token:
            raise ProviderAuthenticationError("UPSTOX_ACCESS_TOKEN is required.")
        self.exchange = exchange.strip().upper()
        self._token = token
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            base_url=UPSTOX_API_URL,
            timeout=httpx.Timeout(timeout_seconds),
            follow_redirects=True,
        )
        self._instrument_cache: dict[str, Instrument] = {}

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Accept": "application/json",
            "Authorization": f"Bearer {self._token}",
        }

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def _get(
        self,
        path: str,
        *,
        params: dict[str, str | int] | None = None,
    ) -> dict[str, Any]:
        try:
            response = await self._client.get(
                path,
                params=params,
                headers=self._headers,
            )
        except httpx.TimeoutException as exc:
            raise ProviderResponseError("Upstox request timed out.") from exc
        except httpx.HTTPError as exc:
            raise ProviderResponseError("Upstox could not be reached.") from exc

        if response.status_code in {401, 403}:
            raise ProviderAuthenticationError(
                "The Upstox access token is invalid or expired. Complete OAuth again."
            )
        if not response.is_success:
            request_id = response.headers.get("x-request-id")
            suffix = f" Reference: {request_id}." if request_id else ""
            raise ProviderResponseError(
                f"Upstox returned HTTP {response.status_code}.{suffix}"
            )
        try:
            payload = response.json()
        except ValueError as exc:
            raise ProviderResponseError("Upstox returned invalid JSON.") from exc
        if not isinstance(payload, dict) or payload.get("status") != "success":
            raise ProviderResponseError("Upstox returned an unsuccessful response.")
        return payload

    async def _search(self, query: str, records: int = 30) -> list[Instrument]:
        payload = await self._get(
            "/v2/instruments/search",
            params={
                "query": query[:50],
                "exchanges": self.exchange,
                "segments": "EQ",
                "page_number": 1,
                "records": min(30, max(1, records)),
            },
        )
        raw_items = payload.get("data")
        if not isinstance(raw_items, list):
            raise ProviderResponseError("Upstox instrument search data is missing.")

        instruments: list[Instrument] = []
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            values = (
                item.get("trading_symbol"),
                item.get("instrument_key"),
                item.get("name") or item.get("short_name"),
                item.get("instrument_type"),
            )
            if not all(isinstance(value, str) and value for value in values):
                continue
            symbol, key, name, instrument_type = values
            instrument = Instrument(
                symbol=symbol,
                name=name,
                exchange=str(item.get("exchange") or self.exchange),
                instrument_key=key,
                instrument_type=instrument_type,
            )
            instruments.append(instrument)
            self._instrument_cache[instrument.symbol] = instrument
        return instruments

    async def _resolve(self, symbol: str) -> Instrument:
        normalized = normalize_symbol(symbol)
        cached = self._instrument_cache.get(normalized)
        if cached is not None:
            return cached
        matches = await self._search(normalized)
        exact = next(
            (
                instrument
                for instrument in matches
                if instrument.symbol == normalized
                and instrument.exchange == self.exchange
                and instrument.instrument_type in {"EQ", "A"}
            ),
            None,
        )
        if exact is None:
            raise InstrumentNotFoundError(
                f"No {self.exchange} equity instrument was found for {normalized}."
            )
        return exact

    async def list_symbols(self, query: str | None = None) -> list[str]:
        if query is None or not query.strip():
            return list(DEFAULT_SYMBOLS)
        instruments = await self._search(query.strip())
        return sorted({instrument.symbol for instrument in instruments})

    @staticmethod
    def _timestamp(value: Any) -> datetime:
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                pass
        return datetime.now(UTC)

    async def get_snapshot(self, symbol: str) -> StockSnapshot:
        instrument = await self._resolve(symbol)
        payload = await self._get(
            "/v2/market-quote/quotes",
            params={"instrument_key": instrument.instrument_key},
        )
        raw_data = payload.get("data")
        if not isinstance(raw_data, dict):
            raise ProviderResponseError("Upstox quote data is missing.")
        quotes = [value for value in raw_data.values() if isinstance(value, dict)]
        quote_data = next(
            (
                value
                for value in quotes
                if value.get("instrument_token") == instrument.instrument_key
            ),
            quotes[0] if quotes else None,
        )
        if not isinstance(quote_data, dict):
            raise ProviderResponseError("Upstox did not return the requested quote.")

        price = float(quote_data.get("last_price") or 0)
        net_change = quote_data.get("net_change")
        ohlc = quote_data.get("ohlc")
        if isinstance(net_change, int | float):
            previous_close = price - float(net_change)
        elif isinstance(ohlc, dict):
            previous_close = float(ohlc.get("close") or 0)
        else:
            previous_close = 0.0
        if price <= 0 or previous_close <= 0:
            raise ProviderResponseError("Upstox quote prices are missing or invalid.")

        return StockSnapshot(
            symbol=instrument.symbol,
            name=instrument.name,
            exchange=instrument.exchange,
            currency="INR",
            price=price,
            previous_close=previous_close,
            volume=int(quote_data.get("volume") or 0),
            as_of=self._timestamp(quote_data.get("timestamp")),
            source=self.name,
            data_status="real_time",
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
        instrument = await self._resolve(symbol)
        unit = "days" if interval == "1d" else "weeks"
        instrument_key = quote(instrument.instrument_key, safe="")
        payload = await self._get(
            f"/v3/historical-candle/{instrument_key}/{unit}/1/"
            f"{end_date.isoformat()}/{start_date.isoformat()}"
        )
        data = payload.get("data")
        candles = data.get("candles") if isinstance(data, dict) else None
        if not isinstance(candles, list):
            raise ProviderResponseError("Upstox historical candle data is missing.")

        bars: list[PriceBar] = []
        for candle in candles:
            if not isinstance(candle, list) or len(candle) < 6:
                continue
            timestamp, open_price, high, low, close, volume = candle[:6]
            try:
                trading_date = datetime.fromisoformat(
                    str(timestamp).replace("Z", "+00:00")
                ).date()
                bars.append(
                    PriceBar(
                        symbol=instrument.symbol,
                        trading_date=trading_date,
                        interval=interval,
                        open=float(open_price),
                        high=float(high),
                        low=float(low),
                        close=float(close),
                        volume=int(volume),
                        source=self.name,
                        data_status="end_of_day",
                    )
                )
            except (TypeError, ValueError):
                continue
        return sorted(bars, key=lambda bar: bar.trading_date)
