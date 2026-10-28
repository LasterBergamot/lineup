"""Tests for lineup/security: headers, body size cap, rate limiting and the startup checks (#96)."""

import logging
import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from starlette.requests import Request

from app import app
from lineup.security import rate_limit
from lineup.security.body_limit import (
    DEFAULT_MAX_BODY_BYTES,
    BodySizeLimitMiddleware,
    read_max_body_bytes,
)
from lineup.security.config import read_docs_enabled, validate_production_config
from lineup.security.headers import SECURITY_HEADERS, SecurityHeadersMiddleware
from lineup.security.rate_limit import (
    LIMITERS,
    SlidingWindowLimiter,
    client_ip,
    ip_rate_limit,
    read_client_ip_header,
    read_rate_limit,
)


@pytest.fixture(autouse=True)
def mock_pdf_converter():
    with patch(
        "lineup.document.pdf_converter.PdfConverter.convert",
        return_value=b"%PDF-1.4 fake",
    ):
        yield


# ── security headers ────────────────────────────────────────────────────────


def _assert_security_headers(response):
    for name, value in SECURITY_HEADERS.items():
        assert response.headers[name] == value


def test_security_header_values():
    assert SECURITY_HEADERS["X-Content-Type-Options"] == "nosniff"
    assert SECURITY_HEADERS["Referrer-Policy"] == "no-referrer"
    assert SECURITY_HEADERS["X-Frame-Options"] == "DENY"
    assert SECURITY_HEADERS["Content-Security-Policy"] == "frame-ancestors 'none'"
    assert SECURITY_HEADERS["Cache-Control"] == "no-store"
    assert SECURITY_HEADERS["Strict-Transport-Security"].startswith("max-age=")


def test_headers_on_a_success_response(client):
    _assert_security_headers(client.get("/health"))


def test_headers_on_error_responses(client):
    _assert_security_headers(client.get("/no-such-route"))  # 404
    _assert_security_headers(client.post("/lineups", json={}))  # 422


def test_headers_on_a_401():
    response = TestClient(app).get("/teams")
    assert response.status_code == 401
    _assert_security_headers(response)


def test_no_store_on_the_generated_file(client, valid_payload):
    response = client.post("/lineups?format=docx", json=valid_payload)
    assert response.status_code == 200
    _assert_security_headers(response)
    assert response.headers["cache-control"] == "no-store"


async def test_no_store_on_personal_data_responses(async_client: AsyncClient):
    created = await async_client.post("/teams", json={"name": "SZVTK"})
    assert created.headers["cache-control"] == "no-store"
    listing = await async_client.get("/teams")
    assert listing.headers["cache-control"] == "no-store"


def test_headers_replace_a_value_set_by_the_route():
    sent = []

    async def downstream(scope, receive, send):
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"cache-control", b"public, max-age=60")],
            }
        )
        await send({"type": "http.response.body", "body": b"x"})

    async def send(message):
        sent.append(message)

    import asyncio

    asyncio.run(
        SecurityHeadersMiddleware(downstream)(
            {"type": "http", "headers": []}, None, send
        )
    )
    start_headers = [(k, v) for k, v in sent[0]["headers"] if k == b"cache-control"]
    assert start_headers == [(b"cache-control", b"no-store")]
    assert sent[1]["body"] == b"x"


@pytest.mark.parametrize(
    "middleware", [SecurityHeadersMiddleware, BodySizeLimitMiddleware]
)
def test_non_http_scopes_pass_through(middleware):
    import asyncio

    seen = []

    async def downstream(scope, receive, send):
        seen.append(scope["type"])

    asyncio.run(middleware(downstream)({"type": "lifespan"}, None, None))
    assert seen == ["lifespan"]


# ── body size cap ───────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("raw", "expected"),
    [(None, DEFAULT_MAX_BODY_BYTES), ("", DEFAULT_MAX_BODY_BYTES), ("1024", 1024)],
)
def test_read_max_body_bytes(raw, expected):
    assert read_max_body_bytes(raw) == expected


