"""Verifying Supabase access tokens (JWTs) against the project's public signing keys.

Supabase Auth signs every access token with a private key and publishes the matching public
keys as a JWKS document at `<SUPABASE_URL>/auth/v1/.well-known/jwks.json`. The API never sees a
secret: it downloads the public keys, caches them and checks each token's signature, issuer,
audience and expiry. Only asymmetric algorithms are accepted, so a token can never be forged by
someone who knows the public keys (the classic "alg confusion" attack with HS256 or `none`).

Nothing in this module logs or returns token contents: failures carry a fixed `reason` string.
"""

import asyncio
import logging
import os
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse
from uuid import UUID

import httpx
import jwt
from jwt import PyJWK, PyJWKSet

logger = logging.getLogger(__name__)

ALLOWED_ALGORITHMS = frozenset({"ES256", "RS256"})
AUDIENCE = "authenticated"
LEEWAY_SECONDS = 10
JWKS_TTL_SECONDS = 600
MIN_REFETCH_INTERVAL_SECONDS = 30
FETCH_TIMEOUT_SECONDS = 5
_LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1"})


class TokenError(Exception):
    """The token is not acceptable. `reason` is a fixed, log-safe code, never token content."""

    def __init__(self, reason: str) -> None:
        """Keep the machine-readable `reason` next to the message."""
        super().__init__(reason)
        self.reason = reason


class AuthConfigError(Exception):
    """`SUPABASE_URL` is missing or unusable: an operator problem, not the caller's."""


class AuthUnavailableError(Exception):
    """The signing keys could not be loaded (Supabase unreachable or returned garbage)."""


@dataclass(frozen=True)
class AuthConfig:
    """Where to find the signing keys and which issuer a token must name."""

    issuer: str
    jwks_url: str


def load_config() -> AuthConfig:
    """Derive the issuer and JWKS URL from the `SUPABASE_URL` environment variable.

    `SUPABASE_URL` is the project URL (`https://<ref>.supabase.co`), the same value the
    frontend uses. Plain `http` is accepted only for localhost (the Supabase CLI), because keys
    fetched over an unauthenticated connection could be swapped by an attacker on the path.
    Raises `AuthConfigError` when unset or malformed. Read on every call, so it is testable.
    """
    raw = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
    if not raw:
        raise AuthConfigError("SUPABASE_URL is not set")
    parsed = urlparse(raw)
    secure = parsed.scheme == "https" or (
        parsed.scheme == "http" and parsed.hostname in _LOCAL_HOSTS
    )
    if not secure or not parsed.hostname or parsed.query or parsed.fragment:
        raise AuthConfigError("SUPABASE_URL must be an https URL")
    issuer = f"{raw}/auth/v1"
    return AuthConfig(issuer=issuer, jwks_url=f"{issuer}/.well-known/jwks.json")


async def _http_fetch(url: str) -> Any:
    async with httpx.AsyncClient(
        timeout=FETCH_TIMEOUT_SECONDS, follow_redirects=False
    ) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()


class JwksCache:
    """The project's public signing keys, downloaded lazily and kept in memory.

    Keys are reloaded after `JWKS_TTL_SECONDS` and also when a token names a `kid` we don't
    know (Supabase rotated its keys). Reloads are rate-limited to one per
    `MIN_REFETCH_INTERVAL_SECONDS`, otherwise anyone could make the API hammer Supabase by
    sending tokens with random key ids.
    """

    def __init__(
        self,
        url: str,
        fetch: Callable[[str], Awaitable[Any]] = _http_fetch,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        """`fetch` and `clock` are injectable so tests need neither network nor sleeping."""
        self.url = url
        self._fetch = fetch
        self._clock = clock
        self._keys: dict[str, PyJWK] = {}
        self._fetched_at: float | None = None
        self._last_attempt: float | None = None
        self._lock = asyncio.Lock()

    async def get_key(self, kid: str) -> PyJWK:
        """Return the signing key for `kid`.

        Raises `TokenError("unknown_kid")` if the keys were loaded recently and `kid` is not
        among them, and `AuthUnavailableError` if the keys are stale and cannot be reloaded.
        Stale keys are never used: failing closed beats trusting a revoked key.
        """
        async with self._lock:
            now = self._clock()
            fresh = (
                self._fetched_at is not None
                and now - self._fetched_at < JWKS_TTL_SECONDS
            )
            key = self._keys.get(kid)
            if key is not None and fresh:
                return key
            throttled = (
                self._last_attempt is not None
                and now - self._last_attempt < MIN_REFETCH_INTERVAL_SECONDS
            )
            if throttled:
                if fresh:
                    raise TokenError("unknown_kid")
                raise AuthUnavailableError("signing keys are stale")
            self._last_attempt = now
            await self._refresh(now)
            key = self._keys.get(kid)
            if key is None:
                raise TokenError("unknown_kid")
            return key

    async def _refresh(self, now: float) -> None:
        try:
            document = await self._fetch(self.url)
            if not isinstance(document, dict):
                raise ValueError("JWKS document is not an object")
            key_set = PyJWKSet.from_dict(document)
        except (httpx.HTTPError, ValueError, jwt.PyJWTError) as exc:
            logger.error("Could not load the signing keys: %s", type(exc).__name__)
            raise AuthUnavailableError("signing keys unavailable") from exc
        self._keys = {
            k.key_id: k
            for k in key_set.keys
            if k.key_id and k.algorithm_name in ALLOWED_ALGORITHMS
        }
        self._fetched_at = now


_cache: JwksCache | None = None


def get_jwks_cache(url: str) -> JwksCache:
    """The process-wide key cache for `url` (recreated if the URL changes)."""
    global _cache
    if _cache is None or _cache.url != url:
        _cache = JwksCache(url)
    return _cache


async def verify_token(token: str, config: AuthConfig, cache: JwksCache) -> UUID:
    """Check `token` and return the user id (`sub`) it was issued for.

    Accepts only `ALLOWED_ALGORITHMS`, requires a `kid`, verifies the signature, `iss` and
    `aud == "authenticated"`, enforces `exp` (and `nbf` when present) with a small clock
    skew, and requires `sub` to be a UUID. Raises `TokenError` (fixed `reason`) when rejected
    and `AuthUnavailableError` when the signing keys cannot be loaded.
    """
    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError as exc:
        raise TokenError("malformed") from exc
    alg = header.get("alg")
    if alg not in ALLOWED_ALGORITHMS:
        raise TokenError("disallowed_alg")
    kid = header.get("kid")
    if not isinstance(kid, str) or not kid:
        raise TokenError("missing_kid")
    key = await cache.get_key(kid)
    try:
        claims = jwt.decode(
            token,
            key,
            algorithms=[alg],
            audience=AUDIENCE,
            issuer=config.issuer,
            leeway=LEEWAY_SECONDS,
            options={"require": ["exp", "sub", "aud", "iss"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("expired") from exc
    except jwt.ImmatureSignatureError as exc:
        raise TokenError("not_yet_valid") from exc
    except jwt.InvalidAudienceError as exc:
        raise TokenError("wrong_audience") from exc
    except jwt.InvalidIssuerError as exc:
        raise TokenError("wrong_issuer") from exc
    except jwt.InvalidSignatureError as exc:
        raise TokenError("bad_signature") from exc
    except jwt.PyJWTError as exc:
        raise TokenError("invalid") from exc
    try:
        return UUID(str(claims["sub"]))
    except ValueError as exc:
        raise TokenError("bad_subject") from exc
