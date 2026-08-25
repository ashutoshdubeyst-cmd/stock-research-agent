"""Factory for selecting the configured market-data provider."""

from collections.abc import Callable

from app.config import Settings
from app.data_providers.base import MarketDataProvider
from app.data_providers.mock_provider import MockMarketDataProvider

ProviderBuilder = Callable[[Settings], MarketDataProvider]


def _build_mock(settings: Settings) -> MarketDataProvider:
    return MockMarketDataProvider(timezone=settings.market_timezone)


PROVIDER_BUILDERS: dict[str, ProviderBuilder] = {"mock": _build_mock}


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