@pytest.mark.parametrize("raw", ["0", "-5", "lots", "1.5"])
def test_read_max_body_bytes_refuses_bad_values(raw):
    with pytest.raises(ValueError, match="MAX_BODY_BYTES"):
        read_max_body_bytes(raw)


def test_default_cap_is_256_kib():
    assert DEFAULT_MAX_BODY_BYTES == 256 * 1024


def test_oversized_declared_body_is_413(client, valid_payload):
    valid_payload["match"] = "x" * (DEFAULT_MAX_BODY_BYTES + 1)
    response = client.post("/lineups?format=docx", json=valid_payload)
    assert response.status_code == 413
    assert response.json() == {"detail": "Request body too large"}
    _assert_security_headers(response)


def test_oversized_streamed_body_is_413(client):
    def chunks():
        for _ in range(DEFAULT_MAX_BODY_BYTES // 1024 + 2):
            yield b"x" * 1024

    # A generator is sent chunked, without a Content-Length header.
    response = client.post(
        "/lineups?format=docx",
        content=chunks(),
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 413
    assert response.json() == {"detail": "Request body too large"}


def test_streamed_body_under_the_cap_is_processed(client, valid_payload):
    import json

    body = json.dumps(valid_payload).encode()

    def chunks():
        yield body[:100]
        yield body[100:]

    response = client.post(
        "/lineups?format=docx",
        content=chunks(),
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 200


def test_body_exactly_at_the_cap_is_allowed(client):
    response = client.post(
        "/lineups?format=docx",
        content=b"x" * DEFAULT_MAX_BODY_BYTES,
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422  # not JSON, but it got past the size check


def test_unparsable_content_length_is_left_to_the_server(client, valid_payload):
    response = client.post(
        "/lineups?format=docx",
        json=valid_payload,
        headers={"Content-Length": "not-a-number"},
    )
    assert response.status_code != 413


def test_413_is_documented_in_openapi():
    spec = app.openapi()
    assert "413" in spec["paths"]["/lineups"]["post"]["responses"]
    assert "413" in spec["paths"]["/lineups/saved"]["post"]["responses"]


# ── sliding-window limiter ──────────────────────────────────────────────────


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def test_limiter_allows_up_to_the_limit_then_reports_retry_after():
    clock = FakeClock()
    limiter = SlidingWindowLimiter(2, 60, clock)
    assert limiter.hit("a") is None
    clock.now += 10
    assert limiter.hit("a") is None
    clock.now += 10
    assert limiter.hit("a") == pytest.approx(40)  # oldest hit leaves after 60 s
    assert limiter.hit("b") is None  # other keys are independent


def test_limiter_window_slides_instead_of_resetting():
    clock = FakeClock()
    limiter = SlidingWindowLimiter(2, 60, clock)
    limiter.hit("a")  # t=0
    clock.now += 30
    limiter.hit("a")  # t=30
    clock.now += 31  # t=61: the first hit expired, the second has not
    assert limiter.hit("a") is None
    assert limiter.hit("a") == pytest.approx(29)


def test_rejected_requests_are_not_counted():
    clock = FakeClock()
    limiter = SlidingWindowLimiter(1, 60, clock)
    limiter.hit("a")
    for _ in range(5):
        clock.now += 1
        assert limiter.hit("a") is not None
    clock.now = 1060.0  # exactly one window after the single counted hit
    assert limiter.hit("a") is None


def test_limiter_forgets_idle_keys():
    clock = FakeClock()
    limiter = SlidingWindowLimiter(5, 60, clock)
    for i in range(50):
        limiter.hit(f"ip-{i}")
    clock.now += 61
    limiter.hit("fresh")
    assert set(limiter._hits) == {"fresh"}


def test_limiter_keeps_active_keys_when_sweeping():
    clock = FakeClock()
    limiter = SlidingWindowLimiter(5, 60, clock)
    limiter.hit("busy")
    clock.now += 40
    limiter.hit("busy")
    clock.now += 21  # sweep runs: "busy" still has a hit inside the window
    limiter.hit("other")
    assert set(limiter._hits) == {"busy", "other"}


def test_reset_clears_the_counters():
    limiter = SlidingWindowLimiter(1, 60)
    limiter.hit("a")
    limiter.reset()
    assert limiter.hit("a") is None


# ── env parsing ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("raw", "expected"), [(None, 7), ("", 7), ("3", 3), (" 12 ", 12)]
)
def test_read_rate_limit(raw, expected):
    assert read_rate_limit("RATE_LIMIT_X", raw, 7) == expected


@pytest.mark.parametrize("raw", ["0", "-1", "ten", "2.5"])
def test_read_rate_limit_refuses_bad_values_without_echoing_them(raw):
    with pytest.raises(ValueError, match="RATE_LIMIT_X") as exc:
        read_rate_limit("RATE_LIMIT_X", raw, 7)
    assert raw not in str(exc.value) or raw == "0"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [(None, None), ("", None), ("   ", None), (" Fly-Client-IP ", "Fly-Client-IP")],
)
def test_read_client_ip_header(raw, expected):
    assert read_client_ip_header(raw) == expected


def test_default_limits():
    assert rate_limit.DEFAULT_GENERATE_PER_IP == 30
    assert rate_limit.DEFAULT_GENERATE_PER_USER == 10
    assert rate_limit.RATE_LIMIT_WINDOW_SECONDS == 60


# ── client ip ───────────────────────────────────────────────────────────────


def _request(headers=None, client=("203.0.113.9", 1234)):
    return Request(
        {
            "type": "http",
            "headers": [
                (k.lower().encode(), v.encode()) for k, v in (headers or {}).items()
            ],
            "client": client,
        }
    )


def test_client_ip_is_the_socket_peer_by_default(monkeypatch):
    monkeypatch.setattr(rate_limit, "CLIENT_IP_HEADER", None)
    assert client_ip(_request({"Fly-Client-IP": "1.2.3.4"})) == "203.0.113.9"


def test_client_ip_uses_the_configured_header(monkeypatch):
    monkeypatch.setattr(rate_limit, "CLIENT_IP_HEADER", "Fly-Client-IP")
    assert client_ip(_request({"Fly-Client-IP": " 1.2.3.4 "})) == "1.2.3.4"


def test_client_ip_falls_back_when_the_header_is_missing_or_blank(monkeypatch):
    monkeypatch.setattr(rate_limit, "CLIENT_IP_HEADER", "Fly-Client-IP")
    assert client_ip(_request()) == "203.0.113.9"
    assert client_ip(_request({"Fly-Client-IP": "  "})) == "203.0.113.9"


def test_client_ip_without_any_peer(monkeypatch):
    monkeypatch.setattr(rate_limit, "CLIENT_IP_HEADER", None)
    assert client_ip(_request(client=None)) == "unknown"


def test_client_ip_header_value_is_length_capped(monkeypatch):
    monkeypatch.setattr(rate_limit, "CLIENT_IP_HEADER", "Fly-Client-IP")
    assert len(client_ip(_request({"Fly-Client-IP": "9" * 5000}))) == 100


def test_a_limiter_name_can_only_be_registered_once():
    with pytest.raises(ValueError, match="already registered"):
        ip_rate_limit("generate:ip", 5)


# ── 429 on the generate endpoints ───────────────────────────────────────────


@pytest.fixture
def tight_limits(monkeypatch):
    monkeypatch.setattr(LIMITERS["generate:user"], "limit", 2)
    monkeypatch.setattr(LIMITERS["generate:ip"], "limit", 50)


def test_exceeding_the_user_limit_on_post_lineups_is_429(
    client, valid_payload, tight_limits, caplog
):
    for _ in range(2):
        assert client.post("/lineups?format=pdf", json=valid_payload).status_code == 200
    with caplog.at_level(logging.DEBUG):
        response = client.post("/lineups?format=pdf", json=valid_payload)
    assert response.status_code == 429
    assert response.json() == {"detail": "Too many requests, try again later"}
    assert 1 <= int(response.headers["retry-after"]) <= 60
    _assert_security_headers(response)
    assert "testclient" not in caplog.text  # the client address is never logged


def test_the_user_limit_is_per_user(client, current_user, valid_payload, tight_limits):
    for _ in range(2):
        client.post("/lineups?format=docx", json=valid_payload)
    assert client.post("/lineups?format=docx", json=valid_payload).status_code == 429
    current_user.id = uuid.uuid4()
    assert client.post("/lineups?format=docx", json=valid_payload).status_code == 200


def test_the_ip_limit_applies_across_users(
    client, current_user, valid_payload, monkeypatch
):
    monkeypatch.setattr(LIMITERS["generate:ip"], "limit", 2)
    for _ in range(2):
        current_user.id = uuid.uuid4()
        assert (
            client.post("/lineups?format=docx", json=valid_payload).status_code == 200
        )
    current_user.id = uuid.uuid4()
    assert client.post("/lineups?format=docx", json=valid_payload).status_code == 429


def test_the_ip_limit_separates_clients_by_the_configured_header(
    client, current_user, valid_payload, monkeypatch
):
    monkeypatch.setattr(rate_limit, "CLIENT_IP_HEADER", "Fly-Client-IP")
    monkeypatch.setattr(LIMITERS["generate:ip"], "limit", 1)

    def post(ip):
        current_user.id = uuid.uuid4()
        return client.post(
            "/lineups?format=docx", json=valid_payload, headers={"Fly-Client-IP": ip}
        ).status_code

    assert post("198.51.100.1") == 200
    assert post("198.51.100.1") == 429
    assert post("198.51.100.2") == 200


def test_the_ip_limit_also_throttles_unauthenticated_requests(monkeypatch):
    monkeypatch.setattr(LIMITERS["generate:ip"], "limit", 2)
    anonymous = TestClient(app)
    assert anonymous.post("/lineups").status_code == 401
    assert anonymous.post("/lineups").status_code == 401
    assert anonymous.post("/lineups").status_code == 429


def test_post_lineups_requires_sign_in(valid_payload):
    response = TestClient(app).post("/lineups?format=docx", json=valid_payload)
    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}


async def test_the_saved_lineup_generate_endpoint_is_limited_too(
    async_client: AsyncClient, tight_limits
):
    missing = "00000000-0000-0000-0000-000000000000"
    assert (
        await async_client.post(f"/lineups/saved/{missing}/generate")
    ).status_code == 404
    assert (
        await async_client.post(f"/lineups/saved/{missing}/generate")
    ).status_code == 404
    response = await async_client.post(f"/lineups/saved/{missing}/generate")
    assert response.status_code == 429
    assert "retry-after" in response.headers


async def test_both_generate_endpoints_share_the_limit(
    async_client: AsyncClient, valid_payload, tight_limits
):
    missing = "00000000-0000-0000-0000-000000000000"
    await async_client.post("/lineups?format=docx", json=valid_payload)
    await async_client.post(f"/lineups/saved/{missing}/generate")
    response = await async_client.post(f"/lineups/saved/{missing}/generate")
    assert response.status_code == 429


def test_rate_limited_responses_are_documented_in_openapi():
    paths = app.openapi()["paths"]
    assert "429" in paths["/lineups"]["post"]["responses"]
    assert "401" in paths["/lineups"]["post"]["responses"]
    assert "429" in paths["/lineups/saved/{lineup_id}/generate"]["post"]["responses"]


# ── docs exposure ───────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("raw", "env", "expected"),
    [
        (None, None, True),
        ("", None, True),
        ("true", "development", True),
        (" TRUE ", None, True),
        ("1", None, True),
        ("yes", None, True),
        ("false", None, False),
        ("0", None, False),
        ("No", None, False),
        ("off", None, False),
        (None, "production", False),
        ("true", "production", False),  # production forces the docs off
    ],
)
def test_read_docs_enabled(raw, env, expected):
    assert read_docs_enabled(raw, env) is expected


