"""Async sliding-window rate limiting for the single-process MVP."""

import asyncio
import math
import time
from collections import defaultdict, deque
from collections.abc import Callable, Iterable
from dataclasses import dataclass

from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

Clock = Callable[[], float]


@dataclass(frozen=True, slots=True)
class RateLimitDecision:
    allowed: bool
    limit: int
    remaining: int
    retry_after_seconds: int
    reset_after_seconds: int


class InMemoryRateLimiter:
    """Concurrency-safe, per-key sliding-window limiter.

    This implementation is appropriate for local development or one server
    process. Use a shared Redis-backed implementation for multiple workers.
    """

    def __init__(
        self,
        limit: int = 30,
        window_seconds: float = 60.0,
        *,
        clock: Clock = time.monotonic,
    ) -> None:
        if limit < 1:
            raise ValueError("limit must be positive.")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be greater than zero.")
        self.limit = limit
        self.window_seconds = window_seconds
        self._clock = clock
        self._requests: defaultdict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def check(self, key: str) -> RateLimitDecision:
        """Consume one request when allowed and return limit metadata."""

        normalized_key = key.strip() or "unknown"
        async with self._lock:
            now = self._clock()
            cutoff = now - self.window_seconds
            requests = self._requests[normalized_key]
            while requests and requests[0] <= cutoff:
                requests.popleft()

            if len(requests) >= self.limit:
                wait = max(0.0, self.window_seconds - (now - requests[0]))
                seconds = max(1, math.ceil(wait))
                return RateLimitDecision(
                    allowed=False,
                    limit=self.limit,
                    remaining=0,
                    retry_after_seconds=seconds,
                    reset_after_seconds=seconds,
                )

            requests.append(now)
            reset = max(1, math.ceil(self.window_seconds - (now - requests[0])))
            return RateLimitDecision(
                allowed=True,
                limit=self.limit,
                remaining=self.limit - len(requests),
                retry_after_seconds=0,
                reset_after_seconds=reset,
            )

    async def clear(self, key: str | None = None) -> None:
        """Clear one key or all counters; useful for tests and administration."""

        async with self._lock:
            if key is None:
                self._requests.clear()
            else:
                self._requests.pop(key.strip() or "unknown", None)


def _client_key(request: Request, trust_proxy_headers: bool) -> str:
    if trust_proxy_headers:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",", maxsplit=1)[0].strip()
    if request.client is not None:
        return request.client.host
    return "unknown"


def _headers(decision: RateLimitDecision) -> dict[str, str]:
    return {
        "X-RateLimit-Limit": str(decision.limit),
        "X-RateLimit-Remaining": str(decision.remaining),
        "X-RateLimit-Reset": str(decision.reset_after_seconds),
    }


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Apply per-client limits and expose standard response metadata."""

    def __init__(
        self,
        app: Starlette,
        *,
        enabled: bool = True,
        requests_per_minute: int = 30,
        excluded_paths: Iterable[str] = ("/health", "/api/v1/health"),
        trust_proxy_headers: bool = False,
        limiter: InMemoryRateLimiter | None = None,
    ) -> None:
        super().__init__(app)
        self.enabled = enabled
        self.excluded_paths = frozenset(excluded_paths)
        self.trust_proxy_headers = trust_proxy_headers
        self.limiter = limiter or InMemoryRateLimiter(
            limit=requests_per_minute,
            window_seconds=60,
        )

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        if (
            not self.enabled
            or request.method == "OPTIONS"
            or request.url.path in self.excluded_paths
        ):
            return await call_next(request)

        decision = await self.limiter.check(
            _client_key(request, self.trust_proxy_headers)
        )
        headers = _headers(decision)
        if not decision.allowed:
            headers["Retry-After"] = str(decision.retry_after_seconds)
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please try again later."},
                headers=headers,
            )

        response = await call_next(request)
        response.headers.update(headers)
        return response
