"""Tests for lineup/auth: token verification, the JWKS cache and the FastAPI dependency.

No network: signing keys are generated here and served to the cache through an injected fetch
function, and `httpx` is given a mock transport for the one test of the real fetcher.
"""

import json
import logging
import time
import uuid

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient
from jwt.algorithms import ECAlgorithm, RSAAlgorithm

from app import app
from lineup.auth import tokens
from lineup.auth.dependencies import get_current_user_id
from lineup.auth.tokens import (
    AuthConfigError,
    AuthUnavailableError,
    JwksCache,
    TokenError,
    load_config,
    verify_token,
)

PROJECT_URL = "https://abcdefgh.supabase.co"
ISSUER = f"{PROJECT_URL}/auth/v1"
JWKS_URL = f"{ISSUER}/.well-known/jwks.json"
USER_ID = uuid.UUID("11111111-2222-4333-8444-555555555555")


class SigningKey:
    """A generated key pair plus its public JWK, like one entry of Supabase's JWKS."""

    def __init__(self, kid: str, alg: str = "ES256") -> None:
        self.kid = kid
        self.alg = alg
        if alg == "ES256":
            self.private = ec.generate_private_key(ec.SECP256R1())
            jwk = json.loads(ECAlgorithm.to_jwk(self.private.public_key()))
        else:
            self.private = rsa.generate_private_key(
                public_exponent=65537, key_size=2048
            )
            jwk = json.loads(RSAAlgorithm.to_jwk(self.private.public_key()))
        self.jwk = {**jwk, "kid": kid, "alg": alg, "use": "sig"}

    def token(self, headers: dict | None = None, **claims) -> str:
        now = int(time.time())
        payload = {
            "sub": str(USER_ID),
            "aud": "authenticated",
            "iss": ISSUER,
            "exp": now + 3600,
            "iat": now,
            **claims,
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        return jwt.encode(
            payload,
            self.private,
            algorithm=self.alg,
            headers={"kid": self.kid, **(headers or {})},
        )


@pytest.fixture
def key() -> SigningKey:
    return SigningKey("key-1")


@pytest.fixture
def config() -> tokens.AuthConfig:
    return tokens.AuthConfig(issuer=ISSUER, jwks_url=JWKS_URL)


def cache_for(*keys: SigningKey, clock=time.monotonic) -> JwksCache:
    async def fetch(url: str):
        assert url == JWKS_URL
        return {"keys": [k.jwk for k in keys]}

    return JwksCache(JWKS_URL, fetch=fetch, clock=clock)


@pytest.fixture(autouse=True)
def _reset_module_cache(monkeypatch):
    monkeypatch.setattr(tokens, "_cache", None)
    monkeypatch.delenv("SUPABASE_URL", raising=False)


# ── verify_token ────────────────────────────────────────────────────────────


@pytest.mark.parametrize("alg", ["ES256", "RS256"])
async def test_valid_token_returns_the_subject(alg, config):
    signing_key = SigningKey("k", alg)
    assert (
        await verify_token(signing_key.token(), config, cache_for(signing_key))
        == USER_ID
    )


@pytest.mark.parametrize(
    ("claims", "reason"),
    [
        ({"exp": 1}, "expired"),
        ({"nbf": int(time.time()) + 3600}, "not_yet_valid"),
        ({"aud": "anon"}, "wrong_audience"),
        ({"aud": None}, "invalid"),
        ({"iss": "https://evil.example/auth/v1"}, "wrong_issuer"),
        ({"iss": None}, "invalid"),
        ({"sub": None}, "invalid"),
        ({"exp": None}, "invalid"),
        ({"sub": "not-a-uuid"}, "bad_subject"),
    ],
)
async def test_rejected_claims(claims, reason, key, config):
    with pytest.raises(TokenError) as exc:
        await verify_token(key.token(**claims), config, cache_for(key))
    assert exc.value.reason == reason


async def test_clock_skew_within_leeway_is_tolerated(key, config):
    almost_expired = key.token(exp=int(time.time()) - 5)
    assert await verify_token(almost_expired, config, cache_for(key)) == USER_ID


async def test_signature_from_another_key_is_rejected(key, config):
    impostor = SigningKey("key-1")  # same kid, different key material
    with pytest.raises(TokenError) as exc:
        await verify_token(impostor.token(), config, cache_for(key))
    assert exc.value.reason == "bad_signature"


async def test_token_alg_must_match_the_key_type(config):
    rsa_key = SigningKey("k", "RS256")
    ec_key = SigningKey("k", "ES256")
    token = rsa_key.token()
    with pytest.raises(TokenError) as exc:
        await verify_token(token, config, cache_for(ec_key))
    assert exc.value.reason == "invalid"


async def test_symmetric_and_none_algorithms_are_refused(key, config):
    cache = cache_for(key)
    # Algorithm confusion: an HS256 token "signed" with the public key as the secret
    hs256 = jwt.encode(
        {"sub": str(USER_ID), "aud": "authenticated", "iss": ISSUER, "exp": 2**31},
        "x" * 64,
        algorithm="HS256",
        headers={"kid": key.kid},
    )
    unsigned = jwt.encode(
        {"sub": str(USER_ID), "aud": "authenticated", "iss": ISSUER, "exp": 2**31},
        None,
        algorithm="none",
        headers={"kid": key.kid},
    )
    for bad in (hs256, unsigned):
        with pytest.raises(TokenError) as exc:
            await verify_token(bad, config, cache)
        assert exc.value.reason == "disallowed_alg"


@pytest.mark.parametrize("garbage", ["", "abc", "a.b.c", "....", "é"])
async def test_malformed_tokens(garbage, config, key):
    with pytest.raises(TokenError) as exc:
        await verify_token(garbage, config, cache_for(key))
    assert exc.value.reason == "malformed"


async def test_token_without_kid_is_rejected(key, config):
    token = jwt.encode(
        {"sub": str(USER_ID), "aud": "authenticated", "iss": ISSUER, "exp": 2**31},
        key.private,
        algorithm="ES256",
    )
    with pytest.raises(TokenError) as exc:
        await verify_token(token, config, cache_for(key))
    assert exc.value.reason == "missing_kid"


async def test_unknown_kid_is_rejected(key, config):
    stranger = SigningKey("other")
    with pytest.raises(TokenError) as exc:
        await verify_token(stranger.token(), config, cache_for(key))
    assert exc.value.reason == "unknown_kid"


# ── JwksCache ───────────────────────────────────────────────────────────────


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


async def test_cache_fetches_once_and_reuses_keys(key):
    calls = []

    async def fetch(url):
        calls.append(url)
        return {"keys": [key.jwk]}

    cache = JwksCache(JWKS_URL, fetch=fetch, clock=Clock())
    assert (await cache.get_key("key-1")).key_id == "key-1"
    assert (await cache.get_key("key-1")).key_id == "key-1"
    assert calls == [JWKS_URL]


async def test_cache_refetches_for_an_unknown_kid_after_the_cooldown():
    old, new = SigningKey("old"), SigningKey("new")
    served = [old]
    clock = Clock()

    async def fetch(url):
        return {"keys": [k.jwk for k in served]}

    cache = JwksCache(JWKS_URL, fetch=fetch, clock=clock)
    await cache.get_key("old")
    served[:] = [old, new]  # Supabase rotated keys

    with pytest.raises(TokenError):  # too soon: no refetch, so still unknown
        await cache.get_key("new")
    clock.now += tokens.MIN_REFETCH_INTERVAL_SECONDS
    assert (await cache.get_key("new")).key_id == "new"


async def test_random_kids_cannot_make_the_cache_hammer_supabase(key):
    calls = []
    clock = Clock()

    async def fetch(url):
        calls.append(1)
        return {"keys": [key.jwk]}

    cache = JwksCache(JWKS_URL, fetch=fetch, clock=clock)
    for i in range(20):
        with pytest.raises(TokenError):
            await cache.get_key(f"random-{i}")
    assert len(calls) == 1


async def test_keys_expire_after_the_ttl(key):
    calls = []
    clock = Clock()

    async def fetch(url):
        calls.append(1)
        return {"keys": [key.jwk]}

    cache = JwksCache(JWKS_URL, fetch=fetch, clock=clock)
    await cache.get_key("key-1")
    clock.now += tokens.JWKS_TTL_SECONDS
    await cache.get_key("key-1")
    assert len(calls) == 2


async def test_stale_keys_are_not_used_when_the_refetch_fails(key):
    clock = Clock()
    failing = False

    async def fetch(url):
        if failing:
            raise httpx.ConnectError("down")
        return {"keys": [key.jwk]}

    cache = JwksCache(JWKS_URL, fetch=fetch, clock=clock)
    await cache.get_key("key-1")
    clock.now += tokens.JWKS_TTL_SECONDS
    failing = True
    with pytest.raises(AuthUnavailableError):
        await cache.get_key("key-1")
    # Still inside the cool-down: no new fetch, and still not trusting the stale key
    with pytest.raises(AuthUnavailableError):
        await cache.get_key("key-1")


@pytest.mark.parametrize(
    "document",
    [{"keys": []}, {"nope": 1}, "garbage", ["keys"]],
)
async def test_unusable_jwks_documents_mean_unavailable(document):
    async def fetch(url):
        return document

    cache = JwksCache(JWKS_URL, fetch=fetch)
    with pytest.raises(AuthUnavailableError):
        await cache.get_key("key-1")


async def test_symmetric_keys_in_the_jwks_are_ignored():
    async def fetch(url):
        return {"keys": [{"kty": "oct", "k": "AAAA", "kid": "shared-secret"}]}

    cache = JwksCache(JWKS_URL, fetch=fetch)
    with pytest.raises(TokenError):
        await cache.get_key("shared-secret")


async def test_keys_without_a_kid_are_ignored(key):
    nameless = {k: v for k, v in key.jwk.items() if k != "kid"}

    async def fetch(url):
        return {"keys": [nameless]}

    cache = JwksCache(JWKS_URL, fetch=fetch)
    with pytest.raises(TokenError):
        await cache.get_key("key-1")


async def test_http_fetch_returns_the_json_document(monkeypatch, key):
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(200, json={"keys": [key.jwk]})

    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        tokens.httpx,
        "AsyncClient",
        lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **kwargs),
    )
    assert await tokens._http_fetch(JWKS_URL) == {"keys": [key.jwk]}
    assert seen == [JWKS_URL]


