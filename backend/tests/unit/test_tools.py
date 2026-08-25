"""Unit tests for registered stock-agent tools and their executor."""

from datetime import date, timedelta

import pytest

import app.tools  # noqa: F401 - importing registers the allowlisted tools
from app.agents.tool_executor import ToolExecutor
from app.agents.tool_registry import tool_registry
from app.agents.tool_schemas import (
    CompareStocksArguments,
    PriceHistoryArguments,
    StockSnapshotArguments,
    TechnicalIndicatorArguments,
)
from app.tools.stock_comparison import compare_stocks
from app.tools.stock_snapshot import get_price_history, get_stock_snapshot
from app.tools.technical_indicators import get_technical_indicators

EXPECTED_TOOLS = {
    "get_stock_snapshot",
    "get_price_history",
    "get_technical_indicators",
    "compare_stocks",
}


def test_all_expected_tools_are_registered_with_schemas() -> None:
    assert set(tool_registry.names()) == EXPECTED_TOOLS
    schema_names = {
        str(schema["function"]["name"])  # type: ignore[index]
        for schema in tool_registry.schemas()
    }
    assert schema_names == EXPECTED_TOOLS


@pytest.mark.asyncio
async def test_stock_snapshot_is_normalized_and_labeled_mock() -> None:
    result = await get_stock_snapshot(StockSnapshotArguments(symbol=" tcs "))

    assert result["symbol"] == "TCS"
    assert result["price"] > 0
    assert result["data_status"] == "mock"
    assert "not current market data" in result["warning"]


@pytest.mark.asyncio
async def test_price_history_is_chronological_and_excludes_weekends() -> None:
    start = date(2026, 8, 17)
    end = date(2026, 8, 23)
    result = await get_price_history(
        PriceHistoryArguments(symbol="INFY", start_date=start, end_date=end)
    )

    dates = [date.fromisoformat(bar["date"]) for bar in result["bars"]]
    assert result["count"] == 5
    assert dates == sorted(dates)
    assert all(trading_date.weekday() < 5 for trading_date in dates)


@pytest.mark.asyncio
async def test_technical_indicator_tool_returns_only_requested_indicators() -> None:
    result = await get_technical_indicators(
        TechnicalIndicatorArguments(
            symbol="RELIANCE",
            indicators=["rsi", "sma", "bollinger"],
        )
    )

    assert set(result["indicators"]) == {
        "rsi_14",
        "sma_20",
        "bollinger_bands_20",
    }
    assert result["observations"] >= 20
    assert result["data_status"] == "mock"


@pytest.mark.asyncio
async def test_comparison_uses_same_metrics_for_each_stock() -> None:
    result = await compare_stocks(
        CompareStocksArguments(
            symbols=["TCS", "INFY"],
            metrics=["price_return", "rsi", "pe"],
        )
    )

    assert len(result["comparison"]) == 2
    for row in result["comparison"]:
        assert {"symbol", "name", "price_return_90d_percent", "rsi_14", "pe"} <= set(
            row
        )


@pytest.mark.asyncio
async def test_executor_validates_arguments_and_runs_registered_tool() -> None:
    executor = ToolExecutor(tool_registry)
    record = await executor.execute(
        call_id="call-1",
        name="get_stock_snapshot",
        raw_arguments='{"symbol":"infy"}',
        trace_id="test-trace",
    )

    assert record.status == "success"
    assert record.arguments == {"symbol": "INFY"}
    assert record.result is not None
    assert record.result["symbol"] == "INFY"


@pytest.mark.asyncio
async def test_executor_rejects_unknown_tool() -> None:
    record = await ToolExecutor(tool_registry).execute(
        call_id="call-2",
        name="delete_everything",
        raw_arguments={},
        trace_id="test-trace",
    )

    assert record.status == "error"
    assert "not registered" in (record.error or "")


@pytest.mark.asyncio
async def test_executor_rejects_invalid_json_and_date_order() -> None:
    executor = ToolExecutor(tool_registry)
    invalid_json = await executor.execute(
        call_id="call-3",
        name="get_stock_snapshot",
        raw_arguments="not-json",
        trace_id="test-trace",
    )
    invalid_dates = await executor.execute(
        call_id="call-4",
        name="get_price_history",
        raw_arguments={
            "symbol": "TCS",
            "start_date": (date.today() - timedelta(days=1)).isoformat(),
            "end_date": (date.today() - timedelta(days=2)).isoformat(),
        },
        trace_id="test-trace",
    )

    assert invalid_json.status == "error"
    assert invalid_dates.status == "error"
    assert "Invalid tool arguments" in (invalid_dates.error or "")


@pytest.mark.asyncio
async def test_executor_masks_handler_error_for_unsupported_symbol() -> None:
    record = await ToolExecutor(tool_registry).execute(
        call_id="call-5",
        name="get_stock_snapshot",
        raw_arguments={"symbol": "UNKNOWN"},
        trace_id="test-trace",
    )

    assert record.status == "error"
    assert record.error == "The tool could not complete the request."
