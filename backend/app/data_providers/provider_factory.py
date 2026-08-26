"""Factory for selecting the configured market-data provider."""

from collections.abc import Callable

from app.config import Settings
from app.data_providers.base import MarketDataProvider
from app.data_providers.mock_provider import MockMarketDataProvider
from app.data_providers.upstox_provider import UpstoxMarketDataProvider

ProviderBuilder = Callable[[Settings], MarketDataProvider]


def _build_mock(settings: Settings) -> MarketDataProvider:
    return MockMarketDataProvider(timezone=settings.market_timezone)


def _build_upstox(settings: Settings) -> MarketDataProvider:
    if settings.upstox_access_token is None:
        raise ValueError(
            "UPSTOX_ACCESS_TOKEN is required when MARKET_DATA_PROVIDER=upstox."
        )
    return UpstoxMarketDataProvider(
        access_token=settings.upstox_access_token.get_secret_value(),
        exchange=settings.market_exchange,
    )


PROVIDER_BUILDERS: dict[str, ProviderBuilder] = {
    "mock": _build_mock,
    "upstox": _build_upstox,
}


def create_market_data_provider(settings: Settings) -> MarketDataProvider:
    """Create the configured provider or fail if it is not implemented."""

    provider_name = settings.market_data_provider
    builder = PROVIDER_BUILDERS.get(provider_name)
    if builder is None:
        implemented = ", ".join(sorted(PROVIDER_BUILDERS))
        raise NotImplementedError(
            f"Market-data provider {provider_name!r} is not implemented. "
            f"Available providers: {implemented}."
        )
    return builder(settings)