async def test_http_fetch_raises_on_an_error_status(monkeypatch):
    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        tokens.httpx,
        "AsyncClient",
        lambda **kwargs: real_client(
            transport=httpx.MockTransport(lambda request: httpx.Response(500)),
            **kwargs,
        ),
    )
    with pytest.raises(httpx.HTTPStatusError):
        await tokens._http_fetch(JWKS_URL)


def test_get_jwks_cache_is_shared_per_url():
    first = tokens.get_jwks_cache(JWKS_URL)
    assert tokens.get_jwks_cache(JWKS_URL) is first
    assert tokens.get_jwks_cache("https://other.supabase.co/x") is not first


# ── load_config ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "value",
    [
        PROJECT_URL,
        PROJECT_URL + "/",
        f"  {PROJECT_URL}  ",
        "http://localhost:54321",
        "http://127.0.0.1:54321",
    ],
)
def test_load_config_derives_issuer_and_jwks_url(monkeypatch, value):
    monkeypatch.setenv("SUPABASE_URL", value)
    cfg = load_config()
    assert cfg.issuer == f"{value.strip().rstrip('/')}/auth/v1"
    assert cfg.jwks_url == f"{cfg.issuer}/.well-known/jwks.json"


@pytest.mark.parametrize(
    "value",
    [
        "",
        "   ",
        "http://abcdefgh.supabase.co",
        "ftp://abcdefgh.supabase.co",
        "https://",
        "not a url",
        f"{PROJECT_URL}?x=1",
        f"{PROJECT_URL}#frag",
    ],
)
def test_load_config_rejects_missing_or_insecure_urls(monkeypatch, value):
    monkeypatch.setenv("SUPABASE_URL", value)
    with pytest.raises(AuthConfigError):
        load_config()