def test_read_docs_enabled_refuses_garbage():
    with pytest.raises(ValueError, match="DOCS_ENABLED"):
        read_docs_enabled("maybe", None)


# ── fail-closed production config ───────────────────────────────────────────

GOOD_URL = "postgresql+asyncpg://user:pw@host.example:6543/postgres?ssl=require"
GOOD_ENV = {
    "ENV": "production",
    "DATABASE_URL": GOOD_URL,
    "SUPABASE_URL": "https://abc.supabase.co",
}


def test_validation_is_skipped_outside_production():
    validate_production_config({})
    validate_production_config({"ENV": "development"})


def test_validation_reads_the_process_environment_by_default(monkeypatch):
    monkeypatch.setenv("ENV", "production")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    with pytest.raises(ValueError, match="DATABASE_URL is not set"):
        validate_production_config()


def test_a_complete_production_config_passes(caplog):
    with caplog.at_level(logging.WARNING):
        validate_production_config(GOOD_ENV)
    assert "verify-full" in caplog.text  # ssl=require is accepted with a warning
    assert "pw" not in caplog.text


@pytest.mark.parametrize(
    "url",
    [
        "postgresql+asyncpg://u:p@h:5432/db?ssl=verify-full",
        "postgresql+asyncpg://u:p@h:5432/db?sslmode=verify-full",
        "postgresql+asyncpg://u:p@h:5432/db?sslmode=require",
    ],
)
def test_accepted_tls_settings(url):
    validate_production_config({**GOOD_ENV, "DATABASE_URL": url})


