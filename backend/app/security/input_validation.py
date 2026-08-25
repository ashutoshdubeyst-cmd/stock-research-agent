"""Central validation helpers for untrusted API and agent input."""

import re
import unicodedata
from collections.abc import Iterable
from datetime import date

SYMBOL_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9._-]{0,29}$")
SEARCH_PATTERN = re.compile(r"^[\w\s.&'()/-]+$", flags=re.UNICODE)
ALLOWED_TEXT_CONTROLS = {"\n", "\r", "\t"}


class InputValidationError(ValueError):
    """Raised when user-controlled input violates an application boundary."""


def _normalize_unicode(value: str) -> str:
    if not isinstance(value, str):
        raise InputValidationError("The input must be text.")
    return unicodedata.normalize("NFKC", value)


def _reject_control_characters(value: str) -> None:
    for character in value:
        if (
            unicodedata.category(character) == "Cc"
            and character not in ALLOWED_TEXT_CONTROLS
        ):
            raise InputValidationError(
                "The input contains unsupported control characters."
            )


def normalize_symbol(symbol: str) -> str:
    """Normalize and strictly validate a stock exchange symbol."""

    normalized = _normalize_unicode(symbol).strip().upper()
    if not SYMBOL_PATTERN.fullmatch(normalized):
        raise InputValidationError(
            "A symbol must contain 1-30 letters, numbers, '.', '_', or '-'."
        )
    return normalized


def validate_user_message(message: str, max_length: int = 2_000) -> str:
    """Validate agent text without altering its meaning or financial terms."""

    if max_length < 1:
        raise ValueError("max_length must be positive.")
    normalized = _normalize_unicode(message).strip()
    _reject_control_characters(normalized)
    if not normalized:
        raise InputValidationError("A message is required.")
    if len(normalized) > max_length:
        raise InputValidationError(
            f"The message cannot exceed {max_length} characters."
        )
    return normalized


def validate_search_query(query: str | None, max_length: int = 50) -> str | None:
    """Normalize an optional human-readable stock search query."""

    if query is None:
        return None
    normalized = " ".join(_normalize_unicode(query).strip().split())
    _reject_control_characters(normalized)
    if not normalized:
        return None
    if len(normalized) > max_length:
        raise InputValidationError(
            f"The search query cannot exceed {max_length} characters."
        )
    if not SEARCH_PATTERN.fullmatch(normalized):
        raise InputValidationError("The search query contains unsupported characters.")
    return normalized


def validate_date_range(
    start_date: date,
    end_date: date,
    *,
    max_days: int = 3_650,
    allow_future: bool = False,
) -> tuple[date, date]:
    """Validate an inclusive market-history date range."""

    if max_days < 1:
        raise ValueError("max_days must be positive.")
    if end_date < start_date:
        raise InputValidationError("end_date must be on or after start_date.")
    if not allow_future and end_date > date.today():
        raise InputValidationError("end_date cannot be in the future.")
    if (end_date - start_date).days > max_days:
        raise InputValidationError(
            f"The requested date range cannot exceed {max_days} days."
        )
    return start_date, end_date


def validate_symbols(
    symbols: Iterable[str],
    *,
    minimum: int = 1,
    maximum: int = 5,
) -> list[str]:
    """Normalize a bounded collection of unique stock symbols."""

    if minimum < 0 or maximum < minimum:
        raise ValueError("Invalid minimum and maximum symbol limits.")
    normalized = [normalize_symbol(symbol) for symbol in symbols]
    if not minimum <= len(normalized) <= maximum:
        raise InputValidationError(
            f"Provide between {minimum} and {maximum} stock symbols."
        )
    if len(set(normalized)) != len(normalized):
        raise InputValidationError("Stock symbols must be unique.")
    return normalized
