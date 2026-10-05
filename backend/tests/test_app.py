import importlib
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

import app as app_module


def test_sentry_not_initialized_without_dsn(monkeypatch):
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    with patch("sentry_sdk.init") as mock_init:
        importlib.reload(app_module)
    mock_init.assert_not_called()


def test_sentry_initialized_with_dsn(monkeypatch):
    dsn = "https://public@o0.ingest.sentry.io/0"
    monkeypatch.setenv("SENTRY_DSN", dsn)
    with patch("sentry_sdk.init") as mock_init:
        importlib.reload(app_module)
    mock_init.assert_called_once_with(dsn=dsn, traces_sample_rate=0.0)


@pytest.fixture
def reload_app(monkeypatch):
    """Reloads `app` with CORS_ORIGINS set to the given value (None = unset)."""

    def _reload(cors_origins: str | None) -> TestClient:
        if cors_origins is None:
            monkeypatch.delenv("CORS_ORIGINS", raising=False)
        else:
            monkeypatch.setenv("CORS_ORIGINS", cors_origins)
        importlib.reload(app_module)
        return TestClient(app_module.app)

    return _reload


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, []),
        ("", []),
        (" , ,", []),
        ("http://localhost:5173", ["http://localhost:5173"]),
        (
            " http://localhost:5173/ , https://app.example.com ",
            ["http://localhost:5173", "https://app.example.com"],
        ),
    ],
)
def test_parse_cors_origins(raw, expected):
    assert app_module.parse_cors_origins(raw) == expected


def test_parse_cors_origins_refuses_wildcard():
    with pytest.raises(ValueError, match="explicit origins"):
        app_module.parse_cors_origins("https://a.example,*")


class TestCors:
    def test_no_cors_headers_when_origins_unset(self, reload_app):
        client = reload_app(None)
        response = client.get("/health", headers={"Origin": "http://localhost:5173"})
        assert "access-control-allow-origin" not in response.headers

    def test_allowed_origin_gets_cors_headers_and_can_read_file_name(self, reload_app):
        client = reload_app("http://localhost:5173")
        response = client.get("/health", headers={"Origin": "http://localhost:5173"})
        assert (
            response.headers["access-control-allow-origin"] == "http://localhost:5173"
        )
        assert (
            "Content-Disposition" in response.headers["access-control-expose-headers"]
        )
        assert "access-control-allow-credentials" not in response.headers

    def test_other_origin_gets_no_cors_headers(self, reload_app):
        client = reload_app("http://localhost:5173")
        response = client.get("/health", headers={"Origin": "https://evil.example"})
        assert "access-control-allow-origin" not in response.headers

    def test_preflight_from_allowed_origin_lists_only_used_methods_and_headers(
        self, reload_app
    ):
        client = reload_app("http://localhost:5173")
        response = client.options(
            "/lineups",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type,authorization",
            },
        )
        assert response.status_code == 200
        assert (
            response.headers["access-control-allow-origin"] == "http://localhost:5173"
        )
        methods = response.headers["access-control-allow-methods"]
        assert set(methods.split(", ")) == {"GET", "POST", "PUT", "DELETE"}

    def test_preflight_from_other_origin_is_rejected(self, reload_app):
        client = reload_app("http://localhost:5173")
        response = client.options(
            "/lineups",
            headers={
                "Origin": "https://evil.example",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert response.status_code == 400
        assert "access-control-allow-origin" not in response.headers

    def test_preflight_with_unexpected_header_is_rejected(self, reload_app):
        client = reload_app("http://localhost:5173")
        response = client.options(
            "/lineups",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "x-custom",
            },
        )
        assert response.status_code == 400


def teardown_module(module):
    import os

    os.environ.pop("SENTRY_DSN", None)
    os.environ.pop("CORS_ORIGINS", None)
    with patch("sentry_sdk.init"):
        importlib.reload(app_module)
