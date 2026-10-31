"""In-memory sliding-window rate limiting for the expensive endpoints.

Generating a PDF starts a LibreOffice process (up to 120 s, a few hundred MB), so a client that
loops on the generate endpoints can starve everyone else. Each generate route therefore carries
two limits, both `RATE_LIMIT_WINDOW_SECONDS` long: one per client IP (`ip_rate_limit`, checked
before sign-in so it also covers bad-token floods) and one per signed-in user (`user_rate_limit`).

State lives in this process's memory. That is deliberate and fine while the API runs as a single
machine (scale-to-zero on Fly): a restart forgets the counters, and with several instances each
would count separately, so the effective limit would be multiplied by the instance count. Move the
counters to a shared store before scaling out.
"""

import math
import os
import time
from collections import deque
from collections.abc import Awaitable, Callable
from uuid import UUID

from fastapi import Depends, HTTPException, Request

from lineup.auth.dependencies import get_current_user_id

RATE_LIMIT_WINDOW_SECONDS = 60
DEFAULT_GENERATE_PER_IP = 30
DEFAULT_GENERATE_PER_USER = 10

# A header value is attacker-influenced when no proxy overwrites it, so cap what becomes a key.
_MAX_KEY_LENGTH = 100


def read_rate_limit(name: str, raw: str | None, default: int) -> int:
    """Parse the requests-per-window env var `name`, falling back to `default` when unset.

    Refuses non-numbers and values < 1 at startup (0 would block the endpoint for everybody).
    The value is never echoed back, only the variable name.
    """
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        raise ValueError(f"{name} must be a whole number") from None
    if value < 1:
        raise ValueError(f"{name} must be at least 1")
    return value


def read_client_ip_header(raw: str | None) -> str | None:
    """`CLIENT_IP_HEADER`: name of a request header that carries the real client IP, or `None`.

    Set it only when a trusted proxy *overwrites* that header on every request (Fly.io:
    `Fly-Client-IP`). Otherwise a client could send any value and dodge the per-IP limit, which
    is why `X-Forwarded-For` (appended to, not replaced) is a poor choice.
    """
    value = (raw or "").strip()
    return value or None


CLIENT_IP_HEADER = read_client_ip_header(os.getenv("CLIENT_IP_HEADER"))


def client_ip(request: Request) -> str:
    """The caller's address: `CLIENT_IP_HEADER` if configured and present, else the socket peer.

    Behind a reverse proxy without `CLIENT_IP_HEADER`, the peer is the proxy, so all clients
    would share one bucket. Never logged: an IP address is personal data (requirement S8).
    """
    if CLIENT_IP_HEADER:
        value = request.headers.get(CLIENT_IP_HEADER, "").strip()
        if value:
            return value[:_MAX_KEY_LENGTH]
    return request.client.host if request.client else "unknown"