def test_verify_full_does_not_warn(caplog):
    url = "postgresql+asyncpg://u:p@h:5432/db?ssl=verify-full"
    with caplog.at_level(logging.WARNING):
        validate_production_config({**GOOD_ENV, "DATABASE_URL": url})
    assert caplog.text == ""


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"DATABASE_URL": ""}, "DATABASE_URL is not set"),
        (
            {"DATABASE_URL": "sqlite+aiosqlite:///./lineup.db"},
            "postgresql+asyncpg driver",
        ),
        (
            {"DATABASE_URL": "postgresql://u:p@h/db?ssl=require"},
            "postgresql+asyncpg driver",
        ),
        (
            {"DATABASE_URL": "postgresql+asyncpg://u:p@h/db"},
            "ssl=require or ssl=verify-full",
        ),
        ({"DATABASE_URL": "postgresql+asyncpg://u:p@h/db?ssl=disable"}, "ssl=require"),
        ({"DATABASE_URL": "postgresql+asyncpg://u:p@h/db?ssl=prefer"}, "ssl=require"),
        ({"DATABASE_URL": "not a url"}, "not a valid database URL"),
        ({"SUPABASE_URL": ""}, "SUPABASE_URL is not set"),
    ],
)
def test_insecure_production_config_is_refused(overrides, message):
    with pytest.raises(ValueError, match="Refusing to start") as exc:
        validate_production_config({**GOOD_ENV, **overrides})
    assert message in str(exc.value)


def test_all_problems_are_reported_together_without_leaking_the_url():
    env = {
        "ENV": "production",
        "DATABASE_URL": "mysql://u:hunter2@h/db",
    }
    with pytest.raises(ValueError) as exc:
        validate_production_config(env)
    message = str(exc.value)
    assert "postgresql+asyncpg driver" in message
    assert "ssl=require" in message
    assert "SUPABASE_URL is not set" in message
    assert "hunter2" not in message