def test_load_config_rejects_an_unset_variable():
    with pytest.raises(AuthConfigError):
        load_config()


# ── get_current_user_id (the FastAPI dependency) ────────────────────────────


def bearer(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


@pytest.fixture
def configured(monkeypatch, key):
    """SUPABASE_URL set and the module cache pre-loaded with `key`'s public key."""
    monkeypatch.setenv("SUPABASE_URL", PROJECT_URL)
    monkeypatch.setattr(tokens, "_cache", cache_for(key))


async def test_dependency_returns_the_user_id(configured, key):
    assert await get_current_user_id(bearer(key.token())) == USER_ID


async def test_dependency_without_credentials_is_401(caplog):
    with caplog.at_level(logging.WARNING), pytest.raises(HTTPException) as exc:
        await get_current_user_id(None)
    assert exc.value.status_code == 401
    assert exc.value.detail == "Not authenticated"
    assert exc.value.headers == {"WWW-Authenticate": "Bearer"}
    assert "missing_token" in caplog.text


async def test_dependency_rejection_is_generic_and_logs_no_token(
    configured, key, caplog
):
    token = key.token(exp=1)
    with caplog.at_level(logging.WARNING), pytest.raises(HTTPException) as exc:
        await get_current_user_id(bearer(token))
    assert exc.value.status_code == 401
    assert exc.value.detail == "Not authenticated"
    assert "expired" in caplog.text
    assert token not in caplog.text


async def test_dependency_fails_closed_when_auth_is_not_configured(caplog):
    with caplog.at_level(logging.ERROR), pytest.raises(HTTPException) as exc:
        await get_current_user_id(bearer("whatever"))
    assert exc.value.status_code == 503
    assert exc.value.detail == "Authentication unavailable"
    assert "SUPABASE_URL" in caplog.text


async def test_dependency_fails_closed_when_the_keys_are_unreachable(monkeypatch, key):
    async def fetch(url):
        raise httpx.ConnectError("down")

    monkeypatch.setenv("SUPABASE_URL", PROJECT_URL)
    monkeypatch.setattr(tokens, "_cache", JwksCache(JWKS_URL, fetch=fetch))
    with pytest.raises(HTTPException) as exc:
        await get_current_user_id(bearer(key.token()))
    assert exc.value.status_code == 503


# ── every protected route really is protected ───────────────────────────────

PUBLIC_ROUTES = {
    ("GET", "/health"),
    ("POST", "/lineups"),  # stateless one-off; see Current-State-Backend.md
    ("GET", "/openapi.json"),
    ("GET", "/docs"),
    ("GET", "/docs/oauth2-redirect"),
    ("GET", "/redoc"),
}


def _protected_routes():
    for route in app.routes:
        for method in getattr(route, "methods", None) or ():
            if method in {"HEAD", "OPTIONS"} or (method, route.path) in PUBLIC_ROUTES:
                continue
            yield method, route.path


@pytest.mark.parametrize(("method", "path"), sorted(_protected_routes()))
def test_every_non_public_route_rejects_requests_without_a_token(method, path):
    concrete = path.replace("{team_id}", str(uuid.uuid4()))
    for name in ("player_id", "lineup_id"):
        concrete = concrete.replace("{" + name + "}", str(uuid.uuid4()))
    response = TestClient(app).request(method, concrete)
    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}


def test_public_routes_stay_reachable_without_a_token():
    assert TestClient(app).get("/health").status_code == 200