class SlidingWindowLimiter:
    """Allows at most `limit` hits per key within the last `window_seconds` seconds.

    A sliding window (timestamps of recent hits) avoids the burst a fixed window allows at its
    boundary, where a client could use `limit` hits at the end of one window and `limit` more at
    the start of the next. Not thread-safe by design: it is only called from async dependencies,
    which all run on the event loop.
    """

    def __init__(
        self,
        limit: int,
        window_seconds: float = RATE_LIMIT_WINDOW_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        """`clock` is injectable so tests can move time without sleeping."""
        self.limit = limit
        self.window_seconds = window_seconds
        self._clock = clock
        self._hits: dict[str, deque[float]] = {}
        self._last_sweep = clock()

    def hit(self, key: str) -> float | None:
        """Record a request for `key`.

        Returns `None` when it is allowed, otherwise the number of seconds until the oldest
        counted request leaves the window (what to send as `Retry-After`). A rejected request is
        not counted, so a client that keeps hammering is let back in as soon as the window frees.
        """
        now = self._clock()
        self._sweep(now)
        hits = self._hits.setdefault(key, deque())
        while hits and now - hits[0] >= self.window_seconds:
            hits.popleft()
        if len(hits) >= self.limit:
            return hits[0] + self.window_seconds - now
        hits.append(now)
        return None

    def reset(self) -> None:
        """Forget every counter (used by the tests between cases)."""
        self._hits.clear()

    def _sweep(self, now: float) -> None:
        # Without this, every distinct key ever seen would stay in memory forever.
        if now - self._last_sweep < self.window_seconds:
            return
        self._last_sweep = now
        expired = [
            key
            for key, hits in self._hits.items()
            if not hits or now - hits[-1] >= self.window_seconds
        ]
        for key in expired:
            del self._hits[key]


LIMITERS: dict[str, SlidingWindowLimiter] = {}


def reset_limiters() -> None:
    """Clear the counters of every registered limiter (test helper)."""
    for limiter in LIMITERS.values():
        limiter.reset()


def _check(limiter: SlidingWindowLimiter, key: str) -> None:
    retry_after = limiter.hit(key)
    if retry_after is not None:
        raise HTTPException(
            status_code=429,
            detail="Too many requests, try again later",
            headers={"Retry-After": str(max(1, math.ceil(retry_after)))},
        )


def _register(name: str, limit: int) -> SlidingWindowLimiter:
    if name in LIMITERS:
        raise ValueError(f"rate limit {name!r} is already registered")
    limiter = SlidingWindowLimiter(limit)
    LIMITERS[name] = limiter
    return limiter


def ip_rate_limit(name: str, limit: int) -> Callable[[Request], Awaitable[None]]:
    """FastAPI dependency factory: at most `limit` requests per minute per client IP.

    Use it in the route's `dependencies=[...]` so it runs before the sign-in check. `name` is
    the limiter's registry key and must be unique. The dependency raises `429` with a
    `Retry-After` header (seconds) and never logs the IP.
    """
    limiter = _register(name, limit)

    async def dependency(request: Request) -> None:
        _check(limiter, client_ip(request))

    return dependency


def user_rate_limit(name: str, limit: int) -> Callable[[UUID], Awaitable[None]]:
    """FastAPI dependency factory: at most `limit` requests per minute per signed-in user.

    Depends on `get_current_user_id`, so an unauthenticated request gets `401` first (FastAPI
    resolves that dependency once per request and shares it with the route). Raises `429` with
    `Retry-After` when exceeded.
    """
    limiter = _register(name, limit)

    async def dependency(user_id: UUID = Depends(get_current_user_id)) -> None:
        _check(limiter, str(user_id))

    return dependency


RATE_LIMIT_RESPONSES = {
    429: {"description": "Too many requests; wait for the `Retry-After` seconds."}
}

GENERATE_PER_IP = read_rate_limit(
    "RATE_LIMIT_GENERATE_PER_IP",
    os.getenv("RATE_LIMIT_GENERATE_PER_IP"),
    DEFAULT_GENERATE_PER_IP,
)
GENERATE_PER_USER = read_rate_limit(
    "RATE_LIMIT_GENERATE_PER_USER",
    os.getenv("RATE_LIMIT_GENERATE_PER_USER"),
    DEFAULT_GENERATE_PER_USER,
)

# Both generate endpoints (`POST /lineups`, `POST /lineups/saved/{id}/generate`) share these two
# limiters, because they cost the same LibreOffice time: switching endpoints is no way around them.
generate_ip_limit = ip_rate_limit("generate:ip", GENERATE_PER_IP)
generate_user_limit = user_rate_limit("generate:user", GENERATE_PER_USER)

# Invitation links (#51): preview, accept and create. Codes are 256-bit random, so these limits
# are not what keeps them safe; they stop a client from hammering the unauthenticated preview
# and from spamming link creation. The join page makes one preview and one accept call per visit.
INVITE_PER_IP = 30
INVITE_PER_USER = 10
invite_ip_limit = ip_rate_limit("invite:ip", INVITE_PER_IP)
invite_user_limit = user_rate_limit("invite:user", INVITE_PER_USER)
